# logger.py

import json
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("logs.jsonl")


def log_event(
    user_query: str,
    intent: str,
    decision: str,
    prob_up: float,
    confidence: float,
    input_tokens:int,
    output_tokens: int,
    total_tokens:int,
    cost_estimate:int,
    latency: float,
    model_used: str,
    predicted_rate: float = None,
    predicted_direction: str = None,
):
    """
    Writes a structured JSON log entry to logs.jsonl
    """

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_query": user_query,
        "intent": intent,
        "decision": decision,
        "prob_up": round(prob_up, 4),
        "confidence": round(confidence, 4),
        "input_tokens":input_tokens,
        "output_tokens": output_tokens,
        "total_tokens":total_tokens,
        "cost_estimate":round(cost_estimate,6),
        "latency": round(latency, 3),
        "model_used": model_used,
    }

    # Add prediction details if provided
    if predicted_rate is not None:
        log_entry["predicted_rate"] = round(predicted_rate, 4)
    if predicted_direction is not None:
        log_entry["predicted_direction"] = predicted_direction

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")
