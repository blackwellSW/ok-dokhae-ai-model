import sys
import json
import random
from pathlib import Path

# 프로젝트 루트 경로를 sys.path에 추가하여 패키지 임포트 문제 해결
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

try:
    from backend.logic.analyzer import LogicAnalyzer
    from backend.logic.evaluator import Evaluator
except ImportError as e:
    print(f"임포트 에러: {e}")
    print("패키지 구조를 확인해주세요.")
    sys.exit(1)

def pick_candidates(nodes, types, top_k=5):
    cand = [n for n in nodes if n.get("type") in types]
    cand = sorted(cand, key=lambda x: x.get("score", 0), reverse=True)
    return cand[:top_k]

def run_cli_demo():
    print("="*50)
    print("옥독해(OK-DOK-HAE) 터미널 데모 모드")
    print("="*50)

    # 1. 인스턴스 초기화
    print("모델 및 분석기 초기화 중... (최초 실행 시 시간이 걸릴 수 있습니다)")
    analyzer = LogicAnalyzer()
    evaluator = Evaluator()
    print("초기화 완료!\n")

    # 2. 데이터셋 로드
    samples_path = repo_root / "data" / "processed" / "cleaned_contexts.json"
    if not samples_path.exists():
        print("에러: 파일을 찾을 수 없습니다. fetch_data.py를 먼저 실행해주세요.")
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
        elif choice == '2':
            text = input("\n분석할 텍스트를 입력하세요: ")
        else:
            continue

        if not text:
            continue

        print("\n" + "-"*30)
        print("본문 내용:")
        print(text)
        print("-"*30)

        # 3. 분석 시작
        print("\n[AI 분석 중...]")
        nodes = analyzer.analyze(text)
        if not nodes:
            print("분석 결과가 비어있습니다. 입력 텍스트를 바꿔주세요.")
            continue

        claim_cands = pick_candidates(nodes, types={"claim", "result", "definition"}, top_k=5)
        evidence_cands = pick_candidates(nodes, types={"evidence", "cause", "contrast"}, top_k=8)
        
        # fallback: 후보가 너무 적으면 점수 상위에서 채움
        ranked = sorted(nodes, key=lambda x: x.get("score", 0), reverse=True)
        if len(claim_cands) < 3:
            claim_cands = ranked[:5]
        if len(evidence_cands) < 3:
            evidence_cands = ranked[:8]

        key_nodes = [n for n in nodes if n.get('is_key_node')]

        # DEBUG: show key nodes
        print("\n[DEBUG] Key nodes selected:")
        for n in key_nodes:
            print(f"- idx={n.get('index')} score={n.get('score')} roles={n.get('roles')} text={n.get('text')[:100]}")
        print()
        # DEBUG END

        print("\n[주장 후보 선택]")
        for i, n in enumerate(claim_cands):
            print(f"{i}: (type={n.get('type')}, score={n.get('score',0):.2f}) {n['text'][:120]}")

        raw = input("주장 후보 번호를 선택하거나(0~), 직접 입력하려면 그냥 엔터 후 직접 입력: ").strip()

        if raw == "":
            claim_text = input("주장을 직접 입력하세요: ").strip()
        else:
            try:
                idx = int(raw)
            except ValueError:
                print("숫자를 입력해주세요.")
                continue
            if not (0 <= idx < len(claim_cands)):
                print("범위 밖 번호입니다.")
                continue
            claim_text = claim_cands[idx]["text"].strip()
        
        print("\n[근거 후보 선택] (여러 개면 쉼표로 입력, 예: 0,2,3)")
        for i, n in enumerate(evidence_cands):
            print(f"{i}: (type={n.get('type')}, score={n.get('score',0):.2f}) {n['text'][:120]}")

        raw = input("근거 번호(쉼표구분) 입력 (없으면 엔터): ").strip()
        evidence_texts = []
        if raw:
            picks = [p.strip() for p in raw.split(",") if p.strip().isdigit()]
            for p in picks:
                j = int(p)
                if 0 <= j < len(evidence_cands):
                    evidence_texts.append(evidence_cands[j]["text"].strip())
        
        question = (
            f"주장: {claim_text}\n"
            f"근거: {' / '.join(evidence_texts) if evidence_texts else '(없음)'}\n"
            "위 근거를 사용해 주장을 논리적으로 설명하시오."
        )
        print(f"\nAI 질문: {question}")
        reasoning_text = input("당신의 설명(Reasoning): ").strip()

        print("\n[AI Validation 중...]")
        result = evaluator.validate_reasoning(
            question=question,
            claim_text=claim_text,
            evidence_texts=evidence_texts,
            reasoning_text=reasoning_text
        )

        print("\n" + "="*30)
        print(f"라벨: {result['label']}")
        print(f"진단(diag): {result.get('diag')}")
        print(f"스코어: {result['scores']}")
        print("="*30)
        input("\n계속하려면 엔터를 누르세요...")

if __name__ == "__main__":
    run_cli_demo()
