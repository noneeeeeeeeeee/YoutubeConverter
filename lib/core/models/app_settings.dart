/// Application settings model
library;

import 'dart:io';
import 'update_config.dart';

/// UI theme mode
enum ThemeMode {
  light('Light'),
  dark('Dark'),
  oled('OLED');

  final String label;
  const ThemeMode(this.label);

  static ThemeMode fromString(String value) {
    return ThemeMode.values.firstWhere(
      (e) => e.name.toLowerCase() == value.toLowerCase(),
      orElse: () => ThemeMode.dark,
    );
  }
}

/// UI settings configuration
class UISettings {
  final bool autoAdvance;
  final bool resetAfterDownloads;
  final String accentColorHex;
  final bool autoFetchUrls;
  final bool autoSearchText;
  final bool liveSearch;
  final int searchDebounceSeconds;
  final bool fastPasteEnabled;
  final int qualityRefetchSeconds;
  final bool backgroundMetadataEnabled;
  final bool autoClearOnSuccess;
  final ThemeMode themeMode;

  const UISettings({
    this.autoAdvance = true,
    this.resetAfterDownloads = true,
    this.accentColorHex = '#F28C28',
    this.autoFetchUrls = true,
    this.autoSearchText = true,
    this.liveSearch = true,
    this.searchDebounceSeconds = 3,
    this.fastPasteEnabled = true,
    this.qualityRefetchSeconds = 1,
    this.backgroundMetadataEnabled = true,
    this.autoClearOnSuccess = true,
    this.themeMode = ThemeMode.dark,
  });

  UISettings copyWith({
    bool? autoAdvance,
    bool? resetAfterDownloads,
    String? accentColorHex,
    bool? autoFetchUrls,
    bool? autoSearchText,
    bool? liveSearch,
    int? searchDebounceSeconds,
    bool? fastPasteEnabled,
    int? qualityRefetchSeconds,
    bool? backgroundMetadataEnabled,
    bool? autoClearOnSuccess,
    ThemeMode? themeMode,
  }) {
    return UISettings(
      autoAdvance: autoAdvance ?? this.autoAdvance,
      resetAfterDownloads: resetAfterDownloads ?? this.resetAfterDownloads,
      accentColorHex: accentColorHex ?? this.accentColorHex,
      autoFetchUrls: autoFetchUrls ?? this.autoFetchUrls,
      autoSearchText: autoSearchText ?? this.autoSearchText,
      liveSearch: liveSearch ?? this.liveSearch,
      searchDebounceSeconds:
          searchDebounceSeconds ?? this.searchDebounceSeconds,
      fastPasteEnabled: fastPasteEnabled ?? this.fastPasteEnabled,
      qualityRefetchSeconds:
          qualityRefetchSeconds ?? this.qualityRefetchSeconds,
      backgroundMetadataEnabled:
          backgroundMetadataEnabled ?? this.backgroundMetadataEnabled,
      autoClearOnSuccess: autoClearOnSuccess ?? this.autoClearOnSuccess,
      themeMode: themeMode ?? this.themeMode,
    );
  }

  Map<String, dynamic> toJson() => {
        'autoAdvance': autoAdvance,
        'resetAfterDownloads': resetAfterDownloads,
        'accentColorHex': accentColorHex,
        'autoFetchUrls': autoFetchUrls,
        'autoSearchText': autoSearchText,
        'liveSearch': liveSearch,
        'searchDebounceSeconds': searchDebounceSeconds,
        'fastPasteEnabled': fastPasteEnabled,
        'qualityRefetchSeconds': qualityRefetchSeconds,
        'backgroundMetadataEnabled': backgroundMetadataEnabled,
        'autoClearOnSuccess': autoClearOnSuccess,
        'themeMode': themeMode.name,
      };

