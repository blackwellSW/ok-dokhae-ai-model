"""
사고유도 대화 생성 시스템
역할: 학생의 질문에 대해 소크라틱 대화법으로 사고를 유도하고 사고 과정을 로깅
"""

import re
import google.generativeai as genai
from typing import Dict, Optional
from app.core.config import get_settings

settings = get_settings()


class ThoughtInducer:
    """
    소크라틱 대화법 기반 사고 유도 엔진
    
    실제 프로덕션에서는 Gemma 3 파인튜닝 모델을 사용하지만,
    개발 단계에서는 Gemini를 프록시로 사용
    """
    
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or settings.GEMINI_API_KEY
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def generate_response(
        self, 
        student_input: str,
        work_title: str = "",
        context: str = ""
    ) -> Dict:
        """
        학생 질문에 대한 사고유도 응답 생성
        
        Args:
            student_input: 학생 질문/답변
            work_title: 고전문학 작품명
            context: 추가 맥락 정보
        
        Returns:
            {
                "induction": 사고유도 응답,
                "log": 사고로그,
                "full_response": 전체 응답
            }
        """
        
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
        
        try:
            response = self.model.generate_content(prompt)
            full_response = response.text.strip()
            
            # 태그별 내용 추출
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
            
        except Exception as e:
            print(f"사고유도 생성 오류: {e}")
            return self._fallback_response(student_input)
    
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
        return {
            "induction": "죄송합니다. 응답 생성에 문제가 발생했습니다. 다시 시도해주세요.",
            "log": "시스템 오류로 사고 과정 기록 불가",
            "full_response": "시스템 오류"
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
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"피드백 생성 오류: {e}")
            return "피드백 생성에 문제가 발생했습니다."
