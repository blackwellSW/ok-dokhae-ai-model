from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from app.services.inference_service import InferenceService
from app.services.logging_service import LoggingService

router = APIRouter()
inference_service = InferenceService()
logging_service = LoggingService()

# Request Models
class AnalyzeRequest(BaseModel):
    user_id: str = Field(..., example="yongbin_choi")
    session_id: str = Field(..., example="sess_20260123_01")
    text: str = Field(..., description="분석할 비문학 원문")

class AnswerRequest(BaseModel):
    user_id: str
    session_id: str
    text: str # User Answer
    target_node_text: str # The part of text being questioned
    question: str # The AI question asked

# Endpoints
@router.post("/analyze", tags=["Inference"])
async def analyze_text(req: AnalyzeRequest):
    try:
        nodes = inference_service.analyze_text(req.text)
        # Log analysis request if needed, currently mainly logging answers
        return {"nodes": nodes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit_answer", tags=["Inference"])
async def submit_answer(req: AnswerRequest, background_tasks: BackgroundTasks):
    """
    Evaluates user answer, generates feedback, and logs detailed execution trace.
    """
    try:
        # 1. Evaluate
        eval_result = inference_service.evaluate_answer(req.text, req.target_node_text)
        
        # 2. Generate Feedback
        feedback_msg = inference_service.generate_feedback(
            eval_result, 
            original_question=req.question,
            node={"text": req.target_node_text} # Simplified node rep
        )
        
        # 3. Create Log Entry (Structured)
        log_entry = logging_service.create_log_entry(
            user_id=req.user_id,
            session_id=req.session_id,
            text=req.text,
            evaluation_result=eval_result,
            feedback_msg=feedback_msg
        )
        
        # 4. Save Log (Background Task)
        # We run this in background to avoid blocking the response
        background_tasks.add_task(logging_service.save_log, log_entry)

        return {
            "evaluation": eval_result,
            "feedback": feedback_msg,
            "log_id": log_entry.meta.log_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
