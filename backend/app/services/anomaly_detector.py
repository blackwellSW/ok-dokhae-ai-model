"""
이상 행동 감지 시스템
역할: 무의미 답변 반복, 복붙, 프롬프트 탈출 감지
"""

import uuid
from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.models import AnomalyDetection, ThinkingLog


class AnomalyDetector:
    """이상 행동 감지기"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def detect_anomalies(
        self,
        user_id: str,
        state_id: str,
        answer: str,
        recent_answers: List[str]
    ) -> List[Dict]:
        """
        이상 행동 종합 감지
        
        Returns:
            감지된 이상 행동 리스트
        """
        
        anomalies = []
        
        # 1. 무의미 답변 반복
        if self._detect_meaningless_repetition(answer, recent_answers):
            anomalies.append({
                "type": "repeated_meaningless",
                "severity": 3,
                "evidence": {"recent_count": len(recent_answers)}
            })
        
        # 2. 복붙 감지
        if self._detect_copy_paste(answer):
            anomalies.append({
                "type": "copy_paste",
                "severity": 2,
                "evidence": {"suspicious_patterns": "반복된 구조"}
            })
        
        # 3. 프롬프트 탈출 시도
        if self._detect_prompt_escape(answer):
            anomalies.append({
                "type": "prompt_escape",
                "severity": 5,
                "evidence": {"detected_keywords": ["ignore", "system", "prompt"]}
            })
        
        # 이상 행동 기록
        for anomaly in anomalies:
            await self._log_anomaly(
                user_id,
                state_id,
                anomaly["type"],
                anomaly["evidence"],
                anomaly["severity"]
            )
        
        return anomalies
    
    def _detect_meaningless_repetition(
        self,
        answer: str,
        recent_answers: List[str]
    ) -> bool:
        """무의미한 반복 답변 감지"""
        
        # 3회 연속 동일 답변
        if len(recent_answers) >= 2:
            if all(ans == answer for ans in recent_answers[-2:]):
                return True
        
        # 매우 짧은 답변 반복
        if len(answer) < 10 and len(recent_answers) >= 3:
            short_count = sum(1 for ans in recent_answers[-3:] if len(ans) < 10)
            if short_count >= 3:
                return True
        
        return False
    
    def _detect_copy_paste(self, answer: str) -> bool:
        """복붙 감지 (간단한 휴리스틱)"""
        
        # 특이한 형식 (HTML 태그, URL 등)
        suspicious_patterns = ['<', '>', 'http://', 'https://']
        if any(pattern in answer for pattern in suspicious_patterns):
            return True
        
        # 너무 완벽한 구조 (향후 고도화 가능)
        lines = answer.split('\n')
        if len(lines) > 5:
            # 모든 줄이 동일한 구조 (예: "1. ", "2. ")
            if all(line.startswith(f"{i+1}.") for i, line in enumerate(lines[:5])):
                return True
        
        return False
    
    def _detect_prompt_escape(self, answer: str) -> bool:
        """프롬프트 탈출 시도 감지"""
        
        escape_keywords = [
            "ignore previous",
            "ignore all",
            "system:",
            "assistant:",
            "you are now",
            "pretend you are"
        ]
        
        answer_lower = answer.lower()
        return any(keyword in answer_lower for keyword in escape_keywords)
    
    async def _log_anomaly(
        self,
        user_id: str,
        state_id: str,
        anomaly_type: str,
        evidence: Dict,
        severity: int
    ) -> None:
        """이상 행동 로그 기록"""
        
        anomaly = AnomalyDetection(
            anomaly_id=str(uuid.uuid4()),
            user_id=user_id,
            state_id=state_id,
            anomaly_type=anomaly_type,
            evidence=evidence,
            severity=severity,
            action_taken="logged" if severity < 4 else "flagged_for_review"
        )
        
        self.db.add(anomaly)
        await self.db.commit()