  factory UISettings.fromJson(Map<String, dynamic> json) {
    return UISettings(
      autoAdvance: json['autoAdvance'] ?? true,
      resetAfterDownloads: json['resetAfterDownloads'] ?? true,
      accentColorHex: json['accentColorHex'] ?? '#F28C28',
      autoFetchUrls: json['autoFetchUrls'] ?? true,
      autoSearchText: json['autoSearchText'] ?? true,
      liveSearch: json['liveSearch'] ?? true,
      searchDebounceSeconds: json['searchDebounceSeconds'] ?? 3,
      fastPasteEnabled: json['fastPasteEnabled'] ?? true,
      qualityRefetchSeconds: json['qualityRefetchSeconds'] ?? 1,
      backgroundMetadataEnabled: json['backgroundMetadataEnabled'] ?? true,
      autoClearOnSuccess: json['autoClearOnSuccess'] ?? true,
      themeMode: ThemeMode.fromString(json['themeMode'] ?? 'dark'),
    );
  }
}

/// Default download settings
class DefaultsSettings {
  final String kind; // 'audio' or 'video'
  final String format; // 'mp3', 'mp4', etc.
  final bool sponsorblockEnabled;
  final List<String> sponsorblockCategories;
  final String sponsorblockApiKey;
  final bool sponsorblockRememberLast;
  final String filenameTemplate;
  final bool downloadSubtitles;
  final String subtitleLanguages;
  final bool embedSubtitles;
  final bool autoGenerateSubs;
  final bool hideSubtitleOptions;

  const DefaultsSettings({
    this.kind = 'audio',
    this.format = 'mp3',
    this.sponsorblockEnabled = false,
    this.sponsorblockCategories = const ['sponsor', 'selfpromo'],
    this.sponsorblockApiKey = '',
    this.sponsorblockRememberLast = false,
    this.filenameTemplate = '{title}',
    this.downloadSubtitles = false,
    this.subtitleLanguages = 'en',
    this.embedSubtitles = false,
    this.autoGenerateSubs = false,
    this.hideSubtitleOptions = true,
  });

  DefaultsSettings copyWith({
    String? kind,
    String? format,
    bool? sponsorblockEnabled,
    List<String>? sponsorblockCategories,
    String? sponsorblockApiKey,
    bool? sponsorblockRememberLast,
    String? filenameTemplate,
    bool? downloadSubtitles,
    String? subtitleLanguages,
    bool? embedSubtitles,
    bool? autoGenerateSubs,
    bool? hideSubtitleOptions,
  }) {
    return DefaultsSettings(
      kind: kind ?? this.kind,
      format: format ?? this.format,
      sponsorblockEnabled: sponsorblockEnabled ?? this.sponsorblockEnabled,
      sponsorblockCategories:
          sponsorblockCategories ?? this.sponsorblockCategories,
      sponsorblockApiKey: sponsorblockApiKey ?? this.sponsorblockApiKey,
      sponsorblockRememberLast:
          sponsorblockRememberLast ?? this.sponsorblockRememberLast,
      filenameTemplate: filenameTemplate ?? this.filenameTemplate,
      downloadSubtitles: downloadSubtitles ?? this.downloadSubtitles,
      subtitleLanguages: subtitleLanguages ?? this.subtitleLanguages,
      embedSubtitles: embedSubtitles ?? this.embedSubtitles,
      autoGenerateSubs: autoGenerateSubs ?? this.autoGenerateSubs,
      hideSubtitleOptions: hideSubtitleOptions ?? this.hideSubtitleOptions,
    );
  }

  Map<String, dynamic> toJson() => {
        'kind': kind,
        'format': format,
        'sponsorblockEnabled': sponsorblockEnabled,
        'sponsorblockCategories': sponsorblockCategories,
        'sponsorblockApiKey': sponsorblockApiKey,
        'sponsorblockRememberLast': sponsorblockRememberLast,
        'filenameTemplate': filenameTemplate,
        'downloadSubtitles': downloadSubtitles,
        'subtitleLanguages': subtitleLanguages,
        'embedSubtitles': embedSubtitles,
        'autoGenerateSubs': autoGenerateSubs,
        'hideSubtitleOptions': hideSubtitleOptions,
      };

