import sys
import os
import json
import random
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가하여 패키지 임포트 문제 해결
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

try:
    from backend.logic.analyzer import LogicAnalyzer
    from backend.logic.evaluator import Evaluator
    from backend.logic.generator import QuestionGenerator
except ImportError as e:
    print(f"임포트 에러: {e}")
    print("패키지 구조를 확인해주세요.")
    sys.exit(1)

def run_cli_demo():
    print("="*50)
    print("옥독해(OK-DOK-HAE) 터미널 데모 모드")
    print("="*50)

    # 1. 인스턴스 초기화
    print("모델 및 분석기 초기화 중... (최초 실행 시 시간이 걸릴 수 있습니다)")
    analyzer = LogicAnalyzer()
    evaluator = Evaluator()
    generator = QuestionGenerator()
    print("초기화 완료!\n")

    # 2. 데이터셋 로드
    samples_path = repo_root / "backend" / "data" / "samples.json"
    if not samples_path.exists():
        print("에러: samples.json 파일을 찾을 수 없습니다. fetch_data.py를 먼저 실행해주세요.")
        return

    with samples_path.open('r', encoding='utf-8') as f:
        samples = json.load(f)

    while True:
        print("\n[메뉴] 1. 무작위 샘플 진행 | 2. 직접 텍스트 입력 | 3. 종료")
        choice = input("선택: ")

        if choice == '3':
            break
        
        text = ""
        if choice == '1':
            sample = random.choice(samples)
            text = sample.get('context', sample.get('sentence1', ''))
            print(f"\n[선택된 샘플 소스: {sample.get('source')}]")
        else:
            text = input("\n분석할 텍스트를 입력하세요: ")

        if not text:
            continue

        print("\n" + "-"*30)
        print("본문 내용:")
        print(text)
        print("-"*30)

        # 3. 분석 시작
        print("\n[AI 분석 중...]")
        nodes = analyzer.analyze(text)
        key_nodes = [n for n in nodes if n['is_key_node']]
        
        if not key_nodes:
            print("핵심 노드를 찾지 못했습니다. 일반 문장으로 진행합니다.")
            key_nodes = nodes[:1]

        # 4. 질문 및 답변 루프 (첫 번째 핵심 노드 대상)
        target_node = key_nodes[0]
        question = generator.generate(target_node)

        print(f"\nAI 질문: {question}")
        user_answer = input("당신의 답변: ")

        # 5. 평가
        print("\n[AI 평가 중...]")
        result = evaluator.evaluate_answer(user_answer, target_node['text'])

        print("\n" + "="*30)
        print(f"결과: {'성공!' if result['is_passed'] else '보완 필요'}")
        print(f"유사도 점수: {result['sts_score']:.2f}")
        print(f"논리적 관계: {result['nli_label']} ({result['nli_confidence']:.2f})")
        print(f"AI 피드백: {result['feedback']}")
        print("="*30)

        input("\n계속하려면 엔터를 누르세요...")

if __name__ == "__main__":
    run_cli_demo()
