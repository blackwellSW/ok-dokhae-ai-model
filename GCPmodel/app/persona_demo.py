#!/usr/bin/env python3
"""
페르소나 시스템 Streamlit 데모

로컬 테스트용 (모델 없이 프롬프트만 확인)
"""

import streamlit as st
import json
import os

# 페이지 설정
st.set_page_config(
    page_title="고전문학 AI 튜터 - 페르소나 데모",
    page_icon="📚",
    layout="wide"
)

# 페르소나 로드
@st.cache_data
def load_personas():
    personas_file = os.path.join(os.path.dirname(__file__), "..", "deployment", "personas.json")
    with open(personas_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data["personas"]


def main():
    st.title("📚 고전문학 AI 튜터 - 페르소나 시스템")
    st.markdown("---")

    # 페르소나 로드
    personas = load_personas()

    # 사이드바 - 페르소나 선택
    with st.sidebar:
        st.header("🎭 선생님 선택")

        # 페르소나 카테고리
        categories = {
            "조선시대 문인": ["정철", "정약용", "허균", "신사임당", "이황"],
            "현대 교육 스타일": ["엄격한_훈장", "친근한_선생님", "유머러스_멘토"],
            "기본": ["default"]
        }

        selected_persona = None
        for category, persona_ids in categories.items():
            st.subheader(f"📖 {category}")
            for pid in persona_ids:
                persona = personas[pid]
                if st.button(
                    f"{persona['name']}",
                    key=f"btn_{pid}",
                    use_container_width=True
                ):
                    selected_persona = pid

        st.markdown("---")
        st.markdown("### ⚙️ 설정")
        max_tokens = st.slider("응답 길이", 100, 1000, 512, 50)
        temperature = st.slider("창의성", 0.0, 1.0, 0.7, 0.1)

    # 메인 영역
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("💬 질문하기")

        # 페르소나 선택 (버튼으로 선택 안했으면 드롭다운)
        if 'selected_persona' not in st.session_state:
            st.session_state.selected_persona = "default"

        if selected_persona:
            st.session_state.selected_persona = selected_persona

        current_persona = personas[st.session_state.selected_persona]

        # 현재 선택된 페르소나 표시
        st.info(f"**선택된 선생님:** {current_persona['name']}")
        if current_persona.get('era'):
            st.caption(f"시대: {current_persona['era']}")
        if current_persona.get('greeting'):
            st.success(f"💬 \"{current_persona['greeting']}\"")

        # 지문 입력 (선택사항)
        with st.expander("📄 지문 추가 (선택사항)"):
            context = st.text_area(
                "고전 작품 지문",
                placeholder="예: 춘향전, 홍길동전 등의 지문을 입력하세요",
                height=150
            )

        # 질문 입력
        question = st.text_area(
            "질문을 입력하세요",
            placeholder="예: 춘향전의 주제가 무엇인가요?",
            height=100
        )

        # 예시 질문 버튼
        st.markdown("**📝 예시 질문:**")
        example_questions = [
            "춘향전의 주제가 무엇인가요?",
            "사씨남정기에서 교산의 역할은?",
            "관동별곡에 나타난 자연 묘사를 설명해주세요",
            "홍길동전이 가진 사회 비판적 의미는?"
        ]

        cols = st.columns(2)
        for i, eq in enumerate(example_questions):
            with cols[i % 2]:
                if st.button(eq, key=f"example_{i}"):
                    question = eq

        # 질문 버튼
        if st.button("🤔 질문하기", type="primary", use_container_width=True):
            if not question:
                st.error("질문을 입력해주세요!")
            else:
                # 실제로는 API 호출, 여기서는 프롬프트만 표시
                st.session_state.last_question = question
                st.session_state.last_context = context if context else ""
                st.session_state.show_result = True

    with col2:
        st.header("🎓 프롬프트 미리보기")

        if 'show_result' in st.session_state and st.session_state.show_result:
            persona = personas[st.session_state.selected_persona]
            question = st.session_state.last_question
            context = st.session_state.last_context

            st.subheader(f"📌 {persona['name']} 선생님")

            # 시스템 프롬프트 표시
            with st.expander("🧠 시스템 프롬프트 (모델에 주입됨)", expanded=True):
                st.code(persona['system_prompt'], language="text")

            # 전체 프롬프트 구성
            st.subheader("📜 전체 프롬프트")

            if context:
                full_prompt = f"""<start_of_turn>system
{persona['system_prompt']}<end_of_turn>
<start_of_turn>user
다음 지문을 읽고 질문에 답하세요.

[작품: {context}]
{question}<end_of_turn>
<start_of_turn>model
"""
            else:
                full_prompt = f"""<start_of_turn>system
{persona['system_prompt']}<end_of_turn>
<start_of_turn>user
{question}<end_of_turn>
<start_of_turn>model
"""

            st.code(full_prompt, language="text")

            # 예상 응답 스타일 설명
            st.subheader("💡 예상 응답 스타일")
            st.info(persona.get('description', ''))

            # API 호출 예시
            with st.expander("🔌 API 호출 예시 (개발자용)"):
                api_payload = {
                    "instances": [
                        {
                            "student_input": question,
                            "context": context if context else "",
                            "persona": st.session_state.selected_persona,
                            "max_new_tokens": max_tokens,
                            "temperature": temperature
                        }
                    ]
                }
                st.json(api_payload)

                st.code(f"""
# Python 예시
import requests

response = requests.post(
    'https://your-endpoint/predict',
    json={api_payload}
)
result = response.json()
print(result['predictions'][0]['response'])
                """, language="python")
        else:
            st.info("👈 왼쪽에서 질문을 입력하고 '질문하기'를 눌러보세요!")

    # 하단 정보
    st.markdown("---")
    with st.expander("ℹ️ 페르소나 시스템 정보"):
        st.markdown("""
        ### 🎭 페르소나 시스템이란?

        - **조선시대 문인 5명**: 정철, 정약용, 허균, 신사임당, 이황
        - **현대 교육 스타일 3명**: 엄격한 훈장, 친근한 선생님, 유머러스 멘토

        각 페르소나는 고유한 교육 스타일과 말투를 가지고 있어, 학생의 선호에 맞는
        선생님을 선택할 수 있습니다.

        ### 🔧 작동 방식

        1. 페르소나별 `system_prompt`가 모델에 주입됨
        2. 모델은 해당 페르소나의 스타일로 응답 생성
        3. [사고유도]와 [사고로그] 태그를 사용하되, 페르소나 특성 반영

        ### 📊 현재 상태

        - ✅ 페르소나 정의 완료
        - ✅ API 구현 완료
        - ⏳ 실제 모델 배포 대기 중
        """)

        st.markdown("### 📋 전체 페르소나 목록")
        for pid, persona in personas.items():
            st.markdown(f"""
            **{persona['name']}** (`{pid}`)
            - 시대: {persona.get('era', 'N/A')}
            - 특징: {persona.get('description', 'N/A')}
            - 인사말: _{persona.get('greeting', 'N/A')}_
            """)


if __name__ == "__main__":
    main()
