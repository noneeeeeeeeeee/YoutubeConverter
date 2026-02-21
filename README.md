# YouTube Converter

A modern YouTube video/audio downloader built with Flutter and Material 3 Expressive design.

![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/vendouple/YoutubeConverter/.github%2Fworkflows%2Fbuilder.yml)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/vendouple/YoutubeConverter/total)

## Features

### ✨ Modern UI

- **Material 3 Expressive Design**: Following Google's latest design guidelines
- **Dark/Light/OLED Themes**: Choose your preferred theme mode
- **Customizable Accent Colors**: Personalize the app with your favorite color
- **Responsive Layout**: Works on desktop and mobile devices

### 🚀 Core Features

- **YouTube Video/Audio Download**: Download videos or extract audio
- **Multiple Format Support**: MP3, M4A, OPUS, WAV, FLAC, MP4, WebM, MKV
- **Quality Selection**: Choose from best quality or specific bitrates/resolutions
- **Playlist Support**: Download individual videos or entire playlists
- **Batch Downloads**: Queue multiple downloads simultaneously

### 🔧 Advanced Features

- **SponsorBlock Integration**: Automatically remove sponsored segments
- **Subtitle Download**: Download video subtitles in multiple languages
- **Auto-Update**: Keep the app and yt-dlp up to date automatically
- **EZ Mode**: Simplified interface for quick downloads

### 📱 Platform Support

| Platform | Status       |
| -------- | ------------ |
| Windows  | ✅ Supported |
| macOS    | ✅ Supported |
| Linux    | ✅ Supported |
| Android  | 🚧 Planned   |

## Getting Started

### Prerequisites

- Flutter SDK 3.0.6 or higher
- Dart SDK 3.0.6 or higher

### Installation

1. Clone the repository:

```bash
git clone https://github.com/vendouple/YoutubeConverter.git
cd YoutubeConverter
```

2. Install dependencies:

```bash
flutter pub get
```

3. Run the app:

```bash
flutter run
```

### Building

```bash
# Windows
flutter build windows --release

# macOS
flutter build macos --release

# Linux
flutter build linux --release
```

## Migration from PyQt6

This Flutter app is a complete rewrite of the original PyQt6 application. Key improvements:

1. **Cross-platform support**: Now runs on Windows, macOS, Linux, and potentially Android
2. **Modern UI**: Material 3 Expressive design with smooth animations
3. **Better performance**: Flutter's compiled nature provides better performance
4. **Easier maintenance**: Dart's sound null safety and Flutter's hot reload
5. **Smaller bundle size**: Flutter compiles to native code

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The core download engine
- [FFmpeg](https://ffmpeg.org/) - Media processing
- [Flutter](https://flutter.dev/) - UI framework
- [Material Design 3](https://m3.material.io/) - Design system
