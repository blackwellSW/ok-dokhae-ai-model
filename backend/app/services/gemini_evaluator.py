"""
Gemini 기반 질적 평가 시스템
역할: 추론 깊이, 비판적 사고, 문학적 이해를 3차원 루브릭으로 평가
"""

import json
import google.generativeai as genai
from typing import Dict, Optional
from app.core.config import get_settings

settings = get_settings()


class GeminiEvaluator:
    """Gemini Pro를 활용한 질적 평가 시스템"""
    
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or settings.GEMINI_API_KEY
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # 3차원 평가 루브릭
        self.rubric = {
            "추론_깊이": {
                "5": "다층적 사고, 여러 요소 통합, 텍스트 맥락 깊이 이해",
                "4": "논리적 추론, 맥락과 내용 연결",
                "3": "기본적 추론, 표면적 맥락 이해",
                "2": "단편적 이해, 논리적 연결 부족",
                "1": "표면적 반응, 추론 없음"
            },
            "비판적_사고": {
                "5": "독자적 해석, 다양한 관점 고려, 텍스트 비평",
                "4": "대안적 해석 시도, 일부 관점 다양성",
                "3": "질문에 대한 직접적 답변",
                "2": "단순 정보 회상, 해석 시도 미흡",
                "1": "관련 없는 응답 또는 오해"
            },
            "문학적_이해": {
                "5": "시대적/문화적 맥락 통합, 작품 전체 구조 파악",
                "4": "작품 구조와 주제 이해",
                "3": "줄거리와 주요 사건 이해",
                "2": "부분적 이해, 오해 일부 포함",
                "1": "작품 내용 오해"
            }
        }
    
    async def evaluate(self, student_input: str, thought_log: str = "") -> Dict:
        """
        학생의 답변을 3차원 루브릭으로 질적 평가
        
        Args:
            student_input: 학생 질문/답변
            thought_log: 사고 과정 로그 (optional)
        
        Returns:
            평가 결과 (점수, 피드백, 평균)
        """
        
        thought_log_section = f"[사고 과정 로그]\n{thought_log}" if thought_log else ""
        
        prompt = f"""고전문학 교육 평가 전문가로서 학생의 사고를 평가하세요.

[평가 루브릭]
{json.dumps(self.rubric, ensure_ascii=False, indent=2)}

[학생 응답]
{student_input}

{thought_log_section}

[출력 형식 - 반드시 JSON만 출력]
{{
  "추론_깊이": {{"점수": X, "피드백": "구체적 근거와 함께 설명"}},
  "비판적_사고": {{"점수": X, "피드백": "구체적 근거와 함께 설명"}},
  "문학적_이해": {{"점수": X, "피드백": "구체적 근거와 함께 설명"}},
  "종합_평가": "전체적인 평가 요약"
}}

JSON만 출력하세요. 코드 블록이나 추가 설명 없이 순수 JSON만 출력하세요.
"""
        
        try:
            response = self.model.generate_content(prompt)
            json_text = response.text.strip()
            
            # JSON 추출 (코드 블록 제거)
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()
            
            evaluation = json.loads(json_text)
            
            # 점수 계산
            scores = [
                evaluation["추론_깊이"]["점수"],
                evaluation["비판적_사고"]["점수"],
                evaluation["문학적_이해"]["점수"]
            ]
            
            evaluation["총점"] = sum(scores)
            evaluation["평균"] = round(sum(scores) / 3, 2)
            
            return evaluation
            
        except Exception as e:
            print(f"Gemini 평가 오류: {e}")
            return self._fallback_eval()
    
    def _fallback_eval(self) -> Dict:
        """평가 실패 시 기본 응답"""
        return {
            "추론_깊이": {"점수": 3, "피드백": "평가 시스템 오류 - 기본 점수"},
            "비판적_사고": {"점수": 3, "피드백": "평가 시스템 오류 - 기본 점수"},
            "문학적_이해": {"점수": 3, "피드백": "평가 시스템 오류 - 기본 점수"},
            "종합_평가": "시스템 오류로 평가 불가",
            "총점": 9,
            "평균": 3.0
        }
    
    async def calculate_qualitative_score(self, evaluation: Dict) -> float:
        """
        질적 평가 점수를 100점 만점 기준으로 환산 (70% 가중치 적용)
        
        Args:
            evaluation: evaluate() 메서드의 결과
        
        Returns:
            질적 평가 점수 (최대 70점)
        """
        avg_score = evaluation.get("평균", 3.0)
        # 5점 만점 평균을 70점 만점으로 변환
        return round(avg_score * 0.7 * 20, 1)

    async def generate_session_summary(self, logs_text: str) -> Dict:
        """
        세션 전체 로그를 바탕으로 종합 리포트 생성 (JSON)
        """
        prompt = f"""당신은 고전문학 교육 전문가입니다. 학생의 전체 학습 대화 로그를 분석하여 최종 리포트를 작성해주세요.

[학습 로그]
{logs_text}

[요청 사항]
1. 학생의 사고 과정 깊이와 변화를 분석하세요.
2. 잘한 점을 칭찬하고, 부족한 점을 부드럽게 지적하며 개선 방향을 제시하세요.
3. 반드시 아래 JSON 형식으로만 응답하세요.

[출력 형식 - JSON]
{{
  "종합_피드백": "전체적인 총평 (3~4문장)",
  "주요_강점": ["발견된 강점 1", "발견된 강점 2"],
  "보완_필요점": ["보완점 1", "보완점 2"],
  "향후_학습_가이드": "구체적인 학습 조언",
  "성취도_등급": "S/A/B/C 중 하나 (로그 내용 기반 판단)"
}}

코드 블록이나 잡담 없이 순수 JSON만 출력하세요.
"""
        
        try:
            response = self.model.generate_content(prompt)
            json_text = response.text.strip()
            
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()
                
            return json.loads(json_text)
            
        except Exception as e:
            print(f"리포트 생성 오류: {e}")
            return {
                "종합_피드백": "리포트 생성 중 오류가 발생했습니다.",
                "주요_강점": [],
                "보완_필요점": [],
                "향후_학습_가이드": "잠시 후 다시 시도해주세요.",
                "성취도_등급": "B"
            }
