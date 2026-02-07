# 🎓 고전문학 사고유도 AI 프로젝트

> **목표**: 고전문학 학습용 사고유도 대화 AI + 자동 평가 시스템  
> **리소스**: GCP 크레딧 500만원, AI HUB 데이터셋, Gemini API

---

## 📋 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [기술 스택](#기술-스택)
4. [데이터 전략](#데이터-전략)
5. [핵심 모듈](#핵심-모듈)
6. [평가 시스템](#평가-시스템)
7. [코드 구조](#코드-구조)
8. [구현 코드](#구현-코드)

---

## 🎯 프로젝트 개요

### 핵심 목표
1. **사고유도 AI**: 고전문학으로 학습된 대화형 AI (Gemma 3 파인튜닝)
2. **사고로그 생성**: 학생의 사고 과정을 구조화하여 자동 기록
3. **자동 평가 시스템**: 
   - Gemini 기반 질적 평가 (추론깊이, 비판적사고, 문학적이해)
   - 언어 분석 기반 정량 평가 (어휘다양성, 개념어사용, 감정톤 등)
4. **확장 가능성**: 다른 과목 코퍼스로 확장 가능한 모듈형 구조

### 핵심 차별점
**기존**: 단순 질문-답변  
**우리**: 사고 유도 → 사고로그 생성 → 질적+정량 평가 → 개인 맞춤 피드백

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                       전체 시스템 플로우                         │
└─────────────────────────────────────────────────────────────────┘

[학생 질문] 
    ↓
┌────────────────────────────────────────────────────────┐
│  Gemma 3 9B (Fine-tuned)                               │
│  - 고전문학 600개 데이터 학습                           │
│  - LoRA 파인튜닝                                       │
│  - 소크라틱 대화 패턴 적용                              │
└────────────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────────────┐
│  사고유도 대화 + 사고로그 생성                          │
│  [사고유도] 단계적 질문으로 학생 사고 유도              │
│  [사고로그] 학생 사고 과정 자동 기록                    │
└────────────────────────────────────────────────────────┘
    ↓
    ├─────────────────────────┬─────────────────────────┐
    ↓                         ↓                         ↓
┌─────────────┐      ┌──────────────┐       ┌────────────────┐
│ Gemini Pro  │      │  언어 분석    │       │  유해표현 AI   │
│ 질적 평가   │      │  정량 평가    │       │  (AI HUB)      │
│             │      │              │       │                │
│ • 추론깊이  │      │ • 어휘다양성  │       │ • 욕설 감지    │
│ • 비판적사고│      │ • 개념어사용  │       │ • 부적절언어   │
│ • 문학이해  │      │ • 문장복잡도  │       │                │
│             │      │ • 감정톤     │       │                │
└─────────────┘      └──────────────┘       └────────────────┘
    │                         │                         │
    └─────────────────────────┴─────────────────────────┘
                              ↓
                    ┌──────────────────┐
                    │   통합 평가       │
                    │   (질적 70%      │
                    │    정량 30%)     │
                    └──────────────────┘
                              ↓
                    [개인 맞춤 피드백]
                    [교사용 리포트]


┌─────────────────────────────────────────────────────────────────┐
│                      기술 아키텍처                               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌─────────────────┐
│ Data Layer   │      │ Model Layer  │      │ Evaluation      │
├──────────────┤      ├──────────────┤      ├─────────────────┤
│ AI HUB       │─────→│ Gemma 3 9B   │─────→│ • Gemini Pro    │
│ • 고전문학600 │      │ + LoRA       │      │ • 언어분석기    │
│ • 지문형문제 │      │ (4bit quant) │      │ • 유해표현AI    │
│ • 주제별평가 │      │              │      │                 │
│ • 교과데이터 │      │              │      │                 │
└──────────────┘      └──────────────┘      └─────────────────┘
        │                     │                       │
        └─────────────────────┴───────────────────────┘
                              │
                   ┌──────────────────┐
                   │ GCP Vertex AI    │
                   │ • A100/L4 GPU    │
                   │ • Cloud Storage  │
                   └──────────────────┘
```

---

## 🛠️ 기술 스택

### 핵심 기술

| 분야 | 기술 | 용도 |
|------|------|------|
| **Base Model** | Gemma 3 (9B-it) | 사고유도 대화 생성 |
| **Evaluation** | Gemini Pro (1.5) | 질적 평가 |
| **Fine-tuning** | LoRA/QLoRA | 메모리 효율적 학습 |
| **Language Analysis** | KoNLPy + Custom | 정량적 언어 분석 |
| **Harmful Content** | 유해표현 검출 AI (AI HUB) | 욕설/부적절 언어 감지 |
| **Framework** | Transformers 4.38+ | 모델 로딩/학습 |
| **Cloud** | GCP Vertex AI | 학습 인프라 |

**왜 Gemma 3인가?**
- **최신 모델** (2025년 3월 출시, 11개월 검증)
- **성능 향상**: Gemma 2 대비 개선된 아키텍처
- **충분한 안정성**: 파인튜닝 사례 풍부, 버그 해결됨
- **GCP 완벽 지원**: Vertex AI 최적화
- **교육 분야 적합**: 대화형 생성에 특화

### 패키지 의존성

```python
# requirements.txt

# 핵심 모델
transformers==4.38.0
peft==0.9.0
accelerate==0.27.0
bitsandbytes==0.42.0
datasets==2.17.0
torch==2.1.0

# 평가 시스템
google-generativeai==0.4.0
google-cloud-aiplatform==1.40.0

# 언어 분석 (개선)
konlpy==0.6.0
sentence-transformers==2.2.2      # 의미 유사도 분석
scikit-learn==1.3.0               # 코사인 유사도

# 기본
pandas==2.1.0
numpy==1.24.0
```

---

## 📊 데이터 전략

### 보유 데이터셋 (AI HUB)

| 데이터 | 크기 | 용도 | 우선순위 |
|--------|------|------|---------|
| 고전문학 | 600개 | 🔴 **핵심 학습 데이터** | 1 |
| 국어 교과 지문형 문제 | 1.26GB | 질문 패턴 학습 | 1 |
| 논술형/서술형 평가 | 232MB | 평가 루브릭 참고 | 1 |
| 유해표현 검출 AI 모델 | 61MB | 욕설/부적절 언어 감지 | 1 |

### 데이터 처리 파이프라인

```
[AI HUB 원본 데이터]
- 고전문학: 600개
- 지문형 문제: 1.26GB
         ↓
[구조 분석 & 전처리]
- 고전문학 텍스트 파싱
- 질문-답변 쌍 추출
         ↓
[소크라틱 대화 변환]
- 수동 작성: 50개 (고품질 템플릿)
- 자동 변환: 250개 (GPT-4/Claude 활용, 고전문학 중심)
         ↓
[태그 추가]
- [사고유도] 태그
- [사고로그] 태그
         ↓
[품질 검증 & 필터링]
- 저품질 데이터 제거
- 일관성 검증
         ↓
[최종 학습 데이터 300개]
- Train: 240개 (80%)
- Valid: 60개 (20%)
```

### 데이터 포맷

```json
{
  "id": "classic_001",
  "source": "춘향전",
  "instruction": "학생의 사고를 유도하며 고전문학을 가르치세요. [사고유도]와 [사고로그] 태그를 사용하세요.",
  "input": "학생: 춘향전에서 이몽룡이 신분을 숨긴 이유가 뭔가요?",
  "output": "[사고유도] 좋은 질문이네요! 먼저 조선시대 신분제를 생각해볼까요? 만약 이몽룡이 처음부터 \"저는 양반 도련님입니다\"라고 밝혔다면, 춘향과의 관계가 어떻게 달라졌을까요? 춘향의 반응은 어땠을까요?\n\n[사고로그] 학생이 신분제와 사랑의 진정성을 연결지어 사고 시작. 조선시대 사회 구조에 대한 이해를 바탕으로 인물 행동의 동기를 추론하려는 시도가 보임. 추론 깊이: 중상. 맥락 이해: 양호."
}
```

---

## 🔧 핵심 모듈

### 1. Gemma 3 파인튜닝 모듈
- **역할**: 고전문학 데이터로 사고유도 대화 학습
- **기술**: LoRA (Low-Rank Adaptation) + 4-bit 양자화
- **학습 설정**:
  - Epochs: 3
  - Batch size: 4
  - Learning rate: 2e-4
  - 예상 시간: 8-12시간 (A100 기준)

### 2. 사고유도 추론 엔진
- **역할**: 학생 질문 → 사고유도 응답 + 사고로그 생성
- **출력**:
  - `[사고유도]`: 단계적 질문으로 사고 유도
  - `[사고로그]`: 학생 사고 과정 자동 기록

### 3. Gemini 평가 시스템 (질적)
- **3차원 루브릭**:
  1. **추론 깊이**: 다층적 사고, 맥락 통합
  2. **비판적 사고**: 독자적 해석, 다양한 관점
  3. **문학적 이해**: 시대/문화 맥락, 작품 구조

### 4. 언어 분석 모듈 (정량)
- **6가지 지표**:
  1. **어휘 다양성**: TTR (Type-Token Ratio)
  2. **핵심 개념어 사용**: 고전문학 관련 용어 빈도
  3. **문장 복잡도**: 평균 문장 길이 + 절 개수
  4. **반복 패턴**: 과도한 반복 표현 감지
  5. **감정 톤**: 긍정/부정/중립 분석
  6. **유해표현 감지**: AI HUB 모델 활용 (욕설, 부적절 언어)

### 5. 통합 평가 시스템
- **질적 평가 (70%)**: Gemini 루브릭 기반
- **정량 평가 (30%)**: 언어 분석 지표
- **최종 출력**:
  - 종합 점수 (A+~C+)
  - 개인 맞춤 피드백
  - 교사용 상세 리포트

---

## 📈 평가 시스템

### 질적 평가 루브릭 (Gemini)

#### 1. 추론 깊이 (1-5점)

| 점수 | 기준 |
|------|------|
| 5점 | 다층적 사고, 여러 요소 통합, 텍스트 맥락 깊이 이해 |
| 4점 | 논리적 추론, 맥락과 내용 연결 |
| 3점 | 기본적 추론, 표면적 맥락 이해 |
| 2점 | 단편적 이해, 논리적 연결 부족 |
| 1점 | 표면적 반응, 추론 없음 |

#### 2. 비판적 사고 (1-5점)

| 점수 | 기준 |
|------|------|
| 5점 | 독자적 해석, 다양한 관점 고려, 텍스트 비평 |
| 4점 | 대안적 해석 시도, 일부 관점 다양성 |
| 3점 | 질문에 대한 직접적 답변 |
| 2점 | 단순 정보 회상, 해석 시도 미흡 |
| 1점 | 관련 없는 응답 또는 오해 |

#### 3. 문학적 이해 (1-5점)

| 점수 | 기준 |
|------|------|
| 5점 | 시대적/문화적 맥락 통합, 작품 전체 구조 파악 |
| 4점 | 작품 구조와 주제 이해 |
| 3점 | 줄거리와 주요 사건 이해 |
| 2점 | 부분적 이해, 오해 일부 포함 |
| 1점 | 작품 내용 오해 |

---

### 정량 평가 지표 (언어 분석)

#### 1. 어휘 다양성 (Vocabulary Diversity)

**개선된 평가 방법: 다층적 분석**

```python
최종 점수 = (
    기본_TTR * 0.3 +           # 고유단어/전체단어
    MTLD * 0.4 +               # 텍스트 길이 보정
    품사_다양성 * 0.2 +        # 명사/동사/형용사/부사 균형
    학문적_어휘 * 0.1          # 한자어, 전문용어 비율
)

등급:
- 0.75 이상: 우수 (풍부하고 정교한 어휘)
- 0.6-0.75: 양호 (적절한 어휘 사용)
- 0.4-0.6: 보통 (기본적 어휘)
- 0.4 미만: 개선필요 (제한적 어휘)
```

**핵심 기술**:
- **MTLD (Measure of Textual Lexical Diversity)**: 텍스트 길이에 덜 민감한 학술적 지표
- **품사 엔트로피**: 명사/동사/형용사/부사의 균형도 측정
- **학문적 어휘 비율**: 한자어, 3음절 이상 명사 등 추상적 표현력

#### 2. 핵심 개념어 사용

**개선된 평가 방법: 임베딩 기반 의미 유사도**

```python
# 고정된 단어 리스트가 아닌, 의미 기반 매칭
개념_카테고리 = {
    "문학적_기법": ["상징", "은유", "복선", "반전", "갈등구조"],
    "사회문화적_맥락": ["신분제", "시대적배경", "계급갈등", "유교사상"],
    "인간관계_심리": ["사랑", "효", "충", "절개", "욕망", "갈등"],
    "주제_메시지": ["주제", "교훈", "풍자", "비판", "가치관"]
}

# Sentence-BERT로 의미 유사도 계산
유사도 >= 0.6 → 개념어로 인정

예시:
- 학생: "계급의 벽" → 매칭: "신분제" (유사도 0.78)
- 학생: "마음의 갈등" → 매칭: "심리적 갈등" (유사도 0.82)

평가:
- 5개 이상 + 3개 카테고리: 우수
- 3-4개 + 2개 카테고리: 양호
- 1-2개: 보통
- 0개: 부족
```

**핵심 기술**:
- **Sentence-BERT (ko-sroberta)**: 한국어 문장/단어 임베딩
- **코사인 유사도**: 의미적으로 유사한 표현 자동 인식
- **사전 없이도 작동**: 학생이 자신만의 표현을 써도 평가 가능

#### 3. 문장 복잡도

```python
복잡도 = (평균 문장 길이 / 10) + (평균 절 개수 * 2)

등급:
- 10 이상: 복잡함 (심층적 사고)
- 6-10: 적절함
- 6 미만: 단순함
```

#### 4. 반복 패턴

```python
과도한 반복 = 같은 단어/표현 3회 이상

평가:
- 반복률 > 0.2: 주의 (다양한 표현 권장)
- 반복률 ≤ 0.2: 양호
```

#### 5. 감정 톤

**개선된 평가 방법: 맥락 고려 AI 모델**

```python
# 다층적 감정 분석
1. 전체_감정: KcELECTRA 감정분석 모델
2. 학습_태도: 탐구적 > 적극적 > 긍정적 > 중립적 > 소극적
3. 맥락_감정: 문장별 분석 후 통합

최종_톤 = (
    전체_감정 * 0.3 +
    학습_태도 * 0.5 +    # 학습 태도를 더 중시
    맥락_감정 * 0.2
)

5단계 톤:
- 매우긍정적 (0.4~1.0): "학습 흥미와 탐구 의지 높음"
- 긍정적 (0.1~0.4): "학습에 적극적"
- 중립적 (-0.1~0.1): "보통 수준, 동기부여 필요"
- 부정적 (-0.4~-0.1): "동기 저하, 지원 필요"
- 매우부정적 (-1.0~-0.4): "즉시 개입 필요"

예시:
- "어렵지만 흥미롭다" → 긍정적 (맥락 이해)
- "이해 안 돼. 하지만 더 알고 싶다" → 탐구적 (학습 의지)
```

**핵심 기술**:
- **KcELECTRA**: 한국어 맥락 이해 감정분석 모델
- **학습 태도 분리**: 단순 감정 vs 학습 의지 구분
- **맥락 고려**: 문장 단위 분석으로 뉘앙스 파악

#### 6. 유해표현 감지

```python
# AI HUB 유해표현 검출 AI 모델 활용
유해표현_모델.detect(student_text)

경고 레벨:
- 안전: 유해표현 0개
- 주의: 1-2개
- 경고: 3개 이상 (교사 알림)
```

---

### 통합 평가 산출

```python
# 질적 평가 (70%)
질적_점수 = Gemini_평균점수 * 0.7 * 20  # 최대 70점

# 정량 평가 (30%)
어휘_점수 = TTR * 10                    # 최대 10점
개념_점수 = min(개념어_사용 * 2, 10)     # 최대 10점
복잡_점수 = min(문장_복잡도, 10)         # 최대 10점
정량_점수 = 어휘_점수 + 개념_점수 + 복잡_점수

# 총점
총점 = 질적_점수 + 정량_점수              # 최대 100점

# 등급
A+: 90점 이상
A:  85-89점
B+: 80-84점
B:  75-79점
C+: 70-74점
```

---

### 평가 결과 예시

```json
{
  "학생_ID": "student_001",
  "질문": "춘향전에서 이몽룡은 왜 신분을 숨겼나요?",
  
  "질적_평가": {
    "추론_깊이": {"점수": 4, "피드백": "신분제와 사랑을 논리적으로 연결"},
    "비판적_사고": {"점수": 3, "피드백": "기본적 추론, 대안적 관점 필요"},
    "문학적_이해": {"점수": 4, "피드백": "작품 주제와 배경 이해 양호"},
    "평균": 3.67
  },
  
  "정량_분석": {
    "어휘_다양성": {"점수": 0.68, "등급": "양호"},
    "핵심_개념어": {"사용횟수": 5, "평가": "우수"},
    "문장_복잡도": {"점수": 7.2, "등급": "적절함"},
    "반복_패턴": {"반복률": 0.15, "평가": "양호"},
    "감정_톤": {"점수": 0.6, "톤": "긍정적"},
    "유해표현": {"감지": 0, "경고레벨": "안전"}
  },
  
  "종합_결과": {
    "질적_점수": 51.4,
    "정량_점수": 23.8,
    "총점": 75.2,
    "등급": "B"
  },
  
  "개인_피드백": [
    "✅ 사고의 깊이가 우수합니다.",
    "✅ 다양한 어휘를 사용하고 있습니다.",
    "✅ 핵심 개념을 잘 활용하고 있습니다.",
    "💡 비판적 관점을 더 발전시켜보세요.",
    "💡 다양한 해석 가능성을 탐색해보세요."
  ]
}
```

---

## 📂 코드 구조

```
classical-literature-ai/
│
├── README.md
├── requirements.txt
│
├── configs/
│   ├── training_config.yaml
│   ├── evaluation_config.yaml
│   └── rubric.json
│
├── data/
│   ├── raw/                    # 원본 AI HUB 데이터
│   │   ├── classics/           # 고전문학 600개
│   │   ├── comprehension/      # 지문형 문제 1.26GB
│   │   └── evaluation/         # 논술형/서술형 평가 232MB
│   ├── processed/              # 전처리 데이터
│   │   ├── train.jsonl
│   │   └── valid.jsonl
│   └── templates/
│       └── socratic_patterns.json
│
├── src/
│   ├── data/
│   │   ├── preprocessor.py     # 데이터 전처리
│   │   └── converter.py        # 소크라틱 변환
│   │
│   ├── model/
│   │   ├── trainer.py          # Gemma 파인튜닝
│   │   └── inferencer.py       # 추론 엔진
│   │
│   ├── evaluation/
│   │   ├── gemini_evaluator.py # Gemini 질적 평가
│   │   └── language_analyzer.py # 언어 분석 정량 평가
│   │
│   ├── integration/
│   │   └── pipeline.py         # 통합 파이프라인
│   │
│   └── utils/
│       ├── gcp_utils.py
│       └── harmful_detector.py # 유해표현 AI 연동
│
├── models/
│   ├── gemma_finetuned/        # 학습된 모델
│   └── harmful_expression/     # 유해표현 AI 모델
│
├── outputs/
│   ├── thought_logs/
│   ├── evaluations/
│   └── reports/
│
└── scripts/
    ├── train.py
    ├── evaluate.py
    └── generate_report.py
```

---

## 💻 구현 코드

### 1. 데이터 전처리 (`src/data/preprocessor.py`)

```python
"""
AI HUB 데이터를 소크라틱 대화로 변환
"""

import json
import openai
from typing import List, Dict

class SocraticConverter:
    def __init__(self, api_key: str):
        self.api_key = api_key
        openai.api_key = api_key
    
    def convert_to_socratic(
        self, 
        passage: str, 
        question: str, 
        answer: str
    ) -> Dict:
        """원본 Q&A를 소크라틱 대화로 변환"""
        
        prompt = f"""다음 고전문학 질문을 소크라틱 대화 형식으로 변환하세요.

[원본 지문]
{passage}

[학생 질문]
{question}

[모범 답안]
{answer}

[변환 요구사항]
1. [사고유도] 태그: 학생의 사고를 유도하는 단계적 질문 (2-3개)
2. [사고로그] 태그: 학생이 거칠 사고 과정 예측 및 기록
3. 직접 답을 주지 말고, 스스로 생각하도록 유도

[출력 형식]
[사고유도] (단계적 질문)
[사고로그] (예상 사고 과정, 추론 깊이/맥락 이해도 포함)
"""
        
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "당신은 소크라틱 대화법 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        converted_text = response.choices[0].message.content
        
        return {
            "instruction": "학생의 사고를 유도하며 고전문학을 가르치세요. [사고유도]와 [사고로그] 태그를 사용하세요.",
            "input": f"학생: {question}",
            "output": converted_text,
            "metadata": {
                "source": "AI_HUB",
                "passage": passage,
                "original_answer": answer
            }
        }
    
    def batch_convert(self, data_list: List[Dict], output_path: str):
        """배치 변환"""
        converted_data = []
        
        for i, item in enumerate(data_list):
            try:
                converted = self.convert_to_socratic(
                    passage=item['passage'],
                    question=item['question'],
                    answer=item['answer']
                )
                converted_data.append(converted)
                
                if (i + 1) % 50 == 0:
                    print(f"Progress: {i+1}/{len(data_list)}")
                    
            except Exception as e:
                print(f"Error at {i}: {e}")
                continue
        
        # JSONL 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in converted_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        return converted_data
```

---

### 2. Gemma 파인튜닝 (`src/model/trainer.py`)

```python
"""
Gemma 3 파인튜닝 - LoRA 기반
"""

import torch
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer,
    TrainingArguments,
    Trainer
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset

class GemmaTrainer:
    def __init__(self):
        self.model_name = "google/gemma-3-9b-it"
        
        self.lora_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM"
        )
    
    def load_model(self):
        """4-bit 양자화 모델 로드"""
        
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        tokenizer.pad_token = tokenizer.eos_token
        
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
        
        model = prepare_model_for_kbit_training(model)
        model = get_peft_model(model, self.lora_config)
        
        return model, tokenizer
    
    def prepare_dataset(self, data_path: str, tokenizer):
        """데이터셋 준비"""
        
        dataset = load_dataset('json', data_files=data_path)
        
        def format_and_tokenize(example):
            text = f"""{example['instruction']}

{example['input']}

{example['output']}"""
            
            tokens = tokenizer(
                text,
                truncation=True,
                max_length=1024,
                padding="max_length"
            )
            tokens["labels"] = tokens["input_ids"].copy()
            return tokens
        
        return dataset.map(
            format_and_tokenize,
            remove_columns=dataset["train"].column_names
        )["train"]
    
    def train(
        self, 
        train_dataset,
        output_dir: str = "models/gemma_finetuned",
        num_epochs: int = 3
    ):
        """학습 실행"""
        
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=4,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            fp16=True,
            logging_steps=10,
            save_steps=100,
            warmup_steps=100,
            optim="paged_adamw_8bit"
        )
        
        model, tokenizer = self.load_model()
        
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset
        )
        
        trainer.train()
        trainer.save_model(output_dir)
        tokenizer.save_pretrained(output_dir)
```

---

### 3. 추론 엔진 (`src/model/inferencer.py`)

```python
"""
사고유도 추론 엔진
"""

import re
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

class ThoughtInducer:
    def __init__(self, model_path: str):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.tokenizer = self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """파인튜닝된 모델 로드"""
        
        base_model = AutoModelForCausalLM.from_pretrained(
            "google/gemma-3-9b-it",
            device_map="auto",
            torch_dtype=torch.bfloat16,
            load_in_4bit=True
        )
        
        model = PeftModel.from_pretrained(base_model, model_path)
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model.eval()
        
        return model, tokenizer
    
    def generate_response(
        self, 
        student_input: str,
        max_new_tokens: int = 256
    ) -> dict:
        """사고유도 응답 생성"""
        
        prompt = f"""학생의 사고를 유도하며 고전문학을 가르치세요. [사고유도]와 [사고로그] 태그를 사용하세요.

학생: {student_input}

AI: [사고유도]"""
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=0.7,
                do_sample=True,
                top_p=0.9
            )
        
        full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        ai_response = full_response.split("AI: ")[-1]
        
        induction = self._extract_tag(ai_response, "사고유도")
        log = self._extract_tag(ai_response, "사고로그")
        
        return {
            "induction": induction,
            "log": log,
            "full_response": ai_response
        }
    
    def _extract_tag(self, text: str, tag: str) -> str:
        """태그 내용 추출"""
        pattern = rf"\[{tag}\](.*?)(?=\[|$)"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else ""
```

---

### 4. 언어 분석 모듈 (`src/evaluation/language_analyzer.py`)

```python
"""
개선된 학생 언어 사용 패턴 분석 (정량 평가)
"""

from collections import Counter
from typing import Dict, List, Tuple
from konlpy.tag import Okt
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import numpy as np
import math

class ComprehensiveLanguageAnalyzer:
    """통합 언어 분석 시스템"""
    
    def __init__(self, harmful_model_path: str = None):
        # 기본 분석기
        self.okt = Okt()
        
        # 개선된 분석기들
        self.vocab_analyzer = ImprovedVocabularyAnalyzer()
        self.concept_analyzer = SemanticConceptAnalyzer()
        self.sentiment_analyzer = AdvancedSentimentAnalyzer()
        
        # 유해표현 AI 모델 (AI HUB)
        if harmful_model_path:
            self.harmful_detector = self._load_harmful(harmful_model_path)
    
    def analyze(self, student_text: str) -> Dict:
        """종합 분석"""
        
        morphs = self.okt.morphs(student_text)
        sentences = self._split_sentences(student_text)
        
        return {
            # 개선된 분석
            "어휘_다양성": self.vocab_analyzer.calculate_diversity(student_text),
            "핵심_개념어": self.concept_analyzer.analyze_concepts(student_text),
            "감정_톤": self.sentiment_analyzer.analyze_sentiment(student_text),
            
            # 기존 분석 (유지)
            "문장_복잡도": self._calc_complexity(sentences, morphs),
            "반복_패턴": self._analyze_repetition(morphs),
            "유해표현": self._detect_harmful(student_text),
            
            # 통계
            "통계": {
                "총_단어": len(morphs),
                "고유_단어": len(set(morphs)),
                "문장_수": len(sentences),
                "평균_문장_길이": round(len(morphs) / len(sentences), 1) if sentences else 0
            }
        }
    
    def _calc_complexity(self, sentences: List[str], morphs: List[str]) -> Dict:
        """문장 복잡도 (기존 유지)"""
        if not sentences:
            return {"점수": 0, "등급": "N/A"}
        
        avg_length = len(morphs) / len(sentences)
        avg_clauses = sum(s.count(',') + 1 for s in sentences) / len(sentences)
        score = (avg_length / 10) + (avg_clauses * 2)
        
        if score >= 10:
            grade = "복잡함"
        elif score >= 6:
            grade = "적절함"
        else:
            grade = "단순함"
        
        return {"점수": round(score, 2), "등급": grade}
    
    def _analyze_repetition(self, morphs: List[str]) -> Dict:
        """반복 패턴 (기존 유지)"""
        freq = Counter(morphs)
        excessive = {w: c for w, c in freq.items() if c >= 3 and len(w) > 1}
        repetition_rate = sum(excessive.values()) / len(morphs) if morphs else 0
        
        return {
            "과도한_반복": excessive,
            "반복률": round(repetition_rate, 3),
            "평가": "주의" if repetition_rate > 0.2 else "양호"
        }
    
    def _detect_harmful(self, text: str) -> Dict:
        """유해표현 감지 (AI HUB 모델)"""
        if hasattr(self, 'harmful_detector'):
            result = self.harmful_detector.predict(text)
            detected_count = len(result.get('harmful_expressions', []))
        else:
            detected_count = 0
        
        if detected_count == 0:
            level = "안전"
        elif detected_count <= 2:
            level = "주의"
        else:
            level = "경고"
        
        return {
            "감지_개수": detected_count,
            "경고_레벨": level,
            "조치": "교사 알림 필요" if level == "경고" else "정상"
        }
    
    def _split_sentences(self, text: str) -> List[str]:
        import re
        return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    def _load_harmful(self, path: str):
        """AI HUB 유해표현 AI 모델 로드"""
        # 실제 구현 시 AI HUB 모델 로딩 코드
        pass


# ============================================================
# 개선된 분석기 1: 어휘 다양성
# ============================================================

class ImprovedVocabularyAnalyzer:
    """MTLD 기반 어휘 다양성 분석"""
    
    def __init__(self):
        self.okt = Okt()
    
    def calculate_diversity(self, text: str) -> Dict:
        """
        다층적 어휘 다양성 분석
        - MTLD (텍스트 길이 보정)
        - 품사 다양성
        - 학문적 어휘
        """
        morphs = self.okt.morphs(text)
        
        if not morphs:
            return {"점수": 0, "등급": "N/A", "해석": "텍스트 없음"}
        
        # 1. 기본 TTR
        basic_ttr = len(set(morphs)) / len(morphs)
        
        # 2. MTLD
        mtld_score = self._calculate_mtld(morphs)
        
        # 3. 품사 다양성
        pos_diversity = self._pos_diversity(text)
        
        # 4. 학문적 어휘
        academic_score = self._academic_vocabulary(morphs)
        
        # 최종 점수
        final_score = (
            basic_ttr * 0.3 +
            mtld_score * 0.4 +
            pos_diversity * 0.2 +
            academic_score * 0.1
        )
        
        return {
            "점수": round(final_score, 3),
            "등급": self._grade(final_score),
            "세부": {
                "기본_TTR": round(basic_ttr, 3),
                "MTLD": round(mtld_score, 3),
                "품사_다양성": round(pos_diversity, 3),
                "학문적_어휘": round(academic_score, 3)
            },
            "해석": self._interpret(final_score)
        }
    
    def _calculate_mtld(self, morphs: List[str], threshold: float = 0.72) -> float:
        """MTLD 계산 (텍스트 길이 보정)"""
        if len(morphs) < 10:
            return len(set(morphs)) / len(morphs)
        
        factors = []
        start = 0
        
        for i in range(10, len(morphs)):
            segment = morphs[start:i]
            ttr = len(set(segment)) / len(segment)
            if ttr < threshold:
                factors.append(i - start)
                start = i
        
        if start < len(morphs):
            factors.append(len(morphs) - start)
        
        avg_factor = sum(factors) / len(factors) if factors else 10
        return min(avg_factor / 50, 1.0)
    
    def _pos_diversity(self, text: str) -> float:
        """품사 다양성 (엔트로피)"""
        pos = self.okt.pos(text)
        pos_counts = {"Noun": 0, "Verb": 0, "Adjective": 0, "Adverb": 0}
        
        for word, tag in pos:
            if tag.startswith("N"):
                pos_counts["Noun"] += 1
            elif tag.startswith("V"):
                pos_counts["Verb"] += 1
            elif tag.startswith("Adj"):
                pos_counts["Adjective"] += 1
            elif tag.startswith("Adv"):
                pos_counts["Adverb"] += 1
        
        total = sum(pos_counts.values())
        if total == 0:
            return 0
        
        entropy = 0
        for count in pos_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        
        return entropy / 2  # 정규화
    
    def _academic_vocabulary(self, morphs: List[str]) -> float:
        """학문적 어휘 비율 (3음절 이상, 한자어 등)"""
        academic_count = sum(1 for m in morphs if len(m) >= 3)
        return academic_count / len(morphs) if morphs else 0
    
    def _grade(self, score: float) -> str:
        if score >= 0.75:
            return "우수"
        elif score >= 0.6:
            return "양호"
        elif score >= 0.4:
            return "보통"
        else:
            return "개선필요"
    
    def _interpret(self, score: float) -> str:
        if score >= 0.75:
            return "풍부하고 정교한 어휘 사용. 학문적 표현력 우수."
        elif score >= 0.6:
            return "적절한 어휘 사용. 다양성 양호."
        elif score >= 0.4:
            return "기본적 어휘 사용. 표현력 향상 필요."
        else:
            return "제한적 어휘. 다양한 표현 연습 권장."


# ============================================================
# 개선된 분석기 2: 핵심 개념어 (임베딩 기반)
# ============================================================

class SemanticConceptAnalyzer:
    """의미 유사도 기반 개념어 분석"""
    
    def __init__(self):
        # 한국어 임베딩 모델
        self.model = SentenceTransformer('jhgan/ko-sroberta-multitask')
        self.okt = Okt()
        
        # 핵심 개념 카테고리
        self.concept_categories = {
            "문학적_기법": ["상징", "은유", "복선", "반전", "갈등구조", "인물형상화"],
            "사회문화적_맥락": ["신분제", "시대적배경", "계급갈등", "유교사상", "가부장제"],
            "인간관계_심리": ["사랑", "효", "충", "절개", "욕망", "갈등", "화해", "희생"],
            "주제_메시지": ["주제", "교훈", "풍자", "비판", "가치관", "이상"]
        }
        
        # 카테고리별 임베딩 생성
        self.category_embeddings = {
            cat: self.model.encode(words)
            for cat, words in self.concept_categories.items()
        }
    
    def analyze_concepts(self, student_text: str) -> Dict:
        """의미 기반 개념어 분석"""
        
        # 명사 추출
        nouns = self.okt.nouns(student_text)
        if not nouns:
            return self._empty_result()
        
        # 후보 임베딩
        candidates = list(set(nouns))
        candidate_embeddings = self.model.encode(candidates)
        
        # 카테고리별 매칭
        category_matches = {}
        all_similarities = []
        threshold = 0.6
        
        for cat_name, cat_emb in self.category_embeddings.items():
            similarities = np.dot(candidate_embeddings, cat_emb.T)
            matches = []
            
            for i, cand in enumerate(candidates):
                max_sim = similarities[i].max()
                if max_sim >= threshold:
                    matched = self.concept_categories[cat_name][similarities[i].argmax()]
                    matches.append({
                        "학생표현": cand,
                        "매칭개념": matched,
                        "유사도": round(float(max_sim), 3)
                    })
                    all_similarities.append(max_sim)
            
            if matches:
                category_matches[cat_name] = matches
        
        total_matches = sum(len(m) for m in category_matches.values())
        avg_similarity = np.mean(all_similarities) if all_similarities else 0
        coverage = len(category_matches)
        
        return {
            "카테고리별_매칭": category_matches,
            "총_개념_사용": total_matches,
            "평균_유사도": round(float(avg_similarity), 3),
            "커버리지": coverage,
            "평가": self._evaluate(total_matches, coverage),
            "해석": self._interpret(total_matches, coverage)
        }
    
    def _evaluate(self, total: int, coverage: int) -> str:
        if total >= 5 and coverage >= 3:
            return "우수"
        elif total >= 3 and coverage >= 2:
            return "양호"
        elif total >= 1:
            return "보통"
        else:
            return "부족"
    
    def _interpret(self, total: int, coverage: int) -> str:
        if total >= 5 and coverage >= 3:
            return "다양한 문학적 개념을 적절히 활용"
        elif total >= 3:
            return "핵심 개념을 부분적으로 사용"
        else:
            return "개념적 용어 사용 부족. 문학적 개념 활용 권장"
    
    def _empty_result(self) -> Dict:
        return {
            "카테고리별_매칭": {},
            "총_개념_사용": 0,
            "평균_유사도": 0,
            "커버리지": 0,
            "평가": "부족",
            "해석": "명사 또는 개념어 감지되지 않음"
        }


# ============================================================
# 개선된 분석기 3: 감정 톤 (맥락 고려 AI 모델)
# ============================================================

class AdvancedSentimentAnalyzer:
    """KcELECTRA 기반 감정 분석"""
    
    def __init__(self):
        # 한국어 감정 분석 모델
        try:
            self.sentiment_model = pipeline(
                "sentiment-analysis",
                model="beomi/KcELECTRA-base-v2022"
            )
        except:
            self.sentiment_model = None
        
        # 학습 관련 키워드
        self.learning_positive = ["흥미롭", "재미있", "이해했", "공감", "인상적"]
        self.learning_negative = ["어렵", "이해안", "모르겠", "헷갈", "복잡"]
        self.learning_constructive = ["궁금", "더알고싶", "생각해볼", "탐구"]
    
    def analyze_sentiment(self, text: str) -> Dict:
        """다층적 감정 분석"""
        
        # 1. 전체 감정 (AI 모델)
        if self.sentiment_model:
            try:
                result = self.sentiment_model(text)[0]
                overall = result['label']
                confidence = result['score']
            except:
                overall, confidence = "neutral", 0.5
        else:
            overall, confidence = "neutral", 0.5
        
        # 2. 학습 태도
        learning_tone = self._analyze_learning_tone(text)
        
        # 3. 맥락 감정
        contextual = self._contextual_sentiment(text)
        
        # 최종 통합
        final_tone, final_score = self._integrate_sentiments(
            overall, learning_tone, contextual
        )
        
        return {
            "전체_감정": overall,
            "신뢰도": round(confidence, 3),
            "학습_태도": learning_tone,
            "최종_톤": final_tone,
            "점수": round(final_score, 3),
            "해석": self._interpret_tone(final_tone, learning_tone)
        }
    
    def _analyze_learning_tone(self, text: str) -> str:
        """학습 태도 분석"""
        pos = sum(1 for w in self.learning_positive if w in text)
        neg = sum(1 for w in self.learning_negative if w in text)
        con = sum(1 for w in self.learning_constructive if w in text)
        
        if con >= 2:
            return "탐구적"
        elif pos >= neg + 2:
            return "적극적"
        elif pos > neg:
            return "긍정적"
        elif neg > pos + 2:
            return "소극적"
        else:
            return "중립적"
    
    def _contextual_sentiment(self, text: str) -> Dict:
        """맥락 고려 감정"""
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        if not sentences:
            return {"평균_감정": 0}
        
        if not self.sentiment_model:
            return {"평균_감정": 0}
        
        sent_scores = []
        for sent in sentences:
            try:
                result = self.sentiment_model(sent)[0]
                label = 1 if result['label'].lower() == 'positive' else -1
                sent_scores.append(label * result['score'])
            except:
                sent_scores.append(0)
        
        return {"평균_감정": round(float(np.mean(sent_scores)), 3)}
    
    def _integrate_sentiments(
        self, overall: str, learning: str, contextual: Dict
    ) -> Tuple[str, float]:
        """통합"""
        overall_score = 0.5 if overall.lower() == 'positive' else -0.5
        learning_scores = {
            "탐구적": 0.8, "적극적": 0.6, "긍정적": 0.4,
            "중립적": 0, "소극적": -0.4
        }
        learning_score = learning_scores.get(learning, 0)
        contextual_score = contextual.get("평균_감정", 0)
        
        final_score = (
            overall_score * 0.3 +
            learning_score * 0.5 +
            contextual_score * 0.2
        )
        
        if final_score > 0.4:
            tone = "매우긍정적"
        elif final_score > 0.1:
            tone = "긍정적"
        elif final_score > -0.1:
            tone = "중립적"
        elif final_score > -0.4:
            tone = "부정적"
        else:
            tone = "매우부정적"
        
        return tone, final_score
    
    def _interpret_tone(self, tone: str, learning: str) -> str:
        if "매우긍정" in tone and learning == "탐구적":
            return "학습 흥미와 탐구 의지 높음. 매우 우수한 학습 태도."
        elif "긍정" in tone:
            return "학습에 적극적. 긍정적 태도 유지."
        elif "부정" in tone:
            return "학습 동기 저하. 지원 필요."
        else:
            return "보통 수준의 학습 태도."
```

---

### 5. Gemini 평가 (`src/evaluation/gemini_evaluator.py`)

```python
"""
Gemini 기반 질적 평가
"""

import json
import google.generativeai as genai
from typing import Dict

class GeminiEvaluator:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        self.rubric = {
            "추론_깊이": {
                "5": "다층적 사고, 텍스트 맥락 깊이 이해",
                "4": "논리적 추론, 맥락 연결",
                "3": "기본적 추론",
                "2": "단편적 이해",
                "1": "표면적 반응"
            },
            "비판적_사고": {
                "5": "독자적 해석, 다양한 관점",
                "4": "대안적 해석 시도",
                "3": "직접적 답변",
                "2": "단순 정보 회상",
                "1": "관련 없는 응답"
            },
            "문학적_이해": {
                "5": "시대/문화 맥락 통합",
                "4": "작품 구조 이해",
                "3": "줄거리 이해",
                "2": "부분적 이해",
                "1": "오해"
            }
        }
    
    def evaluate(self, student_input: str, thought_log: str) -> Dict:
        """질적 평가"""
        
        prompt = f"""고전문학 교육 평가 전문가로서 학생의 사고를 평가하세요.

[평가 루브릭]
{json.dumps(self.rubric, ensure_ascii=False, indent=2)}

[학생 질문]
{student_input}

[사고로그]
{thought_log}

[출력 형식 - JSON만 출력]
{{
  "추론_깊이": {{"점수": X, "피드백": "..."}},
  "비판적_사고": {{"점수": X, "피드백": "..."}},
  "문학적_이해": {{"점수": X, "피드백": "..."}},
  "종합_평가": "...",
  "총점": X,
  "평균": X.XX
}}
"""
        
        response = self.model.generate_content(prompt)
        
        try:
            json_text = response.text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0]
            
            evaluation = json.loads(json_text.strip())
            
            if "총점" not in evaluation:
                scores = [
                    evaluation["추론_깊이"]["점수"],
                    evaluation["비판적_사고"]["점수"],
                    evaluation["문학적_이해"]["점수"]
                ]
                evaluation["총점"] = sum(scores)
                evaluation["평균"] = round(sum(scores) / 3, 2)
            
            return evaluation
            
        except:
            return self._fallback_eval()
    
    def _fallback_eval(self) -> Dict:
        return {
            "추론_깊이": {"점수": 3, "피드백": "평가 오류"},
            "비판적_사고": {"점수": 3, "피드백": "평가 오류"},
            "문학적_이해": {"점수": 3, "피드백": "평가 오류"},
            "종합_평가": "시스템 오류",
            "총점": 9,
            "평균": 3.0
        }
