# Intent classifier

This optional local service fine-tunes DistilBERT to estimate whether an HTML
input resembles the benign or XSS examples in the selected dataset. The result
is advisory only. It does not replace or alter `Sanitizer.sanitize()`.

## Dataset

The training script expects the Kaggle dataset
[Cross site scripting XSS dataset for Deep learning](https://www.kaggle.com/datasets/syedsaqlainhussain/cross-site-scripting-xss-dataset-for-deep-learning),
whose `Sentence` and `Label` columns describe the examples and binary labels
(`0` benign, `1` XSS). Kaggle currently lists the dataset license as **Unknown**.
Use it only if you have permission or rights to do so. Download it from Kaggle
and place the CSV at `data/XSS_dataset.csv`; dataset files are git-ignored.

## Train

From this directory, create an environment and install the dependencies:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
python train.py --dataset data/XSS_dataset.csv
```

The first install selects PyTorch's CPU-only wheels. If you want GPU training,
install the PyTorch build for your hardware using the official
[PyTorch install selector](https://pytorch.org/get-started/locally/) instead.

Training downloads the pretrained
[DistilBERT base uncased](https://huggingface.co/distilbert/distilbert-base-uncased)
model from Hugging Face, makes a stratified 80/20 split, fine-tunes for two
epochs by default, reports held-out metrics, and saves the best model to
`model/`. Override the epoch count with `--epochs`. To train a quick stratified
2,000-example smoke model instead of using all examples, add
`--max-examples 2000`; treat its metrics as preliminary.

## Run the API

Start the service from this directory:

```sh
. .venv/bin/activate
uvicorn api:app --host 127.0.0.1 --port 8000
```

Serve the repository root separately at `http://localhost:8080` and click
**Analyze intent** in the sanitizer demo. The service accepts JSON
`{"text":"..."}` at `POST /api/analyze`; it returns a `label` and confidence
score. Inputs are truncated to 256 model tokens. The API binds to loopback,
accepts browser requests only from the default local origins on port 8080, and
does not persist submitted inputs. To serve the UI from a different local
origin, set `INTENT_ALLOWED_ORIGINS` to a comma-separated list of exact origins.

## Limitations

The output depends on the dataset's coverage, labeling, and class balance;
confidence is not calibrated and is not a security guarantee. The classifier
may miss novel or obfuscated inputs or flag benign markup. Keep the sanitizer
as the security boundary and review evaluation metrics before relying on the
classifier even for triage.
