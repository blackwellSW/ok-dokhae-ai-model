# 백엔드 업데이트 가이드 (2026-02-08)

## 배포 정보

- **서비스 URL**: https://ok-dokhae-backend-84537953160.asia-northeast1.run.app
- **리전**: asia-northeast1
- **리소스**: 4 CPU, 16Gi 메모리, 최소 인스턴스 1개
- **상태**: 운영 중 (v5.0.0)

## 개요

이 문서는 백엔드의 모든 수정사항을 정리합니다:
- Vertex AI 연동 (Fine-tuned Gemma 3 LoRA 모델)
- Firebase Auth + Firestore 연동
- Cloud Logging
- Cloud Functions
- CORS 수정
- 보안 개선
- Cloud Run 배포 설정

---

## 1. Vertex AI 연동

### 수정된 파일
- `app/core/config.py` - Vertex AI 설정 추가
- `app/services/thought_inducer.py` - Vertex AI 엔드포인트 연동

### 설정

```python
# app/core/config.py
VERTEX_AI_ENDPOINT = "https://us-central1-aiplatform.googleapis.com/v1/projects/knu-team-03/locations/us-central1/endpoints/2283851677146546176:rawPredict"
VERTEX_AI_MODEL = "classical-lit"
USE_VERTEX_AI = true  # 로컬 개발 시 false
```

### 작동 방식

1. **프로덕션 모드 (USE_VERTEX_AI=true)**
   - GCP 인증으로 Vertex AI 엔드포인트 호출
   - Fine-tuned Gemma 3 (LoRA) 모델 사용
   - 대화 기록 지원

2. **개발 모드 (USE_VERTEX_AI=false)**
   - Gemini API로 폴백
   - GCP 자격 증명 불필요

### API 요청 형식

```json
{
  "model": "classical-lit",
  "messages": [
    {"role": "user", "content": "시스템 프롬프트 + 학생 질문"}
  ],
  "max_tokens": 512,
  "temperature": 0.7,
  "top_p": 0.9
}
```

### 응답 파싱

모델은 다음 형식으로 응답합니다:
```
[사고유도] <힌트와 질문>
[사고로그] <AI의 사고 과정>
```

`[사고로그]` 부분은 평가용으로 별도 저장되며 학생에게는 표시되지 않습니다.

---

## 2. Firebase Auth + Firestore 연동

### 새 파일
- `app/core/firebase.py` - Firebase Admin SDK 초기화
- `app/services/firestore_session.py` - 세션 메시지 저장

### 수정된 파일
- `app/core/auth.py` - Firebase 토큰 검증 추가
- `app/api/auth.py` - 통합 토큰 검증 사용
- `app/api/sessions.py` - 메모리 저장소를 Firestore로 교체

### 인증 흐름

```
Flutter 앱
    │
    ├── Firebase Auth (Google 로그인)
    │
    └── Firebase ID Token
            │
            ▼
백엔드 (/auth/google-login)
    │
    ├── verify_firebase_token() [기본]
    │   └── firebase_admin.auth.verify_id_token()
    │
    └── verify_google_token() [폴백/레거시]
            │
            ▼
    사용자 생성/조회 (Firestore)
            │
            ▼
    백엔드 JWT 토큰 발급
```

### Firestore 구조

```
sessions/{session_id}
  ├── status: "active" | "ended" | "expired"
  ├── user_id: string
  ├── document_id: string
  ├── mode: "student_led" | "tutor_led"
  ├── created_at: timestamp
  └── messages/{message_id}
        ├── role: "user" | "assistant"
        ├── content: string
        ├── timestamp: ISO string
        └── metadata: { log: string, ... }
```

---

## 3. Cloud Logging

### 새 파일
- `app/services/cloud_logging.py` - Cloud Logging 연동

### 기능

1. **자동 환경 감지**
   - Cloud Run: Google Cloud Logging 사용
   - 로컬: 표준 Python logging 사용

2. **구조화된 로깅 헬퍼**
   ```python
   from app.services.cloud_logging import get_logger, log_model_call

   logger = get_logger(__name__)
   logger.info("세션 생성됨")

   log_model_call(logger, "vertex-ai/classical-lit", success=True, latency_ms=1500)
   ```

