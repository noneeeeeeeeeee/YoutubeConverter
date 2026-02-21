/// Notification specification model
library;

/// Notification category
enum NotificationCategory {
  info('info'),
  success('success'),
  fail('fail');

  final String value;
  const NotificationCategory(this.value);

  static NotificationCategory fromString(String value) {
    return NotificationCategory.values.firstWhere(
      (e) => e.value.toLowerCase() == value.toLowerCase(),
      orElse: () => NotificationCategory.info,
    );
  }
}

/// Notification specification
class NotificationSpec {
  final NotificationCategory category;
  final String message;
  final int durationMs;
  final bool sticky;

  const NotificationSpec({
    required this.category,
    required this.message,
    required this.durationMs,
    this.sticky = false,
  });

  /// Default durations based on category
  static const int infoDurationMs = 30000; // 30 seconds
  static const int successDurationMs = 10000; // 10 seconds
  static const int failDurationMs = 60000; // 60 seconds (sticky candidate)

  /// Create an info notification
  factory NotificationSpec.info(String message, {int? durationMs}) {
    return NotificationSpec(
      category: NotificationCategory.info,
      message: message,
      durationMs: durationMs ?? infoDurationMs,
      sticky: false,
    );
  }

  /// Create a success notification
  factory NotificationSpec.success(String message, {int? durationMs}) {
    return NotificationSpec(
      category: NotificationCategory.success,
      message: message,
      durationMs: durationMs ?? successDurationMs,
      sticky: false,
    );
  }

  /// Create a fail notification
  factory NotificationSpec.fail(String message,
      {int? durationMs, bool sticky = true}) {
    return NotificationSpec(
      category: NotificationCategory.fail,
      message: message,
      durationMs: durationMs ?? failDurationMs,
      sticky: sticky,
    );
  }

  Map<String, dynamic> toJson() => {
        'category': category.value,
        'message': message,
        'durationMs': durationMs,
        'sticky': sticky,
      };

  factory NotificationSpec.fromJson(Map<String, dynamic> json) {
    return NotificationSpec(
      category: NotificationCategory.fromString(json['category'] ?? 'info'),
      message: json['message'],
      durationMs: json['durationMs'] ?? infoDurationMs,
      sticky: json['sticky'] ?? false,
    );
  }
}
