# OK독해 백엔드 기술 스택

## 개요

고전문학 사고유도 AI 학습 시스템의 백엔드 기술 스택입니다.

---

## 1. 핵심 프레임워크

### FastAPI (Python 3.11+)
- **버전**: 0.109.0
- **역할**: REST API 서버
- **선택 이유**:
  - 자동 OpenAPI (Swagger) 문서 생성
  - Pydantic 기반 데이터 검증
  - 비동기(async/await) 네이티브 지원
  - 타입 힌트 기반 개발

### Uvicorn
- **버전**: 0.27.0
- **역할**: ASGI 서버
- **특징**: 고성능 비동기 HTTP 서버

### Pydantic
- **버전**: 2.5.0
- **역할**: 데이터 검증 및 직렬화
- **사용처**: Request/Response 스키마, 설정 관리

---

## 2. AI/ML 서비스

### Google Vertex AI
- **역할**: 메인 AI 모델 서빙
- **모델**: Fine-tuned Gemma 3 LoRA ("classical-lit")
- **엔드포인트**: us-central1-aiplatform.googleapis.com
- **특징**:
  - 고전문학 특화 사고유도 응답 생성
  - 대화 기록 기반 컨텍스트 유지
  - GCP 서비스 계정 인증

```python
# 요청 예시
{
  "model": "classical-lit",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 512,
  "temperature": 0.7
}
```

### Google Gemini API
- **역할**: 폴백 및 분석용
- **모델**: gemini-1.5-flash
- **사용처**:
  - Vertex AI 장애 시 대체
  - 통합 평가 (질적 70% + 정량 30%)
  - 텍스트 분석

### Google Document AI
- **역할**: 문서 텍스트 추출
- **지원 형식**: PDF, 이미지
- **리전**: asia-northeast1

---

## 3. 데이터베이스

### Google Cloud Firestore
- **역할**: 메인 데이터베이스 (NoSQL)
- **컬렉션 구조**:

```
firestore/
├── users/                    # 사용자 정보
│   └── {user_id}
│       ├── email
│       ├── username
│       ├── user_type (student|teacher|admin)
│       └── created_at
│
├── learning_states/          # 학습 세션 상태
│   └── {session_id}
│       ├── user_id
│       ├── status (ACTIVE|COMPLETED)
│       ├── current_turn
│       ├── max_turns
│       └── checkpoint_data
│
├── rag_documents/            # 업로드된 문서
│   └── {doc_id}
│       ├── title
│       ├── content
│       ├── chunks[]
│       └── doc_type
│
├── reports/                  # 평가 리포트
│   └── {report_id}
│       ├── user_id
│       ├── session_id
│       ├── score
│       └── feedback
│
└── teacher_dashboard_data/   # 교사 대시보드
    └── {dashboard_id}
```

### SQLite (로컬 개발용)
- **역할**: 로컬 테스트 및 임시 데이터
- **경로**: `/tmp/classical_literature.db` (Cloud Run)
- **ORM**: SQLAlchemy 2.0 + aiosqlite

---

## 4. 인증 시스템

### Firebase Authentication
- **역할**: 사용자 인증 (프론트엔드)
- **지원 방식**: Google OAuth 2.0
- **토큰**: Firebase ID Token

### JWT (JSON Web Token)
- **역할**: 백엔드 세션 관리
- **라이브러리**: python-jose
- **흐름**:

```
[Flutter] Firebase Auth → ID Token
              ↓
[Backend] 검증 → Backend JWT 발급
              ↓
[Flutter] Authorization: Bearer {JWT}
```

### 인증 흐름

```
1. Flutter에서 Firebase Google Sign-In
2. Firebase ID Token 획득
3. POST /auth/google-login {id_token}
4. Backend에서 Firebase Admin SDK로 검증
5. 사용자 생성/조회 (Firestore)
6. Backend JWT 발급
7. Flutter는 이후 요청에 JWT 사용
```

---

## 5. 클라우드 인프라 (Google Cloud Platform)

### Cloud Run
- **역할**: 컨테이너 기반 서버리스 배포
- **리전**: asia-northeast1
- **스펙**:
  - CPU: 4 vCPU
  - 메모리: 16Gi
  - 최소 인스턴스: 1 (콜드 스타트 방지)
  - 타임아웃: 300초