3. **로그 레벨**
   - DEBUG: 개발 상세 정보
   - INFO: API 호출, 성공 이벤트
   - WARNING: 폴백, 복구 가능한 오류
   - ERROR: 실패, 예외

---

## 4. Cloud Functions

### 새 파일
- `cloud_functions/main.py` - 함수 핸들러
- `cloud_functions/requirements.txt` - 의존성

### 사용 가능한 함수

| 함수 | 트리거 | 설명 |
|------|--------|------|
| `cleanup_sessions` | HTTP/스케줄러 | 만료된 세션 정리 (24시간+) |
| `generate_report` | HTTP | 학습 리포트 생성 |
| `send_notification` | HTTP | FCM 알림 전송 |

### 배포

```bash
# cleanup 함수 배포
gcloud functions deploy cleanup_sessions \
    --runtime python311 \
    --trigger-http \
    --allow-unauthenticated \
    --region asia-northeast3 \
    --project knu-team-03

# Cloud Scheduler로 스케줄링 (매시간)
gcloud scheduler jobs create http cleanup-job \
    --schedule="0 * * * *" \
    --uri="https://REGION-PROJECT.cloudfunctions.net/cleanup_sessions" \
    --http-method=POST
```

---

## 5. CORS 수정 (중요)

### 문제점
브라우저 보안 정책상 `allow_origins=["*"]`와 `allow_credentials=True`를 함께 사용할 수 없음.

### 해결책

```python
# app/main.py
cors_origins = settings.get_cors_origins()

if cors_origins:
    # 프로덕션: 특정 도메인 + credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        ...
    )
else:
    # 개발: 모든 도메인 + credentials 없음
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        ...
    )
```

### 환경 변수

```bash
# 프로덕션
CORS_ORIGINS=https://your-flutter-app.web.app,https://app.example.com

# 개발 (모든 도메인 허용)
CORS_ORIGINS=
```

---

## 6. 보안 개선

### JWT 시크릿 키

`GEMINI_API_KEY` 대신 전용 `JWT_SECRET_KEY` 사용:

```python
# 이전 (보안 취약)
SECRET_KEY = settings.GEMINI_API_KEY

# 이후 (보안 강화)
SECRET_KEY = settings.JWT_SECRET_KEY
```

### 환경 변수

```bash
JWT_SECRET_KEY=프로덕션용-시크릿-키-변경-필요
```

---

## 7. 데이터베이스 경로 수정

### 문제점
SQLite 절대 경로는 슬래시 3개가 아닌 4개가 필요함.

### 수정

```python
# 이전
DATABASE_URL=sqlite+aiosqlite:///tmp/test.db  # 상대 경로

# 이후
DATABASE_URL=sqlite+aiosqlite:////tmp/test.db  # 절대 경로 (슬래시 4개)
```

---

## 8. TextChunk 외래키 수정

### 문제점
`TextChunk.work_id`가 `literary_works.work_id`에 외래키가 있었으나, Document AI 업로드는 `RAGDocument.doc_id`를 사용함.

### 수정
외래키 제약조건을 제거하고 인덱스로 대체:

```python
# 이전
work_id = mapped_column(String(50), ForeignKey("literary_works.work_id"))

# 이후
work_id = mapped_column(String(50), index=True)
```

---

## 9. 새 의존성

`requirements.txt`에 추가:

```
google-cloud-logging>=3.0.0  # Cloud Logging
httpx>=0.25.0                # Vertex AI용 비동기 HTTP
```

---

## 10. 환경 변수 요약

### 프로덕션 필수

```bash
# AI 모델
GEMINI_API_KEY=your_key
USE_VERTEX_AI=true

# 인증
JWT_SECRET_KEY=프로덕션-시크릿

# Firebase
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
FIREBASE_PROJECT_ID=knu-team-03

# CORS
CORS_ORIGINS=https://your-app.web.app
```

### 선택 사항

```bash
# Document AI
DOCUMENT_AI_PROCESSOR_ID=프로세서_ID
DOCUMENT_AI_LOCATION=asia-northeast1

# 데이터베이스 (기본: SQLite)
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
```

