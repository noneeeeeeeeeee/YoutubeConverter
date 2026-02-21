/// Download service for managing YouTube downloads
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:uuid/uuid.dart';
import '../models/download_item.dart';
import '../models/video_info.dart';
import '../models/app_settings.dart';
import 'log_service.dart';

/// Download service for managing YouTube downloads
class DownloadService extends ChangeNotifier {
  final LogService _log = LogService();
  final Map<String, DownloadItem> _downloads = {};
  final Map<String, Process?> _processes = {};
  final Map<String, StreamSubscription> _subscriptions = {};

  String? _ytDlpPath;
  String? _ffmpegPath;

  List<DownloadItem> get downloads => _downloads.values.toList();
  List<DownloadItem> get activeDownloads =>
      _downloads.values.where((d) => d.state.isActive).toList();
  List<DownloadItem> get completedDownloads =>
      _downloads.values.where((d) => d.state.isComplete).toList();

  /// Initialize the download service
  Future<void> initialize() async {
    await _findDependencies();
  }

  /// Find yt-dlp and ffmpeg executables
  Future<void> _findDependencies() async {
    // Look for yt-dlp
    final possibleYtDlpPaths = [
      'yt-dlp',
      'yt-dlp.exe',
      if (Platform.isWindows)
        '${Platform.environment['APPDATA']}\\YoutubeConverter\\yt-dlp.exe',
    ];

    for (final path in possibleYtDlpPaths) {
      if (await _checkExecutable(path)) {
        _ytDlpPath = path;
        _log.info('Found yt-dlp at: $path', source: 'DownloadService');
        break;
      }
    }

    // Look for ffmpeg
    final possibleFfmpegPaths = [
      'ffmpeg',
      'ffmpeg.exe',
      if (Platform.isWindows)
        '${Platform.environment['APPDATA']}\\YoutubeConverter\\ffmpeg\\ffmpeg.exe',
    ];

    for (final path in possibleFfmpegPaths) {
      if (await _checkExecutable(path)) {
        _ffmpegPath = path;
        _log.info('Found ffmpeg at: $path', source: 'DownloadService');
        break;
      }
    }
  }

  /// Check if an executable exists
  Future<bool> _checkExecutable(String path) async {
    try {
      if (Platform.isWindows) {
        // On Windows, check if it's in PATH or a direct path
        if (path.contains('\\') || path.contains('/')) {
          return File(path).exists();
        } else {
          final result = await Process.run('where', [path]);
          return result.exitCode == 0;
        }
      } else {
        // On Unix-like systems
        if (path.contains('/')) {
          return File(path).exists();
        } else {
          final result = await Process.run('which', [path]);
          return result.exitCode == 0;
        }
      }
    } catch (e) {
      return false;
    }
  }

  /// Check if dependencies are ready
  bool get isReady => _ytDlpPath != null;
  bool get ffmpegReady => _ffmpegPath != null;

  /// Fetch video info from a URL
  Future<VideoInfo?> fetchVideoInfo(String url) async {
    if (_ytDlpPath == null) {
      _log.error('yt-dlp not found', source: 'DownloadService');
      return null;
    }

    try {
      final result = await Process.run(
        _ytDlpPath!,
        ['--dump-json', '--no-download', url],
      );

      if (result.exitCode != 0) {
        _log.error('Failed to fetch video info: ${result.stderr}',
            source: 'DownloadService');
        return null;
      }

      final json = jsonDecode(result.stdout) as Map<String, dynamic>;
      return VideoInfo.fromJson(json);
    } catch (e) {
      _log.error('Error fetching video info',
          source: 'DownloadService', error: e);
      return null;
    }
  }

