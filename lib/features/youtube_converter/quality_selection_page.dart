/// Step 2: Quality selection page for YouTube converter
library;

import 'package:flutter/material.dart';
import '../../core/models/video_info.dart';
import '../../core/models/app_settings.dart';

/// Quality selection page widget
class QualitySelectionPage extends StatefulWidget {
  final List<VideoInfo> videos;
  final AppSettings settings;
  final VoidCallback? onNext;
  final VoidCallback? onBack;
  final Function(Map<String, dynamic>)? onSelectionConfirmed;

  const QualitySelectionPage({
    super.key,
    required this.videos,
    required this.settings,
    this.onNext,
    this.onBack,
    this.onSelectionConfirmed,
  });

  @override
  State<QualitySelectionPage> createState() => _QualitySelectionPageState();
}

class _QualitySelectionPageState extends State<QualitySelectionPage> {
  String _downloadKind = 'audio'; // 'audio' or 'video'
  String _audioFormat = 'mp3';
  String _videoFormat = 'mp4';
  String _audioQuality = 'best';
  String _videoQuality = 'best';
  String _outputPath = '';

  bool _showAdvanced = false;
  bool _sponsorblockEnabled = false;
  bool _downloadSubtitles = false;

  @override
  void initState() {
    super.initState();
    _loadDefaults();
  }

  void _loadDefaults() {
    final defaults = widget.settings.defaults;
    setState(() {
      _downloadKind = defaults.kind;
      _audioFormat = defaults.kind == 'audio' ? defaults.format : 'mp3';
      _videoFormat = defaults.kind == 'video' ? defaults.format : 'mp4';
      _sponsorblockEnabled = defaults.sponsorblockEnabled;
      _downloadSubtitles = defaults.downloadSubtitles;
      _outputPath = widget.settings.lastDownloadDir;
    });
  }

  void _confirmSelection() {
    final selection = {
      'items': widget.videos,
      'kind': _downloadKind,
      'format': _downloadKind == 'audio' ? _audioFormat : _videoFormat,
      'quality': _downloadKind == 'audio' ? _audioQuality : _videoQuality,
      'outputPath': _outputPath,
      'sponsorblockEnabled': _sponsorblockEnabled,
      'downloadSubtitles': _downloadSubtitles,
    };

    widget.onSelectionConfirmed?.call(selection);
    widget.onNext?.call();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Video count summary
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer.withOpacity(0.3),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.video_library,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 12),
                Text(
                  '${widget.videos.length} video${widget.videos.length > 1 ? 's' : ''} selected',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 24),

          // Download type selection (Audio/Video)
          Text(
            'Download Type',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),

          const SizedBox(height: 12),

          SegmentedButton<String>(
            segments: const [
              ButtonSegment(
                value: 'audio',
                label: Text('Audio'),
                icon: Icon(Icons.audiotrack),
              ),
              ButtonSegment(
                value: 'video',
                label: Text('Video'),
                icon: Icon(Icons.videocam),
              ),
            ],
            selected: {_downloadKind},
            onSelectionChanged: (Set<String> selection) {
              setState(() => _downloadKind = selection.first);
            },
          ),

          const SizedBox(height: 24),

          // Format selection
          Text(
            'Format',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),

          const SizedBox(height: 12),

          if (_downloadKind == 'audio')
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: ['mp3', 'm4a', 'opus', 'wav', 'flac'].map((format) {
                return ChoiceChip(
                  label: Text(format.toUpperCase()),
                  selected: _audioFormat == format,
                  onSelected: (selected) {
                    if (selected) setState(() => _audioFormat = format);
                  },
                );
              }).toList(),
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: ['mp4', 'webm', 'mkv'].map((format) {
                return ChoiceChip(
                  label: Text(format.toUpperCase()),
                  selected: _videoFormat == format,
                  onSelected: (selected) {
                    if (selected) setState(() => _videoFormat = format);
                  },
                );
              }).toList(),
            ),

          const SizedBox(height: 24),

          // Quality selection
          Text(
            'Quality',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),

          const SizedBox(height: 12),

          if (_downloadKind == 'audio')
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ChoiceChip(
                  label: const Text('Best'),
                  selected: _audioQuality == 'best',
                  onSelected: (selected) {
                    if (selected) setState(() => _audioQuality = 'best');
                  },
                ),
                ...['320k', '256k', '192k', '128k', '96k'].map((quality) {
                  return ChoiceChip(
                    label: Text(quality),
                    selected: _audioQuality == quality,
                    onSelected: (selected) {
                      if (selected) setState(() => _audioQuality = quality);
                    },
                  );
                }),
              ],
            )
          else
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                ChoiceChip(
                  label: const Text('Best'),
                  selected: _videoQuality == 'best',
                  onSelected: (selected) {
                    if (selected) setState(() => _videoQuality = 'best');
                  },
                ),
                ...['4K', '1080p', '720p', '480p', '360p'].map((quality) {
                  return ChoiceChip(
                    label: Text(quality),
                    selected: _videoQuality == quality,
                    onSelected: (selected) {
                      if (selected) setState(() => _videoQuality = quality);
                    },
                  );
                }),
              ],
            ),

          const SizedBox(height: 24),

          // Output directory
          Text(
            'Save Location',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),

          const SizedBox(height: 12),

          Row(
            children: [
              Expanded(
                child: TextField(
                  readOnly: true,
                  controller: TextEditingController(text: _outputPath),
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.folder),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.outlined(
                icon: const Icon(Icons.folder_open),
                tooltip: 'Choose folder',
                onPressed: () async {
                  // File picker would go here
                  // For now, just show a snackbar
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('File picker coming soon')),
                  );
                },
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Advanced options toggle
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Advanced Options'),
            trailing: Switch(
              value: _showAdvanced,
              onChanged: (value) => setState(() => _showAdvanced = value),
            ),
            onTap: () => setState(() => _showAdvanced = !_showAdvanced),
          ),

          // Advanced options
          if (_showAdvanced) ...[
            const Divider(),

            // SponsorBlock
            SwitchListTile(
              title: const Text('Remove Sponsor Segments'),
              subtitle:
                  const Text('Use SponsorBlock to skip sponsored content'),
              value: _sponsorblockEnabled,
              onChanged: (value) =>
                  setState(() => _sponsorblockEnabled = value),
            ),

            // Subtitles
            SwitchListTile(
              title: const Text('Download Subtitles'),
              subtitle: const Text('Download video subtitles if available'),
              value: _downloadSubtitles,
              onChanged: (value) => setState(() => _downloadSubtitles = value),
            ),
          ],

          const SizedBox(height: 32),

          // Navigation buttons
          Row(
            children: [
              OutlinedButton.icon(
                onPressed: widget.onBack,
                icon: const Icon(Icons.arrow_back),
                label: const Text('Back'),
              ),
              const Spacer(),
              FilledButton.icon(
                onPressed: _confirmSelection,
                icon: const Icon(Icons.download),
                label: const Text('Start Download'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
