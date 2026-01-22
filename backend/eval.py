import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
from sklearn.metrics import classification_report, f1_score


def read_jsonl(path: Path) -> List[Dict]:
    items: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_no}") from exc
    return items


def load_xy(path: Path) -> Tuple[List[str], List[str], List[str]]:
    items = read_jsonl(path)
    texts: List[str] = []
    labels: List[str] = []
    ids: List[str] = []
    for idx, obj in enumerate(items):
        text = (obj.get("input") or "").strip()
        label = obj.get("label")
        if not text or not label:
            continue
        texts.append(text)
        labels.append(label)
        ids.append(obj.get("id") or f"row-{idx}")
    return texts, labels, ids


def write_predictions(path: Path, ids: List[str], labels: List[str], preds: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item_id, label, pred in zip(ids, labels, preds):
            obj = {"id": item_id, "label": label, "pred": pred}
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    default_data_dir = repo_root / "data" / "processed" / "dm"
    default_model = repo_root / "models" / "dm_logreg.joblib"

    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(default_data_dir / "test.jsonl"))
    ap.add_argument("--model", default=str(default_model))
    ap.add_argument("--output", default="", help="optional JSONL predictions output path")
    args = ap.parse_args()

    data_path = Path(args.data)
    model_path = Path(args.model)
    if not data_path.exists():
        raise FileNotFoundError(f"Data not found: {data_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    model = joblib.load(model_path)
    texts, labels, ids = load_xy(data_path)
    if not texts:
        raise ValueError(f"No samples found in {data_path}")

    preds = model.predict(texts)
    macro_f1 = f1_score(labels, preds, average="macro", zero_division=0)
    print("[eval] macro_f1:", round(macro_f1, 4))
    print(classification_report(labels, preds, digits=4, zero_division=0))

    if args.output:
        write_predictions(Path(args.output), ids, labels, list(preds))
        print("[eval] saved predictions:", args.output)


if __name__ == "__main__":
    main()
