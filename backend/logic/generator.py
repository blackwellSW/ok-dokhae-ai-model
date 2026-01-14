"""
QuestionGenerator - Phase 2 고도화 버전
논리 역할 우선순위, 동적 슬롯 필링, NLI 기반 피드백, 히스토리 관리 기능 포함
"""
import re
import random
from typing import List, Dict, Optional


class QuestionGenerator:
    """
    분석된 논리 노드 정보를 기반으로 소크라테스식 질문을 생성하는 클래스.
    Phase 2에서 역할 우선순위, 슬롯 필링, 피드백 고도화, 히스토리 관리 기능이 추가됨.
    """

    # =====================================================================
    # [1] Role Priority: 논리 역할 우선순위 정의
    # =====================================================================
    ROLE_PRIORITY_MAP: Dict[str, int] = {
        "claim": 100,
        "cause": 90,
        "result": 80,
        "evidence": 70,
        "contrast": 60,
        "general": 0,
    }
    MIN_CONFIDENCE_THRESHOLD: float = 0.70  # 70% 미만이면 general로 처리

    def __init__(self):
        # =====================================================================
        # [2] Template: 동적 슬롯({snippet}, {entity})이 포함된 질문 템플릿
        # =====================================================================
        self.templates: Dict[str, List[str]] = {
            "claim": [
                # [QAR: Think and Search] 주장 파악
                "'{snippet}'에서 필자가 강조하고자 하는 핵심 주장은 무엇인가요?",
                
                # [Socratic] 전제 확인
                "그 해석은 '{snippet}' 내용이 반드시 참이라는 가정이 필요한데, 그 근거는 무엇인가요?",
                
                # [Toulmin] 영장 탐색
                "제시된 근거에서 이 주장('{snippet}')으로 나아가기 위해, 필자는 어떤 논리적 연결 고리를 사용하고 있나요?",
                
                # [Toulmin] 반박 고려
                "어떤 상황에서 '{snippet}'(이)라는 주장이 성립하지 않을 수 있을까요?",
                
                # [Review] 요약하기 (Reciprocal Teaching)
                "지금까지의 논리를 한 문장으로 압축해 볼까요?",

                # [Bloom: Analyze] 의도 파악
                "글쓴이가 '{snippet}'라고 주장하는 이면에 깔린 궁극적인 의도는 무엇일까요?",

                # [Bloom: Application] 적용하기
                "이 주장('{snippet}')을 우리 현실 문제에 적용한다면 어떤 사례를 들 수 있을까요?",
            ],
            "evidence": [
                # [QAR: Right There] 명시적 정보 확인
                "본문에서 '{entity}'(은)는 무엇이라고 명시되어 있나요?",
                
                # [Socratic] 증거 탐구
                "본문의 정확히 어느 문장이 '{snippet}' 내용을 뒷받침하나요?",
                
                # [Toulmin] 보강 요구
                "'{snippet}'만으로 주장을 뒷받침하기에 충분한가요? 아니면 추가 근거가 더 필요할까요?",
                
                # [Bloom: Evaluate] 근거 평가
                "저자가 제시한 '{entity}' 관련 근거가 주장을 뒷받침하기에 충분히 객관적인가요?",

                # [Critical Thinking] 정보 공백 확인
                "이 근거('{snippet}') 말고도 주장을 강화하기 위해 더 필요한 정보가 있다면 무엇일까요?",

                # [Socratic] 대안적 해석
                "혹시 이 근거('{snippet}')를 다른 방식으로 해석할 여지는 없을까요?",
            ],
            "cause": [
                # [QAR: Think and Search] 원인 분석
                "본문의 여러 부분을 종합해 볼 때, '{snippet}' 현상이 발생한 복합적인 원인은 무엇인가요?",
                
                # [Thinking Routine] See-Think-Wonder
                "'{entity}' 원인과 관련하여, 텍스트에서 발견한 사실(See)과 당신의 해석(Think)을 구분해서 설명해 줄 수 있나요?",
                
                # [Bloom: Analyze] 인과관계 분석
                "이러한 배경이 결과적으로 '{snippet}'에 어떤 영향을 미쳤는지 논리적으로 연결해 볼까요?",

                # [Systems Thinking] 근본 원인 탐색
                "직접적인 원인 외에, '{snippet}' 현상을 초래한 근본적인(사회적/구조적) 배경은 무엇일까요?",

                # [Logic Check] 인과관계 검증
                "이 원인('{snippet}')과 결과 사이의 연결 고리가 필연적인가요, 아니면 우연적인 요소도 있나요?",
            ],
            "result": [
                # [Socratic] 결과 및 함축
                "사용자님의 해석대로라면, '{snippet}' 이후에 어떤 내용이 이어져야 논리적으로 타당할까요?",
                
                # [Reciprocal Teaching] 예측하기
                "'{entity}'(으)로 인한 결과를 바탕으로, 저자가 다음 단락에서 어떤 논리를 펴나갈 것이라 예상하나요?",
                
                # [Bloom: Create] 가설 및 적용
                "만약 이 결과('${snippet}')가 발생하지 않았다면, 상황은 어떻게 달라졌을까요?",
                
                # [Thinking Routine] See-Think-Wonder (Wonder focus)
                "이 결과와 관련하여 더 궁금한 점(Wonder)은 무엇인가요?",

                # [Bloom: Evaluate] 파급 효과 평가
                "이 결과('{snippet}')가 긍정적인 측면만 있을까요? 혹시 부정적인 부작용은 없을까요?",

                # [Interpretation] 주제 연결
                "이 결과('{snippet}')를 통해 저자가 최종적으로 전달하려는 메시지는 무엇일까요?",
            ],
            "contrast": [
                # [Socratic] 관점 전환
                "만약 저자와 반대되는 입장이라면 '{snippet}' 내용을 어떻게 반박할 수 있을까요?",
                
                # [Bloom: Analyze] 대조 분석
                "필자가 '{entity}'을(를) 대비시키며 강조하고자 하는 논리적 차이점은 무엇인가요?",
                
                # [Six Hats] 검은 모자 (부정/비판)
                "이 대조 논리에서 놓치고 있는 예외 상황이나 허점은 없을까요?",
                
                # [Thinking Routine] Compare-Contrast
                "'{entity}'와(과) 비교할 때 가장 두드러지는 차이점은 무엇인가요?",

                # [Synthesis] 통합적 사고
                "두 입장('{entity}') 사이에서 중재안을 찾는다면 어떤 결론을 내릴 수 있을까요?",

                # [Value Assessment] 가치 평가
                "이 대조('{snippet}')를 통해 필자가 부각하고 싶은 핵심 가치는 무엇인가요?",
            ],
            "general": [
                # [QAR: Author and Me] 저자와 내 생각
                "저자가 말한 '{snippet}' 개념을 당신의 실제 경험에 비추어 설명해 본다면?",
                
                # [QAR: On My Own] 내 힘으로
                "이 글의 주제와 관련하여, 당신이라면 '{entity}' 문제에 대해 어떤 해결책을 제시하겠나요?",
                
                # [Thinking Routine] See-Think-Wonder (Opening)
                "'{snippet}' 문장에서 무엇이 보이고(See), 그것이 무엇을 의미한다고 생각하시나요(Think)?",
                
                # [Reciprocal Teaching] 명료화하기
                "이 문맥에서 '{entity}'(이)라는 단어는 흔히 아는 뜻과 다르게 쓰인 것 같은데, 어떻게 정의할 수 있을까요?",
                
                # [Bloom: Analyze] 구조 파악
                "이 문단이 전체 주장 중 어떤 논리적 단계를 담당하고 있나요?",

                # [Socratic] 다각도 분석 (Contrast 유도)
                "만약 '{snippet}' 내용에 반대하는 사람이 있다면, 어떤 근거를 들 수 있을까요?",

                # [Bloom: Apply] 적용 및 예측 (Result 유도)
                "'{snippet}' 상황이 우리 사회(혹은 주변)에 직접 적용된다면 어떤 변화가 생길까요?",

                # [Critical Thinking] 심층 탐구 (Cause 유도)
                "필자가 굳이 '{snippet}'(이)라고 표현한 의도나 숨겨진 의미는 무엇일까요?",
            ],
        }

        # =====================================================================
        # [3] Feedback Matrix: NLI 라벨별 피드백 템플릿
        # =====================================================================
        self.feedback_templates: Dict[str, List[str]] = {
            "contradiction": [
                "본문에서 '{quote}'라고 언급되었는데, 답변과 조금 상충하는 것 같아요. 다시 확인해 볼까요?",
                "흠, 지문의 내용과 반대로 말씀하신 것 같아요. '{quote}' 부분을 다시 읽어보시겠어요?",
                "두 내용이 충돌하네요. 본문의 '{quote}'를 참고해서 다시 생각해 보시겠어요?",
                "잠시만요, 본문에는 '{quote}'라고 나와 있어요. 혹시 반대로 생각하지 않으셨나요?",
                "문맥을 다시 살펴볼까요? '{quote}' 부분이 의미하는 바를 다시 한번 해석해 보세요.",
                "답변하신 내용은 본문의 흐름과 조금 다른 것 같습니다. '{quote}'를 중심으로 다시 정리해 봅시다.",
            ],
            "neutral": [
                "좋은 방향이에요! 하지만 '{keyword}' 부분에 대한 언급이 빠진 것 같아요. 조금 더 보완해 주시겠어요?",
                "핵심을 거의 짚으셨어요. '{keyword}'에 대해 좀 더 자세히 설명해 주실 수 있나요?",
                "대부분 맞았어요! 다만, 논리적 관계를 좀 더 명확히 해주시면 완벽해요.",
                "절반의 정답입니다! '{keyword}'와 관련된 내용을 조금 더 구체적으로 덧붙여 볼까요?",
                "좋은 시도예요. 다만 '{keyword}'에 대한 설명이 조금 부족해 보여요. 이 부분을 보강하면 완벽할 것 같아요.",
                "전반적인 맥락은 맞습니다. 하지만 필자가 말하는 '{keyword}'의 진짜 의미를 좀 더 파고들어 볼까요?",
            ],
            "length_short": [
                "답변이 조금 짧은 것 같아요. 왜 그렇게 생각하시는지 이유도 함께 설명해 주세요.",
                "좀 더 구체적으로 말씀해 주실 수 있나요?",
                "추가 설명을 덧붙여서 논리적 근거를 보강해 주세요.",
                "핵심은 짚으셨는데, 조금 더 자세히 설명해 주시면 좋을 것 같아요. 왜 그렇게 생각하셨나요?",
                "너무 간결해요! 친구에게 설명하듯이 조금 더 풀어서 이야기해 볼까요?",
                "그 생각의 배경이 궁금해요. 본문의 어떤 내용이 그런 생각을 하게 만들었나요?",
            ],
            "off_topic": [
                "질문과 조금 다른 방향으로 가신 것 같아요. 다시 한번, '{question}'에 대해 생각해 볼까요?",
                "본문 중 '{snippet}' 부분에 집중해서 다시 답변해 주시겠어요?",
                "원래 질문으로 돌아가 볼게요: {question}",
                "흥미로운 이야기지만, 지금은 '{question}'에 집중해 볼까요?",
                "잠시 길을 잃은 것 같아요. 본문의 '{snippet}' 내용으로 다시 돌아와 봅시다.",
                "그 답변도 일리가 있지만, 본문의 맥락에서 '{question}'에 대한 답을 찾아보는 건 어떨까요?",
            ],
            "pass": [
                "완벽합니다! 다음 단계로 넘어가 볼까요?",
                "정확하게 이해하고 계시네요! 다음 내용으로 진행해 볼까요?",
                "훌륭해요! 핵심을 완벽히 파악하셨습니다. 계속해 볼까요?",
                "대단해요! 이 부분은 완전히 이해하셨군요.",
                "브라보! 정확한 근거를 바탕으로 논리정연하게 답변하셨네요.",
                "완벽해요! 저자의 의도를 정확히 꿰뚫어 보셨습니다.",
                "더할 나위 없는 답변입니다. 내용을 완전히 자신의 것으로 만드셨군요.",
                "훌륭합니다! 논리적 흐름을 아주 잘 따라오고 계세요.",
            ],
        }

        # [4] History: 질문 중복 방지를 위한 히스토리
        self._history: List[str] = []
        self._current_node_id: Optional[str] = None

    # =========================================================================
    # [1] Role Priority: 우선순위 기반 역할 추출 함수
    # =========================================================================
    def get_primary_role(self, node: Dict) -> str:
        """
        node["roles"] 목록 중 가장 높은 우선순위의 역할을 반환합니다.
        roles가 비어있거나 None인 경우 'general'을 반환합니다.
        신뢰도가 MIN_CONFIDENCE_THRESHOLD 미만이면 'general'로 처리합니다.
        """
        roles = node.get("roles")

        # 예외 처리: roles가 None이거나 빈 리스트인 경우
        if not roles:
            return "general"

        # roles가 문자열 리스트인 경우 (간단한 형태)
        if isinstance(roles[0], str):
            candidate_roles = [r for r in roles if r in self.ROLE_PRIORITY_MAP]
            if not candidate_roles:
                return "general"
                
            # 가중치 기반 확률적 선택 (Weighted Random Choice)
            # 점수가 높을수록 선택 확률 증가, 하지만 낮은 점수도 선택될 수 있음
            weights = [self.ROLE_PRIORITY_MAP.get(r, 0) + 10 for r in candidate_roles] # +10 for smoothing
            return random.choices(candidate_roles, weights=weights, k=1)[0]

        # roles가 딕셔너리 리스트인 경우 (신뢰도 포함 형태)
        if isinstance(roles[0], dict):
            candidates = []
            weights = []
            
            for role_info in roles:
                role_name = role_info.get("role", "general")
                confidence = role_info.get("confidence", 0.0)
                
                if confidence < self.MIN_CONFIDENCE_THRESHOLD:
                    continue
                    
                priority = self.ROLE_PRIORITY_MAP.get(role_name, 0)
                
                candidates.append(role_name)
                # 우선순위와 신뢰도를 결합하여 가중치 계산
                weights.append(priority * confidence * 100)

            if not candidates:
                return "general"
                
            return random.choices(candidates, weights=weights, k=1)[0]

        return "general"

    # =========================================================================
    # [2] Template Slot Filling: 텍스트 스니펫 및 엔티티 추출
    # =========================================================================
    def _extract_snippet(self, text: str, max_length: int = 40) -> str:
        """
        텍스트에서 핵심 문구(최대 max_length자)를 추출합니다.
        단순히 앞부분만 자르는 것이 아니라, 랜덤하게 중간이나 뒷부분을 선택하여 다양성을 줍니다.
        """
        if not text:
            return "해당 내용"

        # 불필요한 공백 제거
        cleaned = " ".join(text.split())
        
        if len(cleaned) <= max_length:
            return cleaned

        # 다양성을 위해 3가지 전략 중 하나 랜덤 선택
        strategy = random.choice(["start", "middle", "end"])
        
        if strategy == "start":
            return cleaned[:max_length] + "..."
            
        elif strategy == "end":
            return "..." + cleaned[-max_length:]
            
        else: # middle
            start_idx = random.randint(0, len(cleaned) - max_length)
            return "..." + cleaned[start_idx : start_idx + max_length] + "..."

    def _extract_entity(self, text: str) -> str:
        """
        텍스트에서 핵심 명사(주어/목적어)를 추출합니다.
        다양한 조사 패턴을 확인하고, 매칭되는 것들 중 랜덤하게 하나를 선택합니다.
        """
        if not text:
            return "주요 대상"

        # 한글 명사구 패턴 (2글자 이상의 한글 단어 + 조사)
        patterns = [
            r"([가-힣]{2,})(은|는)\s",      # 주제격
            r"([가-힣]{2,})(이|가)\s",      # 주격
            r"([가-힣]{2,})(을|를)\s",      # 목적격
            r"([가-힣]{2,})(수|것|점|데)\s", # 의존명사 (제외 대상이지만 일단 추출 후 필터링 가능)
        ]
        
        candidates = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 의존명사 등 불용어 제외
                if match[0] not in ["할수", "하는", "있는", "어떤"]:
                    candidates.append(match[0])
        
        # 첫 단어도 후보에 포함 (명사일 확률 높음)
        words = text.split()
        if words:
            first_word = re.sub(r"[^가-힣]", "", words[0])
            if len(first_word) >= 2:
                candidates.append(first_word)

        if candidates:
            return random.choice(candidates)

        return "해당 내용"

    def _safe_format(self, template: str, slots: Dict[str, str]) -> str:
        """
        템플릿에 슬롯 값을 안전하게 삽입합니다.
        KeyError 방지를 위해 누락된 슬롯은 기본값으로 대체합니다.
        """
        defaults = {
            "snippet": "해당 내용",
            "entity": "주요 대상",
            "quote": "본문 내용",
            "keyword": "핵심 키워드",
            "question": "질문",
        }

        # 기본값과 실제 슬롯 병합
        final_slots = {**defaults, **slots}

        try:
            return template.format(**final_slots)
        except KeyError as e:
            # 예상치 못한 슬롯이 있는 경우 원본 반환
            return template
        except Exception:
            return template

    # =========================================================================
    # [4] History Management: 중복 방지 및 히스토리 관리
    # =========================================================================
    def _update_history(self, node: Dict, question: str) -> None:
        """생성된 질문을 히스토리에 추가합니다."""
        # 노드가 바뀌면 히스토리 초기화
        node_id = node.get("id") or node.get("text", "")[:50]
        if node_id != self._current_node_id:
            self._history = []
            self._current_node_id = node_id

        self._history.append(question)

    def _get_available_templates(self, template_list: List[str]) -> List[str]:
        """
        히스토리에 없는 사용 가능한 템플릿을 반환합니다.
        모든 템플릿이 히스토리에 있으면 히스토리를 리셋하여 다시 랜덤하게 섞이도록 합니다.
        """
        available = [t for t in template_list if t not in self._history]

        if available:
            return available

        # 모든 템플릿을 다 썼으면 히스토리 리셋 (새로운 사이클 시작)
        # 단, 현재 노드 ID는 유지해야 함
        self._history = [] 
        return template_list

    def reset_history(self) -> None:
        """히스토리를 명시적으로 초기화합니다."""
        self._history = []
        self._current_node_id = None

    # =========================================================================
    # 메인 질문 생성 함수
    # =========================================================================
    def generate(self, node: Dict, history: Optional[List[str]] = None) -> str:
        """
        분석된 노드 정보를 바탕으로 적절한 소크라테스식 질문을 생성합니다.

        Args:
            node: 분석된 노드 정보 (text, roles 등 포함)
            history: 외부에서 전달받는 히스토리 (선택적, 내부 히스토리와 병합됨)

        Returns:
            생성된 질문 문자열
        """
        # [1] Role: 우선순위 기반 역할 추출
        primary_role = self.get_primary_role(node)

        # [2] Template 선택
        template_list = self.templates.get(primary_role, self.templates["general"])

        # [4] History: 외부 히스토리와 내부 히스토리 병합
        if history:
            combined_history = list(set(self._history + history))
        else:
            combined_history = self._history

        # 사용 가능한 템플릿 필터링
        self._history = combined_history  # 임시 동기화
        available_templates = self._get_available_templates(template_list)

        # 랜덤 선택
        template = random.choice(available_templates)

        # [2] Slot Filling: 동적 슬롯 채우기
        text = node.get("text", "")
        slots = {
            "snippet": self._extract_snippet(text),
            "entity": self._extract_entity(text),
        }

        question = self._safe_format(template, slots)

        # [4] History: 히스토리에 추가
        self._update_history(node, template)

        return question

    # =========================================================================
    # [3] Feedback: NLI 라벨 기반 피드백 고도화
    # =========================================================================
    def generate_feedback_question(
        self,
        evaluation: Dict,
        original_question: Optional[str] = None,
        node: Optional[Dict] = None,
    ) -> str:
        """
        이해도 평가 결과에 따라 맞춤형 피드백을 생성합니다.

        Args:
            evaluation: 평가 결과 딕셔너리 (is_passed, nli_label, sts_score 등)
            original_question: 원래 질문 (off_topic 피드백 시 사용)
            node: 원본 노드 정보 (quote, snippet 추출에 사용)

        Returns:
            피드백 문자열
        """
        is_passed = evaluation.get("is_passed", False)
        nli_label = evaluation.get("nli_label", "neutral")
        user_answer = evaluation.get("user_answer", "")

        # 성공한 경우
        if is_passed:
            template = random.choice(self.feedback_templates["pass"])
            return template

        # 답변이 너무 짧은 경우
        if user_answer and len(user_answer.strip()) < 10:
            template = random.choice(self.feedback_templates["length_short"])
            return template

        # 슬롯 준비
        slots = {
            "quote": "",
            "keyword": "",
            "snippet": "",
            "question": original_question or "이전 질문",
        }

        if node:
            text = node.get("text", "")
            slots["quote"] = self._extract_snippet(text, max_length=30)
            slots["snippet"] = self._extract_snippet(text)
            slots["keyword"] = self._extract_entity(text)

        # NLI 라벨별 피드백 선택
        if nli_label == "contradiction":
            templates = self.feedback_templates["contradiction"]
        elif nli_label == "neutral":
            templates = self.feedback_templates["neutral"]
        else:
            # 기타 케이스는 neutral로 처리
            templates = self.feedback_templates["neutral"]

        # 주제 이탈 감지 (STS 점수가 매우 낮은 경우)
        sts_score = evaluation.get("sts_score", 0.5)
        if sts_score < 0.2:
            templates = self.feedback_templates["off_topic"]

        template = random.choice(templates)
        return self._safe_format(template, slots)
