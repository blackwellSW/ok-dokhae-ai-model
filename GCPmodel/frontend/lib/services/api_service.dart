import '../models/work.dart';
import '../models/session_task.dart';

abstract class ApiService {
  Future<List<Work>> getWorks();
  Future<List<String>> getWorkContent(String workId);
  
  // [NEW] 대화형 학습을 위한 메서드 2개
  Future<String> startThinkingSession(String workId); // 첫 질문 받기
  Future<Map<String, dynamic>> getGuidance(String workId, String userAnswer); // 꼬리 질문 받기

  // 기존 메서드 (일단 유지)
  Future<List<Task>> getTasks(String workId);
  Future<Map<String, dynamic>> submitResult(String workId, dynamic logs);
}