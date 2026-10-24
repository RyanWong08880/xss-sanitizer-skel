import tempfile
import unittest
from pathlib import Path

from train import read_examples, select_examples


class ReadExamplesTests(unittest.TestCase):
    def read_csv(self, content: str) -> tuple[list[str], list[int]]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dataset.csv"
            path.write_text(content, encoding="utf-8")
            return read_examples(path)

    def test_reads_kaggle_columns_and_removes_same_label_duplicates(self):
        rows = ["Sentence,Label"]
        rows.extend(f'"benign sample {index}",0' for index in range(5))
        rows.extend(f'"xss sample {index}",1' for index in range(5))
        rows.append('"benign sample 0",0')

        texts, labels = self.read_csv("\n".join(rows))

        self.assertEqual(len(texts), 10)
        self.assertEqual(labels.count(0), 5)
        self.assertEqual(labels.count(1), 5)

    def test_rejects_conflicting_duplicate_labels(self):
        rows = ["Sentence,Label"]
        rows.extend(f'"benign sample {index}",0' for index in range(5))
        rows.extend(f'"xss sample {index}",1' for index in range(5))
        rows.append('"benign sample 0",1')

        with self.assertRaisesRegex(ValueError, "conflicting labels"):
            self.read_csv("\n".join(rows))

    def test_rejects_unexpected_label_values(self):
        rows = ["Sentence,Label"]
        rows.extend(f'"benign sample {index}",0' for index in range(5))
        rows.extend(f'"xss sample {index}",1' for index in range(4))
        rows.append('"xss sample 4",unknown')

        with self.assertRaisesRegex(ValueError, "expected 0 or 1"):
            self.read_csv("\n".join(rows))

    def test_select_examples_is_deterministic_and_stratified(self):
        texts = [f"benign {index}" for index in range(20)]
        texts.extend(f"xss {index}" for index in range(20))
        labels = [0] * 20 + [1] * 20

        first_texts, first_labels = select_examples(texts, labels, 20)
        second_texts, second_labels = select_examples(texts, labels, 20)

        self.assertEqual(first_texts, second_texts)
        self.assertEqual(first_labels, second_labels)
        self.assertEqual(first_labels.count(0), 10)
        self.assertEqual(first_labels.count(1), 10)

    def test_rejects_too_small_stratified_sample(self):
        with self.assertRaisesRegex(ValueError, "at least 10"):
            select_examples(["example"] * 10, [0, 1] * 5, 9)


if __name__ == "__main__":
    unittest.main()