```

---

### 6. 통합 파이프라인 (`src/integration/pipeline.py`)

```python
"""
전체 시스템 통합
"""

from src.model.inferencer import ThoughtInducer
from src.evaluation.gemini_evaluator import GeminiEvaluator
from src.evaluation.language_analyzer import LanguageAnalyzer

class IntegratedPipeline:
    def __init__(
        self, 
        model_path: str, 
        gemini_key: str,
        harmful_model_path: str = None
    ):
        self.thought_inducer = ThoughtInducer(model_path)
        self.gemini_eval = GeminiEvaluator(gemini_key)
        self.lang_analyzer = ComprehensiveLanguageAnalyzer(harmful_model_path)
    
    def process(self, student_input: str) -> Dict:
        """전체 파이프라인 실행"""
        
        # 1. 사고유도 대화 생성
        response = self.thought_inducer.generate_response(student_input)
        
        # 2. 질적 평가 (Gemini)
        qualitative = self.gemini_eval.evaluate(
            student_input,
            response['log']
        )
        
        # 3. 정량 분석 (언어)
        quantitative = self.lang_analyzer.analyze(student_input)
        
        # 4. 통합 평가
        integrated = self._integrate_evaluation(qualitative, quantitative)
        
        return {
            "사고유도_응답": response['induction'],
            "사고로그": response['log'],
            "질적_평가": qualitative,
            "정량_분석": quantitative,
            "통합_평가": integrated,
            "개인_피드백": self._generate_feedback(qualitative, quantitative)
        }
    
    def _integrate_evaluation(self, qual: Dict, quan: Dict) -> Dict:
        """질적 + 정량 통합"""
        
        # 질적 70%
        qual_score = qual['평균'] * 0.7 * 20
        
        # 정량 30%
        vocab = quan['어휘_다양성']['점수'] * 10
        concept = min(quan['핵심_개념어']['총_사용'] * 2, 10)
        complexity = min(quan['문장_복잡도']['점수'], 10)
        quan_score = vocab + concept + complexity
        
        total = qual_score + quan_score
        
        if total >= 90:
            grade = "A+"
        elif total >= 85:
            grade = "A"
        elif total >= 80:
            grade = "B+"
        elif total >= 75:
            grade = "B"
        else:
            grade = "C+"
        
        return {
            "질적_점수": round(qual_score, 1),
            "정량_점수": round(quan_score, 1),
            "총점": round(total, 1),
            "등급": grade
        }
    
    def _generate_feedback(self, qual: Dict, quan: Dict) -> List[str]:
        """개인 맞춤 피드백"""
        
        feedback = []
        
        # 강점
        if qual['평균'] >= 4:
            feedback.append("✅ 사고의 깊이가 우수합니다.")
        if quan['어휘_다양성']['점수'] >= 0.6:
            feedback.append("✅ 다양한 어휘를 사용하고 있습니다.")
        if quan['핵심_개념어']['총_사용'] >= 5:
            feedback.append("✅ 핵심 개념을 잘 활용하고 있습니다.")
        
        # 개선점
        if qual['비판적_사고']['점수'] < 3:
            feedback.append("💡 다양한 관점에서 생각해보세요.")
        if quan['핵심_개념어']['총_사용'] < 3:
            feedback.append("💡 핵심 개념어를 더 활용해보세요.")
        if quan['반복_패턴']['반복률'] > 0.2:
            feedback.append("💡 다양한 표현을 시도해보세요.")
        
        # 경고
        if quan['유해표현']['경고_레벨'] != "안전":
            feedback.append("⚠️ 긍정적인 언어 사용을 권장합니다.")
        
        return feedback


