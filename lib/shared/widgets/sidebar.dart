/// Sidebar navigation widget
library;

import 'package:flutter/material.dart';

/// Sidebar navigation destination
class NavDestination {
  final IconData icon;
  final IconData selectedIcon;
  final String label;
  final String tooltip;

  const NavDestination({
    required this.icon,
    required this.selectedIcon,
    required this.label,
    required this.tooltip,
  });
}

/// Sidebar navigation widget
class AppSidebar extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;
  final List<NavDestination> destinations;

  const AppSidebar({
    super.key,
    required this.selectedIndex,
    required this.onDestinationSelected,
    required this.destinations,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return NavigationRail(
      selectedIndex: selectedIndex,
      onDestinationSelected: onDestinationSelected,
      labelType: NavigationRailLabelType.all,
      leading: Column(
        children: [
          const SizedBox(height: 8),
          // App logo/icon
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(
              Icons.download_rounded,
              color: theme.colorScheme.primary,
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
      destinations: destinations.map((dest) {
        return NavigationRailDestination(
          icon: Icon(dest.icon),
          selectedIcon: Icon(dest.selectedIcon),
          label: Text(dest.label),
        );
      }).toList(),
      trailing: Expanded(
        child: Align(
          alignment: Alignment.bottomCenter,
          child: Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Help button
                IconButton(
                  icon: const Icon(Icons.help_outline),
                  tooltip: 'Help & FAQ',
                  onPressed: () {
                    // Show help dialog
                    showDialog(
                      context: context,
                      builder: (context) => _HelpDialog(),
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Help dialog
class _HelpDialog extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AlertDialog(
      title: Row(
        children: [
          Icon(Icons.help_outline, color: theme.colorScheme.primary),
          const SizedBox(width: 8),
          const Text('Help & FAQ'),
        ],
      ),
      content: const SizedBox(
        width: 400,
        height: 300,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Quick Tips',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 8),
            ListTile(
              leading: Icon(Icons.link),
              title: Text('Paste a YouTube URL'),
              subtitle: Text(
                  'The app will automatically detect and fetch video info'),
              contentPadding: EdgeInsets.zero,
            ),
            ListTile(
              leading: Icon(Icons.download),
              title: Text('Choose quality'),
              subtitle:
                  Text('Select audio or video quality before downloading'),
              contentPadding: EdgeInsets.zero,
            ),
            ListTile(
              leading: Icon(Icons.settings),
              title: Text('Customize settings'),
              subtitle: Text('Change theme, default format, and more'),
              contentPadding: EdgeInsets.zero,
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Close'),
        ),
        FilledButton(
          onPressed: () {
            Navigator.of(context).pop();
            // Navigate to FAQ page
          },
          child: const Text('View Full FAQ'),
        ),
      ],
    );
  }
}
