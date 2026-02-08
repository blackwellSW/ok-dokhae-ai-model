# 프론트엔드 개발자를 위한 API 가이드

## 서버 정보

- **Base URL**: `https://ok-dokhae-backend-84537953160.asia-northeast1.run.app`
- **API 문서**: `{Base URL}/docs` (Swagger UI)
- **버전**: v5.0.0

---

## 빠른 시작

### 1. 인증 흐름

```
[Flutter 앱]
    │
    ├─ 1. Firebase Google 로그인
    │      → Firebase ID Token 획득
    │
    ├─ 2. 백엔드 로그인 요청
    │      POST /auth/google-login
    │      → Backend JWT Token 획득
    │
    └─ 3. 이후 모든 요청에 JWT 사용
           Authorization: Bearer {jwt_token}
```

### 2. 학습 세션 흐름

```
[문서 업로드]          →   [세션 생성]           →   [대화 진행]         →   [리포트 조회]
POST /documents           POST /sessions            POST /sessions/{id}      GET /reports/{id}
                                                    /messages (4턴)
```

---

## 인증 API

### 로그인 (Google OAuth)

```http
POST /auth/google-login
Content-Type: application/json

{
  "id_token": "Firebase_ID_Token_여기에",
  "user_type": "student"  // "student" | "teacher"
}
```

**응답:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "user_id": "user_abc123",
    "email": "student@example.com",
    "username": "홍길동",
    "user_type": "student"
  }
}
```

**Flutter 코드 예시:**
```dart
// Firebase 로그인 후
final idToken = await FirebaseAuth.instance.currentUser?.getIdToken();

final response = await http.post(
  Uri.parse('$baseUrl/auth/google-login'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'id_token': idToken,
    'user_type': 'student',
  }),
);

final jwt = jsonDecode(response.body)['access_token'];
// 저장해서 이후 요청에 사용
```

---

## 문서 관리 API

### 문서 업로드

```http
POST /documents
Authorization: Bearer {jwt_token}
Content-Type: multipart/form-data

