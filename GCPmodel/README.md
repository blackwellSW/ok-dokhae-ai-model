# OK독해 AI 학습 시스템

> 고전문학 사고유도 대화 AI + 자동 평가 + Google Cloud 배포까지 연결한 통합 프로젝트

## 수상 이력

- `2026 전국 Google Cloud 기반 AI 융합 경진대회 최우수상`
- 수상일: `2026/02/13`

## 프로젝트 소개

**OK독해**는 고전문학 학습에서 정답을 바로 주는 방식이 아니라, 학생이 스스로 근거를 찾고 사고를 확장하도록 유도하는 AI 학습 시스템입니다.

이 프로젝트는 다음 흐름을 중심으로 구성되어 있습니다.

- `소크라틱 질문` 기반 대화형 튜터
- `4턴 핑퐁` 학습 흐름
- `질적 평가 + 정량 평가`를 결합한 자동 리포트
- `Google Cloud` 기반 학습/배포 파이프라인
- `Flutter` 앱, `FastAPI` 백엔드, `Vertex AI` 모델 서빙 연동

## 핵심 기능

### 1. 사고유도 대화형 학습
- 학생의 답을 바로 정답 처리하지 않고, 다음 사고를 이끌 질문을 제공합니다.
- 작품 이해, 표현 해석, 근거 연결, 재서술을 반복하며 학습을 진행합니다.

### 2. 자동 평가 시스템
- Gemini 기반 질적 평가
- 형태소 분석 및 언어 지표 기반 정량 평가
- 두 결과를 합산해 점수와 피드백 리포트를 생성합니다.

### 3. 문서/세션/리포트 관리
- 문서 업로드 및 파싱
- 학습 세션 생성 및 대화 로그 저장
- 리포트 생성 및 재조회
- 교사용 요약 화면 지원

### 4. 페르소나 기반 응답 스타일
- 조선시대 문인 스타일
- 교육 스타일 기반 페르소나
- 학생이 원하는 튜터 톤을 선택할 수 있는 구조

## 기술 스택

- `Backend`: FastAPI, Python
- `Frontend`: Flutter
- `Model`: Gemma 계열 모델, LoRA/QLoRA
- `Inference`: Vertex AI, vLLM
- `Evaluation`: Gemini, NLP 기반 분석
- `Auth`: JWT, Google OAuth
- `Storage`: Firestore, Cloud Storage, Document AI
- `Deployment`: Google Cloud, Cloud Build, Cloud Run/Vertex AI 계열 배포 스크립트

## 저장소 구성

```text
.
├── backend/                 # FastAPI 서버, API, 서비스, 스키마
├── frontend/                # Flutter 앱
├── deployment/              # vLLM / Vertex AI / Docker 배포 관련 파일
├── scripts/                 # 학습, 평가, 배포, 시각화 스크립트
├── docs/                    # 발표 자료, 기술 정리, 평가 문서
├── model_artifacts/         # 학습된 어댑터 및 모델 산출물
├── app/                     # 데모 및 테스트용 앱
└── requirements.txt         # 공통 의존성
```

## 아키텍처 요약

1. 학생이 Flutter 앱에서 문서를 선택하거나 업로드합니다.
2. FastAPI 백엔드가 세션과 학습 상태를 관리합니다.
3. 모델은 사고유도 질문과 피드백을 생성합니다.
4. Gemini/NLP 평가기가 응답 품질을 점검합니다.
5. 결과는 리포트로 저장되어 교사/학생 화면에 재사용됩니다.

## 실행 방법

### 1. 공통 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 백엔드 실행

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

API 문서는 실행 후 아래에서 확인할 수 있습니다.

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

### 3. Flutter 프론트엔드 실행

```bash
cd frontend
flutter pub get
flutter run
```

### 4. 배포/모델 관련 스크립트

- `scripts/` 아래에 학습, 검증, 배포, 시각화용 스크립트가 정리되어 있습니다.
- `deployment/` 아래에 vLLM 및 Google Cloud 배포용 파일이 있습니다.

## 환경 변수 예시

프로젝트 실행 시 아래 값들이 필요할 수 있습니다.

```bash
GEMINI_API_KEY=your-api-key
GOOGLE_CLIENT_ID=your-google-oauth-client-id
JWT_SECRET_KEY=change-this-in-production
DATABASE_URL=sqlite+aiosqlite:////tmp/test.db
VERTEX_AI_ENDPOINT=your-vertex-endpoint
VERTEX_AI_MODEL=classical-lit
USE_VERTEX_AI=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## 주요 API

- `POST /auth/login`
- `POST /auth/register`
- `POST /documents`
- `POST /sessions`
- `POST /sessions/{id}/messages`
- `GET /reports/{id}`
- `GET /teacher/*`

## 개발 메모

- 백엔드는 `FastAPI` 기반이며 `backend/app/main.py`가 진입점입니다.
- 모델 서빙 설정은 `backend/app/core/config.py`를 참고하면 됩니다.
- 발표/기술 정리 문서는 `docs/` 폴더에 있습니다.

## GitHub

- Repository: https://github.com/blackwellSW/ok-dokhae-ai-model

## 라이선스

MIT License
