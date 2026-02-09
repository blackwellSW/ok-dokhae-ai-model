class Document {
  final String id;
  final String title;
  final String? contentType;
  final int? charCount;

  Document({
    required this.id,
    required this.title,
    this.contentType,
    this.charCount,
  });

  factory Document.fromJson(Map<String, dynamic> json) {
    return Document(
      id: json['id'] ?? '',
      title: json['title'] ?? '제목 없음',
      contentType: json['content_type'],
      charCount: json['char_count'],
    );
  }
}