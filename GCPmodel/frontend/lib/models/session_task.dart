// [데이터 모델] 개별 문제(Task) 정보
class Task {
  final String id;          // 문제 ID (API 연동 시 필요)
  final String typeTag;     // 태그 (상황 파악, 어휘 추론 등)
  final String question;    // 질문
  final List<String> options; // 객관식 선택지
  final int correctOptionIndex; // 정답 인덱스
  
  // 하이라이트 관련 (API에선 chunk_id로 오지만 일단 인덱스로 관리)
  final int highlightSentenceIndex; // 지문 내 노란색 하이라이트 위치
  final List<int> validEvidenceIndices; // 정답 근거 문장 위치들
  
  final String feedbackMessage; // 정답 시 띄울 피드백
  final List<String> whyOptions; // 문제별 맞춤 Why 선택지

  Task({
    this.id = '', // 초기엔 빈 값 허용
    required this.typeTag,
    required this.question,
    required this.options,
    required this.correctOptionIndex,
    required this.highlightSentenceIndex,
    required this.validEvidenceIndices,
    required this.feedbackMessage,
    required this.whyOptions,
  });
}

// [데이터 모델] 유저 학습 기록 (Result 화면용)
class UserLog {
  final String taskType;
  final String question;
  final String selectedAnswer;
  final String evidenceText;
  final String whyReason;

  UserLog({
    required this.taskType,
    required this.question,
    required this.selectedAnswer,
    required this.evidenceText,
    required this.whyReason,
  });
}