"""
사고유도 대화 생성 시스템
역할: 학생의 질문에 대해 소크라틱 대화법으로 사고를 유도하고 사고 과정을 로깅

Vertex AI Integration:
- 프로덕션: Fine-tuned Gemma 3 (LoRA) 모델 사용
- Fallback: Gemini API 사용 (개발/테스트)
"""

import re
import httpx
from typing import Dict, Optional, List
import google.generativeai as genai
from google.auth import default
from google.auth.transport.requests import Request

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

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._use_vertex = settings.USE_VERTEX_AI
        self._vertex_endpoint = settings.VERTEX_AI_ENDPOINT
        self._vertex_model = settings.VERTEX_AI_MODEL
        self._credentials = None

        # Gemini fallback 설정
        if self._api_key:
            genai.configure(api_key=self._api_key)
            self._gemini_model = genai.GenerativeModel('gemini-pro')
        else:
            self._gemini_model = None

        logger.info(f"ThoughtInducer 초기화: use_vertex={self._use_vertex}")

    def _get_gcp_token(self) -> str:
        """GCP 액세스 토큰 획득"""
        try:
            if self._credentials is None:
                self._credentials, _ = default()
            self._credentials.refresh(Request())
            return self._credentials.token
        except Exception as e:
            logger.error(f"GCP 토큰 획득 실패: {e}")
            raise

    async def _call_vertex_ai(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> Dict:
        """
        Vertex AI 엔드포인트 호출

        Args:
            messages: 대화 히스토리 [{"role": "user", "content": "..."}]
            max_tokens: 최대 생성 토큰
            temperature: 생성 다양성

        Returns:
            API 응답 딕셔너리
        """
        token = self._get_gcp_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # vLLM 엔드포인트는 model 필드 불필요 (이미 배포된 모델 사용)
        payload = {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                self._vertex_endpoint,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()

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

        # 메시지 구성
        if conversation_history:
            # 대화 히스토리가 있는 경우
            messages = conversation_history.copy()
            messages.append({"role": "user", "content": student_input})
        else:
            # 첫 대화
            full_prompt = f"{system_prompt}\n\n학생 질문: {student_input}\n\nAI 교사 응답:"
            messages = [{"role": "user", "content": full_prompt}]

        # API 호출
        response = await self._call_vertex_ai(messages)

        # 응답 파싱
        content = response["choices"][0]["message"]["content"]

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