  factory DefaultsSettings.fromJson(Map<String, dynamic> json) {
    return DefaultsSettings(
      kind: json['kind'] ?? 'audio',
      format: json['format'] ?? 'mp3',
      sponsorblockEnabled: json['sponsorblockEnabled'] ?? false,
      sponsorblockCategories: json['sponsorblockCategories'] != null
          ? List<String>.from(json['sponsorblockCategories'])
          : const ['sponsor', 'selfpromo'],
      sponsorblockApiKey: json['sponsorblockApiKey'] ?? '',
      sponsorblockRememberLast: json['sponsorblockRememberLast'] ?? false,
      filenameTemplate: json['filenameTemplate'] ?? '{title}',
      downloadSubtitles: json['downloadSubtitles'] ?? false,
      subtitleLanguages: json['subtitleLanguages'] ?? 'en',
      embedSubtitles: json['embedSubtitles'] ?? false,
      autoGenerateSubs: json['autoGenerateSubs'] ?? false,
      hideSubtitleOptions: json['hideSubtitleOptions'] ?? true,
    );
  }
}

/// Yt-dlp settings
class YtDlpSettings {
  final bool autoUpdate;
  final String branch;

  const YtDlpSettings({
    this.autoUpdate = true,
    this.branch = 'stable',
  });

  YtDlpSettings copyWith({
    bool? autoUpdate,
    String? branch,
  }) {
    return YtDlpSettings(
      autoUpdate: autoUpdate ?? this.autoUpdate,
      branch: branch ?? this.branch,
    );
  }

  Map<String, dynamic> toJson() => {
        'autoUpdate': autoUpdate,
        'branch': branch,
      };

  factory YtDlpSettings.fromJson(Map<String, dynamic> json) {
    return YtDlpSettings(
      autoUpdate: json['autoUpdate'] ?? true,
      branch: json['branch'] ?? 'stable',
    );
  }
}

/// App update settings (legacy)
class AppUpdateSettings {
  final bool autoUpdate;
  final String channel;
  final bool checkOnLaunch;

  const AppUpdateSettings({
    this.autoUpdate = true,
    this.channel = 'release',
    this.checkOnLaunch = false,
  });

  AppUpdateSettings copyWith({
    bool? autoUpdate,
    String? channel,
    bool? checkOnLaunch,
  }) {
    return AppUpdateSettings(
      autoUpdate: autoUpdate ?? this.autoUpdate,
      channel: channel ?? this.channel,
      checkOnLaunch: checkOnLaunch ?? this.checkOnLaunch,
    );
  }

  Map<String, dynamic> toJson() => {
        'autoUpdate': autoUpdate,
        'channel': channel,
        'checkOnLaunch': checkOnLaunch,
      };

  factory AppUpdateSettings.fromJson(Map<String, dynamic> json) {
    return AppUpdateSettings(
      autoUpdate: json['autoUpdate'] ?? true,
      channel: json['channel'] ?? 'release',
      checkOnLaunch: json['checkOnLaunch'] ?? false,
    );
  }
}

/// EZ Mode settings for simplified user experience
class EZModeSettings {
  final bool sanitizeRadioLinks;
  final bool simplePasteMode;
  final bool hideAdvancedQuality;

  const EZModeSettings({
    this.sanitizeRadioLinks = true,
    this.simplePasteMode = false,
    this.hideAdvancedQuality = false,
  });

  EZModeSettings copyWith({
    bool? sanitizeRadioLinks,
    bool? simplePasteMode,
    bool? hideAdvancedQuality,
  }) {
    return EZModeSettings(
      sanitizeRadioLinks: sanitizeRadioLinks ?? this.sanitizeRadioLinks,
      simplePasteMode: simplePasteMode ?? this.simplePasteMode,
      hideAdvancedQuality: hideAdvancedQuality ?? this.hideAdvancedQuality,
    );
  }

  Map<String, dynamic> toJson() => {
        'sanitizeRadioLinks': sanitizeRadioLinks,
        'simplePasteMode': simplePasteMode,
        'hideAdvancedQuality': hideAdvancedQuality,
      };

