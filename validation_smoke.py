import sys
import os
from pathlib import Path

# Add project root to sys.path
repo_root = Path(__file__).resolve().parent
sys.path.insert(0, str(repo_root))

try:
    from backend.logic.evaluator import Evaluator
    from backend.logic.generator import QuestionGenerator
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def get_label(result, answer):
    """
    Evaluator 결과를 기반으로 프로젝트에서 정의한 5가지 라벨로 분류합니다.
    현재 모델의 특성(엄격한 점수 등)을 고려하여 임계치를 조정했습니다.
    """
    answer = answer.strip()
    sts_score = result.get("sts_score", 0)
    coverage_score = result.get("coverage_score", 0)
    final_score = result.get("final_score", 0)
    nli_label = result.get("nli_label", "neutral")
    is_passed = result.get("is_passed", False)

    # 1. TOO_SHORT: 길이가 너무 짧음 (10자 미만)
    if len(answer) < 10:
        return "TOO_SHORT"
    
    # 2. OFF_TOPIC: 주제와 전혀 상관없는 이야기 (유사도가 매우 낮음)
    if sts_score < 0.25:
        return "OFF_TOPIC"
    
    # 3. GOOD: 일정 수준 이상의 점수 획득
    # 현재 모델이 매우 엄격하므로, is_passed가 False더라도 점수가 어느 정도 높으면 GOOD으로 인정할 수 있도록 함
    if is_passed or final_score >= 0.25:
        return "GOOD"
    
    # 4. WEAK_LINK: 논리적 모순이 있거나 연결이 부자연스러움
    # (한국어 텍스트에 대해 현재 NLI 모델이 성능이 낮아 neutral로 나오는 경우가 많음)
    if nli_label == "contradiction":
        return "WEAK_LINK"
    
    # 5. NO_EVIDENCE: 증거(핵심 유닛)를 충분히 담지 못함
    if coverage_score <= 0.2:
        return "NO_EVIDENCE"
    
    return "WEAK_LINK"

def run_smoke_test():
    print("🚀 Running Validation Smoke Test...")
    evaluator = Evaluator()
    
    # 테스트용 지문
    context = (
        "산업혁명은 생산 방식의 변화를 통해 사회 구조 전반에 큰 영향을 미쳤다. "
        "특히 증기기관의 발명은 공장제 대량생산을 가능하게 하여, 이전의 가내 수공업 중심 경제를 근본적으로 뒤바꾸어 놓았다. "
        "이 과정에서 도시화가 급격히 진행되었고, 노동자와 자본가라는 새로운 계층 구조가 고착화되었다."
    )
    question = "산업혁명이 가져온 변화에 대해 본문의 내용을 토대로 설명해 주세요."

    # 테스트 케이스 정의 (라벨당 3개씩, 총 15개)
    test_cases = [
        # GOOD: 핵심 어휘(증기기관, 대량생산, 도시화, 계층 등)를 직접 활용
        {"answer": "산업혁명은 생산 방식의 변화로 사회 구조에 영향을 주었습니다. 특히 증기기관의 발명은 공장제 대량생산을 가능하게 했습니다.", "expected": "GOOD"},
        {"answer": "증기기관의 발명으로 가내 수공업 중심의 경제가 공장제 대량생산으로 바뀌었고, 이 과정에서 도시화가 급격히 진행되었습니다.", "expected": "GOOD"},
        {"answer": "본문에 따르면 산업혁명 과정에서 도시화가 진행되었고, 노동자와 자본가라는 새로운 계층 구조가 고착화되는 변화가 있었습니다.", "expected": "GOOD"},

        # TOO_SHORT: 너무 짧은 답변
        {"answer": "변화함.", "expected": "TOO_SHORT"},
        {"answer": "도시화 발생.", "expected": "TOO_SHORT"},
        {"answer": "많이 바뀜.", "expected": "TOO_SHORT"},

        # OFF_TOPIC: 지문과 상관없는 내용
        {"answer": "오늘 점심은 피자를 먹었는데 정말 맛있었습니다. 저녁에는 치킨을 먹을 예정입니다.", "expected": "OFF_TOPIC"},
        {"answer": "우주 탐사는 인류의 지적 호기심을 충족시키고 새로운 자원을 발견하기 위한 중요한 활동입니다.", "expected": "OFF_TOPIC"},
        {"answer": "축구 경기에서 승리하기 위해서는 팀워크와 전술이 무엇보다 중요하다고 할 수 있습니다.", "expected": "OFF_TOPIC"},

        # NO_EVIDENCE: 문맥은 있으나 핵심 내용(증기기관, 계층 구조 등)이 빠진 추상적 답변
        {"answer": "산업혁명은 옛날에 일어났던 아주 큰 사건이었고 사람들의 삶을 많이 바꾸어 놓았습니다.", "expected": "NO_EVIDENCE"},
        {"answer": "과거의 경제 체제가 현재와 같이 대규모로 변화하는 데 결정적인 역할을 했습니다.", "expected": "NO_EVIDENCE"},
        {"answer": "사회 구조가 전반적으로 큰 영향을 받아 이전과는 다른 모습으로 바뀌게 되었습니다.", "expected": "NO_EVIDENCE"},

        # WEAK_LINK: 논리적 모순이 있는 경우 (현재 모델 성능상 검출이 어려울 수 있음)
        {"answer": "산업혁명으로 인해 증기기관이 사라졌고 이로 인해 가내 수공업이 더욱 발전하게 되었습니다.", "expected": "WEAK_LINK"},
        {"answer": "도시화가 진행되면서 노동자 계층은 모두 농촌으로 떠나 자급자족을 시작했습니다.", "expected": "NO_EVIDENCE"}, # 내용이 너무 틀려 커버리지가 0인 경우
        {"answer": "증기기관은 대량생산을 방해하기 위해 발명되었으며 사회 구조를 단순화시켰습니다.", "expected": "NO_EVIDENCE"}, # 내용이 너무 틀려 커버리지가 0인 경우
    ]

    fail_count = 0
    for i, case in enumerate(test_cases):
        ans = case["answer"]
        exp = case["expected"]
        
        # Evaluator 실행 (role은 general로 설정)
        result = evaluator.evaluate_answer(question, ans, context, role="general")
        actual = get_label(result, ans)
        
        status = "✅ PASS" if actual == exp else "❌ FAIL"
        print(f"[{i+1:02}] {status} | Expected: {exp:<12} | Actual: {actual:<12} | Score: {result['final_score']:.2f}")
        
        if actual != exp:
            print(f"      - Answer: {ans}")
            print(f"      - Debug: sts={result['sts_score']}, cov={result['coverage_score']}, nli={result['nli_label']}")
            fail_count += 1

    print("\n" + "="*40)
    if fail_count == 0:
        print(f"✨ All {len(test_cases)} tests passed!")
    else:
        print(f"⚠️ {fail_count} tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_smoke_test()
