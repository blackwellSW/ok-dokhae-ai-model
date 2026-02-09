import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class DioClient {
  // 백엔드 주소
  static const String baseUrl = "https://ok-dokhae-backend-84537953160.asia-northeast1.run.app";
  
  final Dio _dio;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  DioClient() : _dio = Dio(BaseOptions(
    baseUrl: baseUrl,
    // [수정] 타임아웃을 10초 -> 120초(2분)로 대폭 증가
    // AI 모델이 답변을 생성하는 데 시간이 걸릴 수 있습니다.
    connectTimeout: const Duration(seconds: 300),
    receiveTimeout: const Duration(seconds: 300), 
    sendTimeout: const Duration(seconds: 300),
    responseType: ResponseType.json,
  )) {
    // [Interceptor 설정] 모든 요청 헤더에 토큰 자동 추가
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        // 저장된 토큰 꺼내기
        final token = await _storage.read(key: 'access_token');
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) {
        // 에러 로그 출력
        print("API 에러 발생: ${error.response?.statusCode} / ${error.message}");
        return handler.next(error);
      },
    ));
  }

  // 외부에서 Dio 인스턴스를 가져다 쓸 수 있게 getter 제공
  Dio get dio => _dio;

  // 토큰 저장 (로그인 성공 시 호출)
  Future<void> saveToken(String token) async {
    await _storage.write(key: 'access_token', value: token);
  }

  // 토큰 삭제 (로그아웃 시 호출)
  Future<void> deleteToken() async {
    await _storage.delete(key: 'access_token');
  }
}