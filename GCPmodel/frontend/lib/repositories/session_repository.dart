import '../services/dio_client.dart';

class SessionRepository {
  final DioClient _client = DioClient();

  // [1] 세션 생성 (명세서: POST /sessions)
  // 반환값: Map (session_id, first_question 포함)
  Future<Map<String, dynamic>?> createSession(String documentId, {String mode = 'student_led'}) async {
    try {
      final response = await _client.dio.post(
        '/sessions',
        data: {
          'document_id': documentId,
          'mode': mode, // [추가] 명세서에 mode 필드 있음
        },
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        return response.data; // { "session_id": "...", "first_question": "..." }
      }
    } catch (e) {
      print("세션 생성 실패: $e");
    }
    return null;
  }

  // [2] 메시지 전송 (명세서: POST /sessions/{id}/messages)
  // 채팅을 보내고 AI 응답을 받습니다.
  Future<Map<String, dynamic>?> sendMessage(String sessionId, String content) async {
    try {
      final response = await _client.dio.post(
        '/sessions/$sessionId/messages',
        data: {
          'content': content,
        },
      );

      if (response.statusCode == 200) {
        return response.data; 
        // 예상 응답:
        // {
        //   "assistant_message": "...",
        //   "session_status": "active" | "completed",
        //   "evaluation": { ... } // 종료 시 포함
        // }
      }
    } catch (e) {
      print("메시지 전송 실패: $e");
    }
    return null;
  }

  // [3] 세션 강제 종료 (명세서: POST /sessions/{id}/finalize)
  Future<String?> finalizeSession(String sessionId) async {
    try {
      final response = await _client.dio.post('/sessions/$sessionId/finalize');
      if (response.statusCode == 200) {
        return response.data['report_id'];
      }
    } catch (e) {
      print("세션 종료 실패: $e");
    }
    return null;
  }
}