### Cloud Build
- **역할**: CI/CD 파이프라인
- **설정 파일**: `cloudbuild.yaml`
- **단계**:
  1. Docker 이미지 빌드
  2. Artifact Registry 푸시
  3. Cloud Run 배포

### Artifact Registry
- **역할**: Docker 이미지 저장소
- **경로**: `asia-northeast1-docker.pkg.dev/knu-team-03/last-ok-dokhae/backend`

### Cloud Logging
- **역할**: 중앙 로그 관리
- **특징**:
  - 구조화된 JSON 로그
  - 자동 환경 감지 (Cloud Run vs 로컬)
  - 에러 추적 및 알림

### Cloud Functions (선택적)
- **역할**: 백그라운드 작업
- **사용 예**:
  - 세션 만료 처리
  - 리포트 생성
  - 알림 전송

---

## 6. 주요 라이브러리

| 카테고리 | 라이브러리 | 버전 | 용도 |
|---------|-----------|------|------|
| **웹** | fastapi | 0.109.0 | API 프레임워크 |
| | uvicorn | 0.27.0 | ASGI 서버 |
| | pydantic | 2.5.0 | 데이터 검증 |
| **GCP** | google-cloud-aiplatform | 1.38.0+ | Vertex AI |
| | google-cloud-firestore | latest | Firestore |
| | google-cloud-documentai | 2.20.0+ | Document AI |
| | google-cloud-logging | 3.0.0+ | Cloud Logging |
| | firebase-admin | 6.0.0+ | Firebase Admin |
| **AI** | google-generativeai | 0.3.0+ | Gemini API |
| **인증** | python-jose | 3.3.0 | JWT |
| | passlib | 1.7.4 | 비밀번호 해싱 |
| **DB** | sqlalchemy | 2.0.0+ | ORM |
| | aiosqlite | latest | SQLite 비동기 |
| **HTTP** | httpx | 0.25.0+ | 비동기 HTTP |
| **문서** | pypdf | 3.0.0+ | PDF 파싱 |
| | python-docx | 0.8.11+ | DOCX 파싱 |

---

## 7. 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flutter 앱                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Firebase Auth│  │  API Client  │  │    UI/UX     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Cloud Run (백엔드)                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   FastAPI 애플리케이션                     │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │  │
│  │  │  인증   │ │  세션   │ │ 리포트  │ │  교사   │        │  │
│  │  │  API    │ │   API   │ │   API   │ │   API   │        │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘        │  │
│  │                         │                                  │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │                   서비스 계층                         │ │  │
│  │  │  ThoughtInducer │ Evaluator │ ReportGenerator       │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  │                         │                                  │  │
│  │  ┌─────────────────────────────────────────────────────┐ │  │
│  │  │                 레포지토리 계층                       │ │  │
│  │  │  SessionRepo │ UserRepo │ DocumentRepo │ ReportRepo │ │  │
│  │  └─────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   Vertex AI      │  │    Firestore     │  │   Document AI    │
│ (Gemma 3 LoRA)   │  │   (데이터베이스)  │  │  (OCR/텍스트추출) │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 8. 보안

### 인증
- Firebase ID Token 검증
- Backend JWT 발급 및 검증
- 역할 기반 접근 제어 (student/teacher/admin)

### CORS
- 프로덕션: 특정 도메인만 허용
- 개발: 모든 도메인 허용 (credentials=False)

### 환경 변수
- 민감한 정보는 Cloud Run 환경변수로 관리
- `.env` 파일은 `.gitignore`에 포함

### 네트워크
- HTTPS 전용 (Cloud Run 자동 제공)
- VPC 커넥터 (선택적)

---

## 9. 모니터링

### Cloud Logging
- 모든 API 요청/응답 로깅
- 에러 스택 트레이스
- AI 모델 호출 지연시간

### Cloud Monitoring (선택적)
- CPU/메모리 사용률
- 요청 지연시간
- 에러율 알림

---

## 10. 확장성

### 현재 구조의 장점
- **서버리스**: 자동 스케일링
- **마이크로서비스 준비**: 모듈화된 구조
- **NoSQL**: 스키마 유연성

### 향후 확장 가능
  - Redis 캐싱 추가
  - BigQuery 분석 파이프라인
  - Pub/Sub 이벤트 시스템
  - Kubernetes 마이그레이션

---

*마지막 업데이트: 2026-02-08*
