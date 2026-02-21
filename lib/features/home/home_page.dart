/// Home page with feature shortcuts
library;

import 'package:flutter/material.dart';
import '../../shared/widgets/feature_card.dart';

/// Home page widget
class HomePage extends StatelessWidget {
  final VoidCallback? onYouTubeTap;

  const HomePage({
    super.key,
    this.onYouTubeTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(40),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Welcome section
          Text(
            'Welcome to YouTube Converter',
            style: theme.textTheme.headlineMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 8),

          Text(
            'Choose a feature to get started',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),

          const SizedBox(height: 32),

          // Features section
          Text(
            'Features',
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),

          const SizedBox(height: 16),

          // Feature cards grid
          LayoutBuilder(
            builder: (context, constraints) {
              final crossAxisCount = constraints.maxWidth > 1200
                  ? 4
                  : constraints.maxWidth > 800
                      ? 3
                      : constraints.maxWidth > 500
                          ? 2
                          : 1;

              return GridView.count(
                crossAxisCount: crossAxisCount,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 16,
                crossAxisSpacing: 16,
                childAspectRatio: 1.2,
                children: [
                  // YouTube Download (enabled)
                  FeatureCard(
                    icon: Icons.video_library,
                    title: 'YouTube Downloader',
                    description: 'Download videos and audio from YouTube',
                    onTap: onYouTubeTap,
                    enabled: true,
                  ),

                  // Trimming & Editing (disabled - future)
                  const FeatureCard(
                    icon: Icons.content_cut,
                    title: 'Trimming & Editing',
                    description: 'Cut and edit your media files',
                    enabled: false,
                  ),

                  // File Converter (disabled - future)
                  const FeatureCard(
                    icon: Icons.transform,
                    title: 'File Converter',
                    description: 'Convert between audio and video formats',
                    enabled: false,
                  ),

                  // Movie Downloader (disabled - future)
                  const FeatureCard(
                    icon: Icons.movie,
                    title: 'Movie Downloader',
                    description: 'Download movies from supported sources',
                    enabled: false,
                  ),
                ],
              );
            },
          ),

          const SizedBox(height: 40),

          // Quick tips section
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer.withOpacity(0.3),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: theme.colorScheme.primary.withOpacity(0.2),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.lightbulb_outline,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Quick Tip',
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.primary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Text(
                  'Simply paste a YouTube URL and the app will automatically detect the video. '
                  'You can then choose to download as audio (MP3, M4A, etc.) or video (MP4, etc.).',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
