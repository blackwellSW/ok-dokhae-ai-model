"""
app/db/models.py
역할: 완전한 학습 시스템을 위한 데이터베이스 모델
"""
from sqlalchemy import String, JSON, DateTime, Boolean, Float, Text, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional
from .database import Base


# ============================================================
# A-1. 사용자 인증 및 관리
# ============================================================

class User(Base):
    """사용자 계정"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    # 인증 정보
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    
    # 기본 정보
    username: Mapped[str] = mapped_column(String(100))
    user_type: Mapped[str] = mapped_column(String(20))  # student, teacher, admin
    
    # 상태
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # 프로필
    profile_data: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())



# ============================================================
# B. 콘텐츠 관리
# ============================================================

class LiteraryWork(Base):
    """작품 메타데이터"""
    __tablename__ = "literary_works"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    work_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(100))
    period: Mapped[str] = mapped_column(String(50))  # 조선시대, 고려시대 등
    difficulty: Mapped[int] = mapped_column(Integer)  # 1-5
    genre: Mapped[str] = mapped_column(String(50))  # 판소리계, 설화 등
    
    # 메타데이터
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords: Mapped[dict] = mapped_column(JSON, default=dict)  # 핵심 키워드
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class TextChunk(Base):
    """지문 분할 정보"""
    __tablename__ = "text_chunks"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    work_id: Mapped[str] = mapped_column(String(50), ForeignKey("literary_works.work_id"))
    
    # 분할 정보
    sequence: Mapped[int] = mapped_column(Integer)  # 순서
    chunk_type: Mapped[str] = mapped_column(String(20))  # paragraph, sentence
    
    # 내용
    content: Mapped[str] = mapped_column(Text)
    modern_translation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 태깅
    is_key_sentence: Mapped[bool] = mapped_column(Boolean, default=False)
    difficulty: Mapped[int] = mapped_column(Integer, default=3)
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class RAGDocument(Base):
    """RAG용 문서 인덱싱"""
    __tablename__ = "rag_documents"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    # 문서 유형
    doc_type: Mapped[str] = mapped_column(String(50))  # original, commentary, vocab, error_pattern
    work_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    chunk_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 내용
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # 벡터 임베딩
    
    # 메타데이터: 어떤 단계에서 사용할지
    usage_stages: Mapped[list] = mapped_column(JSON, default=list)  # ["VOCAB", "EVIDENCE"]
    priority: Mapped[int] = mapped_column(Integer, default=5)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ============================================================
# C. Thinking Path 엔진
# ============================================================

class ThinkingStage(Base):
    """사고 단계 정의"""
    __tablename__ = "thinking_stages"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    stage_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    # 단계 정보
    stage_name: Mapped[str] = mapped_column(String(100))  # 사실 확인, 의미 추론, 근거 연결...
    sequence: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(50))  # basic, advanced, synthesis
    
    # 단계별 목표
    objective: Mapped[str] = mapped_column(Text)
    expected_skill: Mapped[str] = mapped_column(Text)
    
    # 허용 답변 유형
    allowed_answer_types: Mapped[dict] = mapped_column(JSON, default=dict)
    min_answer_length: Mapped[int] = mapped_column(Integer, default=20)
    required_elements: Mapped[list] = mapped_column(JSON, default=list)  # ["근거", "추론"]
    
    # 다음 단계 조건
    pass_criteria: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class QuestionTemplate(Base):
    """동적 질문 생성 템플릿"""
    __tablename__ = "question_templates"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    stage_id: Mapped[str] = mapped_column(String(50), ForeignKey("thinking_stages.stage_id"))
    
    # 템플릿 정보
    template_text: Mapped[str] = mapped_column(Text)
    template_type: Mapped[str] = mapped_column(String(50))  # basic, hint, expansion, remedial
    difficulty: Mapped[int] = mapped_column(Integer)
    
    # 사용 조건
    use_when: Mapped[dict] = mapped_column(JSON, default=dict)  # {"weak_skill": "근거추출"}
    
    # 변수
    variables: Mapped[list] = mapped_column(JSON, default=list)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ============================================================
# A. 학습 상태 관리 (User 제외하고 Learning State만)
# ============================================================

class LearningState(Base):
    """사용자별 학습 상태"""
    __tablename__ = "learning_states"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(50), index=True)  # 향후 User와 연결
    
    # 현재 위치
    current_work_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_chunk_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_stage_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 진행 상태
    session_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE, COMPLETED, PAUSED
    current_turn: Mapped[int] = mapped_column(Integer, default=1)      # 현재 핑퐁 회차 (기본 1)
    max_turns: Mapped[int] = mapped_column(Integer, default=4)         # 최대 핑퐁 횟수 (기본 4)
    
    # 복구 데이터
    checkpoint_data: Mapped[dict] = mapped_column(JSON, default=dict)
    last_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 누적 통계
    total_stages_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_time_spent: Mapped[int] = mapped_column(Integer, default=0)  # 초 단위
    weak_skills: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


# ============================================================
# D. 답변 평가 & 판단
# ============================================================

class AnswerEvaluation(Base):
    """답변 평가 결과"""
    __tablename__ = "answer_evaluations"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    eval_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    # 연결
    state_id: Mapped[str] = mapped_column(String(50), ForeignKey("learning_states.state_id"))
    stage_id: Mapped[str] = mapped_column(String(50))
    
    # 답변
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    
    # 평가 결과
    passed: Mapped[bool] = mapped_column(Boolean)
    fail_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    weak_skill: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # 상세 평가
    format_check: Mapped[dict] = mapped_column(JSON, default=dict)
    semantic_check: Mapped[dict] = mapped_column(JSON, default=dict)
    qualitative_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantitative_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 메타
    evaluation_strategy: Mapped[str] = mapped_column(String(50))  # llm, rule, hybrid
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class GateResult(Base):
    """게이트 통과 결과"""
    __tablename__ = "gate_results"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    eval_id: Mapped[str] = mapped_column(String(50), ForeignKey("answer_evaluations.eval_id"))
    state_id: Mapped[str] = mapped_column(String(50))
    
    # 결과
    action: Mapped[str] = mapped_column(String(50))  # pass, retry, hint, strategy_change
    next_stage_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 피드백
    feedback: Mapped[str] = mapped_column(Text)
    hint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 재시도 정보
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ============================================================
# E. 전략 선택 & 적응 로직
# ============================================================

class LearningStrategy(Base):
    """학습 전략 정의"""
    __tablename__ = "learning_strategies"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    # 전략 정보
    strategy_name: Mapped[str] = mapped_column(String(100))  # socratic, hint_decompose, example, counterexample
    description: Mapped[str] = mapped_column(Text)
    
    # 적용 조건
    use_when: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # 전략 설정
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class StrategySelection(Base):
    """전략 선택 로그"""
    __tablename__ = "strategy_selections"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    selection_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    state_id: Mapped[str] = mapped_column(String(50))
    strategy_id: Mapped[str] = mapped_column(String(50))
    
    # 선택 이유
    selection_reason: Mapped[dict] = mapped_column(JSON, default=dict)
    recent_failures: Mapped[list] = mapped_column(JSON, default=list)
    weak_skills_addressed: Mapped[list] = mapped_column(JSON, default=list)
    
    # 결과
    effectiveness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ============================================================
# F. 로그 & 분석 시스템
# ============================================================

class ThinkingLog(Base):
    """사고 과정 로그 (매우 중요!)"""
    __tablename__ = "thinking_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    log_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    # 연결
    state_id: Mapped[str] = mapped_column(String(50), index=True)
    stage_id: Mapped[str] = mapped_column(String(50))
    
    # 사고 과정 데이터
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    eval_result: Mapped[dict] = mapped_column(JSON, default=dict)
    strategy_used: Mapped[str] = mapped_column(String(50))
    
    # 시간
    time_spent: Mapped[int] = mapped_column(Integer)  # 초
    
    # 사고 패턴 분석
    thinking_pattern: Mapped[dict] = mapped_column(JSON, default=dict)
    skill_demonstrated: Mapped[list] = mapped_column(JSON, default=list)
    error_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    
    # 인덱스 최적화
    __table_args__ = (
        Index('idx_thinking_logs_state_created', 'state_id', 'created_at'),
    )


class LearningReport(Base):
    """학습 리포트"""
    __tablename__ = "learning_reports"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    user_id: Mapped[str] = mapped_column(String(50), index=True)
    report_type: Mapped[str] = mapped_column(String(50))  # student, teacher, class
    
    # 기간
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    
    # 학생용 데이터
    stuck_points: Mapped[list] = mapped_column(JSON, default=list)
    weak_thinking_types: Mapped[dict] = mapped_column(JSON, default=dict)
    improvement_areas: Mapped[list] = mapped_column(JSON, default=list)
    
    # 교사용 데이터
    student_patterns: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    class_common_weaknesses: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    # 통계
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ============================================================
# G. 교사용 기능
# ============================================================

class TeacherDashboardData(Base):
    """교사 대시보드 데이터"""
    __tablename__ = "teacher_dashboard_data"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    dashboard_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    teacher_id: Mapped[str] = mapped_column(String(50), index=True)
    class_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # 진도
    student_progress: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # 단계별 통계
    stage_failure_rate: Mapped[dict] = mapped_column(JSON, default=dict)
    question_pass_rate: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # 실시간 모니터링
    active_sessions: Mapped[int] = mapped_column(Integer, default=0)
    students_needing_help: Mapped[list] = mapped_column(JSON, default=list)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class ContentManagement(Base):
    """교사용 콘텐츠 관리"""
    __tablename__ = "content_management"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    teacher_id: Mapped[str] = mapped_column(String(50))
    
    # 관리 대상
    target_type: Mapped[str] = mapped_column(String(50))  # question_template, eval_criteria, forbidden_pattern
    target_id: Mapped[str] = mapped_column(String(50))
    
    # 변경 내용
    changes: Mapped[dict] = mapped_column(JSON, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


# ============================================================
# H. 인프라 / 운영
# ============================================================

class LLMCallLog(Base):
    """LLM 호출 관리"""
    __tablename__ = "llm_call_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    call_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    # 호출 정보
    model_name: Mapped[str] = mapped_column(String(50))
    prompt_version: Mapped[str] = mapped_column(String(20))
    purpose: Mapped[str] = mapped_column(String(100))  # evaluation, question_gen, feedback
    
    # 입력/출력
    input_text: Mapped[str] = mapped_column(Text)
    output_text: Mapped[str] = mapped_column(Text)
    
    # 비용/성능
    token_count: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # 상태
    status: Mapped[str] = mapped_column(String(20))  # success, fallback, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class CachedResult(Base):
    """결과 캐싱"""
    __tablename__ = "cached_results"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    
    # 캐시 유형
    cache_type: Mapped[str] = mapped_column(String(50))  # question, evaluation, feedback
    
    # 데이터
    input_hash: Mapped[str] = mapped_column(String(64))
    result_data: Mapped[dict] = mapped_column(JSON)
    
    # TTL
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


class AnomalyDetection(Base):
    """이상 행동 감지"""
    __tablename__ = "anomaly_detections"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    anomaly_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    
    user_id: Mapped[str] = mapped_column(String(50), index=True)
    state_id: Mapped[str] = mapped_column(String(50))
    
    # 이상 유형
    anomaly_type: Mapped[str] = mapped_column(String(50))  # repeated_meaningless, copy_paste, prompt_escape
    
    # 상세
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    severity: Mapped[int] = mapped_column(Integer)  # 1-5
    
    # 조치
    action_taken: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
