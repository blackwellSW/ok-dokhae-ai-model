# 고전문학 사고유도 AI 프로젝트

> 고전문학 학습용 사고유도 대화 AI + 자동 평가 시스템

## 프로젝트 개요

- **사고유도 AI**: Gemma 3 파인튜닝 기반 대화형 AI
- **사고로그 생성**: 학생의 사고 과정 자동 기록
- **자동 평가**: Gemini 질적 평가 + 언어분석 정량 평가

## 프로젝트 구조

```
classical-literature-ai/
├── configs/                    # 설정 파일
│   ├── training_config.yaml    # 학습 설정
│   ├── evaluation_config.yaml  # 평가 설정
│   └── rubric.json             # 평가 루브릭
│
├── data/                       # 데이터
│   ├── raw/                    # TODO: AI HUB 원본 데이터
│   ├── processed/              # 전처리된 데이터
│   └── templates/              # 소크라틱 대화 템플릿
│
├── src/                        # 소스 코드
│   ├── data/                   # 데이터 처리
│   │   ├── preprocessor.py     # 전처리
│   │   └── converter.py        # 소크라틱 변환
│   │
│   ├── model/                  # 모델
│   │   ├── trainer.py          # Gemma 파인튜닝
│   │   └── inferencer.py       # 추론 엔진
│   │
│   ├── evaluation/             # 평가
│   │   ├── gemini_evaluator.py # 질적 평가
│   │   └── language_analyzer.py # 정량 평가
│   │
│   ├── integration/            # 통합
│   │   └── pipeline.py         # 전체 파이프라인
│   │
│   └── utils/                  # 유틸리티
│       ├── gcp_utils.py        # GCP 연동
│       └── harmful_detector.py # 유해표현 감지
│
├── scripts/                    # 실행 스크립트
│   ├── preprocess.py           # 전처리 실행
│   ├── train.py                # 학습 실행
│   ├── evaluate.py             # 평가 실행
│   └── generate_report.py      # 리포트 생성
│
├── models/                     # TODO: 학습된 모델
├── outputs/                    # 출력 결과
└── requirements.txt            # 패키지 의존성
```

## 설치

```bash
# 패키지 설치
pip install -r requirements.txt

# KoNLPy 설치 (Java 필요)
# macOS: brew install openjdk
# Ubuntu: sudo apt install default-jdk
```

## 사용법

### 1. 데이터 준비

```bash
# 1. AI HUB에서 데이터 다운로드
#    - 고전문학 데이터
#    - 지문형 문제 데이터
#    - 유해표현 검출 AI 모델

# 2. configs/training_config.yaml에 경로 설정
#    data:
#      raw_classics_path: "data/raw/classics"
#      ...

# 3. 전처리 실행
python scripts/preprocess.py

# 4. (선택) 수동 작성 템플릿 생성
python scripts/preprocess.py --create-templates
```

### 2. 모델 학습

```bash
# 설정 파일 사용
python scripts/train.py --config configs/training_config.yaml

# 또는 커맨드라인 인자
python scripts/train.py \
    --train-data data/processed/train.jsonl \
    --epochs 3 \
    --batch-size 4
```

### 3. 평가 실행

```bash
# 대화형 모드
python scripts/evaluate.py --interactive

# 단일 입력
python scripts/evaluate.py \
    --input "춘향전에서 이몽룡이 신분을 숨긴 이유는?" \
    --context "춘향전"

# 배치 처리
python scripts/evaluate.py \
    --input-file inputs.jsonl \
    --output results.jsonl
```

### 4. 리포트 생성

```bash
python scripts/generate_report.py \
    --input outputs/evaluations/evaluation_xxx.json \
    --type both \
    --format markdown
```

## TODO 체크리스트

### 데이터 설정 필요
- [ ] `configs/training_config.yaml` - 데이터 경로 설정
- [ ] `configs/evaluation_config.yaml` - Gemini API 키 설정
- [ ] `src/data/preprocessor.py` - AI HUB 데이터 로딩 로직 구현

### 모델 경로 설정 필요
- [ ] 파인튜닝된 Gemma 모델 경로
- [ ] AI HUB 유해표현 모델 경로

### 환경 변수 (선택)
```bash
export GEMINI_API_KEY="your-api-key"
export OPENAI_API_KEY="your-api-key"  # 소크라틱 변환용
export GCP_PROJECT_ID="your-project"
export GCP_BUCKET_NAME="your-bucket"
```

## 시스템 요구사항

- Python 3.9+
- CUDA GPU (학습 시 A100/L4 권장)
- RAM 32GB+ (추론 시 16GB)
- Java (KoNLPy용)

## 라이선스

MIT License
