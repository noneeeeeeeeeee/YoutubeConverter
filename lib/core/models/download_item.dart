/// Download item model for tracking downloads
library;

/// Download state enum
enum DownloadState {
  created('Created'),
  fetching('Fetching Info'),
  queued('Queued'),
  downloading('Downloading'),
  converting('Converting'),
  completed('Completed'),
  failed('Failed'),
  cancelled('Cancelled'),
  paused('Paused');

  final String label;
  const DownloadState(this.label);

  static DownloadState fromString(String value) {
    return DownloadState.values.firstWhere(
      (e) => e.name.toLowerCase() == value.toLowerCase(),
      orElse: () => DownloadState.created,
    );
  }

  bool get isActive =>
      this == DownloadState.downloading ||
      this == DownloadState.converting ||
      this == DownloadState.fetching;

  bool get isComplete => this == DownloadState.completed;

  bool get isFailed => this == DownloadState.failed;

  bool get canRetry =>
      this == DownloadState.failed || this == DownloadState.cancelled;
}

/// Download item model
class DownloadItem {
  final String id;
  final String sourceUrl;
  final String normalizedUrl;
  final String targetFormat;
  final String? outputPath;
  final DownloadState state;
  final double progress;
  final String? error;
  final String? title;
  final String? thumbnail;
  final String? duration;
  final String? uploader;
  final int? fileSizeBytes;
  final DateTime createdAt;
  final DateTime? completedAt;

  const DownloadItem({
    required this.id,
    required this.sourceUrl,
    required this.normalizedUrl,
    required this.targetFormat,
    this.outputPath,
    this.state = DownloadState.created,
    this.progress = 0.0,
    this.error,
    this.title,
    this.thumbnail,
    this.duration,
    this.uploader,
    this.fileSizeBytes,
    required this.createdAt,
    this.completedAt,
  });

  DownloadItem copyWith({
    String? id,
    String? sourceUrl,
    String? normalizedUrl,
    String? targetFormat,
    String? outputPath,
    DownloadState? state,
    double? progress,
    String? error,
    String? title,
    String? thumbnail,
    String? duration,
    String? uploader,
    int? fileSizeBytes,
    DateTime? createdAt,
    DateTime? completedAt,
  }) {
    return DownloadItem(
      id: id ?? this.id,
      sourceUrl: sourceUrl ?? this.sourceUrl,
      normalizedUrl: normalizedUrl ?? this.normalizedUrl,
      targetFormat: targetFormat ?? this.targetFormat,
      outputPath: outputPath ?? this.outputPath,
      state: state ?? this.state,
      progress: progress ?? this.progress,
      error: error ?? this.error,
      title: title ?? this.title,
      thumbnail: thumbnail ?? this.thumbnail,
      duration: duration ?? this.duration,
      uploader: uploader ?? this.uploader,
      fileSizeBytes: fileSizeBytes ?? this.fileSizeBytes,
      createdAt: createdAt ?? this.createdAt,
      completedAt: completedAt ?? this.completedAt,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'sourceUrl': sourceUrl,
        'normalizedUrl': normalizedUrl,
        'targetFormat': targetFormat,
        'outputPath': outputPath,
        'state': state.name,
        'progress': progress,
        'error': error,
        'title': title,
        'thumbnail': thumbnail,
        'duration': duration,
        'uploader': uploader,
        'fileSizeBytes': fileSizeBytes,
        'createdAt': createdAt.toIso8601String(),
        'completedAt': completedAt?.toIso8601String(),
      };

  factory DownloadItem.fromJson(Map<String, dynamic> json) {
    return DownloadItem(
      id: json['id'],
      sourceUrl: json['sourceUrl'],
      normalizedUrl: json['normalizedUrl'],
      targetFormat: json['targetFormat'],
      outputPath: json['outputPath'],
      state: DownloadState.fromString(json['state'] ?? 'created'),
      progress: (json['progress'] ?? 0.0).toDouble(),
      error: json['error'],
      title: json['title'],
      thumbnail: json['thumbnail'],
      duration: json['duration'],
      uploader: json['uploader'],
      fileSizeBytes: json['fileSizeBytes'],
      createdAt: DateTime.parse(json['createdAt']),
      completedAt: json['completedAt'] != null
          ? DateTime.tryParse(json['completedAt'])
          : null,
    );
  }

  /// Get formatted file size
  String get formattedFileSize {
    if (fileSizeBytes == null) return '';

    const units = ['B', 'KB', 'MB', 'GB'];
    double size = fileSizeBytes!.toDouble();
    int unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return '${size.toStringAsFixed(1)} ${units[unitIndex]}';
  }

  /// Get progress percentage string
  String get progressPercent => '${(progress * 100).toStringAsFixed(1)}%';
}
