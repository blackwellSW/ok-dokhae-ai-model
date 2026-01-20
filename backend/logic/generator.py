from typing import List, Dict, Optional

class QuestionGenerator:
    def __init__(self):
        # 논리 역할별 질문 템플릿
        self.templates = {
            "claim": [
                "필자가 여기서 강조하고자 하는 핵심 주장은 무엇인가요?",
                "이 문장에서 가장 중요하다고 생각되는 단어는 무엇이며, 그 이유는 무엇인가요?",
                "본문의 주장을 뒷받침하기 위해 어떤 근거가 더 필요할까요?"
            ],
            "evidence": [
                "이 증거가 앞에 나온 주장을 어떻게 뒷받침하고 있나요?",
                "여기서 제시된 사실이 실제 상황에서 어떻게 적용될 수 있을까요?",
                "만약 이 근거가 없다면 주장의 설득력이 어떻게 변할까요?"
            ],
            "cause": [
                "이 현상이 일어나게 된 결정적인 계기는 무엇이라고 설명되어 있나요?",
                "원인이 되는 요소를 한 단어로 요약한다면 무엇일까요?",
                "이러한 배경이 결과에 어떤 영향을 주었는지 설명해 보세요."
            ],
            "result": [
                "이 과정의 끝에서 나타난 최종적인 변화는 무엇인가요?",
                "이 결과로 인해 사회나 환경에 어떤 연쇄 반응이 일어날까요?",
                "결과를 다른 관점에서 해석한다면 어떻게 볼 수 있을까요?"
            ],
            "contrast": [
                "앞서 언급된 내용과 이 문장이 상반되는 지점은 어디인가요?",
                "필자가 두 대상을 대조함으로써 강조하려는 차이점은 무엇인가요?",
                "상반된 두 의견 중 어느 쪽에 더 무게가 실려 있다고 느껴지시나요?"
            ],
            "general": [
                "이 문장을 자신의 언어로 한 문장 요약해 주시겠어요?",
                "여기서 말하는 핵심 개념이 무엇인지 설명해 주세요.",
                "방금 읽으신 내용에서 가장 이해하기 어려웠던 단어는 무엇인가요?"
            ]
        }

    def generate(self, node: Dict, history: Optional[List[str]] = None) -> str:
        """
        분석된 노드 정보를 바탕으로 적절한 소크라테스식 질문을 생성합니다.
        """
        primary_role = node["roles"][0] if node["roles"] else "general"
        
        # 기본 템플릿 사용 (향후 T5/LLM 연동 가능)
        import random
        template_list = self.templates.get(primary_role, self.templates["general"])
        
        # 히스토리에 있는 질문은 가급적 피함 (단순 중복 방지 로직)
        chosen = random.choice(template_list)
        if history and chosen in history and len(template_list) > 1:
            chosen = [q for q in template_list if q != chosen][0]
            
        return chosen

    def generate_feedback_question(self, evaluation: Dict) -> str:
        """
        이해도 평가 결과에 따라 추가 질문을 던집니다.
        """
        if not evaluation["is_passed"]:
            if evaluation["nli_label"] == "contradiction":
                return "본문에서 'A'라고 말한 부분과 답변이 조금 다른 것 같아요. 다시 한 번 확인해 볼까요?"
            return "조금만 더 자세히, 본문 전체의 흐름을 고려해서 답변해 주시겠어요?"
        
        return "완벽합니다! 다음 단계로 넘어가 볼까요?"
