"""
QuestionGenerator 실제 사용 예시
"""
import sys
import os
import logging
logging.basicConfig(level=logging.WARNING)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.logic.generator import QuestionGenerator


def demo():
    print("=" * 70)
    print("QuestionGenerator 개선 버전 데모")
    print("=" * 70)
    
    # 1. 기본 질문 생성
    print("\n1. 기본 질문 생성")
    print("-" * 70)
    gen = QuestionGenerator()
    
    nodes = [
        {"text": "기후 변화는 현대 사회의 가장 심각한 문제 중 하나이다", "roles": ["claim"]},
        {"text": "연구 결과에 따르면 지구 온도가 계속 상승하고 있다", "roles": ["evidence"]},
        {"text": "산업화로 인한 온실가스 배출이 주요 원인이다", "roles": ["cause"]},
        {"text": "이로 인해 극한 기후 현상이 빈번해지고 있다", "roles": ["result"]},
    ]
    
    for i, node in enumerate(nodes, 1):
        q = gen.generate(node)
        print(f"{i}. [{node['roles'][0].upper()}] {q}")
    
    # 2. 시드 재현성 테스트
    print("\n\n2. 시드로 재현 가능한 질문 생성")
    print("-" * 70)
    
    gen1 = QuestionGenerator(seed=100)
    gen2 = QuestionGenerator(seed=100)
    
    node = {"text": "인공지능은 산업 혁명을 가져올 것이다", "roles": ["claim"]}
    
    q1 = gen1.generate(node)
    q2 = gen2.generate(node)
    
    print(f"Generator 1: {q1}")
    print(f"Generator 2: {q2}")
    print(f"동일 여부: {'✅ 같음' if q1 == q2 else '❌ 다름'}")
    
    # 3. 복합명사 추출 테스트
    print("\n\n3. 개선된 엔티티 추출 (복합명사)")
    print("-" * 70)
    
    gen3 = QuestionGenerator(seed=200)
    texts = [
        "기후 변화는 심각하다",
        "인공 지능의 발전이 빠르다",
        "사회 구조가 바뀌고 있다",
    ]
    
    for text in texts:
        entity = gen3._extract_entity(text)
        print(f"텍스트: '{text}' → 엔티티: '{entity}'")
    
    # 4. 피드백 생성
    print("\n\n4. 피드백 생성")
    print("-" * 70)
    
    gen4 = QuestionGenerator(seed=300)
    node = {"text": "환경 보호가 중요하다"}
    
    # Pass
    eval_pass = {"is_passed": True}
    fb_pass = gen4.generate_feedback_question(eval_pass, node=node)
    print(f"✅ Pass: {fb_pass}")
    
    # Contradiction
    eval_contra = {"is_passed": False, "nli_label": "contradiction"}
    fb_contra = gen4.generate_feedback_question(eval_contra, node=node)
    print(f"❌ Contradiction: {fb_contra}")
    
    # Short answer
    eval_short = {"is_passed": False, "user_answer": "응"}
    fb_short = gen4.generate_feedback_question(eval_short, node=node)
    print(f"📝 Too Short: {fb_short}")
    
    # 5. 히스토리 관리
    print("\n\n5. 히스토리 관리 (중복 방지)")
    print("-" * 70)
    
    gen5 = QuestionGenerator(seed=400)
    node = {"text": "기술 발전이 사회를 변화시킨다", "roles": ["claim"]}
    
    questions = [gen5.generate(node) for _ in range(5)]
    unique = len(set(questions))
    
    print(f"5번 생성 중 고유한 질문: {unique}개")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q}")
    
    print("\n" + "=" * 70)
    print("데모 완료!")
    print("=" * 70)


if __name__ == "__main__":
    demo()