  factory EZModeSettings.fromJson(Map<String, dynamic> json) {
    return EZModeSettings(
      sanitizeRadioLinks: json['sanitizeRadioLinks'] ?? true,
      simplePasteMode: json['simplePasteMode'] ?? false,
      hideAdvancedQuality: json['hideAdvancedQuality'] ?? false,
    );
  }
}

/// Main application settings container
class AppSettings {
  final String lastDownloadDir;
  final UISettings ui;
  final DefaultsSettings defaults;
  final YtDlpSettings ytdlp;
  final AppUpdateSettings app;
  final EZModeSettings ez;
  final AppUpdateConfig appUpdate;
  final YtDlpUpdateConfig ytdlpUpdate;

  const AppSettings({
    this.lastDownloadDir = '',
    this.ui = const UISettings(),
    this.defaults = const DefaultsSettings(),
    this.ytdlp = const YtDlpSettings(),
    this.app = const AppUpdateSettings(),
    this.ez = const EZModeSettings(),
    this.appUpdate = const AppUpdateConfig(),
    this.ytdlpUpdate = const YtDlpUpdateConfig(
      enabled: true,
      schedule: UpdateSchedule(cadence: UpdateCadence.daily),
    ),
  });

  /// Get default download directory
  static String get defaultDownloadDir {
    if (Platform.isWindows) {
      return '${Platform.environment['USERPROFILE']}\\Downloads';
    } else if (Platform.isMacOS) {
      return '${Platform.environment['HOME']}/Downloads';
    } else {
      return '${Platform.environment['HOME']}/Downloads';
    }
  }

  AppSettings copyWith({
    String? lastDownloadDir,
    UISettings? ui,
    DefaultsSettings? defaults,
    YtDlpSettings? ytdlp,
    AppUpdateSettings? app,
    EZModeSettings? ez,
    AppUpdateConfig? appUpdate,
    YtDlpUpdateConfig? ytdlpUpdate,
  }) {
    return AppSettings(
      lastDownloadDir: lastDownloadDir ?? this.lastDownloadDir,
      ui: ui ?? this.ui,
      defaults: defaults ?? this.defaults,
      ytdlp: ytdlp ?? this.ytdlp,
      app: app ?? this.app,
      ez: ez ?? this.ez,
      appUpdate: appUpdate ?? this.appUpdate,
      ytdlpUpdate: ytdlpUpdate ?? this.ytdlpUpdate,
    );
  }

  Map<String, dynamic> toJson() => {
        'lastDownloadDir': lastDownloadDir,
        'ui': ui.toJson(),
        'defaults': defaults.toJson(),
        'ytdlp': ytdlp.toJson(),
        'app': app.toJson(),
        'ez': ez.toJson(),
        'appUpdate': appUpdate.toJson(),
        'ytdlpUpdate': ytdlpUpdate.toJson(),
      };

  factory AppSettings.fromJson(Map<String, dynamic> json) {
    return AppSettings(
      lastDownloadDir: json['lastDownloadDir'] ?? defaultDownloadDir,
      ui: json['ui'] != null
          ? UISettings.fromJson(json['ui'])
          : const UISettings(),
      defaults: json['defaults'] != null
          ? DefaultsSettings.fromJson(json['defaults'])
          : const DefaultsSettings(),
      ytdlp: json['ytdlp'] != null
          ? YtDlpSettings.fromJson(json['ytdlp'])
          : const YtDlpSettings(),
      app: json['app'] != null
          ? AppUpdateSettings.fromJson(json['app'])
          : const AppUpdateSettings(),
      ez: json['ez'] != null
          ? EZModeSettings.fromJson(json['ez'])
          : const EZModeSettings(),
      appUpdate: json['appUpdate'] != null
          ? AppUpdateConfig.fromJson(json['appUpdate'])
          : const AppUpdateConfig(),
      ytdlpUpdate: json['ytdlpUpdate'] != null
          ? YtDlpUpdateConfig.fromJson(json['ytdlpUpdate'])
          : const YtDlpUpdateConfig(
              enabled: true,
              schedule: UpdateSchedule(cadence: UpdateCadence.daily),
            ),
    );
  }
}
