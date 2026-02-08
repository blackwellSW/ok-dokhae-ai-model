#!/usr/bin/env python3
"""
Gemma 사고유도 모델 데모 (Streamlit)

시뮬레이션 모드: 학습 데이터 샘플 기반 응답 시연
실제 모드: Vertex AI Endpoint 호출 (배포 필요)
"""

import streamlit as st
import json
import random
import subprocess
import requests
from pathlib import Path

# 페이지 설정
st.set_page_config(
    page_title="고전문학 사고유도 AI 교사",
    page_icon="📚",
    layout="wide"
)

# 타이틀
st.title("📚 고전문학 사고유도 AI 교사")
st.markdown("**Gemma 2 9B-IT + LoRA** 기반 소크라틱 대화 모델")

# 사이드바 - 모드 선택
st.sidebar.header("⚙️ 설정")
mode = st.sidebar.radio(
    "실행 모드",
    ["시뮬레이션 (학습 데이터 샘플)", "실제 추론 (Endpoint 필요)"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 모델 정보")
st.sidebar.markdown("""
- **베이스 모델**: Gemma 2 9B-IT
- **학습 방법**: LoRA (r=16, α=32)
- **학습 데이터**: 3,056개 샘플
- **태그 사용률**: 80%
- **평균 질문 수**: 19.7개
""")


# ============================================================
# 시뮬레이션 모드
# ============================================================

def load_training_samples():
    """학습 데이터 샘플 로드"""
    train_file = Path(__file__).parent.parent / "data/final/train_tagged.jsonl"

    if not train_file.exists():
        return []

    samples = []
    with open(train_file, 'r', encoding='utf-8') as f:
        for line in f:
            samples.append(json.loads(line))

    return samples


def display_simulation_mode():
    """시뮬레이션 모드 UI"""
    st.markdown("### 🎭 시뮬레이션 모드")
    st.info("학습 데이터의 실제 샘플을 보여드립니다. 모델이 학습한 응답 패턴을 확인할 수 있습니다.")

    samples = load_training_samples()

    if not samples:
        st.error("학습 데이터 파일을 찾을 수 없습니다: data/final/train_tagged.jsonl")
        return

    # 작품 필터
    contexts = list(set(s.get("instruction", "").split("[작품: ")[-1].split("]")[0]
                       for s in samples if "[작품:" in s.get("instruction", "")))
    contexts = [c for c in contexts if c][:10]  # 상위 10개

    col1, col2 = st.columns([2, 1])

    with col1:
        selected_context = st.selectbox(
            "작품 선택",
            ["전체"] + sorted(contexts),
            index=0
        )

    with col2:
        if st.button("🎲 랜덤 샘플", use_container_width=True):
            st.session_state.random_seed = random.randint(0, len(samples) - 1)

    # 필터링
    if selected_context != "전체":
        filtered = [s for s in samples if f"[작품: {selected_context}]" in s.get("instruction", "")]
    else:
        filtered = samples

    if not filtered:
        st.warning("해당 작품의 샘플이 없습니다.")
        return

    # 샘플 선택
    if "random_seed" in st.session_state:
        sample_idx = st.session_state.random_seed % len(filtered)
    else:
        sample_idx = 0

    sample = filtered[sample_idx]

    st.markdown("---")

    # 입력 표시
    st.markdown("### 💬 학생 질문")

    instruction = sample.get("instruction", "")
    student_input = sample.get("input", "")

    # 작품 추출
    if "[작품:" in instruction:
        work = instruction.split("[작품: ")[-1].split("]")[0]
        st.markdown(f"**작품**: {work}")

    st.markdown(f"**질문**: {student_input}")

    # 응답 표시
    st.markdown("### 🤖 AI 교사 응답")

    output = sample.get("output", "")

    # 태그 분석
    has_induction = "[사고유도]" in output
    has_log = "[사고로그]" in output
    question_count = output.count("?") + output.count("까요")

    # 응답 출력
    response_container = st.container()
    with response_container:
        st.markdown(output)

    # 분석 표시
    st.markdown("---")
    st.markdown("### 📊 응답 분석")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if has_induction:
            st.success("✅ [사고유도] 태그")
        else:
            st.error("❌ [사고유도] 태그")

    with col2:
        if has_log:
            st.success("✅ [사고로그] 태그")
        else:
            st.error("❌ [사고로그] 태그")

    with col3:
        st.metric("질문 수", f"{question_count}개")

    with col4:
        is_evaluator = any(kw in output for kw in ["전달하지 못하고", "부족하여", "평가", "점수"])
        if is_evaluator:
            st.error("❌ 평가자 모드")
        else:
            st.success("✅ 사고유도 모드")

    # 샘플 정보
    st.caption(f"샘플 {sample_idx + 1} / {len(filtered)}")


# ============================================================
# 실제 추론 모드
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


def call_vertex_ai_endpoint(endpoint_id, project, region, question, context, max_tokens=512, temperature=0.7):
    """Vertex AI vLLM 엔드포인트 호출"""
    token = get_access_token()
    if not token:
        return {"error": "gcloud 인증이 필요합니다. 'gcloud auth login'을 실행하세요."}

    # API URL
    url = f"https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/endpoints/{endpoint_id}:rawPredict"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # vLLM OpenAI-compatible API 포맷
    user_prompt = f"당신은 {context} 전문가입니다. 학생의 질문에 친절하고 교육적으로 답변해주세요.\n\n질문: {question}\n\n답변:"

    payload = {
        "model": "classical-lit",  # LoRA 모듈 이름
        "messages": [
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.9
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=180)

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
            return {"error": f"HTTP {response.status_code}: {response.text}"}

    except requests.exceptions.Timeout:
        return {"error": "요청 시간이 초과되었습니다 (180초). 엔드포인트가 응답하지 않습니다."}
    except Exception as e:
        return {"error": str(e)}


def display_inference_mode():
    """실제 추론 모드 UI"""
    st.markdown("### 🚀 실제 추론 모드")

    # deployment_info.json 자동 로드
    deployment_info_path = Path(__file__).parent.parent / "deployment_info.json"
    auto_loaded = False

    if deployment_info_path.exists():
        with open(deployment_info_path) as f:
            deployment_info = json.load(f)

        st.success(f"✅ 배포 정보 자동 로드됨 (배포일: {deployment_info.get('deployed_at', 'N/A')})")

        endpoint_id = deployment_info.get("endpoint_id", "")
        project = deployment_info.get("project_id", "knu-team-03")
        region = deployment_info.get("region", "us-central1")
        auto_loaded = True

    else:
        st.warning("⚠️ deployment_info.json을 찾을 수 없습니다. 수동으로 입력하세요.")

        col1, col2 = st.columns(2)
        with col1:
            project = st.text_input("Project ID", value="knu-team-03")
        with col2:
            region = st.text_input("Region", value="us-central1")

        endpoint_id = st.text_input(
            "Endpoint ID",
            placeholder="2283851677146546176",
            help="숫자만 입력 (전체 리소스 이름 불필요)"
        )

    if not endpoint_id:
        st.info("Endpoint ID를 입력하면 실제 모델과 대화할 수 있습니다.")
        return

    st.markdown("---")

    # 입력 폼
    col1, col2 = st.columns([1, 3])

    with col1:
        context = st.selectbox(
            "작품 선택",
            ["춘향전", "심청전", "흥부전", "홍길동전", "구운몽", "사씨남정기", "한국사", "기타"],
            index=0
        )

        if context == "기타":
            context = st.text_input("작품명 입력")

        max_tokens = st.slider("최대 토큰 수", 128, 1024, 512, 128)
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)

    with col2:
        student_question = st.text_area(
            "학생 질문",
            placeholder="예: 춘향전에서 이몽룡이 신분을 숨긴 이유가 뭔가요?",
            height=150
        )

    if st.button("💬 질문하기", use_container_width=True, type="primary"):
        if not student_question:
            st.warning("질문을 입력해주세요.")
            return

        with st.spinner("🤔 AI 교사가 생각하고 있습니다..."):
            result = call_vertex_ai_endpoint(
                endpoint_id=endpoint_id,
                project=project,
                region=region,
                question=student_question,
                context=context,
                max_tokens=max_tokens,
                temperature=temperature
            )

        if result.get("success"):
            st.markdown("---")
            st.markdown("### 🤖 AI 교사 응답")

            answer = result["answer"]
            st.markdown(answer)

            # 분석
            st.markdown("---")
            st.markdown("### 📊 응답 분석")

            col1, col2, col3, col4 = st.columns(4)

            has_induction = "[사고유도]" in answer
            has_log = "[사고로그]" in answer
            question_count = answer.count("?") + answer.count("까요")

            with col1:
                if has_induction:
                    st.success("✅ [사고유도]")
                else:
                    st.error("❌ [사고유도]")

            with col2:
                if has_log:
                    st.success("✅ [사고로그]")
                else:
                    st.error("❌ [사고로그]")

            with col3:
                st.metric("질문 수", f"{question_count}개")

            with col4:
                usage = result.get("usage", {})
                total_tokens = usage.get("total_tokens", 0)
                st.metric("총 토큰", total_tokens)

            # 토큰 사용량 상세
            with st.expander("📊 토큰 사용량 상세"):
                st.json(usage)

        else:
            st.error(f"❌ 오류: {result.get('error', '알 수 없는 오류')}")
            st.info("gcloud 인증을 확인하세요: `gcloud auth login`")


# ============================================================
# 메인
# ============================================================

def main():
    """메인 함수"""

    # 모드별 UI 표시
    if "시뮬레이션" in mode:
        display_simulation_mode()
    else:
        display_inference_mode()

    # 푸터
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>고전문학 사고유도 AI 교사 | Gemma 2 9B-IT + LoRA</p>
        <p>KNU Team 03 | 2026-02</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
