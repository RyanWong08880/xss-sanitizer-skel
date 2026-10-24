import os
from functools import lru_cache
from pathlib import Path

import torch
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer


MODEL_DIR = Path(os.environ.get("INTENT_MODEL_DIR", Path(__file__).parent / "model"))
MAX_LENGTH = 256


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10_000)


class AnalyzeResponse(BaseModel):
    label: str
    confidence: float


@lru_cache(maxsize=1)
def load_model():
    if not MODEL_DIR.is_dir():
        raise HTTPException(
            status_code=503,
            detail=(
                "Trained intent model not found. Download the dataset and run "
                "the training command in intent/README.md first."
            ),
        )

    tokenizer = AutoTokenizer.from_pretrained(
        str(MODEL_DIR), local_files_only=True
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        str(MODEL_DIR), local_files_only=True
    )
    model.eval()
    return tokenizer, model


app = FastAPI(title="XSS Intent Classifier")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get(
        "INTENT_ALLOWED_ORIGINS",
        "http://localhost:8080,http://127.0.0.1:8080",
    ).split(","),
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    if not request.text.strip():
        raise HTTPException(status_code=422, detail="Input must not be blank.")

    tokenizer, model = load_model()
    encoded = tokenizer(
        request.text,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_LENGTH,
    )
    with torch.inference_mode():
        probabilities = torch.softmax(model(**encoded).logits, dim=-1)[0]

    predicted_label = int(torch.argmax(probabilities).item())
    label = model.config.id2label[predicted_label]
    return AnalyzeResponse(
        label=label,
        confidence=float(probabilities[predicted_label].item()),
    )
