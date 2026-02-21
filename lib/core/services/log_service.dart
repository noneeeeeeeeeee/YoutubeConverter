/// Log service for managing application logs
library;

import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:intl/intl.dart';
import 'package:path_provider/path_provider.dart';
import 'package:archive/archive.dart';

/// Log entry model
class LogEntry {
  final DateTime timestamp;
  final String level;
  final String message;
  final String? source;

  const LogEntry({
    required this.timestamp,
    required this.level,
    required this.message,
    this.source,
  });

  String get formattedTimestamp =>
      DateFormat('yyyy-MM-dd HH:mm:ss.SSS').format(timestamp);

  @override
  String toString() =>
      '[$formattedTimestamp] [$level] ${source != null ? '[$source] ' : ''}$message';
}

/// Log service for managing application logs
class LogService {
  static final LogService _instance = LogService._internal();
  factory LogService() => _instance;
  LogService._internal();

  final List<LogEntry> _entries = [];
  static const int _maxEntries = 1000;
  File? _logFile;

  /// Get all log entries
  List<LogEntry> get entries => List.unmodifiable(_entries);

  /// Initialize the log service
  Future<void> initialize() async {
    try {
      final logsDir = await _getLogsDir();
      if (!await logsDir.exists()) {
        await logsDir.create(recursive: true);
      }

      final now = DateTime.now();
      final filename = 'app-${DateFormat('yyyy-MM-dd').format(now)}.log';
      _logFile = File('${logsDir.path}/$filename');

      // Create or append to log file
      if (!await _logFile!.exists()) {
        await _logFile!.create();
      }
    } catch (e) {
      debugPrint('Failed to initialize log service: $e');
    }
  }

  /// Get the logs directory
  static Future<Directory> _getLogsDir() async {
    if (Platform.isWindows) {
      final appData = Platform.environment['APPDATA'];
      return Directory('$appData\\YoutubeConverter\\logs');
    } else {
      final appDir = await getApplicationDocumentsDirectory();
      return Directory('${appDir.path}/YoutubeConverter/logs');
    }
  }

  /// Log a debug message
  void debug(String message, {String? source}) {
    _log('DEBUG', message, source: source);
  }

  /// Log an info message
  void info(String message, {String? source}) {
    _log('INFO', message, source: source);
  }

  /// Log a warning message
  void warning(String message, {String? source}) {
    _log('WARNING', message, source: source);
  }

  /// Log an error message
  void error(String message,
      {String? source, Object? error, StackTrace? stackTrace}) {
    final fullMessage = error != null
        ? '$message: $error${stackTrace != null ? '\n$stackTrace' : ''}'
        : message;
    _log('ERROR', fullMessage, source: source);
  }

  void _log(String level, String message, {String? source}) {
    final entry = LogEntry(
      timestamp: DateTime.now(),
      level: level,
      message: message,
      source: source,
    );

    _entries.add(entry);

    // Trim old entries
    if (_entries.length > _maxEntries) {
      _entries.removeAt(0);
    }

    // Write to file
    _writeToFile(entry);

    // Also print to debug console
    debugPrint(entry.toString());
  }

  Future<void> _writeToFile(LogEntry entry) async {
    if (_logFile == null) return;

    try {
      await _logFile!.writeAsString(
        '${entry.toString()}\n',
        mode: FileMode.append,
      );
    } catch (e) {
      debugPrint('Failed to write to log file: $e');
    }
  }

  /// Export logs to a zip file
  Future<String?> exportLogs() async {
    try {
      final logsDir = await _getLogsDir();
      if (!await logsDir.exists()) {
        return null;
      }

      final now = DateTime.now();
      final timestamp = DateFormat('yyyyMMdd-HHmmss').format(now);
      final exportPath = '${logsDir.path}/logs-$timestamp.zip';

      final archive = Archive();

      await for (final entity in logsDir.list()) {
        if (entity is File && entity.path.endsWith('.log')) {
          final content = await entity.readAsBytes();
          final name = entity.path.split(Platform.pathSeparator).last;
          archive.addFile(ArchiveFile(name, content.length, content));
        }
      }

      if (archive.isEmpty) {
        return null;
      }

      final zipData = ZipEncoder().encode(archive);
      if (zipData == null) {
        return null;
      }

      final zipFile = File(exportPath);
      await zipFile.writeAsBytes(zipData);

      return exportPath;
    } catch (e) {
      debugPrint('Failed to export logs: $e');
      return null;
    }
  }

  /// Clear all logs
  Future<void> clearLogs() async {
    try {
      final logsDir = await _getLogsDir();
      if (await logsDir.exists()) {
        await for (final entity in logsDir.list()) {
          if (entity is File) {
            await entity.delete();
          }
        }
      }
      _entries.clear();

      // Recreate log file
      await initialize();
    } catch (e) {
      debugPrint('Failed to clear logs: $e');
    }
  }

  /// Get recent log entries as a string
  String getRecentLogs({int count = 100}) {
    final recent = _entries.length > count
        ? _entries.sublist(_entries.length - count)
        : _entries;
    return recent.map((e) => e.toString()).join('\n');
  }
}
