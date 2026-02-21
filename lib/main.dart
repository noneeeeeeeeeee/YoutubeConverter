/// YouTube Converter App - Main Entry Point
///
/// A modern YouTube converter built with Flutter and Material 3 Expressive design.
/// This app allows users to download videos and audio from YouTube with a
/// user-friendly interface suitable for both beginners and advanced users.

import 'package:flutter/material.dart';
import 'core/models/video_info.dart';
import 'core/services/settings_service.dart';
import 'core/services/download_service.dart';
import 'core/services/update_service.dart';
import 'core/services/log_service.dart';
import 'shared/theme/app_theme.dart';
import 'shared/widgets/sidebar.dart';
import 'shared/widgets/stepper_widget.dart';
import 'features/home/home_page.dart';
import 'features/youtube_converter/link_input_page.dart';
import 'features/youtube_converter/quality_selection_page.dart';
import 'features/youtube_converter/downloads_page.dart';
import 'features/settings/settings_page.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize services
  final settingsService = SettingsService();
  await settingsService.initialize();

  final logService = LogService();
  await logService.initialize();

  final downloadService = DownloadService();
  await downloadService.initialize();

  final updateService = UpdateService();
  await updateService.initialize();

  runApp(
    YouTubeConverterApp(
      settingsService: settingsService,
      logService: logService,
      downloadService: downloadService,
      updateService: updateService,
    ),
  );
}

/// Main application widget
class YouTubeConverterApp extends StatelessWidget {
  final SettingsService settingsService;
  final LogService logService;
  final DownloadService downloadService;
  final UpdateService updateService;

  const YouTubeConverterApp({
    super.key,
    required this.settingsService,
    required this.logService,
    required this.downloadService,
    required this.updateService,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: settingsService,
      builder: (context, _) {
        final settings = settingsService.settings;
        final accentColor = _parseColor(settings.ui.accentColorHex);

        return MaterialApp(
          title: 'YouTube Converter',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.getTheme(
            settings.ui.themeMode.name,
            accentColor: accentColor,
          ),
          home: MainScreen(
            settingsService: settingsService,
            downloadService: downloadService,
            updateService: updateService,
          ),
        );
      },
    );
  }

  Color _parseColor(String hex) {
    try {
      return Color(int.parse(hex.replaceFirst('#', '0xFF')));
    } catch (e) {
      return const Color(0xFFF28C28);
    }
  }
}

/// Main screen with navigation
class MainScreen extends StatefulWidget {
  final SettingsService settingsService;
  final DownloadService downloadService;
  final UpdateService updateService;

  const MainScreen({
    super.key,
    required this.settingsService,
    required this.downloadService,
    required this.updateService,
  });

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _selectedIndex = 0;

  // YouTube converter state
  int _converterStep = 0;
  List<VideoInfo> _selectedVideos = [];
  Map<String, dynamic>? _downloadSelection;

  // Navigation destinations
  final List<NavDestination> _destinations = const [
    NavDestination(
      icon: Icons.home_outlined,
      selectedIcon: Icons.home,
      label: 'Home',
      tooltip: 'Home',
    ),
    NavDestination(
      icon: Icons.video_library_outlined,
      selectedIcon: Icons.video_library,
      label: 'Download',
      tooltip: 'YouTube Download',
    ),
    NavDestination(
      icon: Icons.settings_outlined,
      selectedIcon: Icons.settings,
      label: 'Settings',
      tooltip: 'Settings',
    ),
  ];

  void _onDestinationSelected(int index) {
    setState(() {
      _selectedIndex = index;

      // Reset converter state when leaving converter
      if (index != 1) {
        _converterStep = 0;
        _selectedVideos = [];
        _downloadSelection = null;
      }
    });
  }

  void _startYouTubeDownload() {
    setState(() {
      _selectedIndex = 1;
      _converterStep = 0;
      _selectedVideos = [];
      _downloadSelection = null;
    });
  }

  void _onVideosSelected(List<VideoInfo> videos) {
    setState(() {
      _selectedVideos = videos;
      _converterStep = 1;
    });
  }

  void _onSelectionConfirmed(Map<String, dynamic> selection) {
    setState(() {
      _downloadSelection = selection;
      _converterStep = 2;
    });
  }

  void _onDownloadsComplete() {
    setState(() {
      _selectedIndex = 0;
      _converterStep = 0;
      _selectedVideos = [];
      _downloadSelection = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          // Sidebar
          AppSidebar(
            selectedIndex: _selectedIndex,
            onDestinationSelected: _onDestinationSelected,
            destinations: _destinations,
          ),

          // Main content
          Expanded(
            child: Column(
              children: [
                // Stepper (only visible in converter mode)
                if (_selectedIndex == 1)
                  StepperWidget(
                    steps: const ['Select', 'Quality', 'Download'],
                    currentStep: _converterStep,
                  ),

                // Page content
                Expanded(
                  child: _buildPage(),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPage() {
    switch (_selectedIndex) {
      case 0:
        return HomePage(
          onYouTubeTap: _startYouTubeDownload,
        );

      case 1:
        return _buildConverterPage();

      case 2:
        return SettingsPage(
          settings: widget.settingsService.settings,
          settingsService: widget.settingsService,
        );

      default:
        return const Center(child: Text('Unknown page'));
    }
  }

  Widget _buildConverterPage() {
    switch (_converterStep) {
      case 0:
        return LinkInputPage(
          onNext: () => setState(() => _converterStep = 1),
          onVideosSelected: _onVideosSelected,
        );

      case 1:
        return QualitySelectionPage(
          videos: _selectedVideos,
          settings: widget.settingsService.settings,
          onNext: () => setState(() => _converterStep = 2),
          onBack: () => setState(() => _converterStep = 0),
          onSelectionConfirmed: _onSelectionConfirmed,
        );

      case 2:
        return DownloadsPage(
          selection: _downloadSelection,
          onDone: _onDownloadsComplete,
          onBack: () => setState(() => _converterStep = 1),
        );

      default:
        return const Center(child: Text('Unknown step'));
    }
  }
}
