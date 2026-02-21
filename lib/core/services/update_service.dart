/// Update service for managing app and yt-dlp updates
library;

import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import '../models/update_config.dart';
import 'log_service.dart';

/// Update info model
class UpdateInfo {
  final String version;
  final String? changelog;
  final String? downloadUrl;
  final DateTime publishedAt;

  const UpdateInfo({
    required this.version,
    this.changelog,
    this.downloadUrl,
    required this.publishedAt,
  });
}

/// Update service for managing app and yt-dlp updates
class UpdateService extends ChangeNotifier {
  final LogService _log = LogService();

  static const String _githubRepo = 'noneeeeeeeeeee/YoutubeConverter';
  static const String _ytDlpRepo = 'yt-dlp/yt-dlp';

  String? _ytDlpPath;
  bool _isCheckingAppUpdate = false;
  bool _isCheckingYtDlpUpdate = false;
  bool _isUpdating = false;

  UpdateInfo? _availableAppUpdate;
  UpdateInfo? _availableYtDlpUpdate;

  bool get isCheckingAppUpdate => _isCheckingAppUpdate;
  bool get isCheckingYtDlpUpdate => _isCheckingYtDlpUpdate;
  bool get isUpdating => _isUpdating;
  UpdateInfo? get availableAppUpdate => _availableAppUpdate;
  UpdateInfo? get availableYtDlpUpdate => _availableYtDlpUpdate;

  /// Initialize the update service
  Future<void> initialize() async {
    await _findYtDlp();
  }

  /// Find yt-dlp executable
  Future<void> _findYtDlp() async {
    final possiblePaths = [
      'yt-dlp',
      'yt-dlp.exe',
      if (Platform.isWindows)
        '${Platform.environment['APPDATA']}\\YoutubeConverter\\yt-dlp.exe',
    ];

    for (final path in possiblePaths) {
      try {
        if (Platform.isWindows) {
          if (path.contains('\\')) {
            if (await File(path).exists()) {
              _ytDlpPath = path;
              break;
            }
          } else {
            final result = await Process.run('where', [path]);
            if (result.exitCode == 0) {
              _ytDlpPath = path;
              break;
            }
          }
        } else {
          if (path.contains('/')) {
            if (await File(path).exists()) {
              _ytDlpPath = path;
              break;
            }
          } else {
            final result = await Process.run('which', [path]);
            if (result.exitCode == 0) {
              _ytDlpPath = path;
              break;
            }
          }
        }
      } catch (e) {
        continue;
      }
    }
  }

  /// Check for app updates
  Future<UpdateInfo?> checkAppUpdate({String channel = 'release'}) async {
    if (_isCheckingAppUpdate) return null;

    _isCheckingAppUpdate = true;
    notifyListeners();

    try {
      final response = await http.get(
        Uri.parse('https://api.github.com/repos/$_githubRepo/releases/latest'),
        headers: {'Accept': 'application/vnd.github.v3+json'},
      );

      if (response.statusCode != 200) {
        _log.error('Failed to check for app updates: ${response.statusCode}',
            source: 'UpdateService');
        return null;
      }

      final json = jsonDecode(response.body) as Map<String, dynamic>;
      final version = json['tag_name'] as String;
      final changelog = json['body'] as String?;
      final publishedAt = DateTime.parse(json['published_at'] as String);

      String? downloadUrl;
      final assets = json['assets'] as List?;
      if (assets != null) {
        for (final asset in assets) {
          final name = asset['name'] as String;
          if (name.contains(Platform.operatingSystem)) {
            downloadUrl = asset['browser_download_url'] as String;
            break;
          }
        }
      }

      _availableAppUpdate = UpdateInfo(
        version: version,
        changelog: changelog,
        downloadUrl: downloadUrl,
        publishedAt: publishedAt,
      );

      notifyListeners();
      return _availableAppUpdate;
    } catch (e) {
      _log.error('Error checking for app updates',
          source: 'UpdateService', error: e);
      return null;
    } finally {
      _isCheckingAppUpdate = false;
      notifyListeners();
    }
  }

