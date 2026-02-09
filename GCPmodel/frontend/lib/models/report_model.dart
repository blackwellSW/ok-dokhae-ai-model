class StudyReport {
  final String summary;
  final List<String> tags;
  final List<ReportScore> scores;
  final List<FlowAnalysis> flowAnalysis;
  final String prescription;

  StudyReport({
    required this.summary,
    required this.tags,
    required this.scores,
    required this.flowAnalysis,
    required this.prescription,
  });

  factory StudyReport.fromJson(Map<String, dynamic> json) {
    return StudyReport(
      summary: json['summary'] ?? '',
      tags: List<String>.from(json['tags'] ?? []),
      scores: (json['scores'] as List? ?? []).map((e) => ReportScore.fromJson(e)).toList(),
      flowAnalysis: (json['flow_analysis'] as List? ?? []).map((e) => FlowAnalysis.fromJson(e)).toList(),
      prescription: json['prescription'] ?? '',
    );
  }
}

class ReportScore {
  final String label;
  final double score;
  final String reason;

  ReportScore({required this.label, required this.score, required this.reason});

  factory ReportScore.fromJson(Map<String, dynamic> json) {
    return ReportScore(
      label: json['label'] ?? '',
      score: (json['score'] ?? 0).toDouble(),
      reason: json['reason'] ?? '',
    );
  }
}

class FlowAnalysis {
  final String step;
  final String status;
  final String comment;
  final String? quote;

  FlowAnalysis({required this.step, required this.status, required this.comment, this.quote});

  factory FlowAnalysis.fromJson(Map<String, dynamic> json) {
    return FlowAnalysis(
      step: json['step'] ?? '',
      status: json['status'] ?? '',
      comment: json['comment'] ?? '',
      quote: json['quote'],
    );
  }
}