file: (파일 바이너리)
title: "춘향전"
doc_type: "classical_literature"  // 선택
```

**응답:**
```json
{
  "doc_id": "doc_abc123",
  "title": "춘향전",
  "content_preview": "남원부사 자제 이몽룡은...",
  "chunks": [
    {
      "chunk_id": "chunk_001",
      "text": "남원부사 자제 이몽룡은..."
    }
  ],
  "total_chunks": 5,
  "message": "문서가 성공적으로 업로드되었습니다."
}
```

### 문서 목록 조회

```http
GET /documents
Authorization: Bearer {jwt_token}
```

### 문서 상세 조회

```http
GET /documents/{doc_id}
Authorization: Bearer {jwt_token}
```

---

## 세션 관리 API (핵심)

### 세션 생성 (학습 시작)

```http
POST /sessions
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "document_id": "doc_abc123",
  "mode": "student_led"  // "student_led" | "ai_led"
}
```

**응답:**
```json
{
  "session_id": "sess_xyz789",
  "status": "active",
  "first_question": "이 작품에서 가장 인상 깊었던 부분은 무엇인가요?",
  "message": "학습 세션이 시작되었습니다. 4턴의 대화가 진행됩니다."
}
```

### 메시지 전송 (대화 진행)

```http
POST /sessions/{session_id}/messages
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "content": "학생의 답변 내용"
}
```

**응답 (턴 1~3):**
```json
{
  "message_id": "msg_001",
  "assistant_message": "좋은 생각이에요! 그렇다면 작가는 왜 그런 선택을 했을까요?",
  "message_type": "question",
  "current_turn": 2,
  "session_status": "active",
  "evaluation": null
}
```

**응답 (턴 4 - 완료):**
```json
{
  "message_id": "msg_004",
  "assistant_message": "수고하셨습니다! 📊 총점: 85점 (등급: B+)",
  "message_type": "feedback",
  "current_turn": 5,
  "session_status": "completed",
  "evaluation": {
    "report_id": "rpt_abc123",
    "score": 85,
    "grade": "B+",
    "feedback": ["논리적 사고력이 우수합니다", "근거 제시를 더 구체적으로 해보세요"]
  }
}
```

### 세션 목록 조회

```http
GET /sessions?status=active&days=30
Authorization: Bearer {jwt_token}
```

**응답:**
```json
{
  "sessions": [
    {
      "session_id": "sess_xyz789",
      "document_id": "doc_abc123",
      "title": "춘향전 세션",
      "status": "active",
      "current_turn": 2,
      "max_turns": 4,
      "created_at": "2026-02-08T10:00:00Z",
      "updated_at": "2026-02-08T10:30:00Z",
      "report_id": null
    }
  ],
  "total": 1
}
```

### 세션 상세 조회

```http
GET /sessions/{session_id}
Authorization: Bearer {jwt_token}
```

### 대화 로그 조회

```http
GET /sessions/{session_id}/messages
Authorization: Bearer {jwt_token}
```

**응답:**
```json
{
  "session_id": "sess_xyz789",
  "messages": [
    {
      "message_id": "msg_001",
      "role": "assistant",
      "content": "이 작품에서 가장 인상 깊었던 부분은 무엇인가요?",
      "timestamp": "2026-02-08T10:00:00Z",
      "metadata": null
    },
    {
      "message_id": "msg_002",
      "role": "user",
      "content": "이몽룡과 춘향의 만남 장면이요",
      "timestamp": "2026-02-08T10:05:00Z",
      "metadata": null
    }
  ],
  "total": 2
}
```

### 세션 수동 종료

```http
POST /sessions/{session_id}/finalize
Authorization: Bearer {jwt_token}
```

---

## 리포트 API

### 리포트 조회

```http
GET /reports/{report_id}
Authorization: Bearer {jwt_token}
```

**응답:**
```json
{
  "report_id": "rpt_abc123",
  "session_id": "sess_xyz789",
  "user_id": "user_abc123",
  "created_at": "2026-02-08T11:00:00Z",
  "evaluation": {
    "total_score": 85,
    "grade": "B+",
    "qualitative": {
      "score": 82,
      "categories": {
        "논리적_사고": 85,
        "창의적_해석": 80,
        "근거_제시": 78
      }
    },
    "quantitative": {
      "score": 92,
      "metrics": {
        "응답_완성도": 95,
        "시간_관리": 90
      }
    }
  },
  "feedback": [
    "논리적 사고력이 우수합니다",
    "작품의 맥락을 잘 이해하고 있습니다",
    "근거 제시를 더 구체적으로 해보세요"
  ],
  "citations": [
    {
      "type": "text_reference",
      "content": "이몽룡과 춘향의 첫 만남",
      "source": "춘향전 제1장"
    }
  ]
}
```

---

## 교사 API

### 학생 목록 조회

```http
GET /teacher/students
Authorization: Bearer {jwt_token}  // 교사 권한 필요
```

**응답:**
```json
{
  "students": [
    {
      "student_id": "user_abc123",
      "username": "홍길동",
      "email": "student@example.com",
      "total_sessions": 15,
      "last_activity": "2026-02-08T10:30:00Z",
      "risk_level": "low"
    }
  ],
  "total": 25
}
```

### 학생 세션 목록

```http
GET /teacher/students/{student_id}/sessions?range=30d
Authorization: Bearer {jwt_token}
```

### 학생 요약 조회

```http
GET /teacher/students/{student_id}/summary?range=30d
Authorization: Bearer {jwt_token}
```

**응답:**
```json
{
  "student_id": "user_abc123",
  "username": "홍길동",
  "period": "last_30_days",
  "stats": {
    "total_sessions": 15,
    "completed_sessions": 12,
    "completion_rate": 0.8,
    "average_score": 82.5,
    "average_grade": "B"
  },
  "trends": {
    "score_trend": "improving",
    "activity_trend": "stable"
  },
  "risk_flags": [],
  "recommendations": ["꾸준한 학습을 계속 격려하세요"]
}
```

### 대시보드

```http
GET /teacher/dashboard
Authorization: Bearer {jwt_token}
```

---

## 에러 처리

### 공통 에러 형식

```json
{
  "detail": "에러 메시지"
}
```

### HTTP 상태 코드

| 코드 | 의미 | 대응 방법 |
|------|------|----------|
| 200 | 성공 | - |
| 400 | 잘못된 요청 | 요청 데이터 확인 |
| 401 | 인증 실패 | 토큰 갱신 또는 재로그인 |
| 403 | 권한 없음 | 사용자 역할 확인 |
| 404 | 리소스 없음 | ID 확인 |
| 422 | 유효성 검사 실패 | 요청 형식 확인 |
| 500 | 서버 오류 | 잠시 후 재시도 |

### Flutter 에러 처리 예시

```dart
try {
  final response = await http.post(url, ...);

  if (response.statusCode == 200) {
    return jsonDecode(response.body);
  } else if (response.statusCode == 401) {
    // 토큰 만료 - 재로그인
    await authService.refreshToken();
    return retry();
  } else {
    final error = jsonDecode(response.body);
    throw ApiException(error['detail']);
  }
} catch (e) {
  // 네트워크 에러 등
  throw NetworkException(e.toString());
}
```

---

## Flutter 통합 가이드

### 1. API 클라이언트 설정

```dart
class ApiClient {
  static const String baseUrl =
    'https://ok-dokhae-backend-84537953160.asia-northeast1.run.app';

