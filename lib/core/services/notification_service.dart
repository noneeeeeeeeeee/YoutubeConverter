/// Notification service for managing app notifications
library;

import 'package:flutter/foundation.dart';
import '../models/notification_spec.dart';

/// Notification service for displaying toasts and system notifications
class NotificationService extends ChangeNotifier {
  final List<NotificationSpec> _notifications = [];
  List<NotificationSpec> get notifications => List.unmodifiable(_notifications);

  /// Show a notification
  void show(NotificationSpec notification) {
    _notifications.add(notification);
    notifyListeners();

    // Auto-dismiss after duration if not sticky
    if (!notification.sticky) {
      Future.delayed(Duration(milliseconds: notification.durationMs), () {
        dismiss(notification);
      });
    }
  }

  /// Show an info notification
  void info(String message, {int? durationMs}) {
    show(NotificationSpec.info(message, durationMs: durationMs));
  }

  /// Show a success notification
  void success(String message, {int? durationMs}) {
    show(NotificationSpec.success(message, durationMs: durationMs));
  }

  /// Show a fail notification
  void fail(String message, {int? durationMs, bool sticky = true}) {
    show(
        NotificationSpec.fail(message, durationMs: durationMs, sticky: sticky));
  }

  /// Dismiss a notification
  void dismiss(NotificationSpec notification) {
    _notifications.remove(notification);
    notifyListeners();
  }

  /// Dismiss all notifications
  void dismissAll() {
    _notifications.clear();
    notifyListeners();
  }

  /// Clear all non-sticky notifications
  void clearNonSticky() {
    _notifications.removeWhere((n) => !n.sticky);
    notifyListeners();
  }
}
