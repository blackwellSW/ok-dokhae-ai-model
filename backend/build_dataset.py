import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

from sklearn.model_selection import train_test_split


VALID_LABELS = {
    "GOOD",
    "WEAK_LINK",
    "OFF_PATH",
    "INSUFFICIENT_REASONING",
}


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


def normalize_evidence(evidence) -> List[str]:
    if evidence is None:
        return []
    if isinstance(evidence, list):
        return [str(e).strip() for e in evidence if str(e).strip()]
    return [str(evidence).strip()]


def build_input(obj: Dict, include_passage: bool) -> str:
    claim = (obj.get("claim") or "").strip()
    reasoning = (obj.get("reasoning") or "").strip()
    passage = (obj.get("text") or "").strip()
    evidence_list = normalize_evidence(obj.get("evidence"))
    evidence_joined = " / ".join(evidence_list) if evidence_list else "(none)"

    question = (
        f"Claim: {claim}\n"
        f"Evidence: {evidence_joined}\n"
        "Explain how the evidence supports the claim."
    )

    parts: List[str] = []
    if include_passage and passage:
        parts.extend(["[PASSAGE]", passage])
    parts.extend(["[QUESTION]", question, "[REASONING]", reasoning])

    return "\n".join([p for p in parts if p])


def build_records(items: List[Dict], include_passage: bool) -> List[Dict]:
    records: List[Dict] = []
    for idx, obj in enumerate(items):
        label = obj.get("label")
        if label not in VALID_LABELS:
            continue
        input_text = build_input(obj, include_passage=include_passage)
        if not input_text.strip():
            continue
        records.append(
            {
                "id": obj.get("passage_id") or f"row-{idx}",
                "label": label,
                "input": input_text,
                "diag": obj.get("diag"),
            }
        )
    return records


def split_records(
    records: List[Dict],
    train_ratio: float,
    dev_ratio: float,
    seed: int,
) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    if not (0.0 < train_ratio < 1.0):
        raise ValueError("train_ratio must be between 0 and 1")
    if not (0.0 <= dev_ratio < 1.0):
        raise ValueError("dev_ratio must be between 0 and 1")
    if train_ratio + dev_ratio >= 1.0:
        raise ValueError("train_ratio + dev_ratio must be < 1.0")

    labels = [r["label"] for r in records]
    train, temp = train_test_split(
        records,
        test_size=1.0 - train_ratio,
        stratify=labels,
        random_state=seed,
    )

    if not temp:
        return train, [], []

    temp_labels = [r["label"] for r in temp]
    dev_size = dev_ratio / (1.0 - train_ratio)
    dev, test = train_test_split(
        temp,
        test_size=1.0 - dev_size,
        stratify=temp_labels,
        random_state=seed,
    )
    return train, dev, test


def write_jsonl(path: Path, items: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for obj in items:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def count_labels(items: List[Dict]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for obj in items:
        label = obj.get("label") or "UNKNOWN"
        counts[label] = counts.get(label, 0) + 1
    return counts


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    default_input = repo_root / "data" / "processed" / "train_labeled_v1.jsonl"
    default_out_dir = repo_root / "data" / "processed" / "dm"

    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(default_input))
    ap.add_argument("--out-dir", default=str(default_out_dir))
    ap.add_argument("--train-ratio", type=float, default=0.8)
    ap.add_argument("--dev-ratio", type=float, default=0.1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-passage", action="store_true", help="exclude passage text from input")
    args = ap.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    items = read_jsonl(input_path)
    records = build_records(items, include_passage=not args.no_passage)
    if not records:
        raise ValueError("No records built from input")

    train, dev, test = split_records(
        records,
        train_ratio=args.train_ratio,
        dev_ratio=args.dev_ratio,
        seed=args.seed,
    )

    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / "train.jsonl", train)
    write_jsonl(out_dir / "dev.jsonl", dev)
    write_jsonl(out_dir / "test.jsonl", test)

    print("[build_dataset] total:", len(records), count_labels(records))
    print("[build_dataset] train:", len(train), count_labels(train))
    print("[build_dataset] dev:", len(dev), count_labels(dev))
    print("[build_dataset] test:", len(test), count_labels(test))


if __name__ == "__main__":
    main()
