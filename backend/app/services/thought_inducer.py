"""
사고유도 대화 생성 시스템
역할: 학생의 질문에 대해 소크라틱 대화법으로 사고를 유도하고 사고 과정을 로깅

Vertex AI Integration:
- 프로덕션: Fine-tuned Gemma 3 (LoRA) 모델 사용
- Fallback: Gemini API 사용 (개발/테스트)
"""

import re
import asyncio
import json
from typing import Dict, Optional, List
import google.generativeai as genai
from google.cloud import aiplatform

from app.core.config import get_settings
from app.services.cloud_logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class ThoughtInducer:
    """
    소크라틱 대화법 기반 사고 유도 엔진

    프로덕션: Vertex AI Endpoint (Fine-tuned Gemma 3 LoRA)
    개발/Fallback: Gemini API
    """

    # SDK 초기화 상태 (초기화는 한 번만)
    _vertex_sdk_initialized = False

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._use_vertex = settings.USE_VERTEX_AI
        self._vertex_endpoint = settings.VERTEX_AI_ENDPOINT
        self._vertex_model = settings.VERTEX_AI_MODEL

        # Gemini fallback 설정
        if self._api_key:
            genai.configure(api_key=self._api_key)
            self._gemini_model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self._gemini_model = None

        # Vertex AI SDK 초기화 (한 번만)
        if self._use_vertex:
            self._init_vertex_sdk()

        logger.info(f"ThoughtInducer 초기화: use_vertex={self._use_vertex}")

    def _init_vertex_sdk(self):
        """Vertex AI SDK 초기화 (한 번만)"""
        if not ThoughtInducer._vertex_sdk_initialized:
            aiplatform.init(
                project=settings.FIREBASE_PROJECT_ID,
                location="us-central1"
            )
            ThoughtInducer._vertex_sdk_initialized = True
            logger.info("Vertex AI SDK 초기화 완료")

    def _call_vertex_ai_sync(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> Dict:
        """
        Vertex AI 엔드포인트 동기 호출 (SDK 사용)
        """
        self._init_vertex_sdk()

        # 매 호출마다 새 Endpoint 객체 생성
        endpoint = aiplatform.Endpoint("2283851677146546176")

        payload = {
            "model": self._vertex_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9
        }

        logger.info(f"Vertex AI SDK 호출 시작")

        try:
            # rawPredict 사용
            response = endpoint.raw_predict(
                body=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"}
            )

            # 다양한 응답 형식 처리
            if isinstance(response, bytes):
                result = json.loads(response.decode('utf-8'))
            elif hasattr(response, 'data') and isinstance(response.data, bytes):
                result = json.loads(response.data.decode('utf-8'))
            elif hasattr(response, 'text'):
                result = json.loads(response.text)
            elif hasattr(response, '_pb'):
                result = json.loads(response._pb.data.decode('utf-8'))
            else:
                logger.error(f"알 수 없는 응답 형식: {type(response)}")
                raise ValueError(f"알 수 없는 응답 형식: {type(response)}")

            # 에러 응답 체크
            if isinstance(result, dict) and "error" in result:
                error_info = result["error"]
                logger.error(f"Vertex AI 에러 응답: {error_info}")
                raise ValueError(f"Vertex AI error: {error_info}")

            logger.info(f"Vertex AI SDK 응답 수신 성공")
            return result

        except Exception as e:
            logger.error(f"Vertex AI SDK 오류: {type(e).__name__}: {e}")
            raise

    async def _call_vertex_ai(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> Dict:
        """
        Vertex AI 엔드포인트 비동기 호출 (스레드풀 사용)
        """
        return await asyncio.to_thread(
            self._call_vertex_ai_sync,
            messages,
            max_tokens,
            temperature
        )

    def _build_system_prompt(self, work_title: str, context: str) -> str:
        """시스템 프롬프트 생성"""
        context_info = work_title or context or "고전문학"

        return f"""당신은 {context_info} 전문가이며, 소크라테스식 문답법을 사용하는 AI 교사입니다.

학생의 질문에 직접 답을 주지 말고, 학생 스스로 생각하도록 유도하는 질문으로 답변하세요.

[필수 응답 형식]
[사고유도] <1~2문장 힌트>. <질문 1개>?
[사고로그] <AI의 교육적 의도와 사고 과정 기록>

[중요 규칙]
1. 질문은 반드시 1개만 (여러 개 금지)
2. 자연스러운 한국어 대화 톤
3. "model" 단어 사용 금지"""

    def _build_vllm_messages(
        self,
        system_prompt: str,
        conversation_history: Optional[List[Dict]],
        current_input: str
    ) -> List[Dict[str, str]]:
        """
        vLLM 호환 메시지 배열 생성

        vLLM/Gemma 3 요구사항:
        - system role 사용 금지 (첫 user 메시지에 포함)
        - user/assistant 반드시 교차 (핑퐁)
        - 마지막은 user로 끝나야 함

        Args:
            system_prompt: 시스템 지침 (첫 user 메시지에 포함됨)
            conversation_history: 이전 대화 [{"q": "질문", "a": "답변"}, ...]
                                  또는 [{"role": "user/assistant", "content": "..."}]
            current_input: 현재 학생 입력

        Returns:
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
        """
        messages = []

        if not conversation_history:
            # 첫 대화: 시스템 프롬프트 + 현재 질문을 하나의 user 메시지로
            full_content = f"{system_prompt}\n\n학생 질문: {current_input}"
            messages.append({"role": "user", "content": full_content})
        else:
            # 히스토리가 있는 경우: user/assistant 교차 보장
            for i, entry in enumerate(conversation_history):
                # 두 가지 포맷 지원: {"q", "a"} 또는 {"role", "content"}
                if "q" in entry and "a" in entry:
                    # {"q": "질문", "a": "답변"} 포맷
                    if i == 0:
                        # 첫 번째 user 메시지에 시스템 프롬프트 포함
                        user_content = f"{system_prompt}\n\n학생 질문: {entry['q']}"
                    else:
                        user_content = entry['q']

                    messages.append({"role": "user", "content": user_content})
                    messages.append({"role": "assistant", "content": entry['a']})

                elif "role" in entry and "content" in entry:
                    # {"role": "user/assistant", "content": "..."} 포맷
                    if i == 0 and entry["role"] == "user":
                        # 첫 번째 user 메시지에 시스템 프롬프트 포함
                        entry_copy = entry.copy()
                        entry_copy["content"] = f"{system_prompt}\n\n{entry['content']}"
                        messages.append(entry_copy)
                    else:
                        messages.append(entry)

            # 마지막으로 현재 질문 추가
            messages.append({"role": "user", "content": current_input})

        # 검증: user/assistant 교차 확인
        messages = self._validate_message_alternation(messages)

        return messages

    def _validate_message_alternation(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        메시지 배열이 user/assistant 교차 규칙을 따르는지 검증 및 수정

        규칙:
        - 첫 메시지는 user
        - user 다음은 assistant (마지막 제외)
        - assistant 다음은 user
        - 마지막은 user
        """
        if not messages:
            return messages

        validated = []
        expected_role = "user"

        for i, msg in enumerate(messages):
            is_last = (i == len(messages) - 1)

            if msg["role"] == expected_role:
                validated.append(msg)
                # 다음 예상 역할 설정 (마지막이 아닌 경우만)
                if not is_last:
                    expected_role = "assistant" if expected_role == "user" else "user"
            elif msg["role"] == "user" and expected_role == "assistant":
                # user가 연속으로 올 때: 이전 user 내용에 합치기
                if validated and validated[-1]["role"] == "user":
                    validated[-1]["content"] += f"\n\n{msg['content']}"
                else:
                    validated.append(msg)
            # assistant가 연속으로 오면 건너뜀 (비정상 케이스)

        # 마지막이 user인지 확인
        if validated and validated[-1]["role"] != "user":
            logger.warning("메시지가 user로 끝나지 않음 - 비정상 상태")

        return validated

    async def generate_response(
        self,
        student_input: str,
        work_title: str = "",
        context: str = "",
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        학생 질문에 대한 사고유도 응답 생성

        Args:
            student_input: 학생 질문/답변
            work_title: 고전문학 작품명
            context: 추가 맥락 정보
            conversation_history: 이전 대화 히스토리 (Vertex AI용)

        Returns:
            {
                "induction": 사고유도 응답,
                "log": 사고로그,
                "full_response": 전체 응답,
                "model_used": 사용된 모델
            }
        """

        # Vertex AI 사용 시도
        if self._use_vertex:
            try:
                result = await self._generate_with_vertex(
                    student_input, work_title, context, conversation_history
                )
                result["model_used"] = f"vertex-ai/{self._vertex_model}"
                logger.info(f"Vertex AI 응답 생성 성공")
                return result
            except Exception as e:
                logger.warning(f"Vertex AI 호출 실패, Gemini fallback: {e}")

        # Gemini fallback
        if self._gemini_model:
            try:
                result = await self._generate_with_gemini(
                    student_input, work_title, context
                )
                result["model_used"] = "gemini-pro"
                logger.info(f"Gemini 응답 생성 성공")
                return result
            except Exception as e:
                logger.error(f"Gemini 호출 실패: {e}")

        return self._fallback_response(student_input)

    async def _generate_with_vertex(
        self,
        student_input: str,
        work_title: str,
        context: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict:
        """Vertex AI로 응답 생성"""
        system_prompt = self._build_system_prompt(work_title, context)

        # vLLM 호환 메시지 구성 (user/assistant 교차 보장)
        messages = self._build_vllm_messages(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            current_input=student_input
        )

        # 디버그 로그
        logger.info(f"Vertex AI 요청 - 메시지 수: {len(messages)}, 마지막 role: {messages[-1]['role'] if messages else 'none'}")

        # API 호출
        response = await self._call_vertex_ai(messages)

        # 응답 구조 로깅
        logger.info(f"Vertex AI 응답 키: {response.keys() if isinstance(response, dict) else type(response)}")

        # 응답 파싱 (OpenAI 호환 형식)
        if "choices" in response:
            content = response["choices"][0]["message"]["content"]
        elif "predictions" in response:
            # Vertex AI 기본 형식
            content = response["predictions"][0]
        else:
            logger.error(f"알 수 없는 응답 형식: {response}")
            raise ValueError(f"알 수 없는 응답 형식: {list(response.keys())}")

        return self._parse_response(content)

    async def _generate_with_gemini(
        self,
        student_input: str,
        work_title: str,
        context: str
    ) -> Dict:
        """Gemini API로 응답 생성 (개발/Fallback)"""
        prompt = f"""당신은 고전문학 교육 전문가입니다. 학생의 사고를 유도하며 가르치세요.

**중요 규칙**:
1. [사고유도] 태그: 직접적인 답을 주지 말고, 단계적 질문으로 학생 스스로 생각하도록 유도
2. [사고로그] 태그: 학생이 이 답변을 받고 거칠 것으로 예상되는 사고 과정을 기록
3. 소크라틱 대화법 활용: 질문을 통해 깨닫게 만들기

{f"[작품: {work_title}]" if work_title else ""}
{f"[맥락: {context}]" if context else ""}

[학생 질문]
{student_input}

[응답 형식]
[사고유도] (2-3개의 단계적 질문으로 사고 유도. 직접 답을 주지 마세요)

[사고로그] (학생이 예상되는 사고 과정, 추론 깊이, 맥락 이해도 등을 간단히 기록)
"""

        response = self._gemini_model.generate_content(prompt)
        return self._parse_response(response.text.strip())

    def _parse_response(self, full_response: str) -> Dict:
        """응답 파싱: [사고유도]와 [사고로그] 분리"""
        induction = self._extract_tag(full_response, "사고유도")
        log = self._extract_tag(full_response, "사고로그")

        # 태그가 없는 경우 전체를 사고유도로 간주
        if not induction and not log:
            induction = full_response
            log = "사고 과정 기록 없음"

        return {
            "induction": induction,
            "log": log,
            "full_response": full_response
        }

    def _extract_tag(self, text: str, tag: str) -> str:
        """태그 내용 추출"""
        pattern = rf"\[{tag}\](.*?)(?=\[|$)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            content = match.group(1).strip()
            return content
        return ""

    def _fallback_response(self, student_input: str) -> Dict:
        """응답 생성 실패 시 기본 응답"""
        logger.error(f"모든 모델 호출 실패: {student_input[:50]}...")
        return {
            "induction": "죄송합니다. 응답 생성에 문제가 발생했습니다. 다시 시도해주세요.",
            "log": "시스템 오류로 사고 과정 기록 불가",
            "full_response": "시스템 오류",
            "model_used": "fallback"
        }

    async def generate_feedback(
        self,
        student_answer: str,
        correct_answer: str,
        work_title: str = ""
    ) -> str:
        """
        학생 답변에 대한 피드백 생성

        Args:
            student_answer: 학생 답변
            correct_answer: 모범 답안
            work_title: 작품명

        Returns:
            피드백 텍스트
        """

        prompt = f"""고전문학 교육 전문가로서 학생 답변에 피드백을 주세요.

{f"[작품: {work_title}]" if work_title else ""}

[학생 답변]
{student_answer}

[모범 답안]
{correct_answer}

학생 답변의 강점과 보완점을 간단명료하게 피드백해주세요.
직접적으로 답을 주기보다는, 어떤 부분을 더 생각해볼지 제안하세요.
"""

        # Vertex AI 시도
        if self._use_vertex:
            try:
                response = await self._call_vertex_ai(
                    [{"role": "user", "content": prompt}],
                    max_tokens=256
                )
                content = response["choices"][0]["message"]["content"]
                logger.info("Vertex AI 피드백 생성 성공")
                return content
            except Exception as e:
                logger.warning(f"Vertex AI 피드백 실패: {e}")

        # Gemini fallback
        if self._gemini_model:
            try:
                response = self._gemini_model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                logger.error(f"Gemini 피드백 실패: {e}")

        return "피드백 생성에 문제가 발생했습니다."
