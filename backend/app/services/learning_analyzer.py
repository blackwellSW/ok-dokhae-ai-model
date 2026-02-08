"""
학습 분석 및 리포트 생성
역할: 사고 로그 분석, 학생/교사용 리포트 생성
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List
from collections import Counter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.db.models import (
    ThinkingLog, LearningState, AnswerEvaluation,
    LearningReport, GateResult
)
from app.services.gemini_evaluator import GeminiEvaluator


class LearningAnalyzer:
    """학습 로그 분석 및 리포트 생성"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_student_report(
        self,
        user_id: str,
        days: int = 7
    ) -> Dict:
        """
        학생용 학습 리포트 생성
        
        Returns:
            {
                "report_id": str,
                "period": dict,
                "stuck_points": list,
                "weak_thinking_types": dict,
                "improvement_areas": list,
                "stats": dict
            }
        """
        
        # 기간 설정
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # 학습 상태 조회
        stmt = select(LearningState).where(
            LearningState.user_id == user_id
        )
        result = await self.db.execute(stmt)
        states = result.scalars().all()
        
        if not states:
            return self._empty_report(user_id)
        
        state_ids = [s.state_id for s in states]
        
        # 사고 로그 조회
        log_stmt = select(ThinkingLog).where(
            and_(
                ThinkingLog.state_id.in_(state_ids),
                ThinkingLog.created_at.between(start_date, end_date)
            )
        )
        log_result = await self.db.execute(log_stmt)
        logs = log_result.scalars().all()
        
        # 분석
        stuck_points = self._analyze_stuck_points(logs)
        weak_types = self._analyze_weak_thinking_types(logs)
        improvement_areas = self._suggest_improvements(weak_types)
        stats = self._calculate_stats(logs)
        
        # 리포트 저장
        report = LearningReport(
            report_id=str(uuid.uuid4()),
            user_id=user_id,
            report_type="student",
            start_date=start_date,
            end_date=end_date,
            stuck_points=stuck_points,
            weak_thinking_types=weak_types,
            improvement_areas=improvement_areas,
            stats=stats
        )
        
        self.db.add(report)
        await self.db.commit()
        
        return {
            "report_id": report.report_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "stuck_points": stuck_points,
            "weak_thinking_types": weak_types,
            "improvement_areas": improvement_areas,
            "stats": stats
        }
    
    def _analyze_stuck_points(self, logs: List) -> List[Dict]:
        """막힌 지점 분석"""
        stuck_points = []
        
        # 재시도가 많았던 단계
        stage_failures = {}
        
        for log in logs:
            if log.error_type:
                stage_id = log.stage_id
                stage_failures[stage_id] = stage_failures.get(stage_id, 0) + 1
        
        for stage_id, count in sorted(stage_failures.items(), key=lambda x: x[1], reverse=True)[:3]:
            stuck_points.append({
                "stage_id": stage_id,
                "failure_count": count,
                "description": f"{stage_id} 단계에서 {count}번 실패"
            })
        
        return stuck_points
    
    def _analyze_weak_thinking_types(self, logs: List) -> Dict:
        """약한 사고 유형 분석"""
        weak_types = {}
        
        for log in logs:
            if log.error_type:
                weak_types[log.error_type] = weak_types.get(log.error_type, 0) + 1
        
        # 백분율로 변환
        total = sum(weak_types.values())
        if total > 0:
            weak_types = {k: {"count": v, "percentage": round(v / total * 100, 1)} 
                         for k, v in weak_types.items()}
        
        return weak_types
    
    def _suggest_improvements(self, weak_types: Dict) -> List[str]:
        """개선 영역 제안"""
        suggestions = []
        
        for weak_type, data in weak_types.items():
            if data.get("percentage", 0) > 30:
                if "추론" in weak_type:
                    suggestions.append("논리적 추론 연습이 필요합니다. 근거와 결론을 연결하는 연습을 해보세요.")
                elif "비판" in weak_type:
                    suggestions.append("비판적 사고를 키우세요. 다양한 관점에서 생각해보는 연습이 도움됩니다.")
                elif "문학" in weak_type:
                    suggestions.append("작품의 시대적 배경과 문화를 더 공부해보세요.")
        
        if not suggestions:
            suggestions.append("전반적으로 잘하고 있습니다! 계속 유지하세요.")
        
        return suggestions
    
    def _calculate_stats(self, logs: List) -> Dict:
        """통계 계산"""
        if not logs:
            return {}
        
        total_time = sum(log.time_spent for log in logs)
        total_questions = len(logs)
        failed_count = sum(1 for log in logs if log.error_type)
        
        return {
            "total_questions": total_questions,
            "total_time_minutes": round(total_time / 60, 1),
            "avg_time_per_question": round(total_time / total_questions, 1) if total_questions > 0 else 0,
            "success_rate": round((total_questions - failed_count) / total_questions * 100, 1) if total_questions > 0 else 0,
            "failed_count": failed_count
        }
    
    async def generate_session_report(
        self,
        user_id: str,
        state_id: str
    ) -> Dict:
        """
        세션 종료 리포트 생성 (4회 핑퐁 완료 후) - Gemini 기반 분석
        """
        # 세션 로그 조회
        stmt = select(ThinkingLog).where(ThinkingLog.state_id == state_id).order_by(ThinkingLog.created_at)
        result = await self.db.execute(stmt)
        logs = result.scalars().all()
        
        # 1. 통계 분석
        total_turns = 4
        passed_count = sum(1 for log in logs if not log.error_type)
        failed_count = len(logs) - passed_count
        failed_stages = [log.stage_id for log in logs if log.error_type]
        most_failed_stage = max(set(failed_stages), key=failed_stages.count) if failed_stages else "없음"
        strategies = [log.strategy_used for log in logs]
        strategy_counts = dict(Counter(strategies))
        
        stats = {
            "total_turns": total_turns,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "pass_rate": round(passed_count / total_turns * 100, 1),
            "most_failed_stage": most_failed_stage,
            "strategies_used": strategy_counts
        }
        
        # 2. Gemini 기반 심층 분석 (JSON 생성)
        evaluator = GeminiEvaluator()
        
        # 로그 텍스트 변환
        logs_text = ""
        for i, log in enumerate(logs):
            logs_text += f"\n[Turn {i+1}]\nQ: {log.question}\nA: {log.answer}\n피드백: {log.feedback}\n"
            
        gemini_analysis = await evaluator.generate_session_summary(logs_text)
        
        # 리포트 저장
        improvement_areas = gemini_analysis.get("보완_필요점", [])
        if gemini_analysis.get("향후_학습_가이드"):
            improvement_areas.append(gemini_analysis["향후_학습_가이드"])
            
        weak_types = {
            "main_fail_stage": most_failed_stage,
            "detail_weaknesses": gemini_analysis.get("보완_필요점", [])
        }
        
        report = LearningReport(
            report_id=str(uuid.uuid4()),
            user_id=user_id,
            report_type="session_summary",
            start_date=datetime.now(), # 임시
            end_date=datetime.now(),
            stuck_points=[], # 필요시 추가
            weak_thinking_types=weak_types,
            improvement_areas=improvement_areas,
            stats=stats,
            # Gemini 분석 결과 전체 저장 (JSON 필드가 있다면 좋지만, 현재는 stats나 다른 필드에 분산 저장)
            # 여기서는 stats에 포함시키거나 별도 필드를 고려할 수 있음
             # 임시로 stats에 분석 텍스트 포함
        )
        # stats에 gemini 결과 병합 (클라이언트 편의성)
        report_data = {
            "summary_comment": gemini_analysis.get("종합_피드백", ""),
            "strengths": gemini_analysis.get("주요_강점", []),
            "grade": gemini_analysis.get("성취도_등급", "B"),
            "stats": stats,
            "gemini_raw": gemini_analysis
        }
        
        # DB 저장용 stats 덮어쓰기 (JSON 저장 가능 필드 활용)
        report.stats = report_data
        
        self.db.add(report)
        await self.db.commit()
        
        return {
            "report_id": report.report_id,
            "summary": report_data
        }

    async def generate_teacher_report(
        self,
        teacher_id: str,
        user_ids: List[str],  # 담당 학생들
        days: int = 7
    ) -> Dict:
        """
        교사용 리포트 생성
        
        Returns:
            학생별 패턴, 전체 통계, 공통 약점
        """
        
        # 각 학생 분석
        student_reports = []
        
        for user_id in user_ids:
            report = await self.generate_student_report(user_id, days)
            student_reports.append({
                "user_id": user_id,
                "report": report
            })
        
        # 클래스 전체 통계
        all_weak_types = []
        for sr in student_reports:
            weak_types = sr["report"].get("weak_thinking_types", {})
            all_weak_types.extend(weak_types.keys())
        
        common_weaknesses = []
        if all_weak_types:
            counter = Counter(all_weak_types)
            # 50% 이상의 학생이 공통으로 약한 부분
            threshold = len(user_ids) * 0.5
            common_weaknesses = [
                {"weakness": k, "student_count": v, "percentage": round(v / len(user_ids) * 100, 1)}
                for k, v in counter.items() if v >= threshold
            ]
        
        return {
            "teacher_id": teacher_id,
            "student_count": len(user_ids),
            "period_days": days,
            "student_reports": student_reports,
            "common_weaknesses": common_weaknesses
        }
    
    def _empty_report(self, user_id: str) -> Dict:
        """빈 리포트"""
        return {
            "report_id": str(uuid.uuid4()),
            "user_id": user_id,
            "stuck_points": [],
            "weak_thinking_types": {},
            "improvement_areas": ["아직 학습 데이터가 없습니다."],
            "stats": {}
        }
