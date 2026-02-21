/// Settings page with all application settings
library;

import 'package:flutter/material.dart' hide ThemeMode;
import '../../core/models/app_settings.dart';
import '../../core/models/update_config.dart';
import '../../core/services/settings_service.dart';
import '../../core/services/log_service.dart';

/// Settings page widget
class SettingsPage extends StatefulWidget {
  final AppSettings settings;
  final SettingsService settingsService;

  const SettingsPage({
    super.key,
    required this.settings,
    required this.settingsService,
  });

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late AppSettings _settings;
  final LogService _logService = LogService();

  @override
  void initState() {
    super.initState();
    _settings = widget.settings;
  }

  void _updateSettings(AppSettings newSettings) {
    setState(() => _settings = newSettings);
    widget.settingsService.updateSettings(newSettings);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Text(
            'Settings',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),

          const SizedBox(height: 24),

          // Appearance Section
          _SettingsSection(
            title: 'Appearance',
            icon: Icons.palette,
            children: [
              // Theme mode
              ListTile(
                title: const Text('Theme'),
                subtitle: Text(_settings.ui.themeMode.label),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _showThemeDialog(),
              ),

              // Accent color
              ListTile(
                title: const Text('Accent Color'),
                subtitle: Text(_settings.ui.accentColorHex),
                trailing: Container(
                  width: 24,
                  height: 24,
                  decoration: BoxDecoration(
                    color: _parseColor(_settings.ui.accentColorHex),
                    shape: BoxShape.circle,
                  ),
                ),
                onTap: () => _showColorPicker(),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Downloads Section
          _SettingsSection(
            title: 'Downloads',
            icon: Icons.download,
            children: [
              // Default download type
              ListTile(
                title: const Text('Default Download Type'),
                subtitle: Text(
                    _settings.defaults.kind == 'audio' ? 'Audio' : 'Video'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _showDownloadTypeDialog(),
              ),

              // Default audio format
              ListTile(
                title: const Text('Default Audio Format'),
                subtitle: Text(_settings.defaults.format.toUpperCase()),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _showAudioFormatDialog(),
              ),

              // EZ Mode
              SwitchListTile(
                title: const Text('EZ Mode'),
                subtitle:
                    const Text('Simplified interface for quick downloads'),
                value: _settings.ez.sanitizeRadioLinks,
                onChanged: (value) {
                  _updateSettings(_settings.copyWith(
                    ez: _settings.ez.copyWith(sanitizeRadioLinks: value),
                  ));
                },
              ),
            ],
          ),

          const SizedBox(height: 16),

          // SponsorBlock Section
          _SettingsSection(
            title: 'SponsorBlock',
            icon: Icons.block,
            children: [
              SwitchListTile(
                title: const Text('Enable SponsorBlock'),
                subtitle: const Text('Remove sponsored segments from videos'),
                value: _settings.defaults.sponsorblockEnabled,
                onChanged: (value) {
                  _updateSettings(_settings.copyWith(
                    defaults: _settings.defaults.copyWith(
                      sponsorblockEnabled: value,
                    ),
                  ));
                },
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Updates Section
          _SettingsSection(
            title: 'Updates',
            icon: Icons.update,
            children: [
              ListTile(
                title: const Text('App Updates'),
                subtitle: Text(_settings.appUpdate.action.label),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _showUpdateActionDialog(),
              ),
              ListTile(
                title: const Text('yt-dlp Updates'),
                subtitle: Text(_settings.ytdlpUpdate.schedule.cadence.label),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _showYtDlpUpdateDialog(),
              ),
            ],
          ),

          const SizedBox(height: 16),

          // Maintenance Section
          _SettingsSection(
            title: 'Maintenance',
            icon: Icons.build,
            children: [
              ListTile(
                title: const Text('Export Logs'),
                subtitle: const Text('Export logs for troubleshooting'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _exportLogs(),
              ),
              ListTile(
                title: const Text('Clear Logs'),
                subtitle: const Text('Delete all log files'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _clearLogs(),
              ),
              ListTile(
                title: const Text('Reset Settings'),
                subtitle: const Text('Reset all settings to defaults'),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => _resetSettings(),
              ),
            ],
          ),

          const SizedBox(height: 24),

          // Version info
          Center(
            child: Text(
              'Version 1.0.0',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _parseColor(String hex) {
    try {
      return Color(
        int.parse(hex.replaceFirst('#', '0xFF')),
      );
    } catch (e) {
      return const Color(0xFFF28C28);
    }
  }

  void _showThemeDialog() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Theme'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: ThemeMode.values.map((mode) {
              return RadioListTile<ThemeMode>(
                title: Text(mode.label),
                value: mode,
                groupValue: _settings.ui.themeMode,
                onChanged: (value) {
                  if (value != null) {
                    _updateSettings(_settings.copyWith(
                      ui: _settings.ui.copyWith(themeMode: value),
                    ));
                  }
                  Navigator.of(context).pop();
                },
              );
            }).toList(),
          ),
        );
      },
    );
  }

  void _showColorPicker() {
    // Simple color picker dialog
    final colors = [
      '#F28C28', // Orange (default)
      '#2196F3', // Blue
      '#4CAF50', // Green
      '#E91E63', // Pink
      '#9C27B0', // Purple
      '#FF5722', // Deep Orange
      '#00BCD4', // Cyan
      '#FFEB3B', // Yellow
    ];

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Accent Color'),
          content: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: colors.map((hex) {
              final color = _parseColor(hex);
              final isSelected = _settings.ui.accentColorHex == hex;

              return GestureDetector(
                onTap: () {
                  _updateSettings(_settings.copyWith(
                    ui: _settings.ui.copyWith(accentColorHex: hex),
                  ));
                  Navigator.of(context).pop();
                },
                child: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: color,
                    shape: BoxShape.circle,
                    border: isSelected
                        ? Border.all(color: Colors.white, width: 3)
                        : null,
                    boxShadow: [
                      BoxShadow(
                        color: color.withOpacity(0.4),
                        blurRadius: 4,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: isSelected
                      ? const Icon(Icons.check, color: Colors.white, size: 20)
                      : null,
                ),
              );
            }).toList(),
          ),
        );
      },
    );
  }

  void _showDownloadTypeDialog() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Default Download Type'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              RadioListTile<String>(
                title: const Text('Audio'),
                value: 'audio',
                groupValue: _settings.defaults.kind,
                onChanged: (value) {
                  if (value != null) {
                    _updateSettings(_settings.copyWith(
                      defaults: _settings.defaults.copyWith(kind: value),
                    ));
                  }
                  Navigator.of(context).pop();
                },
              ),
              RadioListTile<String>(
                title: const Text('Video'),
                value: 'video',
                groupValue: _settings.defaults.kind,
                onChanged: (value) {
                  if (value != null) {
                    _updateSettings(_settings.copyWith(
                      defaults: _settings.defaults.copyWith(kind: value),
                    ));
                  }
                  Navigator.of(context).pop();
                },
              ),
            ],
          ),
        );
      },
    );
  }

  void _showAudioFormatDialog() {
    final formats = ['mp3', 'm4a', 'opus', 'wav', 'flac'];

    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Default Audio Format'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: formats.map((format) {
              return RadioListTile<String>(
                title: Text(format.toUpperCase()),
                value: format,
                groupValue: _settings.defaults.format,
                onChanged: (value) {
                  if (value != null) {
                    _updateSettings(_settings.copyWith(
                      defaults: _settings.defaults.copyWith(format: value),
                    ));
                  }
                  Navigator.of(context).pop();
                },
              );
            }).toList(),
          ),
        );
      },
    );
  }

  void _showUpdateActionDialog() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('App Updates'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: UpdateAction.values.map((action) {
              return RadioListTile<UpdateAction>(
                title: Text(action.label),
                value: action,
                groupValue: _settings.appUpdate.action,
                onChanged: (value) {
                  if (value != null) {
                    _updateSettings(_settings.copyWith(
                      appUpdate: _settings.appUpdate.copyWith(action: value),
                    ));
                  }
                  Navigator.of(context).pop();
                },
              );
            }).toList(),
          ),
        );
      },
    );
  }

  void _showYtDlpUpdateDialog() {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('yt-dlp Updates'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: UpdateCadence.values.map((cadence) {
              return RadioListTile<UpdateCadence>(
                title: Text(cadence.label),
                value: cadence,
                groupValue: _settings.ytdlpUpdate.schedule.cadence,
                onChanged: (value) {
                  if (value != null) {
                    _updateSettings(_settings.copyWith(
                      ytdlpUpdate: _settings.ytdlpUpdate.copyWith(
                        schedule: _settings.ytdlpUpdate.schedule.copyWith(
                          cadence: value,
                        ),
                      ),
                    ));
                  }
                  Navigator.of(context).pop();
                },
              );
            }).toList(),
          ),
        );
      },
    );
  }

  Future<void> _exportLogs() async {
    final path = await _logService.exportLogs();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(path != null
              ? 'Logs exported successfully'
              : 'No logs to export'),
        ),
      );
    }
  }

  Future<void> _clearLogs() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Clear Logs'),
          content: const Text('Are you sure you want to delete all log files?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Clear'),
            ),
          ],
        );
      },
    );

    if (confirmed == true) {
      await _logService.clearLogs();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Logs cleared')),
        );
      }
    }
  }

  Future<void> _resetSettings() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Reset Settings'),
          content: const Text(
              'Are you sure you want to reset all settings to defaults?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Reset'),
            ),
          ],
        );
      },
    );

    if (confirmed == true) {
      await widget.settingsService.resetToDefaults();
      setState(() => _settings = widget.settingsService.settings);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Settings reset to defaults')),
        );
      }
    }
  }
}

/// Settings section widget
class _SettingsSection extends StatelessWidget {
  final String title;
  final IconData icon;
  final List<Widget> children;

  const _SettingsSection({
    required this.title,
    required this.icon,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            child: Row(
              children: [
                Icon(
                  icon,
                  size: 20,
                  color: theme.colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: theme.colorScheme.primary,
                  ),
                ),
              ],
            ),
          ),
          ...children,
        ],
      ),
    );
  }
}
