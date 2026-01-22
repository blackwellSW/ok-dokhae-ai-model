# DM 데이터 스키마 (DM Dataset Schema)

**범위**: `data/processed/train_labeled_v1.jsonl` 파일만 사용합니다. 다른 데이터셋은 무시합니다.

## Raw Record 스키마 (train_labeled_v1.jsonl)
각 줄(line)은 다음과 같은 필드를 가진 JSON 객체입니다:

- `passage_id`: string
- `source`: object (dataset, subject, topic, file, passage_range)
- `text`: string (본문, passage)
- `claim`: string (주장)
- `evidence`: list[string] (근거 목록)
- `reasoning`: string (이유/추론 과정)
- `label`: string (`GOOD`, `WEAK_LINK`, `OFF_PATH`, `INSUFFICIENT_REASONING` 중 하나)
- `diag`: string (검증기의 진단 태그)
- `scores`: object (qa_score, link_score, length_chars, length_tokens, evidence_count)
- `debug`: object
- `meta`: object (gen_mode, created_at)

## 학습용 파생 데이터 (Derived Training Sample)
Raw 필드로부터 `input`을 다음과 같이 조합하여 생성합니다:

**질문 템플릿:**
```
Claim: {claim}
Evidence: {evidence_joined}
Explain how the evidence supports the claim.
```

**입력(Input) 레이아웃:**
```
[PASSAGE]
{text}            (옵션)
[QUESTION]
{question}
[REASONING]
{reasoning}
```

## 데이터 분할 (Splits)
기본 분할: train/dev/test = 0.8/0.1/0.1 (라벨 비율 유지(stratified), seed=42)

## 라벨 의미 (Label Semantics)
- **GOOD**: 추론이 주제에 맞고, 근거를 사용하며, 주장을 잘 뒷받침함.
- **WEAK_LINK**: 추론이 주제에는 맞으나, 연결고리나 근거가 약함.
- **OFF_PATH**: 추론이 질문에 대한 답이 아님(동문서답).
- **INSUFFICIENT_REASONING**: 추론이 너무 짧거나 판단하기에 내용이 빈약함.

## 참고 사항 (Notes)
- 라벨은 검증기(`Evaluator.validate_reasoning`)를 통해 자동 생성된(silver) 라벨입니다.
- 클래스 불균형 문제로 인해 모델 평가 시 **Macro-F1** 점수를 우선합니다.

---

## 모델 서빙 인터페이스 스펙 (백엔드 연동용)
이 섹션은 백엔드 담당(`dragon콩`)이 학습된 모델과 어떻게 연동해야 하는지 정의합니다.

### 1. 엔드포인트 (Endpoint)
- **경로**: `/predict` (권장) 또는 명시적인 Python 함수 호출
- **입력 형식**: JSON

### 2. 요청 (Request / Input)
백엔드는 다음 필드를 포함한 JSON 객체를 보내야 합니다:

```json
{
  "claim": "민초는 맛있다.",
  "evidence": ["판매량이 전년 대비 3배 증가했다.", "SNS 언급량이 많다."],
  "reasoning": "판매량이 늘어났다는 것은 대중적인 선호도가 높다는 뜻이므로 맛있다.",
  "text": "..." // (선택사항) 원본 본문 텍스트
}
```

> **참고**: `claim`, `evidence` (리스트 또는 문자열), `reasoning`이 모두 제공될 때 모델이 가장 잘 작동합니다.

### 3. 응답 (Response / Output)
모델은 판정 라벨(`label`)과 신뢰도 점수(`confidence`)를 반환합니다.

```json
{
  "label": "GOOD",  // 가능한 값: GOOD, WEAK_LINK, OFF_PATH, INSUFFICIENT_REASONING
  "confidence": {
    "GOOD": 0.85,
    "WEAK_LINK": 0.10,
    "OFF_PATH": 0.03,
    "INSUFFICIENT_REASONING": 0.02
  },
  "model_version": "dm_logreg_v1"
}
```
