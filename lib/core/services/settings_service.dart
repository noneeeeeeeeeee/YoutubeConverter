/// Settings service for managing application settings
library;

import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/app_settings.dart';

/// Service for managing application settings persistence
class SettingsService extends ChangeNotifier {
  static const String _settingsKey = 'app_settings';

  AppSettings _settings = const AppSettings();
  AppSettings get settings => _settings;

  SharedPreferences? _prefs;
  File? _settingsFile;

  /// Initialize the settings service
  Future<void> initialize() async {
    _prefs = await SharedPreferences.getInstance();

    // Try to load from SharedPreferences first
    final jsonString = _prefs?.getString(_settingsKey);

    if (jsonString != null) {
      try {
        final json = jsonDecode(jsonString) as Map<String, dynamic>;
        _settings = AppSettings.fromJson(json);
      } catch (e) {
        debugPrint('Failed to parse settings from SharedPreferences: $e');
      }
    }

    // Also try to load from file (for migration from Python version)
    await _loadFromFile();

    notifyListeners();
  }

  /// Load settings from file (for migration)
  Future<void> _loadFromFile() async {
    try {
      final appDir = await getApplicationDocumentsDirectory();
      final settingsDir = Platform.isWindows
          ? '${Platform.environment['APPDATA']}\\YoutubeConverter'
          : '${appDir.path}/YoutubeConverter';

      _settingsFile = File('$settingsDir/settings.json');

      if (await _settingsFile!.exists()) {
        final content = await _settingsFile!.readAsString();
        final json = jsonDecode(content) as Map<String, dynamic>;
        _settings = AppSettings.fromJson(json);

        // Save to SharedPreferences for faster access
        await _saveToPrefs();
      }
    } catch (e) {
      debugPrint('Failed to load settings from file: $e');
    }
  }

  /// Save settings to SharedPreferences
  Future<void> _saveToPrefs() async {
    if (_prefs == null) return;

    final jsonString = jsonEncode(_settings.toJson());
    await _prefs!.setString(_settingsKey, jsonString);
  }

  /// Save settings to file
  Future<void> _saveToFile() async {
    if (_settingsFile == null) return;

    try {
      final dir = _settingsFile!.parent;
      if (!await dir.exists()) {
        await dir.create(recursive: true);
      }

      final jsonString =
          const JsonEncoder.withIndent('  ').convert(_settings.toJson());
      await _settingsFile!.writeAsString(jsonString);
    } catch (e) {
      debugPrint('Failed to save settings to file: $e');
    }
  }

  /// Update settings
  Future<void> updateSettings(AppSettings newSettings) async {
    _settings = newSettings;
    await _saveToPrefs();
    await _saveToFile();
    notifyListeners();
  }

  /// Update UI settings
  Future<void> updateUISettings(UISettings ui) async {
    _settings = _settings.copyWith(ui: ui);
    await _saveToPrefs();
    await _saveToFile();
    notifyListeners();
  }

  /// Update defaults settings
  Future<void> updateDefaultsSettings(DefaultsSettings defaults) async {
    _settings = _settings.copyWith(defaults: defaults);
    await _saveToPrefs();
    await _saveToFile();
    notifyListeners();
  }

  /// Update EZ mode settings
  Future<void> updateEZModeSettings(EZModeSettings ez) async {
    _settings = _settings.copyWith(ez: ez);
    await _saveToPrefs();
    await _saveToFile();
    notifyListeners();
  }

  /// Update last download directory
  Future<void> updateLastDownloadDir(String path) async {
    _settings = _settings.copyWith(lastDownloadDir: path);
    await _saveToPrefs();
    await _saveToFile();
    notifyListeners();
  }

  /// Reset settings to defaults
  Future<void> resetToDefaults() async {
    _settings = const AppSettings();
    await _saveToPrefs();
    await _saveToFile();
    notifyListeners();
  }

  /// Get the settings directory path
  static Future<String> get settingsDir async {
    if (Platform.isWindows) {
      return '${Platform.environment['APPDATA']}\\YoutubeConverter';
    } else if (Platform.isMacOS) {
      final appDir = await getApplicationDocumentsDirectory();
      return '${appDir.path}/YoutubeConverter';
    } else {
      final appDir = await getApplicationDocumentsDirectory();
      return '${appDir.path}/YoutubeConverter';
    }
  }

  /// Get the logs directory path
  static Future<String> get logsDir async {
    final base = await settingsDir;
    return '$base/logs';
  }
}
