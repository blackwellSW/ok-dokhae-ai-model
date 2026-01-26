import kss
import re
from typing import List, Dict

class LogicAnalyzer:
    def __init__(self):
        # 논리적 표지어 사전 고도화
        self.patterns = {
            "claim": [
                r"~해야 한다", r"~함이 중요하다", r"~라고 주장한다", r"~로 밝혀졌다",
                r"~임이 분명하다", r"~할 필요가 있다", r"결론적으로"
            ],
            "evidence": [
                r"~에 따르면", r"~가 보여주듯", r"~는 사실이다", r"예를 들어",
                r"실제로", r"연구에 의하면", r"~라는 조사 결과"
            ],
            "cause": [
                r"~때문에", r"~로 인하여", r"~의 원인은", r"~가 계기가 되어",
                r"~에 기인한다", r"~의 배경에는"
            ],
            "result": [
                r"따라서", r"그러므로", r"결과적으로", r"이로 인해",
                r"~하게 되었다", r"~를 초래했다", r"결국"
            ],
            "contrast": [
                r"하지만", r"그러나", r"반면", r"이와 달리",
                r"그럼에도 불구하고", r"반대로"
            ]
        }

    def analyze(self, text: str) -> List[Dict]:
        """
        텍스트를 문장 단위로 분리하고, 각 문장의 논리적 역할과 핵심 키워드를 추출합니다.
        """
        sentences = kss.split_sentences(text)
        analyzed_nodes = []

        for i, s in enumerate(sentences):
            roles = self._detect_roles(s)
            keywords = self._extract_keywords(s)
            
            analyzed_nodes.append({
                "index": i,
                "text": s,
                "roles": roles if roles else ["general"],
                "keywords": keywords,
                "is_key_node": self._check_if_key_node(roles, i, len(sentences))
            })
            
        return analyzed_nodes

    def _detect_roles(self, sentence: str) -> List[str]:
        roles = []
        for role, patterns in self.patterns.items():
            for pattern in patterns:
                # 간단한 리터럴 및 정규표현식 매칭
                if pattern.startswith("~"):
                    if pattern[1:] in sentence:
                        roles.append(role)
                elif re.search(pattern, sentence):
                    roles.append(role)
        return list(set(roles))

    def _extract_keywords(self, sentence: str) -> List[str]:
        # TODO: KoNLPy 또는 Transformers 기반 키워드 추출 도입 가능
        # 현재는 명사성 간단 추출 (가이드라인 수준)
        words = sentence.split()
        return [w for w in words if len(w) > 1][:5]

    def _check_if_key_node(self, roles: List[str], index: int, total: int) -> bool:
        """
        문장이 핵심 노드인지 판별 (주장, 결과 또는 문단의 처음/마지막 등)
        """
        priority_roles = ["claim", "result", "contrast"]
        if any(role in priority_roles for role in roles):
            return True
        if index == 0 or index == total - 1:
            return True
        return False
