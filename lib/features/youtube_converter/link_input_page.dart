/// Step 1: Link input page for YouTube converter
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../core/models/video_info.dart';
import '../../core/services/download_service.dart';

/// Link input page widget
class LinkInputPage extends StatefulWidget {
  final VoidCallback? onNext;
  final Function(List<VideoInfo>)? onVideosSelected;

  const LinkInputPage({
    super.key,
    this.onNext,
    this.onVideosSelected,
  });

  @override
  State<LinkInputPage> createState() => _LinkInputPageState();
}

class _LinkInputPageState extends State<LinkInputPage> {
  final TextEditingController _urlController = TextEditingController();
  final DownloadService _downloadService = DownloadService();

  bool _isLoading = false;
  bool _isMultiSelectMode = false;
  VideoInfo? _videoInfo;
  List<VideoInfo> _selectedVideos = [];
  String? _error;

  @override
  void initState() {
    super.initState();
    _downloadService.initialize();

    // Listen for clipboard paste
    _checkClipboard();
  }

  Future<void> _checkClipboard() async {
    // Auto-paste if clipboard contains a YouTube URL
    final data = await Clipboard.getData(Clipboard.kTextPlain);
    final text = data?.text ?? '';

    if (_isYouTubeUrl(text) && _urlController.text.isEmpty) {
      // Optionally auto-paste (can be configured in settings)
      // _urlController.text = text;
      // _fetchVideoInfo();
    }
  }

  bool _isYouTubeUrl(String url) {
    final youtubeRegex = RegExp(
      r'^(https?://)?(www\.)?(youtube\.com|youtu\.be|music\.youtube\.com)/.+$',
      caseSensitive: false,
    );
    return youtubeRegex.hasMatch(url);
  }

  Future<void> _fetchVideoInfo() async {
    final url = _urlController.text.trim();

    if (url.isEmpty) {
      setState(() => _error = 'Please enter a URL');
      return;
    }

    if (!_isYouTubeUrl(url)) {
      setState(() => _error = 'Please enter a valid YouTube URL');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
      _videoInfo = null;
    });

    try {
      final info = await _downloadService.fetchVideoInfo(url);

      if (info != null) {
        setState(() {
          _videoInfo = info;
          _isLoading = false;
        });

        // If it's a playlist, switch to multi-select mode
        if (info.isPlaylist && info.playlistEntries != null) {
          setState(() {
            _isMultiSelectMode = true;
            _selectedVideos = info.playlistEntries!.take(10).toList();
          });
        }
      } else {
        setState(() {
          _error = 'Could not fetch video information';
          _isLoading = false;
        });
      }
    } catch (e) {
      setState(() {
        _error = 'Error: $e';
        _isLoading = false;
      });
    }
  }

  void _proceedToNext() {
    if (_isMultiSelectMode) {
      widget.onVideosSelected?.call(_selectedVideos);
    } else if (_videoInfo != null) {
      widget.onVideosSelected?.call([_videoInfo!]);
    }
    widget.onNext?.call();
  }

  @override
  void dispose() {
    _urlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // URL Input Section
          Text(
            'Enter YouTube URL',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),

          const SizedBox(height: 12),

          // URL Input with paste button
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _urlController,
                  decoration: InputDecoration(
                    hintText: 'https://youtube.com/watch?v=...',
                    prefixIcon: const Icon(Icons.link),
                    suffixIcon: _urlController.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear),
                            onPressed: () {
                              _urlController.clear();
                              setState(() {
                                _videoInfo = null;
                                _error = null;
                              });
                            },
                          )
                        : null,
                    errorText: _error,
                  ),
                  onSubmitted: (_) => _fetchVideoInfo(),
                  onChanged: (_) => setState(() {}),
                ),
              ),
              const SizedBox(width: 8),
              IconButton.outlined(
                icon: const Icon(Icons.paste),
                tooltip: 'Paste from clipboard',
                onPressed: () async {
                  final data = await Clipboard.getData(Clipboard.kTextPlain);
                  if (data?.text != null) {
                    _urlController.text = data!.text!;
                    setState(() {});
                  }
                },
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Fetch button
          FilledButton.icon(
            onPressed: _isLoading ? null : _fetchVideoInfo,
            icon: _isLoading
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.search),
            label: Text(_isLoading ? 'Fetching...' : 'Fetch Video Info'),
          ),

          // Video Preview
          if (_videoInfo != null && !_videoInfo!.isPlaylist) ...[
            const SizedBox(height: 24),
            _buildVideoPreview(theme),
          ],

          // Playlist Preview
          if (_videoInfo != null && _videoInfo!.isPlaylist) ...[
            const SizedBox(height: 24),
            _buildPlaylistPreview(theme),
          ],

          // Proceed Button
          if (_videoInfo != null) ...[
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: _proceedToNext,
              icon: const Icon(Icons.arrow_forward),
              label: const Text('Continue to Quality Selection'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildVideoPreview(ThemeData theme) {
    final video = _videoInfo!;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Thumbnail
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Container(
                width: 160,
                height: 90,
                color: theme.colorScheme.surfaceVariant,
                child: video.thumbnail != null
                    ? Image.network(
                        video.thumbnail!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) =>
                            const Icon(Icons.video_library),
                      )
                    : const Icon(Icons.video_library),
              ),
            ),

            const SizedBox(width: 16),

            // Info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    video.title,
                    style: theme.textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  if (video.uploader != null)
                    Text(
                      video.uploader!,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      if (video.duration != null)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.surfaceVariant,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            video.formattedDuration,
                            style: theme.textTheme.labelSmall,
                          ),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlaylistPreview(ThemeData theme) {
    final playlist = _videoInfo!;
    final entries = playlist.playlistEntries ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          playlist.playlistTitle ?? 'Playlist',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),

        Text(
          '${entries.length} videos',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),

        const SizedBox(height: 12),

        // Video list
        SizedBox(
          height: 300,
          child: ListView.builder(
            itemCount: entries.length,
            itemBuilder: (context, index) {
              final video = entries[index];
              final isSelected = _selectedVideos.contains(video);

              return ListTile(
                leading: Checkbox(
                  value: isSelected,
                  onChanged: (value) {
                    setState(() {
                      if (value == true) {
                        _selectedVideos.add(video);
                      } else {
                        _selectedVideos.remove(video);
                      }
                    });
                  },
                ),
                title: Text(
                  video.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                subtitle: video.uploader != null ? Text(video.uploader!) : null,
                trailing: Text(video.formattedDuration),
                onTap: () {
                  setState(() {
                    if (isSelected) {
                      _selectedVideos.remove(video);
                    } else {
                      _selectedVideos.add(video);
                    }
                  });
                },
              );
            },
          ),
        ),

        Text(
          '${_selectedVideos.length} videos selected',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.primary,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}
