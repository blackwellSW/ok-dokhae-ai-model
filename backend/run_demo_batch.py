#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch labeling tool for OK-DOK-HAE.

What it does:
- Loads passages from a JSON or JSONL file (supports your merged_all.json style).
- Uses LogicAnalyzer to pick claim/evidence candidates automatically (simple heuristic).
- Builds a prompt and calls an external LLM command (or manual paste) to generate reasoning.
- Runs Evaluator to get label/diag/scores.
- Appends results to an output JSONL file (one sample per line).

Usage examples:

1) Manual mode (prints prompt, you paste LLM output):
   python run_demo_batch.py --input merged_all.json --output train_labeled.jsonl --llm_mode manual

2) Automated via a command that reads prompt from stdin and prints completion to stdout:
   python run_demo_batch.py --input raw_passages.jsonl --output train_labeled.jsonl \
       --llm_mode cmd --llm_cmd "python llm_call.py"

3) Split work across two people (shard 0/2 and 1/2):
   python run_demo_batch.py --input merged_all.json --output out0.jsonl --shard_idx 0 --num_shards 2
   python run_demo_batch.py --input merged_all.json --output out1.jsonl --shard_idx 1 --num_shards 2

Notes:
- This script does NOT require changing analyzer/generator.
- It assumes backend.logic.analyzer / backend.logic.evaluator are importable like your run_demo.py.
"""
import argparse
import json
import os
import sys
import time
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make repo imports work (same trick as run_demo.py)
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

try:
    from backend.logic.analyzer import LogicAnalyzer
    from backend.logic.evaluator import Evaluator
except ImportError as e:
    print(f"[ERROR] ImportError: {e}")
    print("Check your repo structure and PYTHONPATH.")
    raise


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_passages(input_path: Path) -> List[Dict[str, Any]]:
    """
    Supports:
    - JSONL where each line is already {passage_id, source, text}
    - merged_all.json style list of dicts {file, passage_range, passage, questions?}
    - single dict with keys that contain a list under 'items' or similar (best-effort)
    """
    if input_path.suffix.lower() == ".jsonl":
        items: List[Dict[str, Any]] = []
        with input_path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                # normalize keys
                text = obj.get("text") or obj.get("passage") or obj.get("context")
                if not text:
                    raise ValueError(f"JSONL line {line_no} missing text/passage/context")
                items.append({
                    "passage_id": obj.get("passage_id") or f"{input_path.stem}:{line_no}",
                    "source": obj.get("source") or {},
                    "text": text
                })
        return items

    data = _read_json(input_path)
    if isinstance(data, list):
        items = []
        for i, obj in enumerate(data):
            text = obj.get("text") or obj.get("passage") or obj.get("context")
            if not text:
                # skip silently (or raise) — for now skip
                continue
            passage_id = obj.get("passage_id")
            if not passage_id:
                # stable-ish id from file + range + index
                f = obj.get("file", input_path.name)
                r = obj.get("passage_range", "")
                passage_id = f"{Path(f).stem}__{r}__{i:05d}"
            source = obj.get("source") or {
                "file": obj.get("file"),
                "passage_range": obj.get("passage_range"),
            }
            items.append({"passage_id": passage_id, "source": source, "text": text})
        return items

    # best effort: find a list field
    for key in ("items", "data", "passages", "entries"):
        if key in data and isinstance(data[key], list):
            # recurse using temporary file-like structure
            items = []
            for i, obj in enumerate(data[key]):
                text = obj.get("text") or obj.get("passage") or obj.get("context")
                if not text:
                    continue
                passage_id = obj.get("passage_id") or f"{input_path.stem}:{key}:{i}"
                items.append({"passage_id": passage_id, "source": obj.get("source") or {}, "text": text})
            return items

    raise ValueError("Unsupported JSON structure. Use JSONL or a list of passage objects.")


def _pick_claim_evidence(nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Simple heuristic:
    - claim: highest score node
    - evidence: next highest score node with different id
      If none, evidence == claim (fallback)
    """
    if not nodes:
        raise ValueError("Analyzer returned no nodes")

    ranked = sorted(nodes, key=lambda n: float(n.get("score", 0.0)), reverse=True)
    claim = ranked[0]

    evidence = None
    for n in ranked[1:]:
        if n.get("id") != claim.get("id"):
            evidence = n
            break
    if evidence is None:
        evidence = claim

    return {
        "claim_text": claim.get("text", "").strip(),
        "evidence_texts": [evidence.get("text", "").strip()],
        "claim_node": claim,
        "evidence_nodes": [evidence],
    }


