# Flutter Firebase 연동 가이드

## 개요

백엔드가 Firebase Auth + Firestore로 업그레이드되었습니다.
**프론트엔드 변경은 최소화**되도록 설계했습니다.

---

## 1. 필요한 패키지 설치

```yaml
# pubspec.yaml
dependencies:
  firebase_core: ^2.24.0
  firebase_auth: ^4.16.0
  google_sign_in: ^6.2.1  # 기존에 사용 중이면 유지
```

```bash
flutter pub get
```

---

## 2. Firebase 프로젝트 설정

### 2.1 Firebase Console에서 앱 등록

1. [Firebase Console](https://console.firebase.google.com) 접속
2. 프로젝트: `knu-team-03` 선택
3. "앱 추가" → Flutter 선택
4. 안내에 따라 `google-services.json` (Android) / `GoogleService-Info.plist` (iOS) 다운로드

### 2.2 FlutterFire CLI 설정 (권장)

```bash
# FlutterFire CLI 설치
dart pub global activate flutterfire_cli

# Firebase 설정 자동 생성
flutterfire configure --project=knu-team-03
```

이 명령어가 `lib/firebase_options.dart` 파일을 자동 생성합니다.

---

## 3. Firebase 초기화

```dart
// lib/main.dart
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  runApp(MyApp());
}
```

---

## 4. Google 로그인 구현

### 4.1 AuthService 클래스

```dart
// lib/services/auth_service.dart
import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';

class AuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final GoogleSignIn _googleSignIn = GoogleSignIn();

  /// Google 로그인 후 Firebase ID Token 반환
  Future<String?> signInWithGoogle() async {
    try {
      // 1. Google 로그인
      final GoogleSignInAccount? googleUser = await _googleSignIn.signIn();
      if (googleUser == null) return null;

      // 2. Google 인증 정보 가져오기
      final GoogleSignInAuthentication googleAuth =
          await googleUser.authentication;

      // 3. Firebase 로그인
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      final UserCredential userCredential =
          await _auth.signInWithCredential(credential);

      // 4. Firebase ID Token 반환 (백엔드로 전송할 토큰)
      final idToken = await userCredential.user?.getIdToken();
      return idToken;

    } catch (e) {
      print('Google 로그인 오류: $e');
      return null;
    }
  }

  /// 현재 사용자의 ID Token 가져오기 (갱신 포함)
  Future<String?> getIdToken({bool forceRefresh = false}) async {
    final user = _auth.currentUser;
    if (user == null) return null;
    return await user.getIdToken(forceRefresh);
  }

  /// 로그아웃
  Future<void> signOut() async {
    await _googleSignIn.signOut();
    await _auth.signOut();
  }

  /// 현재 로그인 상태
  bool get isLoggedIn => _auth.currentUser != null;

  /// 현재 사용자
  User? get currentUser => _auth.currentUser;
}
```

---

## 5. 백엔드 API 호출

### 5.1 API Service 수정

```dart
// lib/services/api_service.dart
import 'package:dio/dio.dart';
import 'auth_service.dart';

class ApiService {
  final Dio _dio = Dio();
  final AuthService _authService = AuthService();

  // 백엔드 URL (Cloud Run 배포 시 변경)
  static const String baseUrl = 'https://your-backend-url.run.app';
  // 로컬 개발: 'http://10.0.2.2:8000' (Android 에뮬레이터)
  // 로컬 개발: 'http://localhost:8000' (iOS 시뮬레이터/웹)

  /// Google 로그인 → 백엔드 인증
  Future<Map<String, dynamic>?> loginWithGoogle({
    String userType = 'student',
  }) async {
    try {
      // 1. Firebase로 Google 로그인
      final idToken = await _authService.signInWithGoogle();
      if (idToken == null) {
        throw Exception('Google 로그인 실패');
      }

      // 2. 백엔드에 토큰 전송 (기존 API와 동일!)
      final response = await _dio.post(
        '$baseUrl/auth/google-login',
        data: {
          'id_token': idToken,
          'user_type': userType,
        },
      );

      // 3. 백엔드에서 받은 JWT 토큰 저장
      final data = response.data;
      await _saveToken(data['access_token']);

      return data;

    } catch (e) {
      print('로그인 오류: $e');
      return null;
    }
  }

  /// 인증이 필요한 API 호출
  Future<Response> authenticatedRequest(
    String method,
    String path, {
    Map<String, dynamic>? data,
  }) async {
    final token = await _getToken();

    return await _dio.request(
      '$baseUrl$path',
      data: data,
      options: Options(
        method: method,
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      ),
    );
  }

  // 토큰 저장/조회 (SharedPreferences 또는 FlutterSecureStorage 사용)
  Future<void> _saveToken(String token) async {
    // TODO: 토큰 저장 구현
  }

  Future<String?> _getToken() async {
    // TODO: 토큰 조회 구현
    return null;
  }
}
```

---

## 6. 사용 예시

### 6.1 로그인 화면

```dart
// lib/screens/login_screen.dart
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class LoginScreen extends StatelessWidget {
  final ApiService _apiService = ApiService();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ElevatedButton.icon(
          icon: Icon(Icons.login),
          label: Text('Google로 로그인'),
          onPressed: () async {
            final result = await _apiService.loginWithGoogle(
              userType: 'student',
            );

            if (result != null) {
              print('로그인 성공: ${result['username']}');
              // 홈 화면으로 이동
              Navigator.pushReplacementNamed(context, '/home');
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('로그인 실패')),
              );
            }
          },
        ),
      ),
    );
  }
}
```

### 6.2 세션 생성

```dart
// 세션 시작 예시
Future<void> startSession(String documentId) async {
  final response = await _apiService.authenticatedRequest(
    'POST',
    '/sessions',
    data: {
      'document_id': documentId,
      'mode': 'student_led',
    },
  );

  final sessionId = response.data['session_id'];
  final firstQuestion = response.data['first_question'];

  print('세션 시작: $sessionId');
  print('첫 질문: $firstQuestion');
}
```

---

## 7. 변경 사항 요약

### 프론트엔드에서 변경할 것

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| 패키지 | `google_sign_in` | `firebase_auth` + `google_sign_in` |
| 토큰 획득 | Google ID Token | Firebase ID Token |
| API 호출 | 동일 | 동일 (변경 없음!) |

### 백엔드 API는 그대로

- `POST /auth/google-login` - 동일한 요청/응답 형식
- `POST /sessions` - 동일
- `POST /sessions/{id}/messages` - 동일
- `GET /reports/{id}` - 동일

---

## 8. 테스트 체크리스트

- [ ] Firebase 초기화 성공
- [ ] Google 로그인 팝업 표시
- [ ] Firebase ID Token 획득
- [ ] 백엔드 `/auth/google-login` 호출 성공
- [ ] JWT 토큰 수신 및 저장
- [ ] 인증된 API 호출 (세션 생성 등)

---

## 9. 문제 해결

### CORS 오류가 발생하면

백엔드 CORS 설정이 업데이트되었습니다. 하지만 문제가 계속되면:

```bash
# 환경변수로 특정 도메인 허용 (Cloud Run 배포 시)
CORS_ORIGINS=https://your-flutter-web.web.app
```

### "Invalid token" 오류

1. Firebase ID Token이 만료되었는지 확인
2. `getIdToken(forceRefresh: true)` 호출해서 갱신

### Android에서 SHA-1 인증서 문제

```bash
# 디버그 SHA-1 확인
cd android && ./gradlew signingReport
```

Firebase Console에서 이 SHA-1을 앱에 추가해야 합니다.

---

## 10. 참고 자료

- [FlutterFire 공식 문서](https://firebase.flutter.dev/)
- [Firebase Auth 가이드](https://firebase.google.com/docs/auth/flutter/start)
- [Google Sign-In 설정](https://firebase.google.com/docs/auth/flutter/google-signin)
