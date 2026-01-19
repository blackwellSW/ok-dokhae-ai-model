import sys
import os
import json
import random
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가하여 패키지 임포트 문제 해결
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

try:
    from sentence_transformers import util as st_util
except Exception:
    st_util = None

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
    samples_path = repo_root / "data" / "processed" / "cleaned_contexts.json"
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
            if sample.get("processed_sentences"):
                text = "\n".join(sample["processed_sentences"])
            else:
                text = sample.get("context", sample.get("sentence1", ""))
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
        
        # DEBUG: show key nodes
        print("\n[DEBUG] Key nodes selected:")
        for n in key_nodes:
            print(f"- idx={n['index']} score={n.get('score')} roles={n['roles']} text={n['text'][:100]}")
        print()
        # DEBUG END

        # 4. 질문 및 답변 루프 (첫 번째 핵심 노드 대상)
        target_node = key_nodes[0]
        question = generator.generate(target_node)

        print(f"\nAI 질문: {question}")
        user_answer = input("당신의 답변: ")

        # 5. 평가
        print("\n[AI 평가 중...]")
        role = generator.get_primary_role(target_node)

        # DEBUG: evaluator readiness + policy
        policy = evaluator.ROLE_POLICY.get(role, evaluator.ROLE_POLICY["general"])
        print("\n[DEBUG] Evaluator status:")
        print(f"- role={role}")
        print(f"- NLI model loaded? {evaluator.nli_model is not None}")
        print(f"- policy: unit_sim_th={policy['unit_sim_th']} pass_th={policy['pass_th']} w_cov={policy['w_cov']} w_sts={policy['w_sts']}")
        # DEBUG END

        result = evaluator.evaluate_answer(user_answer, target_node["text"], role=role)

        # DEBUG: show logic units + similarity + coverage reconstruction
        print("\n[DEBUG] Evaluation details:")
        print(f"- sts_score={result.get('sts_score')}, coverage_score={result.get('coverage_score')}, final_score={result.get('final_score')}, passed={result.get('is_passed')}")
        print(f"- nli_label={result.get('nli_label')} nli_conf={result.get('nli_confidence')}")

        logic_units_info = evaluator._get_weighted_logic_units(target_node["text"])
        unit_texts = [info["text"] for info in logic_units_info]
        unit_weights = [info["weight"] for info in logic_units_info]

        print(f"- logic_units: {len(unit_texts)} units")
        for i, info in enumerate(logic_units_info):
            print(f"  * unit[{i}] w={info['weight']:.1f} text={info['text'][:80]}")

        # Similarity + coverage reconstruction (to see what's being counted)
        covered_units = []
        if st_util is None:
            print("  [WARN] sentence_transformers.util not available in run_demo.py, skipping unit similarity debug.")
        else:
            try:
                ans_emb = evaluator.sts_model.encode(user_answer.strip(), convert_to_tensor=True)
                unit_embs = evaluator.sts_model.encode(unit_texts, convert_to_tensor=True)
                sims = st_util.cos_sim(unit_embs, ans_emb).flatten().tolist()

                th = policy["unit_sim_th"]
                total_w = sum(unit_weights) if unit_weights else 0.0
                covered_w = 0.0

                # show top matches
                ranked = sorted(list(enumerate(sims)), key=lambda x: x[1], reverse=True)
                print(f"- unit_sim_th={th} (coverage threshold)")
                print("- top unit matches:")
                for rank, (idx, sim) in enumerate(ranked[: min(8, len(ranked))], start=1):
                    mark = "COVER" if sim > th else "----"
                    print(f"  {rank:>2}. [{mark}] sim={sim:.3f} w={unit_weights[idx]:.1f} text={unit_texts[idx][:80]}")

                # compute covered units
                for i, sim in enumerate(sims):
                    if sim > th:
                        covered_w += unit_weights[i]
                        covered_units.append(unit_texts[i])

                cov = (covered_w / total_w) if total_w > 0 else 1.0
                print(f"- reconstructed_coverage={cov:.3f} (covered_weight={covered_w:.2f} / total_weight={total_w:.2f})")

                # important missing check (mirrors evaluator logic)
                important_missing = [
                    info["text"] for info in logic_units_info
                    if info["weight"] >= 1.4 and info["text"] not in covered_units
                ]
                if important_missing:
                    print(f"- important_missing (w>=1.4): {len(important_missing)}")
                    print(f"  -> example: {important_missing[0][:120]}")
                else:
                    print("- important_missing (w>=1.4): none")

            except Exception as e:
                print(f"  [WARN] unit similarity debug failed: {e}")

        print("[DEBUG END]\n")
        # DEBUG END
        feedback = generator.generate_feedback_question(
            result,
            original_question=question, 
            node=target_node,
        )

        print("\n" + "="*30)
        print(f"결과: {'성공!' if result['is_passed'] else '보완 필요'}")
        print(f"유사도 점수: {result['sts_score']:.2f}")
        print(f"논리적 관계: {result['nli_label']} ({result['nli_confidence']:.2f})")
        print(f"AI 피드백: {feedback}")
        print("="*30)

        input("\n계속하려면 엔터를 누르세요...")

if __name__ == "__main__":
    run_cli_demo()
