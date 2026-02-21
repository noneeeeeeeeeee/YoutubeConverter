/// Update configuration models
library;

/// Update cadence options for scheduling
enum UpdateCadence {
  off('Off'),
  launch('Every Launch'),
  daily('Daily'),
  weekly('Weekly'),
  monthly('Monthly');

  final String label;
  const UpdateCadence(this.label);

  static UpdateCadence fromString(String value) {
    return UpdateCadence.values.firstWhere(
      (e) => e.name.toLowerCase() == value.toLowerCase(),
      orElse: () => UpdateCadence.off,
    );
  }
}

/// Update action options
enum UpdateAction {
  noCheck('No Check'),
  prompt('Prompt'),
  auto('Auto Update');

  final String label;
  const UpdateAction(this.label);

  static UpdateAction fromString(String value) {
    return UpdateAction.values.firstWhere(
      (e) => e.name.toLowerCase() == value.toLowerCase(),
      orElse: () => UpdateAction.prompt,
    );
  }
}

/// Update schedule configuration
class UpdateSchedule {
  final UpdateCadence cadence;
  final DateTime? lastCheck;

  const UpdateSchedule({
    this.cadence = UpdateCadence.off,
    this.lastCheck,
  });

  UpdateSchedule copyWith({
    UpdateCadence? cadence,
    DateTime? lastCheck,
  }) {
    return UpdateSchedule(
      cadence: cadence ?? this.cadence,
      lastCheck: lastCheck ?? this.lastCheck,
    );
  }

  Map<String, dynamic> toJson() => {
        'cadence': cadence.name,
        'lastCheck': lastCheck?.toIso8601String(),
      };

  factory UpdateSchedule.fromJson(Map<String, dynamic> json) {
    return UpdateSchedule(
      cadence: UpdateCadence.fromString(json['cadence'] ?? 'off'),
      lastCheck: json['lastCheck'] != null
          ? DateTime.tryParse(json['lastCheck'])
          : null,
    );
  }

  /// Check if an update check is due based on the schedule
  bool get isCheckDue {
    if (cadence == UpdateCadence.off) return false;
    if (lastCheck == null) return true;

    final now = DateTime.now();
    final difference = now.difference(lastCheck!);

    switch (cadence) {
      case UpdateCadence.launch:
        return true;
      case UpdateCadence.daily:
        return difference.inDays >= 1;
      case UpdateCadence.weekly:
        return difference.inDays >= 7;
      case UpdateCadence.monthly:
        return difference.inDays >= 30;
      case UpdateCadence.off:
        return false;
    }
  }
}

/// App update configuration
class AppUpdateConfig {
  final UpdateSchedule schedule;
  final UpdateAction action;

  const AppUpdateConfig({
    this.schedule = const UpdateSchedule(),
    this.action = UpdateAction.prompt,
  });

  AppUpdateConfig copyWith({
    UpdateSchedule? schedule,
    UpdateAction? action,
  }) {
    return AppUpdateConfig(
      schedule: schedule ?? this.schedule,
      action: action ?? this.action,
    );
  }

  Map<String, dynamic> toJson() => {
        'schedule': schedule.toJson(),
        'action': action.name,
      };

  factory AppUpdateConfig.fromJson(Map<String, dynamic> json) {
    return AppUpdateConfig(
      schedule: json['schedule'] != null
          ? UpdateSchedule.fromJson(json['schedule'])
          : const UpdateSchedule(),
      action: UpdateAction.fromString(json['action'] ?? 'prompt'),
    );
  }
}

/// Yt-dlp update configuration
class YtDlpUpdateConfig {
  final bool enabled;
  final UpdateSchedule schedule;
  final String branch;

  const YtDlpUpdateConfig({
    this.enabled = true,
    this.schedule = const UpdateSchedule(cadence: UpdateCadence.daily),
    this.branch = 'stable',
  });

  YtDlpUpdateConfig copyWith({
    bool? enabled,
    UpdateSchedule? schedule,
    String? branch,
  }) {
    return YtDlpUpdateConfig(
      enabled: enabled ?? this.enabled,
      schedule: schedule ?? this.schedule,
      branch: branch ?? this.branch,
    );
  }

  Map<String, dynamic> toJson() => {
        'enabled': enabled,
        'schedule': schedule.toJson(),
        'branch': branch,
      };

  factory YtDlpUpdateConfig.fromJson(Map<String, dynamic> json) {
    return YtDlpUpdateConfig(
      enabled: json['enabled'] ?? true,
      schedule: json['schedule'] != null
          ? UpdateSchedule.fromJson(json['schedule'])
          : const UpdateSchedule(cadence: UpdateCadence.daily),
      branch: json['branch'] ?? 'stable',
    );
  }
}
