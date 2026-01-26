# OK-DOK-HAE API 문서

이 문서는 Cloud Run에 배포된 **OK-DOK-HAE 백엔드 API**의 사용법을 설명합니다.

- **Base URL**: `https://ok-dokhae-backend-42wbg5perq-an.a.run.app`
- **Swagger UI**: [https://ok-dokhae-backend-42wbg5perq-an.a.run.app/docs](https://ok-dokhae-backend-42wbg5perq-an.a.run.app/docs)

---

## 1. 서버 상태 확인 (Health Check)
서버가 정상적으로 동작 중인지, AI 모델이 로드되었는지 확인합니다.

- **URL**: `/`
- **Method**: `GET`
- **응답 예시**:
  ```json
  {
    "status": "ready",      // "loading"이면 아직 모델 로딩 중
    "message": "OK-DOK-HAE API is online"
  }
  ```

---

## 2. 비문학 지문 분석 (Analyze Text)
텍스트를 입력받아 구조화된 분석 결과(노드)를 반환합니다.

- **URL**: `/analyze`
- **Method**: `POST`
- **Content-Type**: `application/json`

### 요청 본문 (Request Body)
| 필드명 | 타입 | 필수 여부 | 설명 | 예시 |
| :--- | :--- | :--- | :--- | :--- |
| `user_id` | string | 필수 | 사용자 ID (로그용) | `"yongbin_choi"` |
| `session_id` | string | 필수 | 세션 식별자 | `"sess_001"` |
| `text` | string | 필수 | 분석할 비문학 지문 내용 | `"인공지능은..."` |

**요청 예시**:
```json
{
  "user_id": "test_user",
  "session_id": "session_123",
  "text": "DNA 컴퓨팅은 DNA 분자의 결합 반응을 이용하여 연산을 수행하는 새로운 패러다임이다."
}
```

### 응답 (Response)
- **성공 (200 OK)**
  ```json
  {
    "nodes": [ ...분석된 노드 데이터... ]
  }
  ```
- **실패 (503 Service Unavailable)**
  - AI 엔진이 아직 로딩 중일 때 발생합니다. 1~2분 후 다시 시도하세요.
  ```json
  {
    "detail": "AI 엔진이 로딩 중입니다. 1~2분 후 다시 시도해 주세요."
  }
  ```

---

## 3. 사용 예시 코드 (Python)

```python
import requests
import json

API_URL = "https://ok-dokhae-backend-42wbg5perq-an.a.run.app/analyze"

payload = {
    "user_id": "demo_user",
    "session_id": "demo_session_1",
    "text": "여기에 분석할 텍스트를 입력하세요."
}

try:
    response = requests.post(API_URL, json=payload)
    response.raise_for_status() # 오류 발생 시 예외 처리
    
    result = response.json()
    print("분석 결과:", result)
    
except requests.exceptions.HTTPError as err:
    print(f"HTTP 오류 발생: {err}")
    print(response.text)
```