def build_prompt(text: str, claim_text: str, evidence_texts: List[str], mode: str) -> str:
    """
    mode:
      - good
      - weak_no_grounding
      - weak_missing_why
      - weak_generic
      - short
    """
    evidence_block = "\n".join([f"- {e}" for e in evidence_texts])
    common = f"""[지문]
{text}

[주장]
{claim_text}

[근거]
{evidence_block}

[과제]
위 근거를 사용해 주장을 논리적으로 설명하는 '설명문(reasoning)'을 한국어로 작성하세요.
"""

    if mode == "good":
        return common + """요구사항:
- 2~3문장, 80~180자
- 근거에서 핵심 표현(단어/구)을 최소 2개 포함
- '왜/때문/따라서/그러므로/하지만/반면/만약' 중 최소 1개 연결어를 사용
- 지문 밖 지식 금지(지문 내용만 사용)

설명문만 출력하세요.
"""
    if mode == "weak_no_grounding":
        return common + """요구사항:
- 1~2문장, 40~120자
- 근거에 나온 핵심 용어/표현을 되도록 쓰지 말 것(가능하면 피함)
- 내용은 일반론/엉뚱한 방향으로 써서 주장을 지지하는 근거 사용이 거의 없게 만들 것
- 욕설/비속어 금지

설명문만 출력하세요.
"""
    if mode == "weak_missing_why":
        return common + """요구사항:
- 1~2문장, 60~160자
- 근거에서 단어는 1~2개 포함하되,
- '왜 그렇게 되는지' 인과/대조/조건 설명을 하지 말 것(연결어 최소화)
- 근거 요약 → 결론 점프 형태로 작성

설명문만 출력하세요.
"""
    if mode == "weak_generic":
        return common + """요구사항:
- 1~2문장, 60~160자
- 근거를 언급하긴 하지만, '전반적으로/중요하다/효율적이다/의미 있다' 같은 뭉뚱그린 표현 위주
- 구체적 연결(어떤 조건/어떤 과정 때문에)을 피함

설명문만 출력하세요.
"""
    if mode == "short":
        return common + """요구사항:
- 10~25자 내외로 매우 짧게
- 내용이 거의 없도록 작성

설명문만 출력하세요.
"""
    raise ValueError(f"Unknown mode: {mode}")


