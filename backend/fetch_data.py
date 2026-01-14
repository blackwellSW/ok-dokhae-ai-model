import json
import random
import re
import statistics
from collections import Counter
from pathlib import Path

from datasets import load_dataset


# -----------------------------
# Config (필요하면 숫자만 조정)
# -----------------------------
SEED = 42
MAX_TOTAL = 100

# 텍스트 품질 필터
MIN_CHARS = 200        # 너무 짧은 글 제거
MAX_CHARS = 1800       # 너무 긴 글은 문장 단위로 잘라내기
MIN_SENTENCES = 3      # 문장 수 너무 적으면 제거

# 데이터셋별 목표 샘플 수(합이 MAX_TOTAL보다 커도 됨. 마지막에 MAX_TOTAL로 자름)
TARGETS = {
    "KLUE-MRC": 30,
    "KLUE-NLI": 30,
    "KLUE-STS": 20,
    "SQuAD": 20,
}


# -----------------------------
# Text preprocessing utilities
# -----------------------------
_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\ufeff]")  # zero-width chars
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_REPEAT_PUNCT = re.compile(r"([!?.,])\1{3,}")  # !!!! -> !!! 정도로 줄이기

def normalize_text(text: str) -> str:
    """텍스트 정규화: 보이지 않는 문자 제거, 공백/줄바꿈 정리 등."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _ZERO_WIDTH.sub("", text)
    text = _REPEAT_PUNCT.sub(r"\1\1\1", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()

def split_sentences(text: str) -> list[str]:
    """문장 분리: kss가 있으면 사용, 없으면 간단 규칙으로 대체."""
    text = text.strip()
    if not text:
        return []
    try:
        import kss
        sents = kss.split_sentences(text)
        return [s.strip() for s in sents if s.strip()]
    except Exception:
        # fallback: 아주 단순한 규칙 기반 분리(완벽하진 않지만 최소 기능)
        sents = re.split(r"(?<=[\.!?。！？])\s+", text)
        return [s.strip() for s in sents if s.strip()]

def truncate_by_sentences(text: str, max_chars: int) -> str:
    """문장 단위로 최대 길이를 넘지 않게 자르기."""
    if len(text) <= max_chars:
        return text
    sents = split_sentences(text)
    if not sents:
        return text[:max_chars].strip()

    acc = []
    total = 0
    for s in sents:
        # 문장 사이 공백 1개 가정
        add_len = len(s) + (1 if acc else 0)
        if total + add_len > max_chars:
            break
        acc.append(s)
        total += add_len

    # 문장이 하나도 못 들어가면 그냥 하드 컷
    if not acc:
        return text[:max_chars].strip()

    return " ".join(acc).strip()

def preprocess_context(raw: str) -> tuple[str, int]:
    """정규화 + 길이 제한 + 문장 수 반환."""
    cleaned = normalize_text(raw)
    cleaned = truncate_by_sentences(cleaned, MAX_CHARS)
    sent_count = len(split_sentences(cleaned))
    return cleaned, sent_count


def passes_filters(text: str, sent_count: int, task: str = "mrc") -> bool:
    """품질 필터 통과 여부. Task에 따라 기준 완화."""
    # NLI, STS 등 짧은 문장이 정상인 태스크는 기준을 대폭 낮춤
    if task in ["nli", "sts"]:
        if len(text) < 10:  # 최소 10자 (너무 짧은 노이즈만 제거)
            return False
        if sent_count < 1:  # 최소 1문장
            return False
        return True

    # 기본(MRC 등)은 기존 엄격한 기준 적용
    if len(text) < MIN_CHARS:
        return False
    if sent_count < MIN_SENTENCES:
        return False
    return True


def remove_duplicates(samples: list[dict]) -> list[dict]:
    """텍스트 내용을 기준으로 중복 제거."""
    seen_texts = set()
    unique_samples = []
    
    for s in samples:
        text = s.get("text", "").strip()
        if text and text not in seen_texts:
            seen_texts.add(text)
            unique_samples.append(s)
            
    removed_count = len(samples) - len(unique_samples)
    if removed_count > 0:
        print(f"Removed {removed_count} duplicate samples.")
    
    return unique_samples


# -----------------------------
# Sampling utilities
# -----------------------------
def sample_indices(n: int, k: int, rng: random.Random) -> list[int]:
    """앞에서부터가 아니라 랜덤 샘플링(재현 가능)."""
    if n <= 0 or k <= 0:
        return []
    k = min(k, n)
    return rng.sample(range(n), k)


# -----------------------------
# Main fetch
# -----------------------------
def fetch_samples() -> None:
    rng = random.Random(SEED)
    all_samples = []

    # ---------------- KLUE MRC ----------------
    print("Fetching KLUE MRC samples...")
    try:
        klue_mrc = load_dataset("klue", "mrc", split="train")  # trust_remote_code 제거
        idxs = sample_indices(len(klue_mrc), TARGETS["KLUE-MRC"], rng)
        for i, idx in enumerate(idxs):
            item = klue_mrc[idx]
            context, n_sent = preprocess_context(item.get("context", ""))
            if not passes_filters(context, n_sent, task="mrc"):
                continue

            all_samples.append({
                "id": f"KLUE-MRC-{idx}",
                "source": "KLUE-MRC",
                "task": "mrc",
                "text": context,           # 공통 필드
                "context": context,        # 기존 파이프라인 호환을 위해 유지
                "question": item.get("question", ""),
                "answer": (item.get("answers", {}).get("text") or [""])[0],
                "stats": {"n_sentences": n_sent, "n_chars": len(context)},
            })
    except Exception as e:
        print(f"Error fetching KLUE MRC: {e}")

    # ---------------- KLUE NLI ----------------
    print("Fetching KLUE NLI samples...")
    try:
        klue_nli = load_dataset("klue", "nli", split="train")  # trust_remote_code 제거
        idxs = sample_indices(len(klue_nli), TARGETS["KLUE-NLI"], rng)
        label_map = {0: "entailment", 1: "neutral", 2: "contradiction"}

        for idx in idxs:
            item = klue_nli[idx]
            premise = item.get("premise", "")
            premise_clean, n_sent = preprocess_context(premise)
            if not passes_filters(premise_clean, n_sent, task="nli"):
                continue

            hypothesis = normalize_text(item.get("hypothesis", ""))
            label = label_map.get(item.get("label"), "unknown")

            # NLI도 데모에서 읽을 수 있게 question을 하나 만들어둠(추가 필드라 깨지지 않음)
            pseudo_question = "가설이 전제에서 참인지/거짓인지/판단불가인지 설명해보세요."

            all_samples.append({
                "id": f"KLUE-NLI-{idx}",
                "source": "KLUE-NLI",
                "task": "nli",
                "text": premise_clean,
                "context": premise_clean,   # 호환용
                "question": pseudo_question,
                "hypothesis": hypothesis,
                "label": label,
                "stats": {"n_sentences": n_sent, "n_chars": len(premise_clean)},
            })
    except Exception as e:
        print(f"Error fetching KLUE NLI: {e}")

    # ---------------- KLUE STS ----------------
    print("Fetching KLUE STS samples...")
    try:
        klue_sts = load_dataset("klue", "sts", split="train")  # trust_remote_code 제거
        idxs = sample_indices(len(klue_sts), TARGETS["KLUE-STS"], rng)

        for idx in idxs:
            item = klue_sts[idx]
            s1 = normalize_text(item.get("sentence1", ""))
            s2 = normalize_text(item.get("sentence2", ""))

            # STS는 두 문장을 같이 보여주는 게 자연스러워서 context를 결합
            combined = f"문장 A: {s1}\n문장 B: {s2}"
            combined_clean, n_sent = preprocess_context(combined)

            if not passes_filters(combined_clean, n_sent, task="sts"):
                continue

            pseudo_question = "두 문장이 의미가 얼마나 비슷한지 근거를 들어 설명해보세요."

            all_samples.append({
                "id": f"KLUE-STS-{idx}",
                "source": "KLUE-STS",
                "task": "sts",
                "text": combined_clean,
                "context": combined_clean,  # 호환용
                "question": pseudo_question,
                "sentence1": s1,
                "sentence2": s2,
                "score": item.get("labels", {}).get("label", None),
                "stats": {"n_sentences": n_sent, "n_chars": len(combined_clean)},
            })
    except Exception as e:
        print(f"Error fetching KLUE STS: {e}")

    # ---------------- SQuAD ----------------
    print("Fetching SQuAD samples...")
    try:
        squad = load_dataset("rajpurkar/squad", split="train")  # trust_remote_code 제거
        idxs = sample_indices(len(squad), TARGETS["SQuAD"], rng)

        for idx in idxs:
            item = squad[idx]
            context, n_sent = preprocess_context(item.get("context", ""))
            if not passes_filters(context, n_sent, task="mrc"):
                continue

            all_samples.append({
                "id": f"SQuAD-{idx}",
                "source": "SQuAD",
                "task": "mrc",
                "text": context,
                "context": context,
                "question": item.get("question", ""),
                "answer": (item.get("answers", {}).get("text") or [""])[0],
                "stats": {"n_sentences": n_sent, "n_chars": len(context)},
            })
    except Exception as e:
        print(f"Error fetching SQuAD: {e}")


    # --------------- Finalize / Report / Save ---------------
    # 중복 제거
    all_samples = remove_duplicates(all_samples)

    # 섞어서 편향 줄이기(재현 가능)
    rng.shuffle(all_samples)
    final_samples = all_samples[:MAX_TOTAL]

    # 품질 리포트
    print("\n========== Data Report ==========")
    print(f"Total collected (before cut): {len(all_samples)}")
    print(f"Total saved (after cut):      {len(final_samples)}")

    by_source = Counter(s["source"] for s in final_samples)
    print("By source:", dict(by_source))

    lengths = [s["stats"]["n_chars"] for s in final_samples if "stats" in s]
    sents = [s["stats"]["n_sentences"] for s in final_samples if "stats" in s]
    if lengths:
        print(f"Chars   avg/median/min/max: {statistics.mean(lengths):.1f} / {statistics.median(lengths)} / {min(lengths)} / {max(lengths)}")
    if sents:
        print(f"Sents   avg/median/min/max: {statistics.mean(sents):.1f} / {statistics.median(sents)} / {min(sents)} / {max(sents)}")
    print("================================\n")

    repo_root = Path(__file__).resolve().parents[1]
    out_path = repo_root / "data" / "samples.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(final_samples, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(final_samples)} samples to {out_path}")


if __name__ == "__main__":
    fetch_samples()
