#!/usr/bin/env python3
"""
고전문학 사고유도 AI 교사 - 채팅형 인터페이스

소크라틱 대화 방식으로 학생과 상호작용하며 사고를 유도합니다.
"""

import streamlit as st
import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="고전문학 사고유도 AI 교사",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .user-message {
        background-color: #4A90E2;
        color: white;
        padding: 16px 20px;
        border-radius: 18px;
        margin: 12px 0;
        max-width: 75%;
        margin-left: auto;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    .ai-message {
        background-color: #FFFFFF;
        color: #212121;
        padding: 16px 20px;
        border-radius: 18px;
        margin: 12px 0;
        max-width: 75%;
        border: 1px solid #E0E0E0;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    .chat-container {
        height: 550px;
        overflow-y: auto;
        padding: 24px;
        background-color: #F8F9FA;
        border-radius: 12px;
        margin-bottom: 24px;
    }
    .timestamp {
        font-size: 0.85rem;
        color: rgba(255,255,255,0.8);
        margin-top: 6px;
    }
    .ai-timestamp {
        font-size: 0.85rem;
        color: #999;
        margin-top: 6px;
    }
    .message-label {
        font-weight: 600;
        margin-bottom: 8px;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 백엔드 함수
# ============================================================

@st.cache_data(ttl=300)
def get_access_token():
    """GCP 액세스 토큰 가져오기 (5분 캐싱)"""
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"],
            stderr=subprocess.PIPE
        ).decode("utf-8").strip()
        return token
    except Exception as e:
        return None


def call_ai_teacher(endpoint_id, project, region, conversation_history, context, max_tokens=100, temperature=0.7):
    """
    AI 교사 호출 (대화 히스토리 포함)

    Args:
        conversation_history: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    """
    token = get_access_token()
    if not token:
        return {"error": "gcloud 인증이 필요합니다."}

    # API URL
    url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/endpoints/{endpoint_id}:rawPredict"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 대화 컨텍스트 구성
    # vLLM은 system role을 지원하지 않으므로, 첫 메시지에 컨텍스트 포함
    messages = []

    if len(conversation_history) == 1:
        # 첫 번째 질문인 경우 컨텍스트 추가
        first_user_msg = f"""당신은 {context} 전문가이며, 소크라테스식 문답법을 사용하는 AI 교사입니다.

학생의 질문에 직접 답을 주지 말고, 학생 스스로 생각하도록 유도하는 질문으로 답변하세요.

[필수 응답 형식]
[사고유도] <1~2문장 힌트>. <질문 1개>?
[사고로그] <AI의 교육적 의도와 사고 과정 기록>

[중요 규칙]
1. 질문은 반드시 1개만 (여러 개 금지)
2. 자연스러운 한국어 대화 톤
3. "model" 단어 사용 금지

[좋은 예시]
[사고유도] 춘향이가 이몽룡을 처음 만날 때를 떠올려보세요. 그때 이몽룡은 어떤 모습으로 나타났나요?
[사고로그] 학생이 작품의 핵심 장면을 떠올리게 하여, 이몽룡의 신분 은폐가 자연스러운 상황이었음을 스스로 깨닫도록 유도함.

학생 질문: {conversation_history[0]['content']}

AI 교사 응답:"""
        messages.append({"role": "user", "content": first_user_msg})
    else:
        # 대화가 진행 중인 경우, 전체 히스토리 전달
        # 단, 첫 메시지는 컨텍스트가 포함된 형태로 유지
        first_msg_with_context = f"""당신은 {context} 전문가이며, 소크라테스식 문답법을 사용하는 AI 교사입니다.

[필수 응답 형식]
[사고유도] <힌트>. <질문 1개>?
[사고로그] <교육적 의도>

학생 질문: {conversation_history[0]['content']}

AI 교사 응답:"""
        messages.append({"role": "user", "content": first_msg_with_context})

        # 이후 대화 추가 (assistant, user 번갈아가며)
        for i in range(1, len(conversation_history)):
            msg = conversation_history[i]
            if msg['role'] == 'assistant':
                # vLLM에서는 assistant가 마지막이면 안 되므로 처리
                if i < len(conversation_history) - 1:
                    messages.append({"role": "assistant", "content": msg['content']})
            else:
                messages.append({"role": "user", "content": msg['content']})

    payload = {
        "model": "classical-lit",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.9
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            result = response.json()
            choices = result.get("choices", [])

            if choices:
                answer = choices[0].get("message", {}).get("content", "")
                usage = result.get("usage", {})

                return {
                    "success": True,
                    "answer": answer,
                    "usage": usage
                }
            else:
                return {"error": "응답 데이터가 비어있습니다"}
        else:
            return {"error": f"HTTP {response.status_code}"}

    except requests.exceptions.Timeout:
        return {"error": "요청 시간 초과 (60초)"}
    except Exception as e:
        return {"error": str(e)}


def load_deployment_info():
    """배포 정보 로드"""
    deployment_info_path = Path(__file__).parent.parent / "deployment_info.json"

    if deployment_info_path.exists():
        with open(deployment_info_path) as f:
            return json.load(f)
    return None


# ============================================================
# 세션 상태 초기화
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "context" not in st.session_state:
    st.session_state.context = "춘향전"

if "max_tokens" not in st.session_state:
    st.session_state.max_tokens = 100

if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7


# ============================================================
# 사이드바
# ============================================================

with st.sidebar:
    st.header("⚙️ 설정")

    # 배포 정보 로드
    deployment_info = load_deployment_info()

    if deployment_info:
        st.success(f"✅ 엔드포인트 연결됨")
        st.caption(f"배포일: {deployment_info.get('deployed_at', 'N/A')}")
        endpoint_id = deployment_info.get("endpoint_id")
        project = deployment_info.get("project_id")
        region = deployment_info.get("region")
    else:
        st.warning("⚠️ deployment_info.json이 없습니다")
        endpoint_id = st.text_input("Endpoint ID", "2283851677146546176")
        project = st.text_input("Project ID", "knu-team-03")
        region = st.text_input("Region", "us-central1")

    st.markdown("---")

    # 작품 선택
    st.session_state.context = st.selectbox(
        "📚 학습 작품",
        ["춘향전", "심청전", "흥부전", "홍길동전", "구운몽", "사씨남정기", "한국사"],
        index=0
    )

    st.markdown("---")

    # 파라미터 조정
    st.subheader("🎛️ AI 파라미터")

    st.session_state.max_tokens = st.slider(
        "응답 길이",
        min_value=50,
        max_value=200,
        value=100,
        step=25,
        help="짧을수록 빠르고 간결한 답변"
    )

    st.session_state.temperature = st.slider(
        "창의성",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="높을수록 다양한 답변"
    )

    st.markdown("---")

    # 대화 초기화
    if st.button("🔄 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")

    # 통계 (간소화)
    if len(st.session_state.messages) > 0:
        st.caption(f"💬 대화 턴: {len(st.session_state.messages) // 2}회")

    st.markdown("---")

    # 사고로그 보기
    st.subheader("📊 사고로그")

    if len(st.session_state.messages) == 0:
        st.caption("대화가 시작되면 사고로그가 표시됩니다")
    else:
        import re

        # AI 응답에서 [사고로그] 또는 [사실로그] 추출
        logs = []
        for idx, msg in enumerate(st.session_state.messages):
            if msg["role"] == "assistant":
                content = msg["content"]

                # [사고로그] 또는 [사실로그] 패턴 찾기
                # [사고로그] 태그 이후부터 문자열 끝까지 추출
                if '[사고로그]' in content:
                    log_text = content.split('[사고로그]')[1].strip()
                    if log_text:
                        log_matches = [('사고로그', log_text)]
                    else:
                        log_matches = []
                elif '[사실로그]' in content:
                    log_text = content.split('[사실로그]')[1].strip()
                    if log_text:
                        log_matches = [('사실로그', log_text)]
                    else:
                        log_matches = []
                else:
                    log_matches = []

                for tag, log_text in log_matches:
                    logs.append({
                        "turn": (idx + 1) // 2,
                        "tag": tag,
                        "text": log_text.strip()
                    })

        if logs:
            for log in logs:
                with st.expander(f"턴 {log['turn']} - [{log['tag']}]", expanded=False):
                    st.markdown(log['text'])
        else:
            st.caption("사고로그가 없습니다")


# ============================================================
# 메인 화면
# ============================================================

st.markdown("""
<h1 style='font-size: 2.5rem; margin-bottom: 10px;'>📚 고전문학 사고유도 AI 교사</h1>
<p style='font-size: 1.2rem; color: #666; margin-bottom: 30px;'>
소크라틱 대화를 통해 학생 스스로 생각하도록 돕는 AI 교사입니다
</p>
""", unsafe_allow_html=True)

st.markdown("---")

# 채팅 컨테이너
chat_container = st.container()

with chat_container:
    if len(st.session_state.messages) == 0:
        # 환영 메시지
        st.markdown("""
        <div style='text-align: center; padding: 60px 20px; color: #555;'>
            <h2 style='color: #333; margin-bottom: 20px;'>👋 안녕하세요!</h2>
            <p style='font-size: 1.1rem; line-height: 1.8; margin: 12px 0;'>
                궁금한 것을 자유롭게 질문해보세요.
            </p>
            <p style='font-size: 1.1rem; line-height: 1.8; margin: 12px 0;'>
                AI 교사가 질문을 통해 스스로 답을 찾도록 도와드립니다.
            </p>
            <p style='font-size: 0.95rem; color: #888; margin-top: 30px;'>
                💡 왼쪽 사이드바에서 작품을 선택하고 시작하세요
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # 대화 히스토리 표시
        for idx, message in enumerate(st.session_state.messages):
            # AI 응답에서 태그 제거
            content = message['content']
            if message["role"] == "assistant":
                import re
                # [사고로그] 이후 내용 전체 제거 (사고로그는 사이드바에서만 표시)
                if '[사고로그]' in content:
                    parts = content.split('[사고로그]')
                    content = parts[0]
                # [태그] 형식만 제거하고 내용은 유지
                content = re.sub(r'\[사고유도\]|\[질문\]', '', content).strip()
                # HTML 특수문자 이스케이프 (XSS 방지)
                content = content.replace('<', '&lt;').replace('>', '&gt;')
                # 빈 내용이면 기본 메시지
                if not content:
                    content = "(응답 생성 중 오류가 발생했습니다)"

            if message["role"] == "user":
                st.markdown(f"""
                <div style='text-align: right;'>
                    <div class='user-message'>
                        {content}
                        <div class='timestamp'>{message.get('timestamp', '')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='ai-message'>
                    {content}
                    <div class='ai-timestamp'>{message.get('timestamp', '')}</div>
                </div>
                """, unsafe_allow_html=True)

st.markdown("---")

# 입력 폼
st.markdown("""
<style>
    .stTextInput input {
        font-size: 1.1rem !important;
        padding: 12px !important;
    }
    .stButton button {
        font-size: 1.1rem !important;
        padding: 12px 24px !important;
        height: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])

    with col1:
        user_input = st.text_input(
            "메시지 입력",
            placeholder="예: 춘향전에서 이몽룡이 신분을 숨긴 이유가 뭔가요?",
            label_visibility="collapsed"
        )

    with col2:
        submitted = st.form_submit_button("📤 전송", use_container_width=True, type="primary")

# 메시지 전송 처리
if submitted and user_input:
    # 사용자 메시지 추가
    timestamp = datetime.now().strftime("%H:%M")
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": timestamp
    })

    # AI 응답 생성
    with st.spinner("🤔 AI 교사가 생각하고 있습니다..."):
        # 대화 히스토리 변환
        conversation_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in st.session_state.messages
        ]

        result = call_ai_teacher(
            endpoint_id=endpoint_id,
            project=project,
            region=region,
            conversation_history=conversation_history,
            context=st.session_state.context,
            max_tokens=st.session_state.max_tokens,
            temperature=st.session_state.temperature
        )

    if result.get("success"):
        # AI 응답 추가
        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "timestamp": datetime.now().strftime("%H:%M"),
            "usage": result.get("usage", {})
        })
    else:
        # 오류 메시지
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"❌ 오류가 발생했습니다: {result.get('error', '알 수 없는 오류')}",
            "timestamp": datetime.now().strftime("%H:%M")
        })

    # 화면 새로고침
    st.rerun()

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>고전문학 사고유도 AI 교사 | Gemma 2 9B-IT + LoRA (vLLM)</p>
    <p>KNU Team 03 | 2026-02</p>
</div>
""", unsafe_allow_html=True)
