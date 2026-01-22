import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Generator
from contextlib import contextmanager

import joblib
from google.cloud import storage
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.pipeline import Pipeline


@contextmanager
def open_path(path_str: str, mode: str = "r"):
    """
    Context manager that handles both local paths and gs:// paths.
    If gs://, downloads to temp file (for read) or uploads from temp file (for write - not fully implemented for write stream here, mostly for read).
    For writing model (joblib), we handle it separately.
    """
    if path_str.startswith("gs://"):
        client = storage.Client()
        if "w" in mode:
            # Writing to GCS not implemented via this simple context manager for text files yet, 
            # as we mainly need it for reading inputs or writing artifacts explicitly.
            raise NotImplementedError("Writing directly to gs:// via open_path context is limited.")
        
        # READ from GCS
        bucket_name, blob_name = path_str[5:].split("/", 1)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        with tempfile.NamedTemporaryFile(mode="w+b", delete=True) as tmp:
            print(f"⬇️ Downloading {path_str} to temp...")
            blob.download_to_file(tmp)
            tmp.flush()
            tmp.seek(0)
            
            # Re-open in text mode for processing
            with open(tmp.name, mode, encoding="utf-8") as f:
                yield f
    else:
        # Local file
        with open(path_str, mode, encoding="utf-8") as f:
            yield f


def upload_model(local_limit_path: Path, gcs_uri: str) -> None:
    if not gcs_uri.startswith("gs://"):
        return
    
    client = storage.Client()
    bucket_name, blob_name = gcs_uri[5:].split("/", 1)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    print(f"⬆️ Uploading model to {gcs_uri}...")
    blob.upload_from_filename(str(local_limit_path))


def read_jsonl(path_str: str) -> List[Dict]:
    items: List[Dict] = []
    with open_path(path_str, "r") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_no}") from exc
    return items


def load_xy(path_str: str) -> Tuple[List[str], List[str]]:
    items = read_jsonl(path_str)
    texts: List[str] = []
    labels: List[str] = []
    for obj in items:
        text = (obj.get("input") or "").strip()
        label = obj.get("label")
        if not text or not label:
            continue
        texts.append(text)
        labels.append(label)
    return texts, labels


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    default_data_dir = repo_root / "data" / "processed" / "dm"
    default_model = repo_root / "models" / "dm_logreg.joblib"

    ap = argparse.ArgumentParser()
    ap.add_argument("--train", default=str(default_data_dir / "train.jsonl"))
    ap.add_argument("--dev", default=str(default_data_dir / "dev.jsonl"))
    ap.add_argument("--test", default=str(default_data_dir / "test.jsonl"))
    ap.add_argument("--model-out", default=str(default_model))
    ap.add_argument("--max-features", type=int, default=50000)
    ap.add_argument("--min-df", type=int, default=2)
    ap.add_argument("--ngram-max", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    train_path = args.train
    dev_path = args.dev
    test_path = args.test

    x_train, y_train = load_xy(train_path)
    if not x_train:
        raise ValueError(f"No training samples found in {train_path}")

    vectorizer = TfidfVectorizer(
        max_features=args.max_features,
        min_df=args.min_df,
        ngram_range=(1, args.ngram_max),
        lowercase=False,
    )
    clf = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=args.seed,
        n_jobs=None,
    )

    pipeline = Pipeline(
        [
            ("tfidf", vectorizer),
            ("clf", clf),
        ]
    )
    pipeline.fit(x_train, y_train)

    print("[train] samples:", len(x_train))

    # Dev evaluation (simple check if path exists or if it's GCS assume yes/try)
    if dev_path: 
        try:
            x_dev, y_dev = load_xy(dev_path)
            if x_dev:
            preds = pipeline.predict(x_dev)
            macro_f1 = f1_score(y_dev, preds, average="macro", zero_division=0)
            print("[dev] macro_f1:", round(macro_f1, 4))
            print(classification_report(y_dev, preds, digits=4, zero_division=0))

    if test_path:
        try:
            x_test, y_test = load_xy(test_path)
            if x_test:
            preds = pipeline.predict(x_test)
            macro_f1 = f1_score(y_test, preds, average="macro", zero_division=0)
            print("[test] macro_f1:", round(macro_f1, 4))
            print(classification_report(y_test, preds, digits=4, zero_division=0))

    # Model Save
    model_out = args.model_out
    
    if model_out.startswith("gs://"):
        # Save locally to temp then upload
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as tmp:
            temp_model_path = Path(tmp.name)
        
        joblib.dump(pipeline, temp_model_path)
        print("[train] saved temp model:", temp_model_path)
        
        upload_model(temp_model_path, model_out)
        
        # Cleanup
        temp_model_path.unlink()
    else:
        model_path = Path(model_out)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, model_path)
        print("[train] saved model:", model_path)


if __name__ == "__main__":
    main()
