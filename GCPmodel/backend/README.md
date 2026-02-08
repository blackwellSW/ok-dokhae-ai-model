# 🎓 고전문학 사고유도 AI 학습 시스템 (Ok-Dokhae Backend)

> **사고를 깨우는 질문, 깊이 있는 독해**  
> 학생의 사고 과정을 유도하고(Socratic Method), 다차원적으로 평가하여(Gemini + NLP) 맞춤형 피드백을 제공하는 AI 학습 플랫폼입니다.

---

## 📌 핵심 기능 (Features)

### 1. 💬 채팅형 사고유도 학습 (Chat Learning)
- **소크라틱 대화법**: 정답을 바로 알려주는 것이 아니라, 꼬리에 꼬리를 무는 질문으로 학생 스스로 깨닫게 유도합니다.
- **4단계 핑퐁 시스템**: 질문 → 답변 → 평가 → 재질문의 4회 턴(Turn) 구조로 학습 세션이 진행됩니다.
- **자동 리포트 생성**: 4회 핑퐁 완료 시, 전체 대화 내용을 분석하여 종합 리포트를 자동 생성합니다.

### 2. 🔐 사용자 및 인증 (Authentication)
- **JWT 기반 인증**: 안전한 회원가입 및 로그인 시스템.
- **역할 관리**: 학생(Student), 교사(Teacher), 관리자(Admin) 권한 분리.

### 3. 📊 다차원 평가 시스템 (Evaluation)
- **질적 평가 (Qualitative)**: Gemini Pro를 활용해 추론 깊이, 비판적 사고, 문학적 이해를 5점 척도로 평가하고 구체적인 피드백을 제공합니다. (가중치 70%)
- **정량 평가 (Quantitative)**: 형태소 분석(KoNLPy)을 통해 어휘 다양성, 문장 복잡도, 개념어 사용 빈도를 분석합니다. (가중치 30%)
- **통합 점수**: 두 평가 결과를 종합하여 100점 만점 점수와 등급(S~C)을 산출합니다.

### 4. 📈 상세 리포트 생성 (Report Generation)
- **표준화된 JSON 리포트**: 
  - 점수 카드 (5개 영역)
  - 사고 흐름 분석 (Perfect/Good/Weak)
  - 맞춤형 처방전 (Actionable Prescription)
- **프론트엔드 최적화**: UI 렌더링에 바로 사용할 수 있는 구조화된 데이터를 제공합니다.

---

## 🛠️ 기술 스택 (Tech Stack)

- **Language**: Python 3.10+
- **Framework**: FastAPI (Async)
- **Database**: 
  - ORM: SQLAlchemy (AsyncIO)
  - DB: SQLite (Dev) / PostgreSQL (Prod)
- **AI & NLP**:
  - LLM: Google Gemini Pro
  - NLP: KoNLPy (Okt)
- **Auth**: JWT (Python-Jose), Passlib (Bcrypt)

---

## 📂 프로젝트 구조

```
backend/
├── app/
│   ├── api/                # API 엔드포인트 (컨트롤러)
│   │   ├── auth.py             # 인증 (로그인/회원가입)
│   │   ├── chat_learning.py    # 채팅 학습 (메인)
│   │   ├── report_generator_api.py # 리포트 생성
│   │   └── ...
│   ├── core/               # 핵심 설정 (Config, Security)
│   ├── db/                 # DB 모델 및 세션
│   │   └── models.py           # User, LearningState, Logs 등 모든 모델
│   ├── services/           # 비즈니스 로직 (핵심 엔진)
│   │   ├── report_generator.py # 리포트 생성 로직
│   │   ├── gemini_evaluator.py # LLM 평가 엔진
│   │   ├── thought_inducer.py  # 사고유도 질문 생성기
│   │   └── ...
│   └── main.py             # 앱 진입점
├── init_db.py              # DB 초기화 스크립트
├── test_imports.py         # 실행 환경 테스트 스크립트
└── requirements.txt        # 의존성 목록
```

---

## 🚀 시작 가이드 (Quick 

### 1. 환경 설정

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 (.env) 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 내용을 입력하세요.

```ini
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=sqlite+aiosqlite:///./classical_literature.db
```

### 3. 데이터베이스 초기화

최초 1회 실행하여 테이블을 생성합니다.

```bash
python init_db.py
```

### 4. 서버 실행

```bash
# 개발 모드 (Auto Reload)
python -m uvicorn app.main:app --reload --port 8000
```

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📡 주요 API 명세

### 1. 인증 (Auth)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/auth/register` | 회원가입 (student/teacher) |
| `POST` | `/auth/login` | 로그인 (Access Token 발급) |

### 2. 채팅 학습 (Learning)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/chat/works` | 학습 가능한 작품 목록 조회 |
| `POST` | `/chat/send` | 메시지 전송 (사고유도 질문 받기) |
| `POST` | `/chat/evaluate` | 답변 평가 요청 (점수/피드백) |

### 3. 학습 시스템 (Advanced)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/learning/start` | 4턴 학습 세션 시작 |
| `POST` | `/learning/submit-answer` | 답변 제출 (4턴 도달 시 종료 및 리포트 ID 반환) |
| `POST` | `/reports/generate` | 평가 데이터를 기반으로 최종 리포트 JSON 생성 |

---

## 💡 프론트엔드 연동 가이드

### 세션 종료 처리 (4-Turn Session)

`/learning/submit-answer` 응답의 `session_status` 필드를 확인하여 처리합니다.

1. **진행 중 (`ACTIVE`)**:
   - `next_question`을 채팅창에 표시하고 사용자 입력을 기다립니다.
   
2. **종료 (`COMPLETED`)**:
   - `report_id`가 함께 반환됩니다.
   - 더 이상 입력을 받지 말고, **결과 리포트 페이지**로 이동시킵니다.

### 리포트 데이터 구조

`/reports/generate` 응답은 100% UI 렌더링용 데이터입니다. 복잡한 가공 없이 그대로 뿌려주면 됩니다.

```json
{
  "summary": "총 4단계 중 3단계를 성공적으로...",
  "tags": ["#논리적추론", "#어휘력풍부", "#성실한학습"],
  "scores": [
    {"label": "추론 깊이", "score": 0.8, "label_text": "탁월함", "reason": "..."}
  ],
  "prescription": "주장에 대한 근거를 본문에서 찾아 연결하는 연습을 하세요."
}
```

---

## ✅ 버전 정보

- **Current Version**: v4.1.0
- **Last Updated**: 2026.02.05
