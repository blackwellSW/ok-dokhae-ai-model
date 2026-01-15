"""
피드백 우선순위 변경 테스트
"""
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logic.generator import QuestionGenerator

def test_feedback_priority():
    gen = QuestionGenerator(seed=42)
    node = {"text": "테스트 문장입니다."}
    
    # 상황: 답변이 정답(Pass)이지만, 길이가 1글자('네')인 경우
    # 기대: length_short 피드백이 나와야 함 (우선순위 변경됨)
    evaluation = {
        "is_passed": True,       # 정답임
        "user_answer": "네",     # 하지만 너무 짧음 (<= 3)
        "nli_label": "entailment" 
    }
    
    feedback = gen.generate_feedback_question(evaluation, node=node)
    
    print(f"답변: '{evaluation['user_answer']}'")
    print(f"평가 결과: Passed? {evaluation['is_passed']}")
    print(f"생성된 피드백: {feedback}")
    
    # 검증: length_short 템플릿 중 하나인지 확인
    short_templates = gen.feedback_templates["length_short"]
    if feedback in short_templates:
        print("\n✅ 테스트 성공: 정답이어도 답변이 짧아서 '길이 부족' 피드백이 생성되었습니다.")
    else:
        print("\n❌ 테스트 실패: 예상치 못한 피드백이 생성되었습니다.")
        
    # 상황 2: 답변이 길고 정답인 경우
    evaluation2 = {
        "is_passed": True,
        "user_answer": "네, 그 부분은 확실히 동의합니다.",  # 10글자 이상
        "nli_label": "entailment"
    }
    feedback2 = gen.generate_feedback_question(evaluation2, node=node)
    
    print(f"\n답변: '{evaluation2['user_answer']}'")
    print(f"생성된 피드백: {feedback2}")
    
    pass_templates = gen.feedback_templates["pass"]
    if feedback2 in pass_templates:
         print("✅ 테스트 성공: 답변이 길어서 'Pass' 피드백이 생성되었습니다.")

    # 상황 3: 무의미한 입력 (Gibberish)
    print("\n[테스트 3: 무의미한 입력]")
    gibberish_inputs = ["ddddddd", "ㅋㅋㅋㅋㅋ", "......"]
    
    for inputs in gibberish_inputs:
        evaluation3 = {
            "is_passed": False,
            "user_answer": inputs,
            "sts_score": 0.1
        }
        feedback3 = gen.generate_feedback_question(evaluation3, node=node)
        print(f"입력: '{inputs}' -> 피드백: {feedback3}")
        
        # off_topic 템플릿인지 확인
        off_topic_templates = gen.feedback_templates["off_topic"]
        # 템플릿 포맷팅 때문에 정확한 매칭은 어려울 수 있으니, 템플릿의 일부 문구가 포함되어 있는지 확인
        # (실제로는 _safe_format을 거치므로 텍스트가 변형될 수 있음)
        
        # 템플릿 중 하나와 유사한지 확인 (간단히 첫 10글자 비교)
        is_off_topic = False
        for t in off_topic_templates:
            # {question} 같은게 있어서 포맷팅 전 템플릿과 비교는 어려움.
            # 하지만 현재 off_topic 템플릿은 비교적 고유함.
            pass
            
        # "질문과 조금 다른", "원래 질문으로", "잠시 길을 잃은" 등이 포함되어야 함
        keywords = ["질문과 조금 다른", "원래 질문으로", "잠시 길을 잃은", "대해 생각해 볼까요", "집중해 볼까요", "답변도 일리가 있지만", "답을 찾아보는 건 어떨까요"]
        if any(k in feedback3 for k in keywords):
            print(f"✅ Gibberish 감지 성공 (Off-topic 처리됨)")
        else:
             print(f"❌ 실패? 예상 밖의 피드백: {feedback3}")

if __name__ == "__main__":
    test_feedback_priority()
