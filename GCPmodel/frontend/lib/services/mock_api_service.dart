import 'package:flutter/material.dart';
import 'api_service.dart';
import '../models/work.dart';
import '../models/session_task.dart';

class MockApiService implements ApiService {
  // ✅ workId별 대화 턴 상태 (세션 시작 시 리셋)
  final Map<String, int> _turnIndexByWork = {};

  // ✅ 테스트용 지문 기반(테스트용 지문.txt) “튜터 응답” 스크립트
  //  - 사용자가 첫 질문을 하면, getGuidance()가 아래 순서대로 응답합니다.
  //  - 스크립트가 끝나면 마지막 요약/마무리로 종료(is_finish=true).
  static const List<String> _tutorScript = [
    "홍길동이 자신의 처지를 한탄하며 '아버지를 아버지라 부르지 못하네'라고 말하는 장면이 있죠? 그렇다면, 홍길동에게 '아버지'라는 존재가 실제로 얼마나 중요했을까요?",
    "그렇군요. 홍길동이 아버지를 인정받고 싶어 했던 이유는 무엇이라고 생각하나요? 단순히 부모님의 은혜를 갚고 싶었던 것일까요, 아니면 다른 이유가 있을까요?",
    "그렇군요. 자기 존재의 의미를 부모의 인정에서 찾는다는 것은 어떤 의미일까요? 만약 홍길동이 부모의 인정을 받지 못한다면, 그는 자신의 존재가 어떻다고 생각할까요?",
    "그렇군요. 부모의 인정을 받지 못하는 상황이 홍길동에게 어떤 불안감을 안겨주었을까요? 그 불안감은 그의 행동에 어떤 영향을 미쳤을까요?",
    // 데모용 마무리(추가)
    "좋아요. 오늘 대화를 정리하면, 홍길동은 '인정'을 통해 자기 존재의 의미를 확인하려 했고, 그 결핍이 불안과 행동으로 이어졌다고 볼 수 있겠네요. 이제 마지막으로, 이런 관점이 작품의 주제(신분 제도/차별)와 어떻게 연결되는지 한 문장으로 말해볼래요?",
  ];

  @override
  Future<List<Work>> getWorks() async {
    return [
      Work(
        id: 'simcheong',
        title: '심청전',
        author: '작자미상',
        category: '고전소설',
        baseColor: const Color(0xFFD7CCC8),
        patternColor: const Color(0xFF8D6E63),
        spineColor: const Color(0xFF5D4037),
      ),
      Work(
        id: 'gwandong',
        title: '관동별곡',
        author: '정철',
        category: '고전시가',
        baseColor: const Color(0xFFC8E6C9),
        patternColor: const Color(0xFF2E7D32),
        spineColor: const Color(0xFF1B5E20),
      ),
    ];
  }

  @override
  Future<List<String>> getWorkContent(String workId) async {
    await Future.delayed(const Duration(milliseconds: 300));

    if (workId == 'simcheong') {
      return [
        "심청이 거동 봐라.",
        "밥 빌러 나갈 제, 치마 자락을 거둠거둠 안고...",
        "\"아가 아가 심청 아가. 이리 와서 점심이나 먹고 가라.\"",
        "심청이 생각한들 아니 슬플소냐.",
      ];
    }

    // 관동별곡 등은 데모용 안내 텍스트
    return [
      "[파일 내용 추출 완료]",
      "업로드하신 문서의 텍스트가 여기에 표시됩니다.",
      "튜터가 내용을 바탕으로 소크라틱 질문을 이어갑니다.",
      "(데모 모드: 실제 파싱/검색/RAG는 생략)",
    ];
  }

  /// ✅ 세션 시작 시 보여줄 “첫 안내 멘트”
  /// - 여기서 턴을 리셋해두면, getGuidance()가 0번부터 시작합니다.
  @override
  Future<String> startThinkingSession(String workId) async {
    await Future.delayed(const Duration(milliseconds: 400));

    // 🔥 중요: 세션 시작 시 턴 리셋
    _turnIndexByWork[workId] = 0;

    return "좋아요. 먼저 학생이 궁금한 걸 질문해보세요. 예: \"이 구절이 왜 중요한지 모르겠어.\"";
  }

  /// ✅ 사용자가 보낸 메시지에 대해 ‘스크립트 기반’으로 다음 질문을 반환
  /// - 너무 짧은 입력은 턴을 진행하지 않고 재질문
  /// - 스크립트가 끝나면 is_finish=true로 종료 유도
  @override
  Future<Map<String, dynamic>> getGuidance(String workId, String userAnswer) async {
    await Future.delayed(const Duration(milliseconds: 500));

    final trimmed = userAnswer.trim();

    // 너무 짧으면 턴 진행 X
    if (trimmed.length < 5) {
      return {
        "text": "조금 더 구체적으로 이야기해 줄래요? 가능하면 본문 표현(단어/구절)을 같이 언급해보면 좋아요.",
        "is_finish": false,
      };
    }

    // 세션 시작을 안 거쳤더라도 안전하게 초기화
    _turnIndexByWork.putIfAbsent(workId, () => 0);

    final idx = _turnIndexByWork[workId]!;
    if (idx < _tutorScript.length) {
      _turnIndexByWork[workId] = idx + 1;

      final isLast = (idx == _tutorScript.length - 1);
      return {
        "text": _tutorScript[idx],
        "is_finish": isLast, // 마지막 멘트는 종료(true)
      };
    }

    // 스크립트 소진 후 (안전망)
    return {
      "text": "좋아요. 여기까지 내용을 바탕으로 리포트를 생성해볼까요?",
      "is_finish": true,
    };
  }

  // === 기존 메서드 (현재 UI에서 안 쓰면 그대로 둬도 OK) ===
  @override
  Future<List<Task>> getTasks(String workId) async => [];

  @override
  Future<Map<String, dynamic>> submitResult(String workId, dynamic logs) async => {};
}
