# DM Dataset Schema

Scope: Only `data/processed/train_labeled_v1.jsonl` is used. All other datasets are ignored.

## Raw Record Schema (train_labeled_v1.jsonl)
Each line is a JSON object with fields:

- passage_id: string
- source: object (dataset, subject, topic, file, passage_range)
- text: string (passage)
- claim: string
- evidence: list[string]
- reasoning: string
- label: string in {GOOD, WEAK_LINK, OFF_PATH, INSUFFICIENT_REASONING}
- diag: string (diagnostic tag from validator)
- scores: object (qa_score, link_score, length_chars, length_tokens, evidence_count)
- debug: object
- meta: object (gen_mode, created_at)

## Derived Training Sample
We generate `input` from raw fields:

Question template:
Claim: {claim}
Evidence: {evidence_joined}
Explain how the evidence supports the claim.

Input layout:
[PASSAGE]
{text}            (optional)
[QUESTION]
{question}
[REASONING]
{reasoning}

## Splits
Default split: train/dev/test = 0.8/0.1/0.1, stratified by label, seed=42.

## Label Semantics
- GOOD: reasoning is on-topic, uses evidence, and links to the claim.
- WEAK_LINK: reasoning is on-topic but the link or grounding is weak.
- OFF_PATH: reasoning does not answer the question.
- INSUFFICIENT_REASONING: reasoning is too short or too thin to judge.

## Notes
- Labels are heuristic (silver) from Evaluator.validate_reasoning.
- Prefer macro-F1 for model evaluation due to class imbalance.
