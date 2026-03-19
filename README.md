<div align="center">

# OK독해 AI 학습 시스템

<p>
  <img src="https://img.shields.io/badge/Award-2026%20Google%20Cloud%20AI%20Competition%20Grand%20Prize-3FA34D?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Award Badge" />
  <img src="https://img.shields.io/badge/Stack-FastAPI%20%7C%20Flutter%20%7C%20Vertex%20AI-2F855A?style=for-the-badge" alt="Stack Badge" />
  <img src="https://img.shields.io/badge/Model-Gemma%20%2B%20LoRA-14532D?style=for-the-badge" alt="Model Badge" />
</p>

<p>
  <strong>2026 전국 Google Cloud 기반 AI 융합 경진대회 최우수상</strong><br/>
  <sub>수상일: 2026/02/13</sub>
</p>

<p>
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:14532d,50:16a34a,100:86efac&height=220&section=header&text=Thinking%20Beyond%20Answers&fontSize=44&fontColor=ffffff&animation=fadeIn&fontAlignY=35" width="100%" alt="banner" />
</p>

<p>
  <strong>Socratic AI Tutor for Classical Literature</strong><br/>
  <sub>Green-themed portfolio highlight for the OK독해 project</sub>
</p>

</div>

## 프로젝트 한 줄 소개

고전문학 학습에서 정답을 바로 주는 대신, 학생이 스스로 근거를 찾고 사고를 확장하도록 유도하는 AI 학습 시스템입니다.

## 하이라이트

- `소크라틱 질문` 기반 대화형 튜터
- `4턴 핑퐁` 구조의 학습 흐름
- `질적 평가 + 정량 평가` 결합 리포트
- `Google Cloud` 기반 학습 및 배포 파이프라인
- `Flutter` 앱 + `FastAPI` 백엔드 + `Vertex AI` 서빙 연동

## 언론 보도

- Pressian: https://www.pressian.com/pages/articles/2026022317460997947

## 수상 실적

<table>
  <tr>
    <td align="center" width="50%">
      <div style="font-size:18px; font-weight:700;">🏆 최우수상</div>
      <div>2026 전국 Google Cloud 기반 AI 융합 경진대회</div>
      <div><strong>2026/02/13</strong></div>
    </td>
    <td align="center" width="50%">
      <div style="font-size:18px; font-weight:700;">🌿 프로젝트 방향</div>
      <div>정답 중심이 아니라 사고 과정 중심</div>
      <div>문학 해석, 근거 연결, 재서술 강화</div>
    </td>
  </tr>
</table>

## 팀

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/healthy27">
        <img src="https://github.com/healthy27.png?size=120" width="96" height="96" style="border-radius:50%;" alt="healthy27" />
      </a>
      <br/>
      <strong>healthy27</strong>
      <br/>
      <sub>팀장, AI/데이터 담당</sub>
    </td>
    <td align="center">
      <a href="https://github.com/blackwellSW">
        <img src="https://github.com/blackwellSW.png?size=120" width="96" height="96" style="border-radius:50%;" alt="blackwellSW" />
      </a>
      <br/>
      <strong>blackwellSW</strong>
      <br/>
      <sub>프론트엔드/기획</sub>
    </td>
    <td align="center">
      <a href="https://github.com/amblergonz">
        <img src="https://github.com/amblergonz.png?size=120" width="96" height="96" style="border-radius:50%;" alt="amblergonz" />
      </a>
      <br/>
      <strong>amblergonz</strong>
      <br/>
      <sub>백엔드/기획</sub>
    </td>
    <td align="center">
      <a href="https://github.com/123k444">
        <img src="https://github.com/123k444.png?size=120" width="96" height="96" style="border-radius:50%;" alt="123k444" />
      </a>
      <br/>
      <strong>123k444</strong>
      <br/>
      <sub>백엔드/디자인</sub>
    </td>
  </tr>
</table>

## 핵심 기능

### 1. 사고유도 대화형 학습
- 학생의 답을 바로 정답 처리하지 않고, 다음 사고를 이끌 질문을 제공합니다.
- 작품 이해, 표현 해석, 근거 연결, 재서술을 반복하며 학습합니다.

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

## 아키텍처

```text
학생 입력
   ↓
Flutter 앱
   ↓
FastAPI 백엔드
   ↓
Vertex AI / vLLM 모델 서빙
   ↓
Gemini + NLP 평가
   ↓
리포트 저장 및 재조회
```

## 기술 스택

<p>
  <img src="https://img.shields.io/badge/FastAPI-0F766E?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Flutter-0F9D58?style=for-the-badge&logo=flutter&logoColor=white" alt="Flutter" />
  <img src="https://img.shields.io/badge/Python-2E7D32?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Google_Cloud-34A853?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Google Cloud" />
  <img src="https://img.shields.io/badge/Vertex_AI-16A34A?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Vertex AI" />
  <img src="https://img.shields.io/badge/Gemini-15803D?style=for-the-badge&logo=google&logoColor=white" alt="Gemini" />
  <img src="https://img.shields.io/badge/Firestore-65A30D?style=for-the-badge&logo=firebase&logoColor=white" alt="Firestore" />
  <img src="https://img.shields.io/badge/Document_AI-166534?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Document AI" />
</p>

## 저장소 구성

```text
.
├── backend/                 # FastAPI 서버, API, 서비스, 스키마
├── frontend/                # Flutter 앱
├── deployment/              # vLLM / Vertex AI / Docker 배포 파일
├── scripts/                 # 학습, 평가, 배포, 시각화 스크립트
├── docs/                    # 발표 자료, 기술 정리, 평가 문서
├── model_artifacts/         # 학습된 어댑터 및 모델 산출물
├── app/                     # 데모 및 테스트용 앱
└── requirements.txt         # 공통 의존성
```

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

### 3. Flutter 프론트엔드 실행

```bash
cd frontend
flutter pub get
flutter run
```

## 환경 변수 예시

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
