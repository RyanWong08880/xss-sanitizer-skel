import argparse
import csv
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from datasets import Dataset
from sklearn.model_selection import train_test_split
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)


MODEL_NAME = "distilbert/distilbert-base-uncased"
LABEL_NAMES = {0: "benign", 1: "potentially_malicious"}


def read_examples(dataset_path: Path) -> tuple[list[str], list[int]]:
    with dataset_path.open(encoding="utf-8-sig", newline="") as dataset_file:
        reader = csv.DictReader(dataset_file)
        if not reader.fieldnames:
            raise ValueError("The dataset must include a CSV header row.")

        columns = {name.strip().casefold(): name for name in reader.fieldnames}
        text_column = next(
            (
                columns[name]
                for name in ("sentence", "text", "payload", "input")
                if name in columns
            ),
            None,
        )
        label_column = columns.get("label")
        if text_column is None or label_column is None:
            raise ValueError(
                "Expected text and label columns (for example, Sentence and Label)."
            )

        examples: dict[str, int] = {}
        for row_number, row in enumerate(reader, start=2):
            text = (row.get(text_column) or "").strip()
            raw_label = (row.get(label_column) or "").strip().casefold()
            if not text:
                continue
            if raw_label not in {"0", "1"}:
                raise ValueError(
                    f"Row {row_number} has label {raw_label!r}; expected 0 or 1."
                )

            label = int(raw_label)
            existing_label = examples.get(text)
            if existing_label is not None and existing_label != label:
                raise ValueError(
                    f"Duplicate text has conflicting labels at row {row_number}."
                )
            examples[text] = label

    labels = list(examples.values())
    if len(examples) < 10 or set(labels) != {0, 1}:
        raise ValueError("Need at least 10 unique examples containing both labels.")

    label_counts = Counter(labels)
    if min(label_counts.values()) < 2:
        raise ValueError("Need at least two unique examples of each label to split data.")

    return list(examples.keys()), labels


def select_examples(
    texts: list[str], labels: list[int], max_examples: int | None
) -> tuple[list[str], list[int]]:
    if max_examples is None or max_examples >= len(texts):
        return texts, labels
    if max_examples < 10:
        raise ValueError("A stratified sample must contain at least 10 examples.")

    selected_texts, _, selected_labels, _ = train_test_split(
        texts,
        labels,
        train_size=max_examples,
        random_state=42,
        stratify=labels,
    )
    return selected_texts, selected_labels


def make_metrics(prediction):
    predicted_labels = np.argmax(prediction.predictions, axis=-1)
    expected_labels = prediction.label_ids
    true_positives = int(
        np.sum((predicted_labels == 1) & (expected_labels == 1))
    )
    false_positives = int(
        np.sum((predicted_labels == 1) & (expected_labels == 0))
    )
    false_negatives = int(
        np.sum((predicted_labels == 0) & (expected_labels == 1))
    )
    precision = true_positives / max(true_positives + false_positives, 1)
    recall = true_positives / max(true_positives + false_negatives, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    accuracy = float(np.mean(predicted_labels == expected_labels))
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


class WeightedTrainer(Trainer):
    def __init__(self, *args, class_weights: torch.Tensor, **kwargs):
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(
        self, model, inputs, return_outputs=False, num_items_in_batch=None
    ):
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        weights = self.class_weights.to(outputs.logits.device)
        loss = torch.nn.functional.cross_entropy(
            outputs.logits, labels, weight=weights
        )
        return (loss, outputs) if return_outputs else loss


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fine-tune DistilBERT to classify benign and XSS-labeled HTML."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        required=True,
        help="Path to the Kaggle CSV containing Sentence and Label columns.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "model",
        help="Directory for the trained model (default: ./model).",
    )
    parser.add_argument("--epochs", type=float, default=2)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument(
        "--max-examples",
        type=int,
        help="Use a stratified subset of this size (useful for smoke training).",
    )
    args = parser.parse_args()

    texts, labels = read_examples(args.dataset)
    dataset_size = len(texts)
    texts, labels = select_examples(texts, labels, args.max_examples)
    train_texts, eval_texts, train_labels, eval_labels = train_test_split(
        texts,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def tokenize(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=args.max_length,
        )

    train_data = Dataset.from_dict({"text": train_texts, "label": train_labels})
    eval_data = Dataset.from_dict({"text": eval_texts, "label": eval_labels})
    train_data = train_data.map(tokenize, batched=True, remove_columns=["text"])
    eval_data = eval_data.map(tokenize, batched=True, remove_columns=["text"])

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=2,
        id2label=LABEL_NAMES,
        label2id={name: label for label, name in LABEL_NAMES.items()},
    )
    train_counts = Counter(train_labels)
    class_weights = torch.tensor(
        [
            len(train_labels) / (2 * train_counts[label])
            for label in range(len(LABEL_NAMES))
        ],
        dtype=torch.float,
    )
    training_args = TrainingArguments(
        output_dir=str(args.output_dir / "checkpoints"),
        num_train_epochs=args.epochs,
        learning_rate=2e-5,
        weight_decay=0.01,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=16,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        save_total_limit=1,
        report_to="none",
        seed=42,
    )
    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
        eval_dataset=eval_data,
        processing_class=tokenizer,
        compute_metrics=make_metrics,
        class_weights=class_weights,
    )
    trainer.train()
    metrics = trainer.evaluate()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))
    shutil.rmtree(args.output_dir / "checkpoints")
    print(
        f"Examples: {len(texts)} total; "
        f"Examples: {len(texts)} selected from {dataset_size} unique examples; "
        f"{len(train_texts)} train; {len(eval_texts)} test"
    )
    print(f"Evaluation metrics: {metrics}")
    print(f"Saved fine-tuned model to {args.output_dir}")


if __name__ == "__main__":
    main()
