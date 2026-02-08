"""
학습 상태 관리 서비스
역할: 사용자의 학습 진행 상태를 추적하고 관리
"""

import uuid
from datetime import datetime
from typing import Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import LearningState


class LearningStateManager:
    """학습 상태 관리자"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_or_resume_state(
        self, 
        user_id: str,
        work_id: str,
        chunk_id: str
    ) -> Dict:
        """
        새 학습 상태 생성 또는 기존 상태 복구
        
        Returns:
            state_data: 현재 학습 상태
        """
        
        # 기존 active 상태 확인
        stmt = select(LearningState).where(
            LearningState.user_id == user_id,
            LearningState.status == "active"
        )
        result = await self.db.execute(stmt)
        existing_state = result.scalar_one_or_none()
        
        if existing_state:
            # 중간 이탈 복구
            return {
                "state_id": existing_state.state_id,
                "user_id": existing_state.user_id,
                "current_work_id": existing_state.current_work_id,
                "current_chunk_id": existing_state.current_chunk_id,
                "current_stage_id": existing_state.current_stage_id,
                "checkpoint_data": existing_state.checkpoint_data,
                "last_question": existing_state.last_question,
                "last_answer": existing_state.last_answer,
                "resumed": True
            }
        
        # 새 상태 생성
        new_state = LearningState(
            state_id=str(uuid.uuid4()),
            user_id=user_id,
            current_work_id=work_id,
            current_chunk_id=chunk_id,
            current_stage_id="STAGE_1_FACT_CHECK",
            status="ACTIVE",
            current_turn=1,  # 1회차부터 시작
            max_turns=4,
            checkpoint_data={},
            total_stages_completed=0,
            total_time_spent=0,
            weak_skills={}
        )
        
        self.db.add(new_state)
        await self.db.commit()
        await self.db.refresh(new_state)
        
        return {
            "state_id": new_state.state_id,
            "user_id": new_state.user_id,
            "current_work_id": new_state.current_work_id,
            "current_chunk_id": new_state.current_chunk_id,
            "current_stage_id": new_state.current_stage_id,
            "current_turn": new_state.current_turn,
            "resumed": False
        }
    
    async def increment_turn(self, state_id: str) -> Dict[str, Any]:
        """
        턴 증가 및 종료 여부 확인
        Returns:
            {
                "current_turn": int,
                "is_completed": bool
            }
        """
        stmt = select(LearningState).where(LearningState.state_id == state_id)
        result = await self.db.execute(stmt)
        state = result.scalar_one_or_none()
        
        if not state:
            raise ValueError(f"State {state_id} not found")
            
        state.current_turn += 1
        
        # 4회차 답변 후 -> 5가 되면 종료 (또는 4회차 완료 시점으로 처리)
        # 정책: 1(질문) -> 1(답변) -> 2(질문) ... -> 4(질문) -> 4(답변) -> 종료
        
        is_completed = False
        if state.current_turn > state.max_turns:
            state.status = "COMPLETED"
            state.current_turn = state.max_turns # UI 표시용으로 4로 유지
            is_completed = True
            
        await self.db.commit()
        await self.db.refresh(state)
        
        return {
            "current_turn": state.current_turn,
            "is_completed": is_completed
        }
    
    async def update_state(
        self,
        state_id: str,
        updates: Dict
    ) -> None:
        """학습 상태 업데이트"""
        
        stmt = select(LearningState).where(LearningState.state_id == state_id)
        result = await self.db.execute(stmt)
        state = result.scalar_one_or_none()
        
        if not state:
            raise ValueError(f"State {state_id} not found")
        
        # 업데이트
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        await self.db.commit()
    
    async def save_checkpoint(
        self,
        state_id: str,
        checkpoint_data: Dict
    ) -> None:
        """체크포인트 저장 (복구용)"""
        
        await self.update_state(state_id, {
            "checkpoint_data": checkpoint_data,
            "last_question": checkpoint_data.get("last_question"),
            "last_answer": checkpoint_data.get("last_answer")
        })
    
    async def get_weak_skills(self, state_id: str) -> Dict:
        """누적 약점 기술 조회"""
        
        stmt = select(LearningState).where(LearningState.state_id == state_id)
        result = await self.db.execute(stmt)
        state = result.scalar_one_or_none()
        
        return state.weak_skills if state else {}
    
    async def update_weak_skills(
        self,
        state_id: str,
        weak_skill: str
    ) -> None:
        """약점 기술 누적"""
        
        stmt = select(LearningState).where(LearningState.state_id == state_id)
        result = await self.db.execute(stmt)
        state = result.scalar_one_or_none()
        
        if state:
            weak_skills = state.weak_skills.copy()
            weak_skills[weak_skill] = weak_skills.get(weak_skill, 0) + 1
            state.weak_skills = weak_skills
            await self.db.commit()
