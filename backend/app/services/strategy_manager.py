"""
학습 전략 매니저
역할: 학생의 약점과 상황에 맞는 학습 전략 선택
"""

import uuid
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import LearningStrategy, StrategySelection, LearningState


class StrategyManager:
    """학습 전략 선택 및 적응"""
    
    # 기본 전략 정의
    STRATEGIES = {
        "socratic": {
            "name": "소크라테스식 질문",
            "description": "질문을 통해 스스로 깨닫게 만들기",
            "use_when": {"retry_count": 0, "learning_style": "independent"}
        },
        "hint_decompose": {
            "name": "힌트 분해",
            "description": "문제를 작은 단위로 나누어 힌트 제공",
            "use_when": {"retry_count": 1, "weak_skill": "추론깊이"}
        },
        "example_based": {
            "name": "예시 제공",
            "description": "유사한 예시를 통해 이해 돕기",
            "use_when": {"retry_count": 2, "weak_skill": "문학적이해"}
        },
        "counterexample": {
            "name": "반례 제시",
            "description": "잘못된 사고를 반례로 교정",
            "use_when": {"retry_count": 1, "weak_skill": "비판적사고"}
        }
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def select_strategy(
        self,
        state_id: str,
        recent_failures: List[Dict],
        current_weak_skills: Dict
    ) -> str:
        """
        현재 상황에 맞는 최적 전략 선택
        
        Args:
            state_id: 학습 상태 ID
            recent_failures: 최근 실패 목록
            current_weak_skills: 현재 약점 기술들
        
        Returns:
            strategy_id: 선택된 전략 ID
        """
        
        # 재시도 횟수
        retry_count = len(recent_failures)
        
        # 주요 약점
        main_weakness = None
        if current_weak_skills:
            main_weakness = max(current_weak_skills.items(), key=lambda x: x[1])[0]
        
        # 전략 선택 로직
        if retry_count == 0:
            selected = "socratic"
        elif retry_count == 1:
            if main_weakness == "추론깊이":
                selected = "hint_decompose"
            elif main_weakness == "비판적사고":
                selected = "counterexample"
            else:
                selected = "hint_decompose"
        else:  # retry_count >= 2
            selected = "example_based"
        
        # 선택 기록
        selection = StrategySelection(
            selection_id=str(uuid.uuid4()),
            state_id=state_id,
            strategy_id=selected,
            selection_reason={
                "retry_count": retry_count,
                "main_weakness": main_weakness
            },
            recent_failures=[f["fail_reason"] for f in recent_failures],
            weak_skills_addressed=[main_weakness] if main_weakness else []
        )
        
        self.db.add(selection)
        await self.db.commit()
        
        return selected
    
    def get_strategy_config(self, strategy_id: str) -> Dict:
        """전략 설정 조회"""
        return self.STRATEGIES.get(strategy_id, self.STRATEGIES["socratic"])
