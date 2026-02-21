/// FAQ entry model
library;

/// FAQ entry for help and troubleshooting
class FaqEntry {
  final String category;
  final String question;
  final String answer;

  const FaqEntry({
    required this.category,
    required this.question,
    required this.answer,
  });

  Map<String, dynamic> toJson() => {
        'category': category,
        'question': question,
        'answer': answer,
      };

  factory FaqEntry.fromJson(Map<String, dynamic> json) {
    return FaqEntry(
      category: json['category'] ?? '',
      question: json['question'] ?? '',
      answer: json['answer'] ?? '',
    );
  }
}

/// Default FAQ entries
class DefaultFaqEntries {
  static List<FaqEntry> get all => [
        // Downloads
        FaqEntry(
          category: 'Downloads',
          question: 'Can the app resume partial downloads?',
          answer: 'Yes it can, try it out! It may be buggy still.',
        ),
        FaqEntry(
          category: 'Downloads',
          question: 'How do I choose audio quality (e.g., 160k)?',
          answer:
              'In Step 3 (Quality), pick a target like \'best\' or an approximate bitrate (e.g., 160k). The app selects the closest available stream.',
        ),
        FaqEntry(
          category: 'Downloads',
          question: 'Downloads are very slow or keep failing',
          answer:
              'This can be caused by:\n• Network congestion or unstable connection\n• YouTube rate limiting (try waiting and retrying)\n• Antivirus blocking the download\n• Disk space running low\n• Proxy/VPN interfering with connection\n\nTry changing your network, disabling VPN temporarily, or clearing browser cache.',
        ),
        FaqEntry(
          category: 'Downloads',
          question: 'Video/audio is out of sync after download',
          answer:
              'This can happen with certain video formats. Try:\n• Selecting a different quality option\n• Using \'best\' quality instead of specific resolution\n• For audio-only, choose a direct audio format\n• Check if the original video has sync issues',
        ),
        FaqEntry(
          category: 'Downloads',
          question: 'Getting \'Video unavailable\' or \'Private video\' errors',
          answer:
              'This occurs when:\n• Video is private, unlisted, or deleted\n• Video is geo-blocked in your region\n• Age-restricted content requiring sign-in\n• Copyright takedown\n\nTry accessing the video in your browser first to confirm availability.',
        ),
        // Updates
        FaqEntry(
          category: 'Updates',
          question: 'What do the update schedules mean?',
          answer:
              'Off disables checks. Every Launch checks on startup. Daily/Weekly/Monthly check based on the last successful check time.',
        ),
        FaqEntry(
          category: 'Updates',
          question:
              'What is the difference between App updates and yt-dlp updates?',
          answer:
              'App updates refresh this application. yt-dlp updates refresh the bundled downloader binary. They can be scheduled independently.',
        ),
        FaqEntry(
          category: 'Updates',
          question: 'Update failed or app won\'t restart after update',
          answer:
              'Try these steps:\n• Close the app completely and restart manually\n• Check if antivirus is blocking the update\n• Run as administrator if on Windows\n• Download fresh copy from official source\n• Export logs before updating for troubleshooting',
        ),
        // SponsorBlock
        FaqEntry(
          category: 'SponsorBlock',
          question: 'How does SponsorBlock removal work?',
          answer:
              'When enabled, segments (e.g., sponsor/intro/outro) are removed using the community-maintained database. You can choose which categories to remove.',
        ),
        FaqEntry(
          category: 'SponsorBlock',
          question: 'SponsorBlock isn\'t removing segments',
          answer:
              'This can happen if:\n• Video is too new (segments not yet submitted)\n• No community submissions for this video\n• Network issues accessing SponsorBlock API\n• Selected categories don\'t match available segments\n\nSponsorBlock relies on community contributions, so newer or less popular videos may not have segments.',
        ),
        // Troubleshooting
        FaqEntry(
          category: 'Troubleshooting',
          question: 'I get a network or permission error—what should I try?',
          answer:
              'Check your connection, try again, or export logs from Settings → Maintenance and share the zip for support.',
        ),
        FaqEntry(
          category: 'Troubleshooting',
          question: 'Where are the exported log files saved?',
          answer:
              'Log zip files are saved to:\nWindows: %APPDATA%\\YoutubeConverter\\logs\\logs-YYYYMMDD-HHMMSS.zip\nExample: C:\\Users\\YourName\\AppData\\Roaming\\YoutubeConverter\\logs\\logs-20250913-143022.zip\n\nYou can find this folder by:\n• Pressing Win+R, typing %APPDATA%\\YoutubeConverter\\logs and hitting Enter\n• The app shows the filename in a success toast after export',
        ),
        FaqEntry(
          category: 'Troubleshooting',
          question: 'App crashes on startup or won\'t open',
          answer:
              'Try these solutions:\n• Update graphics drivers\n• Run as administrator\n• Check Windows Event Viewer for error details\n• Disable antivirus temporarily\n• Clear app settings: Delete %APPDATA%\\YoutubeConverter folder\n• Reinstall Microsoft Visual C++ Redistributables',
        ),
        FaqEntry(
          category: 'Troubleshooting',
          question: 'FFmpeg errors or \'Conversion failed\'',
          answer:
              'FFmpeg issues can occur due to:\n• Corrupted or missing FFmpeg binary\n• Unsupported video/audio codec\n• File path with special characters\n• Insufficient disk space\n• Antivirus quarantining FFmpeg\n\nTry reinstalling the app or adding FFmpeg folder to antivirus exclusions.',
        ),
        FaqEntry(
          category: 'Troubleshooting',
          question: 'High CPU/memory usage during downloads',
          answer:
              'This is normal for video processing, but can be reduced by:\n• Downloading fewer concurrent streams\n• Choosing lower quality options\n• Closing other applications\n• Using audio-only format for music\n• Avoiding video conversion when possible',
        ),
        FaqEntry(
          category: 'Troubleshooting',
          question: 'App interface appears corrupted or unreadable',
          answer:
              'Display issues can be fixed by:\n• Changing theme in Settings → Appearance\n• Adjusting Windows display scaling (100%, 125%, 150%)\n• Updating graphics drivers\n• Try different color theme (Dark/Light/OLED)\n• Reset app settings if problem persists',
        ),
        // File Management
        FaqEntry(
          category: 'File Management',
          question: 'Where are downloaded files saved?',
          answer:
              'By default, files are saved to your Downloads folder. You can change the destination in Settings or during the download process. The app remembers your last used location.',
        ),
        FaqEntry(
          category: 'File Management',
          question: 'How to organize downloads by playlist/channel?',
          answer:
              'The app can create subfolders based on:\n• Playlist name\n• Channel name\n• Upload date\n\nConfigure this in Settings → Downloads → Folder structure options.',
        ),
        FaqEntry(
          category: 'File Management',
          question: 'Downloaded file has wrong extension or won\'t play',
          answer:
              'This can happen if:\n• Codec not supported by your media player\n• File corrupted during download\n• Wrong format selected\n\nTry:\n• Using VLC media player (supports most formats)\n• Re-downloading with different quality\n• Converting to MP4/MP3 format',
        ),
        // Performance
        FaqEntry(
          category: 'Performance',
          question: 'How to speed up downloads?',
          answer:
              'To optimize download speed:\n• Use wired internet connection\n• Close bandwidth-heavy applications\n• Select appropriate quality (higher = slower)\n• Download during off-peak hours\n• Ensure sufficient free disk space\n• Consider downloading audio-only for music',
        ),
        // Accessibility
        FaqEntry(
          category: 'Accessibility',
          question: 'Is there a high-contrast theme?',
          answer:
              'Yes. Choose \'Dark\' or \'OLED\' themes in Settings → Appearance. The UI aims for improved contrast and readable controls.',
        ),
        FaqEntry(
          category: 'Accessibility',
          question: 'Keyboard shortcuts and navigation',
          answer:
              'The app supports:\n• Tab navigation through interface elements\n• Enter to activate buttons\n• Escape to close dialogs\n• Ctrl+V to paste URLs\n• Standard Windows accessibility features',
        ),
      ];

  /// Get all unique categories
  static List<String> get categories =>
      all.map((e) => e.category).toSet().toList()..sort();
}