# 사용 예시
if __name__ == "__main__":
    pipeline = IntegratedPipeline(
        model_path="models/gemma_finetuned",
        gemini_key="YOUR_KEY",
        harmful_model_path="models/harmful_expression"
    )
    
    result = pipeline.process("춘향전에서 이몽룡은 왜 신분을 숨겼나요?")
    
    print("=" * 60)
    print("사고유도:", result['사고유도_응답'])
    print("=" * 60)
    print("평가 결과:", result['통합_평가'])
    print("=" * 60)
    print("피드백:")
    for fb in result['개인_피드백']:
        print(f"  {fb}")
```

---

## 🎯 핵심 포인트

### 성공을 위한 5가지 원칙

1. **데이터 품질 최우선**
   - 50개 고품질 샘플 수동 작성
   - 자동 변환 후 반드시 검증

2. **모듈형 구조**
   - 각 모듈 독립적으로 테스트
   - 통합 전 개별 검증

3. **평가 시스템 균형**
   - 질적 70% + 정량 30%
   - 유해표현은 별도 처리

4. **확장성 고려**
   - 다른 코퍼스로 확장 가능
   - 평가 루브릭 커스터마이징 가능

5. **실시간 피드백**
   - 즉각적인 평가 및 피드백
   - 교사용 상세 리포트 제공

---

## 🔄 확장성 (교수님 강조 사항)

### 왜 고전문학만 사용하는가?

**✅ 집중을 통한 깊이**
- 129GB 범용 데이터보다 600개 고품질 고전문학 데이터가 더 효과적
- 도메인 특화 → 사고유도 품질 극대화
- 파인튜닝 시간 최적화 (8-12시간)

**✅ 확장성은 구조로 증명**

```python
# 다른 과목 적용 예시