  /// Start a download
  Future<DownloadItem?> startDownload({
    required String url,
    required String format,
    required String outputPath,
    String? quality,
    bool audioOnly = false,
    bool videoOnly = false,
    AppSettings? settings,
  }) async {
    if (_ytDlpPath == null) {
      _log.error('yt-dlp not found', source: 'DownloadService');
      return null;
    }

    final id = const Uuid().v4();
    final item = DownloadItem(
      id: id,
      sourceUrl: url,
      normalizedUrl: url,
      targetFormat: format,
      outputPath: outputPath,
      createdAt: DateTime.now(),
    );

    _downloads[id] = item;
    notifyListeners();

    // Build yt-dlp arguments
    final args = <String>[
      '--newline', // Output progress on new lines
      '--progress',
      '--progress-template',
      '%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s',
      '-o', '$outputPath/%(title)s.%(ext)s',
    ];

    // Format selection
    if (audioOnly) {
      args.addAll(['-x', '--audio-format', format]);
      if (quality != null && quality != 'best') {
        args.addAll(['--audio-quality', quality]);
      }
    } else if (videoOnly) {
      args.addAll([
        '--format',
        'bestvideo[ext=$format]+bestaudio/best[ext=$format]/best'
      ]);
    } else {
      if (quality != null && quality != 'best') {
        args.addAll(['-f', 'best[height<=$quality]']);
      }
    }

    // Add ffmpeg path if available
    if (_ffmpegPath != null) {
      final ffmpegDir = _ffmpegPath!
          .substring(0, _ffmpegPath!.lastIndexOf(Platform.pathSeparator));
      args.addAll(['--ffmpeg-location', ffmpegDir]);
    }

    // SponsorBlock settings
    if (settings?.defaults.sponsorblockEnabled ?? false) {
      final categories =
          settings?.defaults.sponsorblockCategories ?? ['sponsor', 'selfpromo'];
      args.addAll(['--sponsorblock-remove', categories.join(',')]);
    }

    // Subtitle settings
    if (settings?.defaults.downloadSubtitles ?? false) {
      final langs = settings?.defaults.subtitleLanguages ?? 'en';
      args.addAll(['--write-subs', '--sub-langs', langs]);

      if (settings?.defaults.autoGenerateSubs ?? false) {
        args.add('--write-auto-subs');
      }

      if (settings?.defaults.embedSubtitles ?? false) {
        args.add('--embed-subs');
      }
    }

    args.add(url);

    // Start the download process
    try {
      _updateDownload(id, state: DownloadState.fetching);

      final process = await Process.start(
        _ytDlpPath!,
        args,
      );

      _processes[id] = process;

      // Listen to stdout for progress
      _subscriptions[id] = process.stdout.transform(utf8.decoder).listen(
            (data) => _handleProgress(id, data),
            onError: (error) => _handleError(id, error),
            onDone: () => _handleComplete(id),
          );

      // Listen to stderr for errors
      process.stderr.transform(utf8.decoder).listen(
            (data) => _log.warning(data, source: 'yt-dlp'),
          );

      _updateDownload(id, state: DownloadState.downloading);

      return _downloads[id];
    } catch (e) {
      _log.error('Failed to start download',
          source: 'DownloadService', error: e);
      _updateDownload(id, state: DownloadState.failed, error: e.toString());
      return null;
    }
  }

  void _handleProgress(String id, String data) {
    // Parse progress from yt-dlp output
    final lines = data.split('\n');
    for (final line in lines) {
      if (line.contains('[download]')) {
        // Parse percentage
        final percentMatch = RegExp(r'(\d+\.?\d*)%').firstMatch(line);
        if (percentMatch != null) {
          final percent = double.tryParse(percentMatch.group(1) ?? '0') ?? 0;
          _updateDownload(id, progress: percent / 100);
        }
      }
    }
  }

  void _handleError(String id, dynamic error) {
    _log.error('Download error', source: 'DownloadService', error: error);
    _updateDownload(id, state: DownloadState.failed, error: error.toString());
  }

  void _handleComplete(String id) {
    final item = _downloads[id];
    if (item != null && item.state != DownloadState.failed) {
      _updateDownload(
        id,
        state: DownloadState.completed,
        progress: 1.0,
        completedAt: DateTime.now(),
      );
    }

    _processes.remove(id);
    _subscriptions.remove(id);
  }

  void _updateDownload(
    String id, {
    DownloadState? state,
    double? progress,
    String? error,
    DateTime? completedAt,
  }) {
    final item = _downloads[id];
    if (item == null) return;

    _downloads[id] = item.copyWith(
      state: state ?? item.state,
      progress: progress ?? item.progress,
      error: error,
      completedAt: completedAt,
    );

    notifyListeners();
  }

  /// Cancel a download
  Future<void> cancelDownload(String id) async {
    final process = _processes[id];
    if (process != null) {
      process.kill();
      _processes.remove(id);
    }

    _subscriptions[id]?.cancel();
    _subscriptions.remove(id);

    _updateDownload(id, state: DownloadState.cancelled);
  }

  /// Retry a failed download
  Future<void> retryDownload(String id) async {
    final item = _downloads[id];
    if (item == null || !item.state.canRetry) return;

    // Remove the old download
    _downloads.remove(id);
    notifyListeners();

    // Start a new download with the same parameters
    await startDownload(
      url: item.sourceUrl,
      format: item.targetFormat,
      outputPath: item.outputPath ?? '',
    );
  }

  /// Remove a download from the list
  void removeDownload(String id) {
    cancelDownload(id);
    _downloads.remove(id);
    notifyListeners();
  }

  /// Clear completed downloads
  void clearCompleted() {
    _downloads.removeWhere((_, item) => item.state.isComplete);
    notifyListeners();
  }

  /// Cancel all active downloads
  Future<void> cancelAll() async {
    for (final id in _processes.keys.toList()) {
      await cancelDownload(id);
    }
  }
}
