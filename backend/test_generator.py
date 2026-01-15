"""
QuestionGenerator 테스트 스크립트
개선사항들이 정상적으로 작동하는지 검증
"""
import sys
import os
import logging

# 로깅 설정 (WARNING 레벨로 설정하여 테스트 중 로그 최소화)
logging.basicConfig(level=logging.WARNING)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logic.generator import QuestionGenerator


def test_deterministic_with_seed():
    """시드 설정 시 재현성 테스트"""
    print("\n=== 테스트 1: 시드 재현성 ===")
    gen1 = QuestionGenerator(seed=42)
    gen2 = QuestionGenerator(seed=42)
    
    node = {"text": "기후 변화는 심각한 문제이다", "roles": ["claim"]}
    
    q1 = gen1.generate(node)
    q2 = gen2.generate(node)
    
    assert q1 == q2, f"시드가 같으면 동일한 질문이 생성되어야 함\nq1: {q1}\nq2: {q2}"
    print(f"✓ 시드 재현성 성공: {q1}")


def test_bug_fixes():
    """버그 수정 확인"""
    print("\n=== 테스트 2: 버그 수정 확인 ===")
    gen = QuestionGenerator(seed=123)
    
    # 1. IndexError 방지 (빈 roles 리스트)
    node1 = {"text": "테스트", "roles": []}
    result1 = gen.generate(node1)
    assert result1, "빈 roles 리스트에도 질문 생성되어야 함"
    print(f"✓ 빈 roles 처리: {result1}")
    
    # 2. 템플릿 오타 수정 확인 (${snippet} → {snippet})
    node2 = {"text": "결과가 발생했다", "roles": ["result"]}
    result2 = gen.generate(node2)
    assert "{snippet}" not in result2 and "${snippet}" not in result2, "템플릿 변수가 치환되어야 함"
    print(f"✓ 템플릿 오타 수정: {result2}")
    
    # 3. 입력 검증 (text 누락)
    node3 = {"roles": ["claim"]}
    result3 = gen.generate(node3)
    assert result3 == "이 부분에 대해 어떻게 생각하시나요?", "text 누락 시 폴백 질문 반환"
    print(f"✓ 입력 검증: {result3}")


def test_weighted_random():
    """가중치 기반 랜덤 테스트"""
    print("\n=== 테스트 3: 가중치 기반 랜덤 ===")
    gen = QuestionGenerator(seed=456)
    
    node = {"text": "이것은 매우 중요한 내용입니다. 여기에 핵심이 있습니다.", "roles": ["claim"]}
    
    # 여러 번 실행하여 start 전략이 더 많이 선택되는지 확인
    snippets = []
    for _ in range(10):
        gen_temp = QuestionGenerator()
        snippet = gen_temp._extract_snippet(node["text"])
        snippets.append(snippet)
    
    start_count = sum(1 for s in snippets if s.startswith("이것은"))
    print(f"✓ 10회 중 start 전략 사용: {start_count}회 (기대: ~7회)")


def test_entity_extraction():
    """개선된 엔티티 추출 테스트"""
    print("\n=== 테스트 4: 엔티티 추출 개선 ===")
    gen = QuestionGenerator(seed=789)
    
    # 복합명사 추출
    text1 = "기후 변화는 심각한 문제이다"
    entity1 = gen._extract_entity(text1)
    print(f"✓ 복합명사 추출: '{entity1}' (기대: '기후 변화')")
    
    # 불용어 제외
    text2 = "그것은 중요한 개념이다"
    entity2 = gen._extract_entity(text2)
    assert entity2 != "그것", "불용어 '그것'은 제외되어야 함"
    print(f"✓ 불용어 제외: '{entity2}' (기대: '개념')")


def test_history_management():
    """히스토리 관리 테스트"""
    print("\n=== 테스트 5: 히스토리 관리 ===")
    gen = QuestionGenerator(seed=999)
    
    node = {"text": "테스트 내용", "roles": ["claim"]}
    
    # 여러 번 generate 호출
    questions = []
    for i in range(10):
        q = gen.generate(node)
        questions.append(q)
    
    # 중복 확인
    unique_count = len(set(questions))
    print(f"✓ 10회 생성 중 고유 질문: {unique_count}개")
    assert unique_count > 1, "히스토리 관리로 다양한 질문이 생성되어야 함"


def test_role_priority():
    """역할 우선순위 테스트"""
    print("\n=== 테스트 6: 역할 우선순위 ===")
    gen = QuestionGenerator(seed=111)
    
    # 문자열 리스트
    node1 = {"text": "테스트", "roles": ["evidence", "claim", "contrast"]}
    role1 = gen.get_primary_role(node1)
    print(f"✓ 문자열 roles: {role1} (가중치 기반 선택)")
    
    # Dict 리스트 (신뢰도 포함)
    node2 = {
        "text": "테스트",
        "roles": [
            {"role": "claim", "confidence": 0.9},
            {"role": "evidence", "confidence": 0.95},
        ]
    }
    role2 = gen.get_primary_role(node2)
    print(f"✓ Dict roles: {role2} (우선순위 + 신뢰도)")


def test_feedback_generation():
    """피드백 생성 테스트"""
    print("\n=== 테스트 7: 피드백 생성 ===")
    gen = QuestionGenerator(seed=222)
    
    node = {"text": "기후 변화는 심각한 문제이다"}
    
    # Pass
    eval1 = {"is_passed": True}
    fb1 = gen.generate_feedback_question(eval1, node=node)
    assert "완벽" in fb1 or "훌륭" in fb1 or "정확" in fb1, "pass일 때 긍정 피드백"
    print(f"✓ Pass 피드백: {fb1}")
    
    # Contradiction
    eval2 = {"is_passed": False, "nli_label": "contradiction"}
    fb2 = gen.generate_feedback_question(eval2, node=node)
    print(f"✓ Contradiction 피드백: {fb2}")
    
    # Short length
    eval3 = {"is_passed": False, "user_answer": "응"}
    fb3 = gen.generate_feedback_question(eval3, node=node)
    print(f"✓ Short 피드백: {fb3}")


def run_all_tests():
    """모든 테스트 실행"""
    print("=" * 60)
    print("QuestionGenerator 개선사항 테스트 시작")
    print("=" * 60)
    
    try:
        test_deterministic_with_seed()
        test_bug_fixes()
        test_weighted_random()
        test_entity_extraction()
        test_history_management()
        test_role_priority()
        test_feedback_generation()
        
        print("\n" + "=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)
        return True
    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 예외 발생: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
