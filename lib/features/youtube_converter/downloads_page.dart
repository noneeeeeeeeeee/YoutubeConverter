/// Step 3: Downloads page for YouTube converter
library;

import 'package:flutter/material.dart';
import '../../core/models/download_item.dart';
import '../../core/services/download_service.dart';

/// Downloads page widget
class DownloadsPage extends StatefulWidget {
  final Map<String, dynamic>? selection;
  final VoidCallback? onDone;
  final VoidCallback? onBack;

  const DownloadsPage({
    super.key,
    this.selection,
    this.onDone,
    this.onBack,
  });

  @override
  State<DownloadsPage> createState() => _DownloadsPageState();
}

class _DownloadsPageState extends State<DownloadsPage> {
  final DownloadService _downloadService = DownloadService();

  @override
  void initState() {
    super.initState();
    _downloadService.addListener(_onDownloadsChanged);
    _startDownloads();
  }

  void _onDownloadsChanged() {
    setState(() {});

    // Check if all downloads are complete
    final activeCount = _downloadService.activeDownloads.length;
    if (activeCount == 0 && _downloadService.downloads.isNotEmpty) {
      // All downloads finished
    }
  }

  Future<void> _startDownloads() async {
    if (widget.selection == null) return;

    final items = widget.selection!['items'] as List;
    final kind = widget.selection!['kind'] as String;
    final format = widget.selection!['format'] as String;
    final quality = widget.selection!['quality'] as String;
    final outputPath = widget.selection!['outputPath'] as String;

    for (final video in items) {
      await _downloadService.startDownload(
        url: video.webpageUrl,
        format: format,
        outputPath: outputPath,
        quality: quality,
        audioOnly: kind == 'audio',
      );
    }
  }

  @override
  void dispose() {
    _downloadService.removeListener(_onDownloadsChanged);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final downloads = _downloadService.downloads;
    final activeCount = _downloadService.activeDownloads.length;
    final completedCount = _downloadService.completedDownloads.length;

    return Column(
      children: [
        // Header
        Container(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    'Downloads',
                    style: theme.textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const Spacer(),
                  if (activeCount > 0)
                    TextButton.icon(
                      onPressed: () => _downloadService.cancelAll(),
                      icon: const Icon(Icons.cancel),
                      label: const Text('Cancel All'),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                '$activeCount active • $completedCount completed',
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),

        const Divider(),

        // Downloads list
        Expanded(
          child: downloads.isEmpty
              ? _buildEmptyState(theme)
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: downloads.length,
                  itemBuilder: (context, index) {
                    return _DownloadItemCard(
                      item: downloads[index],
                      onCancel: () =>
                          _downloadService.cancelDownload(downloads[index].id),
                      onRetry: downloads[index].state.canRetry
                          ? () => _downloadService
                              .retryDownload(downloads[index].id)
                          : null,
                      onRemove: () =>
                          _downloadService.removeDownload(downloads[index].id),
                    );
                  },
                ),
        ),

        // Footer
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            border: Border(
              top: BorderSide(color: theme.colorScheme.outline),
            ),
          ),
          child: Row(
            children: [
              if (widget.onBack != null)
                OutlinedButton.icon(
                  onPressed: activeCount > 0 ? null : widget.onBack,
                  icon: const Icon(Icons.arrow_back),
                  label: const Text('Back'),
                ),
              const Spacer(),
              if (completedCount > 0 && activeCount == 0)
                FilledButton.icon(
                  onPressed: widget.onDone,
                  icon: const Icon(Icons.check),
                  label: const Text('Done'),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState(ThemeData theme) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.download_outlined,
            size: 64,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(height: 16),
          Text(
            'No downloads yet',
            style: theme.textTheme.titleMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

/// Download item card widget
class _DownloadItemCard extends StatelessWidget {
  final DownloadItem item;
  final VoidCallback? onCancel;
  final VoidCallback? onRetry;
  final VoidCallback? onRemove;

  const _DownloadItemCard({
    required this.item,
    this.onCancel,
    this.onRetry,
    this.onRemove,
  });

  Color _getStateColor(ThemeData theme) {
    switch (item.state) {
      case DownloadState.completed:
        return Colors.green;
      case DownloadState.failed:
        return theme.colorScheme.error;
      case DownloadState.downloading:
      case DownloadState.converting:
      case DownloadState.fetching:
        return theme.colorScheme.primary;
      default:
        return theme.colorScheme.onSurfaceVariant;
    }
  }

  IconData _getStateIcon() {
    switch (item.state) {
      case DownloadState.completed:
        return Icons.check_circle;
      case DownloadState.failed:
        return Icons.error;
      case DownloadState.downloading:
      case DownloadState.converting:
      case DownloadState.fetching:
        return Icons.downloading;
      case DownloadState.paused:
        return Icons.pause_circle;
      case DownloadState.cancelled:
        return Icons.cancel;
      default:
        return Icons.pending;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Title and state
            Row(
              children: [
                Expanded(
                  child: Text(
                    item.title ?? item.sourceUrl,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                Icon(
                  _getStateIcon(),
                  size: 20,
                  color: _getStateColor(theme),
                ),
              ],
            ),

            const SizedBox(height: 8),

            // Progress bar (for active downloads)
            if (item.state.isActive) ...[
              LinearProgressIndicator(
                value: item.progress,
                backgroundColor: theme.colorScheme.primaryContainer,
              ),
              const SizedBox(height: 4),
              Text(
                item.progressPercent,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],

            // Error message
            if (item.state == DownloadState.failed && item.error != null) ...[
              const SizedBox(height: 8),
              Text(
                item.error!,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.error,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ],

            const SizedBox(height: 8),

            // Actions
            Row(
              children: [
                if (item.state.isActive && onCancel != null)
                  TextButton.icon(
                    onPressed: onCancel,
                    icon: const Icon(Icons.cancel, size: 18),
                    label: const Text('Cancel'),
                  ),
                if (item.state.canRetry && onRetry != null)
                  TextButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh, size: 18),
                    label: const Text('Retry'),
                  ),
                if (item.state.isComplete && onRemove != null)
                  TextButton.icon(
                    onPressed: onRemove,
                    icon: const Icon(Icons.delete, size: 18),
                    label: const Text('Remove'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
