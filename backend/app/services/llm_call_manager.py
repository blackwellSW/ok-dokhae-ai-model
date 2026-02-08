"""
LLM 호출 관리 시스템
역할: 프롬프트 버저닝, 토큰 관리, 캐싱, fallback 처리
"""

import uuid
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import LLMCallLog, CachedResult
import google.generativeai as genai
from app.core.config import get_settings

settings = get_settings()


class LLMCallManager:
    """LLM 호출 관리자"""
    
    # 프롬프트 버전
    PROMPT_VERSION = "v1.0"
    
    # 토큰 가격 (USD per 1K tokens, Gemini Pro 기준)
    COST_PER_1K_INPUT = 0.000375
    COST_PER_1K_OUTPUT = 0.0015
    
    def __init__(self, db: AsyncSession):
        self.db = db
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def call_with_management(
        self,
        prompt: str,
        purpose: str,
        use_cache: bool = True
    ) -> Dict:
        """
        관리 기능이 포함된 LLM 호출
        
        Returns:
            {
                "output": str,
                "cache_hit": bool,
                "cost": float,
                "latency_ms": int
            }
        """
        
        # 1. 캐시 확인
        if use_cache:
            cached = await self._get_cached(prompt, purpose)
            if cached:
                return {
                    "output": cached,
                    "cache_hit": True,
                    "cost": 0,
                    "latency_ms": 0
                }
        
        # 2. LLM 호출
        start_time = time.time()
        
        try:
            response = self.model.generate_content(prompt)
            output = response.text.strip()
            status = "success"
            error_message = None
            
        except Exception as e:
            # Fallback
            output = await self._fallback_response(purpose)
            status = "fallback"
            error_message = str(e)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 3. 토큰 및 비용 추정
        token_count = self._estimate_tokens(prompt, output)
        cost = self._calculate_cost(token_count)
        
        # 4. 로그 기록
        log = LLMCallLog(
            call_id=str(uuid.uuid4()),
            model_name="gemini-pro",
            prompt_version=self.PROMPT_VERSION,
            purpose=purpose,
            input_text=prompt[:1000],  # 앞 1000자만 저장
            output_text=output[:1000],
            token_count=token_count,
            latency_ms=latency_ms,
            cost_usd=cost,
            status=status,
            error_message=error_message
        )
        
        self.db.add(log)
        
        # 5. 캐싱
        if use_cache and status == "success":
            await self._save_cache(prompt, purpose, output)
        
        await self.db.commit()
        
        return {
            "output": output,
            "cache_hit": False,
            "cost": cost,
            "latency_ms": latency_ms
        }
    
    async def _get_cached(self, prompt: str, purpose: str) -> Optional[str]:
        """캐시 조회"""
        cache_key = self._generate_cache_key(prompt, purpose)
        
        stmt = select(CachedResult).where(
            CachedResult.cache_key == cache_key,
            CachedResult.expires_at > datetime.utcnow()
        )
        result = await self.db.execute(stmt)
        cached = result.scalar_one_or_none()
        
        if cached:
            # 히트 카운트 증가
            cached.hit_count += 1
            await self.db.commit()
            return cached.result_data.get("output")
        
        return None
    
    async def _save_cache(self, prompt: str, purpose: str, output: str) -> None:
        """캐시 저장"""
        cache_key = self._generate_cache_key(prompt, purpose)
        input_hash = hashlib.md5(prompt.encode()).hexdigest()
        
        # TTL: 7일
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        cached = CachedResult(
            cache_key=cache_key,
            cache_type=purpose,
            input_hash=input_hash,
            result_data={"output": output},
            hit_count=0,
            expires_at=expires_at
        )
        
        self.db.add(cached)
    
    def _generate_cache_key(self, prompt: str, purpose: str) -> str:
        """캐시 키 생성"""
        content = f"{purpose}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _estimate_tokens(self, prompt: str, output: str) -> int:
        """토큰 수 추정 (대략 1 token = 4 characters for Korean)"""
        return (len(prompt) + len(output)) // 3
    
    def _calculate_cost(self, token_count: int) -> float:
        """비용 계산"""
        # 간단하게 평균 비용으로 계산
        avg_cost_per_1k = (self.COST_PER_1K_INPUT + self.COST_PER_1K_OUTPUT) / 2
        return (token_count / 1000) * avg_cost_per_1k
    
    async def _fallback_response(self, purpose: str) -> str:
        """Fallback 응답"""
        fallbacks = {
            "question_gen": "이 부분에 대해 더 자세히 설명해주시겠어요?",
            "evaluation": "답변을 다시 검토 중입니다.",
            "feedback": "조금 더 구체적으로 작성해보세요."
        }
        return fallbacks.get(purpose, "일시적인 오류가 발생했습니다.")