---

## 11. 로컬 개발

### 설정

```bash
cd backend

# 환경 변수 템플릿 복사
cp .env.example .env

# .env 편집
# 로컬 개발을 위해 USE_VERTEX_AI=false 설정

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload --port 8000
```

### 테스트 엔드포인트

```bash
# 헬스 체크
curl http://localhost:8000/health

# 인증 헬스
curl http://localhost:8000/auth/health

# 테스트 로그인 (TEST_TOKEN 사용)
curl -X POST http://localhost:8000/auth/google-login \
  -H "Content-Type: application/json" \
  -d '{"id_token": "TEST_TOKEN", "user_type": "student"}'
```

---

## 12. Cloud Run 배포

### 빌드 및 배포

```bash
cd backend
gcloud builds submit --config=cloudbuild.yaml \
  --substitutions=_GEMINI_API_KEY=xxx,_JWT_SECRET_KEY=xxx
```

---

## 13. 파일 변경 요약

| 파일 | 상태 | 설명 |
|------|------|------|
| `app/core/config.py` | 수정 | Vertex AI, JWT, CORS 설정 추가 |
| `app/core/auth.py` | 수정 | Firebase 토큰 검증 |
| `app/core/firebase.py` | **신규** | Firebase Admin SDK |
| `app/main.py` | 수정 | CORS 설정 수정 |
| `app/api/auth.py` | 수정 | 통합 토큰 검증 |
| `app/api/sessions.py` | 수정 | Firestore 연동 |
| `app/db/models.py` | 수정 | TextChunk FK 제거 |
| `app/services/thought_inducer.py` | 수정 | Vertex AI 연동 |
| `app/services/cloud_logging.py` | **신규** | Cloud Logging |
| `app/services/firestore_session.py` | **신규** | Firestore 세션 저장 |
| `cloud_functions/main.py` | **신규** | Cloud Functions |
| `cloud_functions/requirements.txt` | **신규** | CF 의존성 |
| `requirements.txt` | 수정 | 새 패키지 추가 |

---

## 14. 테스트 체크리스트

- [ ] 서버가 오류 없이 시작됨
- [ ] `/health`가 200 반환
- [ ] TEST_TOKEN으로 `/auth/google-login` 작동
- [ ] 세션 생성 작동
- [ ] 메시지 전송 작동
- [ ] Vertex AI 응답 (프로덕션)
- [ ] Gemini 폴백 작동 (개발)
- [ ] Cloud Logging 출력 확인
- [ ] Firestore 메시지 저장 확인

---

## 15. Cloud Run 배포 설정 (cloudbuild.yaml)

### 현재 설정

```yaml
steps:
  # 1. Docker 이미지 빌드
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'asia-northeast1-docker.pkg.dev/${PROJECT_ID}/last-ok-dokhae/backend:${BUILD_ID}', '.']

  # 2. Artifact Registry에 푸시
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '...']

  # 3. Cloud Run 배포
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - '--set-env-vars'
      - 'GEMINI_API_KEY,DOCUMENT_AI_PROCESSOR_ID,JWT_SECRET_KEY,USE_VERTEX_AI=true,FIREBASE_PROJECT_ID'
      - '--memory'
      - '16Gi'
      - '--cpu'
      - '4'
      - '--min-instances'
      - '1'
      - '--timeout'
      - '300'
```

---

## 16. 최근 수정사항 (2026-02-08 최신)

| 파일 | 변경 내용 |
|------|----------|
| `cloudbuild.yaml` | CPU 4, 메모리 16Gi로 증가 |
| `app/repository/session_repository.py` | `session_repo` 싱글톤 인스턴스 추가 |
| `app/api/teacher.py` | 미사용 `LearningReport` import 제거 |

### Repository 싱글톤 패턴

```python
# session_repository.py 끝에 추가됨
session_repo = SessionRepository()

# report_repository.py (기존)
report_repo = ReportRepository()
```

---

## 문의

- 프로젝트: KNU Team 03
- 업데이트: 2026-02-08