def call_llm(prompt: str, llm_mode: str, llm_cmd: Optional[str]) -> str:
    if llm_mode == "manual":
        print("\n" + "=" * 60)
        print("[LLM PROMPT]")
        print(prompt)
        print("=" * 60)
        return input("LLM 출력(설명문)만 붙여넣고 엔터: ").strip()

    if llm_mode == "cmd":
        if not llm_cmd:
            raise ValueError("--llm_mode cmd requires --llm_cmd")
        cmd = shlex.split(llm_cmd)
        p = subprocess.run(cmd, input=prompt, text=True, capture_output=True)
        if p.returncode != 0:
            raise RuntimeError(f"LLM cmd failed: {p.stderr.strip()}")
        return p.stdout.strip()

    raise ValueError(f"Unknown llm_mode: {llm_mode}")


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="merged_all.json or raw_passages.jsonl")
    ap.add_argument("--output", required=True, help="output JSONL to append labeled samples")
    ap.add_argument("--mode", default="good",
                    choices=["good", "weak_no_grounding", "weak_missing_why", "weak_generic", "short"],
                    help="type of reasoning to generate via LLM")
    ap.add_argument("--limit", type=int, default=0, help="0 = no limit, else max passages to process")
    ap.add_argument("--shard_idx", type=int, default=0, help="which shard to process (0-based)")
    ap.add_argument("--num_shards", type=int, default=1, help="total shards")
    ap.add_argument("--llm_mode", default="manual", choices=["manual", "cmd"])
    ap.add_argument("--llm_cmd", default="", help="command that reads prompt from stdin and prints completion")
    ap.add_argument("--sleep_sec", type=float, default=0.0, help="sleep between samples (rate limiting)")
    args = ap.parse_args()

    input_path = Path(args.input)
    out_path = Path(args.output)

    analyzer = LogicAnalyzer()
    evaluator = Evaluator()

    passages = _iter_passages(input_path)
    if not passages:
        print("[WARN] No passages loaded.")
        return

    # shard split
    if args.num_shards < 1:
        raise ValueError("--num_shards must be >= 1")
    if not (0 <= args.shard_idx < args.num_shards):
        raise ValueError("--shard_idx out of range")

    selected = [p for i, p in enumerate(passages) if i % args.num_shards == args.shard_idx]
    if args.limit and args.limit > 0:
        selected = selected[: args.limit]

    print(f"[INFO] Loaded {len(passages)} passages; processing {len(selected)} (shard {args.shard_idx}/{args.num_shards})")
    for idx, item in enumerate(selected, 1):
        passage_id = item["passage_id"]
        text = item["text"]

        # Analyze
        try:
            nodes = analyzer.analyze(text)
        except Exception as e:
            print(f"[WARN] analyzer failed for {passage_id}: {e}")
            continue

        try:
            picked = _pick_claim_evidence(nodes)
        except Exception as e:
            print(f"[WARN] pick failed for {passage_id}: {e}")
            continue

        claim_text = picked["claim_text"]
        evidence_texts = picked["evidence_texts"]

        # Build question (same style as run_demo)
        question = f"주장: {claim_text}\n근거: " + " ".join(evidence_texts) + "\n위 근거를 사용해 주장을 논리적으로 설명하시오."

        # LLM reasoning
        prompt = build_prompt(text=text, claim_text=claim_text, evidence_texts=evidence_texts, mode=args.mode)
        try:
            reasoning_text = call_llm(prompt, llm_mode=args.llm_mode, llm_cmd=args.llm_cmd)
        except Exception as e:
            print(f"[WARN] LLM failed for {passage_id}: {e}")
            continue

        # Evaluate
        try:
            result = evaluator.validate_reasoning(
                question=question,
                claim_text=claim_text,
                evidence_texts=evidence_texts,
                reasoning_text=reasoning_text,
            )
        except Exception as e:
            print(f"[WARN] evaluator failed for {passage_id}: {e}")
            continue

        sample = {
            "passage_id": passage_id,
            "source": item.get("source", {}),
            "text": text,
            "claim": claim_text,
            "evidence": evidence_texts,
            "reasoning": reasoning_text,
            # IMPORTANT:
            # - label/diag here are produced by heuristic evaluator.
            #   If you generate *targeted* reasoning types, you may also store 'target_label/target_diag'.
            "label": result.get("label"),
            "diag": result.get("diag"),
            "scores": result.get("scores", {}),
            "debug": result.get("debug", {}),
            "meta": {
                "gen_mode": args.mode,
                "created_at": int(time.time()),
            },
        }
        append_jsonl(out_path, sample)

        print(f"[OK] {idx}/{len(selected)} {passage_id} -> {sample['label']} / {sample['diag']} scores={sample['scores']}")
        if args.sleep_sec and args.sleep_sec > 0:
            time.sleep(args.sleep_sec)


if __name__ == "__main__":
    main()