  String? _token;

  void setToken(String token) {
    _token = token;
  }

  Map<String, String> get headers => {
    'Content-Type': 'application/json',
    if (_token != null) 'Authorization': 'Bearer $_token',
  };

  Future<Map<String, dynamic>> get(String path) async {
    final response = await http.get(
      Uri.parse('$baseUrl$path'),
      headers: headers,
    );
    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) async {
    final response = await http.post(
      Uri.parse('$baseUrl$path'),
      headers: headers,
      body: jsonEncode(body),
    );
    return _handleResponse(response);
  }

  Map<String, dynamic> _handleResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body);
    }
    throw ApiException(response.statusCode, response.body);
  }
}
```

### 2. 인증 서비스

```dart
class AuthService {
  final ApiClient _api;

  Future<User> loginWithGoogle() async {
    // 1. Firebase 로그인
    final googleUser = await GoogleSignIn().signIn();
    final googleAuth = await googleUser?.authentication;
    final credential = GoogleAuthProvider.credential(
      accessToken: googleAuth?.accessToken,
      idToken: googleAuth?.idToken,
    );

    await FirebaseAuth.instance.signInWithCredential(credential);

    // 2. Firebase ID Token 획득
    final idToken = await FirebaseAuth.instance.currentUser?.getIdToken();

    // 3. 백엔드 로그인
    final response = await _api.post('/auth/google-login', {
      'id_token': idToken,
      'user_type': 'student',
    });

    // 4. JWT 저장
    _api.setToken(response['access_token']);

    return User.fromJson(response['user']);
  }
}
```

### 3. 세션 서비스

```dart
class SessionService {
  final ApiClient _api;

  Future<Session> createSession(String documentId) async {
    final response = await _api.post('/sessions', {
      'document_id': documentId,
      'mode': 'student_led',
    });
    return Session.fromJson(response);
  }

  Future<MessageResponse> sendMessage(String sessionId, String content) async {
    final response = await _api.post('/sessions/$sessionId/messages', {
      'content': content,
    });
    return MessageResponse.fromJson(response);
  }

  Future<List<Message>> getMessages(String sessionId) async {
    final response = await _api.get('/sessions/$sessionId/messages');
    return (response['messages'] as List)
        .map((m) => Message.fromJson(m))
        .toList();
  }
}
```

### 4. 대화 화면 예시

```dart
class ChatScreen extends StatefulWidget {
  final String sessionId;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _sessionService = SessionService();
  final _controller = TextEditingController();
  List<Message> _messages = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadMessages();
  }

  Future<void> _loadMessages() async {
    final messages = await _sessionService.getMessages(widget.sessionId);
    setState(() => _messages = messages);
  }

  Future<void> _sendMessage() async {
    if (_controller.text.isEmpty) return;

    setState(() => _isLoading = true);

    try {
      final response = await _sessionService.sendMessage(
        widget.sessionId,
        _controller.text,
      );

      _controller.clear();
      await _loadMessages();

      // 세션 완료 시 리포트 화면으로 이동
      if (response.sessionStatus == 'completed') {
        Navigator.push(
          context,
          MaterialPageRoute(
            builder: (_) => ReportScreen(reportId: response.evaluation!.reportId),
          ),
        );
      }
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('학습 대화')),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: _messages.length,
              itemBuilder: (_, i) => MessageBubble(message: _messages[i]),
            ),
          ),
          Padding(
            padding: EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: InputDecoration(hintText: '답변을 입력하세요'),
                  ),
                ),
                IconButton(
                  icon: _isLoading
                    ? CircularProgressIndicator()
                    : Icon(Icons.send),
                  onPressed: _isLoading ? null : _sendMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
```

---

## 자주 묻는 질문

### Q: 토큰이 만료되면 어떻게 하나요?
401 에러가 발생하면 Firebase ID Token을 다시 받아서 `/auth/google-login`을 호출하세요.

### Q: 세션은 언제 만료되나요?
24시간 동안 활동이 없으면 만료됩니다. Cloud Function이 주기적으로 정리합니다.

### Q: 오프라인에서도 작동하나요?
현재는 온라인 전용입니다. 메시지 캐싱은 추후 지원 예정입니다.

### Q: 파일 업로드 최대 크기는?
10MB입니다. PDF, TXT, DOCX를 지원합니다.

---

## 문의

- Swagger 문서: https://ok-dokhae-backend-84537953160.asia-northeast1.run.app/docs
- 프로젝트: KNU Team 03
- 업데이트: 2026-02-08
