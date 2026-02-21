/// Video information model for YouTube videos
library;

/// Video format information
class VideoFormat {
  final String formatId;
  final String? ext;
  final String? resolution;
  final String? fps;
  final String? vcodec;
  final String? acodec;
  final int? filesize;
  final int? tbr; // Total bitrate
  final int? vbr; // Video bitrate
  final int? abr; // Audio bitrate
  final bool hasVideo;
  final bool hasAudio;
  final String? note;

  const VideoFormat({
    required this.formatId,
    this.ext,
    this.resolution,
    this.fps,
    this.vcodec,
    this.acodec,
    this.filesize,
    this.tbr,
    this.vbr,
    this.abr,
    this.hasVideo = false,
    this.hasAudio = false,
    this.note,
  });

  factory VideoFormat.fromJson(Map<String, dynamic> json) {
    return VideoFormat(
      formatId: json['format_id']?.toString() ?? '',
      ext: json['ext'],
      resolution: json['resolution'],
      fps: json['fps']?.toString(),
      vcodec: json['vcodec'],
      acodec: json['acodec'],
      filesize: json['filesize'],
      tbr: json['tbr'],
      vbr: json['vbr'],
      abr: json['abr'],
      hasVideo: json['vcodec'] != null && json['vcodec'] != 'none',
      hasAudio: json['acodec'] != null && json['acodec'] != 'none',
      note: json['format_note'] ?? json['note'],
    );
  }

  /// Get formatted file size
  String get formattedFilesize {
    if (filesize == null) return '~';

    const units = ['B', 'KB', 'MB', 'GB'];
    double size = filesize!.toDouble();
    int unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return '${size.toStringAsFixed(1)} ${units[unitIndex]}';
  }

  /// Get quality label
  String get qualityLabel {
    if (resolution != null && resolution!.isNotEmpty) {
      return resolution!;
    }
    if (tbr != null) {
      return '${tbr}k';
    }
    return formatId;
  }

  /// Get full description
  String get description {
    final parts = <String>[];
    if (ext != null) parts.add(ext!.toUpperCase());
    if (resolution != null) parts.add(resolution!);
    if (fps != null) parts.add('${fps}fps');
    if (vbr != null && hasVideo) parts.add('${vbr}k video');
    if (abr != null && hasAudio) parts.add('${abr}k audio');
    if (note != null) parts.add(note!);
    return parts.join(' • ');
  }
}

/// Video information from YouTube
class VideoInfo {
  final String id;
  final String title;
  final String? description;
  final String? thumbnail;
  final String? uploader;
  final String? uploaderId;
  final int? duration;
  final String? viewCount;
  final String? uploadDate;
  final String webpageUrl;
  final String? extractor;
  final String? extractorKey;
  final List<VideoFormat> formats;
  final bool isPlaylist;
  final List<VideoInfo>? playlistEntries;
  final String? playlistTitle;
  final int? playlistIndex;
  final int? playlistCount;

  const VideoInfo({
    required this.id,
    required this.title,
    this.description,
    this.thumbnail,
    this.uploader,
    this.uploaderId,
    this.duration,
    this.viewCount,
    this.uploadDate,
    required this.webpageUrl,
    this.extractor,
    this.extractorKey,
    this.formats = const [],
    this.isPlaylist = false,
    this.playlistEntries,
    this.playlistTitle,
    this.playlistIndex,
    this.playlistCount,
  });

