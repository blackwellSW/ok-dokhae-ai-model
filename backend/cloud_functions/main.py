"""
Google Cloud Functions - 백그라운드 작업 핸들러

이 파일은 Cloud Functions로 배포되어 다음 작업을 처리합니다:
1. 세션 정리 (만료된 세션 삭제)
2. 리포트 생성 (학습 세션 분석)
3. 알림 전송 (학습 완료 알림)

배포 명령어:
gcloud functions deploy cleanup_sessions \
    --runtime python311 \
    --trigger-http \
    --allow-unauthenticated \
    --region asia-northeast3 \
    --project knu-team-03
"""

import functions_framework
from google.cloud import firestore
from datetime import datetime, timedelta, timezone
import json


@functions_framework.http
def cleanup_sessions(request):
    """
    만료된 세션 정리 (HTTP 트리거)

    호출: Cloud Scheduler로 1시간마다 호출
    기능: 24시간 이상 업데이트 없는 세션을 ended로 마킹
    """
    try:
        db = firestore.Client()

        # 24시간 이상 된 active 세션 조회
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)

        sessions_ref = db.collection("sessions")
        old_sessions = sessions_ref.where(
            "status", "==", "active"
        ).where(
            "updated_at", "<", cutoff_time.isoformat()
        ).stream()

        cleaned_count = 0
        for session in old_sessions:
            session.reference.update({
                "status": "expired",
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "end_reason": "auto_cleanup"
            })
            cleaned_count += 1

        return json.dumps({
            "success": True,
            "cleaned_sessions": cleaned_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }), 200, {"Content-Type": "application/json"}

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }), 500, {"Content-Type": "application/json"}


@functions_framework.http
def generate_report(request):
    """
    학습 리포트 생성 (HTTP 트리거)

    호출: 세션 종료 시 또는 수동 호출
    기능: 세션 데이터를 분석하여 학습 리포트 생성
    """
    try:
        request_json = request.get_json(silent=True)

        if not request_json or "session_id" not in request_json:
            return json.dumps({
                "success": False,
                "error": "session_id required"
            }), 400, {"Content-Type": "application/json"}

        session_id = request_json["session_id"]
        db = firestore.Client()

        # 세션 데이터 조회
        session_ref = db.collection("sessions").document(session_id)
        session = session_ref.get()

        if not session.exists:
            return json.dumps({
                "success": False,
                "error": "Session not found"
            }), 404, {"Content-Type": "application/json"}

        session_data = session.to_dict()

        # 메시지 조회
        messages = session_ref.collection("messages").order_by("timestamp").stream()
        message_list = [msg.to_dict() for msg in messages]

        # 기본 분석
        total_messages = len(message_list)
        user_messages = [m for m in message_list if m.get("role") == "user"]
        ai_messages = [m for m in message_list if m.get("role") == "assistant"]

        # 리포트 생성
        report = {
            "session_id": session_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_turns": len(user_messages),
                "duration_minutes": _calculate_duration(message_list),
                "completion_status": session_data.get("status", "unknown")
            },
            "thinking_log_summary": _extract_thinking_logs(ai_messages),
            "recommendations": []
        }

        # 리포트 저장
        db.collection("reports").document(session_id).set(report)

        return json.dumps({
            "success": True,
            "report": report
        }), 200, {"Content-Type": "application/json"}

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }), 500, {"Content-Type": "application/json"}


def _calculate_duration(messages: list) -> int:
    """메시지 리스트에서 세션 시간 계산 (분)"""
    if len(messages) < 2:
        return 0

    try:
        first_time = datetime.fromisoformat(messages[0]["timestamp"])
        last_time = datetime.fromisoformat(messages[-1]["timestamp"])
        return int((last_time - first_time).total_seconds() / 60)
    except:
        return 0


def _extract_thinking_logs(ai_messages: list) -> list:
    """AI 메시지에서 사고로그 추출"""
    logs = []
    for msg in ai_messages:
        metadata = msg.get("metadata", {})
        if "log" in metadata:
            logs.append(metadata["log"])
    return logs


@functions_framework.http
def send_notification(request):
    """
    알림 전송 (HTTP 트리거)

    호출: 특정 이벤트 발생 시 (세션 완료, 피드백 준비 등)
    기능: FCM 또는 이메일로 알림 전송
    """
    try:
        request_json = request.get_json(silent=True)

        if not request_json:
            return json.dumps({
                "success": False,
                "error": "Request body required"
            }), 400, {"Content-Type": "application/json"}

        user_id = request_json.get("user_id")
        notification_type = request_json.get("type")
        message = request_json.get("message")

        # TODO: FCM 또는 이메일 전송 구현
        # 현재는 로그만 기록

        print(f"Notification: user={user_id}, type={notification_type}, msg={message}")

        return json.dumps({
            "success": True,
            "message": "Notification logged (FCM integration pending)"
        }), 200, {"Content-Type": "application/json"}

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        }), 500, {"Content-Type": "application/json"}
