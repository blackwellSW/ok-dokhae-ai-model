# Vertex AI Integration Guide

## 개요

OK독해 백엔드는 **Fine-tuned Gemma 3 (LoRA) 모델**을 Vertex AI Endpoint를 통해 사용합니다.
이 문서는 Vertex AI 연동 관련 수정 사항을 설명합니다.

---

## 아키텍처

```
[Flutter App] → [Cloud Run Backend] → [Vertex AI Endpoint]
                                           ↓
                                    [Fine-tuned Gemma 3]
                                    (vLLM 서빙)
```

---

## 주요 수정 사항

### 1. Cloud Run 리전 변경

**변경 전:** `asia-northeast1`
**변경 후:** `us-central1`

Vertex AI Endpoint가 `us-central1`에 있으므로, Cloud Run도 같은 리전으로 배포하여 네트워크 지연 최소화.

**파일:** `backend/cloudbuild.yaml`
```yaml
- '--region'
- 'us-central1'
```

### 2. Vertex AI SDK 사용

HTTP 직접 호출 대신 `google-cloud-aiplatform` SDK 사용.

**이유:**
- Cloud Run → Vertex AI 간 HTTP 직접 호출 시 타임아웃 발생
- SDK는 Google 내부 네트워크 최적화 적용

**파일:** `backend/app/services/thought_inducer.py`
```python
from google.cloud import aiplatform

# SDK 초기화 (한 번만)
aiplatform.init(project="knu-team-03", location="us-central1")

# Endpoint 객체 생성 및 rawPredict 호출
endpoint = aiplatform.Endpoint("2283851677146546176")
response = endpoint.raw_predict(
    body=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"}
)
```

### 3. vLLM 메시지 형식 준수

vLLM/Gemma 3 모델 요구사항:

| 규칙 | 설명 |
|------|------|
| `system` role 금지 | 첫 `user` 메시지에 시스템 프롬프트 포함 |
| user/assistant 교차 | 반드시 핑퐁 형식 유지 |
| 마지막은 `user` | 마지막 메시지는 항상 user role |

**올바른 예시:**
```json
{
  "messages": [
    {"role": "user", "content": "[시스템 프롬프트]\n\n학생 질문: 춘향전에서..."},
    {"role": "assistant", "content": "좋은 질문입니다. 춘향이의 감정을..."},
    {"role": "user", "content": "그렇다면 이몽룡은..."}
  ]
}
```

### 4. 환경 변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `USE_VERTEX_AI` | Vertex AI 사용 여부 | `true` |
| `VERTEX_AI_MODEL` | 모델 이름 | `classical-lit` |
| `FIREBASE_PROJECT_ID` | GCP 프로젝트 ID | `knu-team-03` |

---

## API 엔드포인트

### 사고유도 대화 생성

```
POST /classical-literature/dialogue
```

**Request:**
```json
{
  "student_input": "춘향전에서 이몽룡이 과거를 보러 떠날 때 춘향이는 왜 울었을까요?",
  "work_title": "춘향전"
}
```

**Response:**
```json
{
  "induction": "[사고유도 응답]",
  "log": "[사고로그]",
  "full_response": "[전체 응답]"
}
```

---

## 응답 시간

| 환경 | 응답 시간 |
|------|----------|
| 직접 curl (Cloud Shell) | ~3초 |
| SDK (Cloud Run) | ~12-30초 |

**참고:** SDK 오버헤드로 인해 응답 시간이 증가하지만, 안정적인 연결을 보장합니다.

---

## Fallback 동작

1. **Vertex AI 호출 시도**
2. **실패 시 Gemini API fallback** (현재 API 키 만료 상태)
3. **모두 실패 시 기본 오류 응답**

---

## 트러블슈팅

### 1. 503 Service Unavailable

Vertex AI Endpoint 과부하. 잠시 후 재시도.

### 2. ReadTimeout

Cloud Run → Vertex AI 네트워크 이슈.
- SDK 사용 확인
- 같은 리전 배포 확인

### 3. "system" role 오류

vLLM이 `system` role을 거부함.
→ 첫 `user` 메시지에 시스템 프롬프트 포함하도록 수정.

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `backend/app/services/thought_inducer.py` | Vertex AI 호출 로직 |
| `backend/app/core/config.py` | 환경 설정 |
| `backend/cloudbuild.yaml` | Cloud Build/Run 배포 설정 |
| `backend/requirements.txt` | 의존성 (`google-cloud-aiplatform`) |

---

## 담당자 참고

- **프론트엔드:** API 응답 시간이 12-30초 걸릴 수 있으므로 로딩 UI 필요
- **백엔드:** Gemini API 키 갱신 필요 (현재 만료됨)
- **ML팀:** Vertex AI Endpoint 상태 모니터링 필요

---

*최종 업데이트: 2026-02-09*