  /// Get formatted duration (MM:SS or HH:MM:SS)
  String get formattedDuration {
    if (duration == null) return '';

    final hours = duration! ~/ 3600;
    final minutes = (duration! % 3600) ~/ 60;
    final seconds = duration! % 60;

    if (hours > 0) {
      return '${hours.toString().padLeft(2, '0')}:${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
    }
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  /// Get video-only formats
  List<VideoFormat> get videoFormats =>
      formats.where((f) => f.hasVideo).toList();

  /// Get audio-only formats
  List<VideoFormat> get audioFormats =>
      formats.where((f) => f.hasAudio && !f.hasVideo).toList();

  /// Get combined formats (video + audio)
  List<VideoFormat> get combinedFormats =>
      formats.where((f) => f.hasVideo && f.hasAudio).toList();

  factory VideoInfo.fromJson(Map<String, dynamic> json) {
    final isPlaylist = json['_type'] == 'playlist' || json['entries'] != null;

    List<VideoInfo>? playlistEntries;
    if (isPlaylist && json['entries'] != null) {
      playlistEntries = (json['entries'] as List)
          .where((e) => e != null)
          .map((e) => VideoInfo.fromJson(e as Map<String, dynamic>))
          .toList();
    }

    List<VideoFormat> formats = [];
    if (json['formats'] != null) {
      formats = (json['formats'] as List)
          .where((f) => f != null)
          .map((f) => VideoFormat.fromJson(f as Map<String, dynamic>))
          .toList();
    }

    return VideoInfo(
      id: json['id']?.toString() ?? '',
      title: json['title'] ?? 'Unknown Title',
      description: json['description'],
      thumbnail: json['thumbnail'] ?? json['thumbnails']?.first?['url'],
      uploader: json['uploader'] ?? json['channel'],
      uploaderId: json['uploader_id'] ?? json['channel_id'],
      duration: json['duration'],
      viewCount: json['view_count']?.toString(),
      uploadDate: json['upload_date'],
      webpageUrl: json['webpage_url'] ?? json['url'] ?? '',
      extractor: json['extractor'],
      extractorKey: json['extractor_key'],
      formats: formats,
      isPlaylist: isPlaylist,
      playlistEntries: playlistEntries,
      playlistTitle: json['title'] ?? json['playlist_title'],
      playlistIndex: json['playlist_index'],
      playlistCount: json['playlist_count'] ?? json['n_entries'],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'description': description,
        'thumbnail': thumbnail,
        'uploader': uploader,
        'uploader_id': uploaderId,
        'duration': duration,
        'view_count': viewCount,
        'upload_date': uploadDate,
        'webpage_url': webpageUrl,
        'extractor': extractor,
        'extractor_key': extractorKey,
        '_type': isPlaylist ? 'playlist' : null,
        'playlist_title': playlistTitle,
        'playlist_index': playlistIndex,
        'playlist_count': playlistCount,
      };

  /// Create a copy with updated fields
  VideoInfo copyWith({
    String? id,
    String? title,
    String? description,
    String? thumbnail,
    String? uploader,
    String? uploaderId,
    int? duration,
    String? viewCount,
    String? uploadDate,
    String? webpageUrl,
    String? extractor,
    String? extractorKey,
    List<VideoFormat>? formats,
    bool? isPlaylist,
    List<VideoInfo>? playlistEntries,
    String? playlistTitle,
    int? playlistIndex,
    int? playlistCount,
  }) {
    return VideoInfo(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      thumbnail: thumbnail ?? this.thumbnail,
      uploader: uploader ?? this.uploader,
      uploaderId: uploaderId ?? this.uploaderId,
      duration: duration ?? this.duration,
      viewCount: viewCount ?? this.viewCount,
      uploadDate: uploadDate ?? this.uploadDate,
      webpageUrl: webpageUrl ?? this.webpageUrl,
      extractor: extractor ?? this.extractor,
      extractorKey: extractorKey ?? this.extractorKey,
      formats: formats ?? this.formats,
      isPlaylist: isPlaylist ?? this.isPlaylist,
      playlistEntries: playlistEntries ?? this.playlistEntries,
      playlistTitle: playlistTitle ?? this.playlistTitle,
      playlistIndex: playlistIndex ?? this.playlistIndex,
      playlistCount: playlistCount ?? this.playlistCount,
    );
  }
}