  /// Check for yt-dlp updates
  Future<UpdateInfo?> checkYtDlpUpdate() async {
    if (_isCheckingYtDlpUpdate) return null;

    _isCheckingYtDlpUpdate = true;
    notifyListeners();

    try {
      final response = await http.get(
        Uri.parse('https://api.github.com/repos/$_ytDlpRepo/releases/latest'),
        headers: {'Accept': 'application/vnd.github.v3+json'},
      );

      if (response.statusCode != 200) {
        _log.error('Failed to check for yt-dlp updates: ${response.statusCode}',
            source: 'UpdateService');
        return null;
      }

      final json = jsonDecode(response.body) as Map<String, dynamic>;
      final version = json['tag_name'] as String;
      final publishedAt = DateTime.parse(json['published_at'] as String);

      String? downloadUrl;
      final assets = json['assets'] as List?;
      if (assets != null) {
        for (final asset in assets) {
          final name = asset['name'] as String;
          if (Platform.isWindows && name.endsWith('.exe')) {
            downloadUrl = asset['browser_download_url'] as String;
            break;
          } else if (!Platform.isWindows && !name.contains('.')) {
            downloadUrl = asset['browser_download_url'] as String;
            break;
          }
        }
      }

      _availableYtDlpUpdate = UpdateInfo(
        version: version,
        downloadUrl: downloadUrl,
        publishedAt: publishedAt,
      );

      notifyListeners();
      return _availableYtDlpUpdate;
    } catch (e) {
      _log.error('Error checking for yt-dlp updates',
          source: 'UpdateService', error: e);
      return null;
    } finally {
      _isCheckingYtDlpUpdate = false;
      notifyListeners();
    }
  }

  /// Update yt-dlp
  Future<bool> updateYtDlp(String downloadUrl) async {
    if (_isUpdating) return false;

    _isUpdating = true;
    notifyListeners();

    try {
      // Download the new version
      final response = await http.get(Uri.parse(downloadUrl));

      if (response.statusCode != 200) {
        _log.error('Failed to download yt-dlp: ${response.statusCode}',
            source: 'UpdateService');
        return false;
      }

      // Determine the target path
      String targetPath;
      if (Platform.isWindows) {
        final appData = Platform.environment['APPDATA'];
        targetPath = '$appData\\YoutubeConverter\\yt-dlp.exe';
      } else {
        final appDir = await getApplicationDocumentsDirectory();
        targetPath = '${appDir.path}/YoutubeConverter/yt-dlp';
      }

      // Create directory if needed
      final file = File(targetPath);
      if (!await file.parent.exists()) {
        await file.parent.create(recursive: true);
      }

      // Write the new version
      await file.writeAsBytes(response.bodyBytes);

      // Make executable on Unix
      if (!Platform.isWindows) {
        await Process.run('chmod', ['+x', targetPath]);
      }

      _ytDlpPath = targetPath;
      _availableYtDlpUpdate = null;

      _log.info('yt-dlp updated successfully', source: 'UpdateService');
      return true;
    } catch (e) {
      _log.error('Error updating yt-dlp', source: 'UpdateService', error: e);
      return false;
    } finally {
      _isUpdating = false;
      notifyListeners();
    }
  }

  /// Get current yt-dlp version
  Future<String?> getYtDlpVersion() async {
    if (_ytDlpPath == null) return null;

    try {
      final result = await Process.run(_ytDlpPath!, ['--version']);
      if (result.exitCode == 0) {
        return (result.stdout as String).trim();
      }
    } catch (e) {
      _log.error('Error getting yt-dlp version',
          source: 'UpdateService', error: e);
    }
    return null;
  }

  /// Check if updates should be checked based on schedule
  bool shouldCheckUpdate(UpdateSchedule schedule) {
    return schedule.isCheckDue;
  }
}