# 1. 수학 문제 풀이
math_data = load_dataset("math_problems")
math_model = GemmaTrainer().train(math_data)
# → 같은 [사고유도] + [사고로그] 시스템 적용

# 2. 과학 실험 설계
science_data = load_dataset("science_experiments")
science_model = GemmaTrainer().train(science_data)
# → 동일한 평가 시스템 (질적 + 정량)

# 3. 역사 사건 분석
history_data = load_dataset("historical_events")
history_model = GemmaTrainer().train(history_data)
# → 루브릭만 조정하면 바로 적용
```

**✅ 실제 확장 시연 계획**
- 발표 시: 수학 문제 1-2개로 시스템 범용성 증명
- 데모: 코퍼스 교체만으로 즉시 작동하는 모습 보여줌

**✅ 129GB 데이터를 안 쓰는 이유**
1. **초점 분산**: 고전문학 특화 모델 vs 범용 모델 → 전자가 우수
2. **비효율**: 학습 시간 폭증 (수일 ~ 수주)
3. **불필요**: 확장성은 아키텍처로 입증 가능

→ **"적은 데이터로 높은 품질"이 핵심 전략**

---

## 📊 예상 성과

### 정량적 지표
- **파인튜닝 성공률**: 95%+
- **평가 정확도**: 85%+
- **응답 시간**: 평균 2-3초
- **사고로그 생성률**: 90%+

### 정성적 성과
- 학생 사고력 향상 도구
- 교사 평가 부담 경감
- 개인 맞춤형 학습 가능
- 다과목 확장 가능성 입증

---

**최종 정리: 이 문서로 바로 개발 시작 가능! 🚀**
