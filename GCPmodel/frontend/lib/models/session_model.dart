class LearningSession {
  final String id;
  final String documentId;
  final String status; // 'active', 'finalized'
  final DateTime createdAt;

  LearningSession({
    required this.id,
    required this.documentId,
    required this.status,
    required this.createdAt,
  });

  factory LearningSession.fromJson(Map<String, dynamic> json) {
    return LearningSession(
      id: json['id'] ?? '',
      documentId: json['document_id'] ?? '',
      status: json['status'] ?? 'active',
      createdAt: DateTime.parse(json['created_at'] ?? DateTime.now().toIso8601String()),
    );
  }
}