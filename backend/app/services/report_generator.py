"""
리포트 생성 서비스
역할: 평가 결과와 사고 로그를 기반으로 규격화된 리포트 JSON 생성
"""

from typing import Dict, List, Any, Optional

class ReportGenerator:
    """
    규격화된 학습 리포트 생성기
    입력: 평가 데이터 및 로그
    출력: 프론트엔드 연동용 표준 JSON
    """
    
    def generate(
        self,
        qualitative_eval: Dict,
        quantitative_eval: Dict,
        integrated_eval: Dict,
        thought_log: List[Dict]
    ) -> Dict[str, Any]:
        """
        리포트 생성 메인 메서드
        """
        
        # 1. 요약 생성
        summary = self._generate_summary(integrated_eval, thought_log)
        
        # 2. 태그 생성
        tags = self._generate_tags(quantitative_eval, qualitative_eval)
        
        # 3. 점수 카드 생성
        scores = self._generate_scores(qualitative_eval, quantitative_eval)
        
        # 4. 흐름 분석 생성
        flow_analysis = self._generate_flow_analysis(thought_log)
        
        # 5. 처방전 생성
        prescription = self._generate_prescription(scores, flow_analysis)
        
        return {
            "summary": summary,
            "tags": tags,
            "scores": scores,
            "flow_analysis": flow_analysis,
            "prescription": prescription
        }
    
    def _generate_summary(self, integrated_eval: Dict, thought_log: List[Dict]) -> str:
        """전체 학습 요약 생성"""
        grade = integrated_eval.get("등급", "B")
        total_score = integrated_eval.get("총점", 0)
        
        total_steps = len(thought_log)
        passed_steps = sum(1 for log in thought_log if not log.get("error_type"))
        
        if grade in ["S", "A"]:
            tone = "매우 훌륭합니다."
        elif grade == "B":
            tone = "전반적으로 양호합니다."
        else:
            tone = "노력이 필요합니다."
            
        return f"총 {total_steps}단계 중 {passed_steps}단계를 성공적으로 통과했으며, 종합 점수는 {total_score}점으로 {grade} 등급입니다. {tone}"

    def _generate_tags(self, quant: Dict, qual: Dict) -> List[str]:
        """핵심 키워드 태그 3개 생성"""
        tags = []
        
        # 1. 강점 기반 태그
        if quant.get("어휘_다양성", {}).get("점수", 0) > 0.8:
            tags.append("#어휘력풍부")
        
        # 2. 질적 특성 태그
        if qual.get("추론_깊이", {}).get("점수", 0) >= 4:
            tags.append("#논리적추론")
        elif qual.get("비판적_사고", {}).get("점수", 0) >= 4:
            tags.append("#비판적시각")
            
        # 3. 문학적 이해 태그
        if qual.get("문학적_이해", {}).get("점수", 0) >= 4:
            tags.append("#문학적감수성")
            
        # 부족하면 기본 태그 채우기
        defaults = ["#성실한학습", "#꾸준한노력", "#고전문학탐구"]
        for tag in defaults:
            if len(tags) < 3:
                tags.append(tag)
                
        return tags[:3]

    def _generate_scores(self, qual: Dict, quant: Dict) -> List[Dict]:
        """역량별 점수 카드 생성 (0.0 ~ 1.0 정규화)"""
        scores = []
        
        # 매핑: (표시이름, 소스딕셔너리, 키, 최대점수)
        metrics = [
            ("추론 깊이", qual, "추론_깊이", 5),
            ("비판적 사고", qual, "비판적_사고", 5),
            ("문학적 이해", qual, "문학적_이해", 5),
            ("어휘 다양성", quant, "어휘_다양성", 1), # 정량 평가 점수는 이미 0~1 비율 
            ("문장 복잡도", quant, "문장_복잡도", 10) # 10점 만점 가정
        ]
        
        for label, source, key, max_score in metrics:
            data = source.get(key, {})
            raw_score = data.get("점수", 0)
            
            # 정규화
            if max_score == 1:
                normalized = min(raw_score, 1.0)
            else:
                normalized = min(round(raw_score / max_score, 2), 1.0)
                
            # 라벨 텍스트 결정
            if normalized >= 0.85:
                label_text = "탁월함"
            elif normalized >= 0.70:
                label_text = "좋음"
            elif normalized >= 0.55:
                label_text = "보통"
            else:
                label_text = "부족"
                
            reason = data.get("피드백", data.get("comment", ""))
            
            scores.append({
                "label": label,
                "score": normalized,
                "label_text": label_text,
                "reason": reason[:50] + "..." if len(reason) > 50 else reason
            })
            
        return scores

    def _generate_flow_analysis(self, logs: List[Dict]) -> List[Dict]:
        """사고 흐름 단계별 분석"""
        analysis = []
        
        for i, log in enumerate(logs):
            step_name = log.get("stage_id", f"Step {i+1}")
            error_type = log.get("error_type")
            
            # 상태 매핑
            if not error_type:
                status = "perfect"
                comment = "매우 논리적으로 잘 연결된 사고입니다."
            elif error_type in ["단순실수", "형식오류"]:
                status = "good" 
                comment = "대체로 좋으나 사소한 실수가 있었습니다."
            else:
                status = "weak"
                comment = log.get("feedback", "논리적 연결이 다소 부족합니다.")
                
            # 인용구 (학생 답변의 일부라고 가정)
            answer = log.get("answer", "")
            quote = answer[:30] + "..." if len(answer) > 30 else answer
            if not quote:
                quote = None
                
            analysis.append({
                "step": step_name,
                "status": status,
                "comment": comment,
                "quote": quote
            })
            
        return analysis

    def _generate_prescription(self, scores: List[Dict], flow_analysis: List[Dict]) -> str:
        """구체적 행동 지침 한 문장 생성"""
        
        # 1. 가장 낮은 점수 항목 찾기
        lowest_metric = min(scores, key=lambda x: x["score"])
        
        # 2. 흐름에서 약한 부분 찾기
        weak_steps = [item["step"] for item in flow_analysis if item["status"] == "weak"]
        
        if lowest_metric["score"] >= 0.8:
            return "현재의 뛰어난 감각을 유지하며 더 어려운 작품에 도전해보세요!"
            
        target = lowest_metric["label"]
        
        if target == "추론 깊이":
            return "주장에 대한 근거를 본문에서 찾아 연결하는 연습을 다음 학습 목표로 삼으세요."
        elif target == "비판적 사고":
            return "작가의 의도를 의심해보고 다른 관점에서 상황을 바라보는 연습이 필요합니다."
        elif target == "문학적 이해":
            return "작품의 시대적 배경과 인물의 관계도를 먼저 그려보고 독해를 시작하세요."
        elif target == "어휘 다양성":
            return "비슷한 단어보다는 더 구체적이고 다채로운 표현을 사용해보려 노력하세요."
        else:
            return "답변을 조금 더 길고 구체적으로 작성하는 연습을 해보세요."
