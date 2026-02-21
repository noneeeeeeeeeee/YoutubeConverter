/// Toast notification widget
library;

import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../core/models/notification_spec.dart';

/// Toast notification widget
class ToastWidget extends StatelessWidget {
  final NotificationSpec notification;
  final VoidCallback? onDismiss;

  const ToastWidget({
    super.key,
    required this.notification,
    this.onDismiss,
  });

  Color _getBackgroundColor(BuildContext context) {
    switch (notification.category) {
      case NotificationCategory.success:
        return Colors.green.shade700;
      case NotificationCategory.fail:
        return Colors.red.shade700;
      case NotificationCategory.info:
      default:
        return Theme.of(context).colorScheme.surfaceVariant;
    }
  }

  Color _getTextColor(BuildContext context) {
    switch (notification.category) {
      case NotificationCategory.success:
      case NotificationCategory.fail:
        return Colors.white;
      case NotificationCategory.info:
      default:
        return Theme.of(context).colorScheme.onSurfaceVariant;
    }
  }

  IconData _getIcon() {
    switch (notification.category) {
      case NotificationCategory.success:
        return Icons.check_circle_outline;
      case NotificationCategory.fail:
        return Icons.error_outline;
      case NotificationCategory.info:
      default:
        return Icons.info_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: _getBackgroundColor(context),
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Icon(
              _getIcon(),
              color: _getTextColor(context),
              size: 20,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                notification.message,
                style: TextStyle(
                  color: _getTextColor(context),
                  fontSize: 14,
                ),
              ),
            ),
            if (notification.sticky) ...[
              const SizedBox(width: 8),
              GestureDetector(
                onTap: onDismiss,
                child: Icon(
                  Icons.close,
                  color: _getTextColor(context),
                  size: 18,
                ),
              ),
            ],
          ],
        ),
      ),
    ).animate().fadeIn(duration: 200.ms).slideY(begin: 0.2, end: 0);
  }
}

/// Toast overlay manager
class ToastOverlay {
  static OverlayEntry? _overlayEntry;
  static final List<NotificationSpec> _queue = [];
  static bool _isShowing = false;

  static void show(BuildContext context, NotificationSpec notification) {
    _queue.add(notification);
    _showNext(context);
  }

  static void _showNext(BuildContext context) {
    if (_isShowing || _queue.isEmpty) return;

    _isShowing = true;
    final notification = _queue.removeAt(0);

    _overlayEntry = OverlayEntry(
      builder: (context) => Positioned(
        bottom: 24,
        right: 24,
        left: 24,
        child: ToastWidget(
          notification: notification,
          onDismiss: () {
            _dismiss();
          },
        ),
      ),
    );

    Overlay.of(context).insert(_overlayEntry!);

    // Auto dismiss after duration
    if (!notification.sticky) {
      Future.delayed(
        Duration(milliseconds: notification.durationMs),
        () => _dismiss(),
      );
    }
  }

  static void _dismiss() {
    _overlayEntry?.remove();
    _overlayEntry = null;
    _isShowing = false;
  }

  static void dismissAll() {
    _queue.clear();
    _dismiss();
  }
}
