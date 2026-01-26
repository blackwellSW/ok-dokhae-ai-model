import json
from datasets import load_dataset
import random
from pathlib import Path

def fetch_samples():
    all_samples = []

    print("Fetching KLUE MRC samples...")
    try:
        klue_mrc = load_dataset("klue", "mrc", split="train", trust_remote_code=True)
        for i in range(min(30, len(klue_mrc))):
            item = klue_mrc[i]
            all_samples.append({
                "id": f"KLUE-MRC-{i}",
                "source": "KLUE-MRC",
                "context": item['context'],
                "question": item['question'],
                "answer": item['answers']['text'][0] if item['answers']['text'] else ""
            })
    except Exception as e:
        print(f"Error fetching KLUE MRC: {e}")

    print("Fetching KLUE NLI samples...")
    try:
        klue_nli = load_dataset("klue", "nli", split="train", trust_remote_code=True)
        for i in range(min(30, len(klue_nli))):
            item = klue_nli[i]
            # NLI labels: 0: entailment, 1: neutral, 2: contradiction
            label_map = {0: "entailment", 1: "neutral", 2: "contradiction"}
            all_samples.append({
                "id": f"KLUE-NLI-{i}",
                "source": "KLUE-NLI",
                "context": item['premise'],
                "hypothesis": item['hypothesis'],
                "label": label_map.get(item['label'], "unknown")
            })
    except Exception as e:
        print(f"Error fetching KLUE NLI: {e}")

    print("Fetching KLUE STS samples...")
    try:
        klue_sts = load_dataset("klue", "sts", split="train", trust_remote_code=True)
        for i in range(min(20, len(klue_sts))):
            item = klue_sts[i]
            all_samples.append({
                "id": f"KLUE-STS-{i}",
                "source": "KLUE-STS",
                "sentence1": item['sentence1'],
                "sentence2": item['sentence2'],
                "score": item['labels']['label']
            })
    except Exception as e:
        print(f"Error fetching KLUE STS: {e}")

    print("Fetching SQuAD samples...")
    try:
        squad = load_dataset("rajpurkar/squad", split="train", trust_remote_code=True)
        for i in range(min(20, len(squad))):
            item = squad[i]
            all_samples.append({
                "id": f"SQuAD-{i}",
                "source": "SQuAD",
                "context": item['context'],
                "question": item['question'],
                "answer": item['answers']['text'][0] if item['answers']['text'] else ""
            })
    except Exception as e:
        print(f"Error fetching SQuAD: {e}")

    # Limit to 100 total
    final_samples = all_samples[:100]
    
    repo_root = Path(__file__).resolve().parents[2]
    out_path = repo_root / "data" / "samples.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(final_samples, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully saved {len(final_samples)} samples to {out_path}")

if __name__ == "__main__":
    fetch_samples()
