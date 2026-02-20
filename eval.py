"""
eval.py - Evaluation script for FX predictions

Usage:
    python eval.py                    # Evaluate all predictions
    python eval.py --backtest         # Backtest the model on historical data
"""

import json
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

from fx.data import load_cache, get_current_rate


LOG_FILE = Path("logs.jsonl")


def load_predictions(days=None):
    predictions = []
    if not LOG_FILE.exists():
        return predictions
    with LOG_FILE.open("r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if entry.get("intent") == "fx":
                    predictions.append(entry)
            except:
                continue
    if days:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
        predictions = [p for p in predictions if datetime.fromisoformat(p["timestamp"]) >= cutoff]
    return predictions


def get_historical_rate(target_date):
    cache = load_cache()
    key = f"{target_date}_inr_aud"
    if key in cache:
        return cache[key]
    try:
        return get_current_rate(base="inr", target="aud", date=target_date)
    except:
        return None


def evaluate_prediction(pred):
    pred_date = pred.get("timestamp", "")[:10]
    pred_rate = pred.get("predicted_rate")
    pred_dir = pred.get("predicted_direction")
    if not pred_date or not pred_rate:
        return None
    try:
        eval_date = (datetime.strptime(pred_date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")
    except:
        return None
    actual = get_historical_rate(eval_date)
    if actual is None:
        return None
    actual_dir = "up" if actual > pred_rate else "down"
    return {
        "prediction_date": pred_date,
        "predicted_rate": pred_rate,
        "actual_rate": actual,
        "predicted_direction": pred_dir,
        "actual_direction": actual_dir,
        "was_correct": pred_dir == actual_dir,
        "confidence": pred.get("confidence", 0.5),
    }


def calc_metrics(evaled):
    if not evaled:
        return {"rolling_accuracy": 0, "avg_confidence_when_correct": 0, "avg_confidence_when_wrong": 0, "total": 0}
    correct = sum(1 for x in evaled if x["was_correct"])
    acc = correct / len(evaled)
    correct_confs = [x["confidence"] for x in evaled if x["was_correct"]]
    wrong_confs = [x["confidence"] for x in evaled if not x["was_correct"]]
    return {
        "rolling_accuracy": round(acc, 4),
        "avg_confidence_when_correct": round(mean(correct_confs), 4) if correct_confs else 0,
        "avg_confidence_when_wrong": round(mean(wrong_confs), 4) if wrong_confs else 0,
        "total": len(evaled),
        "correct": correct,
    }


def run_eval(days=None, verbose=False):
    print(f"\n{'='*50}")
    print("EVALUATING SAVED PREDICTIONS")
    print(f"{'='*50}")
    preds = load_predictions(days)
    print(f"Found {len(preds)} predictions")
    evaled = [evaluate_prediction(p) for p in preds]
    evaled = [x for x in evaled if x]
    print(f"Evaluated: {len(evaled)}")
    if not evaled:
        print("No results")
        return calc_metrics([])
    m = calc_metrics(evaled)
    print(f"\nAccuracy: {m['rolling_accuracy']*100:.1f}% ({m['correct']}/{m['total']})")
    print(f"Conf correct: {m['avg_confidence_when_correct']:.3f}")
    print(f"Conf wrong:   {m['avg_confidence_when_wrong']:.3f}")
    if verbose:
        for e in evaled:
            s = "✓" if e["was_correct"] else "✗"
            print(f"{s} {e['prediction_date']}: {e['predicted_direction']} -> {e['actual_direction']}")
    return m


def run_backtest(interval=2):
    import math
    from statistics import mean
    from fx.analysis import compute_moving_average, compute_rsi, compute_bollinger_position
    from fx.sim import monte_carlo_simulation

    print(f"\n{'='*50}")
    print("BACKTESTING IMPROVED MODEL")
    print(f"{'='*50}")

    cache = load_cache()
    dates = sorted([datetime.strptime(k.split("_")[0], "%Y-%m-%d").date() for k in cache.keys() if k.endswith("_inr_aud")])
    print(f"Data: {len(dates)} days ({dates[0]} to {dates[-1]})")

    if len(dates) < 48:
        print("Need more data")
        return calc_metrics([])

    rate_map = {d: cache[f"{d.strftime('%Y-%m-%d')}_inr_aud"] for d in dates}
    results = []

    # Make predictions every 'interval' days, starting after we have 40 days of data
    for i in range(40, len(dates) - 7, interval):
        # Get 40 days of history
        hist = [rate_map[dates[j]] for j in range(i - 40, i)]
        if len(hist) < 40:
            continue

        current = hist[-1]
        pred_date = dates[i]

        # Calculate features
        log_returns = [math.log(hist[j] / hist[j-1]) for j in range(1, len(hist))]
        drift = mean(log_returns)
        vol = (sum((x - drift) ** 2 for x in log_returns) / len(log_returns)) ** 0.5

        ma7 = compute_moving_average(hist, 7)[-1]
        ma30 = compute_moving_average(hist, 30)[-1]
        momentum = current - ma7
        slope = hist[-1] - hist[-8]
        vol = (sum((x - mean(hist[-30:])) ** 2 for x in hist[-30:]) / 30) ** 0.5
        rsi = compute_rsi(hist)
        bb = compute_bollinger_position(current, hist)

        # Monte Carlo
        fcst = monte_carlo_simulation(current, drift, vol, days=7)
        prob_mc = sum(1 for x in fcst if x > current) / len(fcst)

        # Mean reversion
        mr = 0.5
        if current > ma30 * 1.01:
            mr = 0.2
        elif current < ma30 * 0.99:
            mr = 0.8

        # Momentum
        mom = 0.5 + (momentum / vol * 0.3) if vol > 0 else 0.5

        # Trend
        tr = 0.5 + (slope / vol * 0.2) if vol > 0 else 0.5

        # RSI
        if rsi > 70:
            rsi_prob = 0.25
        elif rsi < 30:
            rsi_prob = 0.75
        else:
            rsi_prob = 0.5

        # Bollinger
        bb_prob = 1 - bb

        # Ensemble
        prob = 0.20*prob_mc + 0.25*mr + 0.15*mom + 0.15*tr + 0.15*rsi_prob + 0.10*bb_prob

        # Get actual 7 days later
        actual = rate_map[dates[i + 7]]

        pred_dir = "up" if prob > 0.5 else "down"
        actual_dir = "up" if actual > current else "down"
        correct = pred_dir == actual_dir

        # Confidence
        ps = abs(prob - 0.5) * 2
        conf = round(max(min(0.5 + ps*0.4 - vol*0.1, 1.0), 0.1), 2)

        results.append({
            "prediction_date": pred_date.strftime("%Y-%m-%d"),
            "predicted_rate": current,
            "actual_rate": actual,
            "predicted_direction": pred_dir,
            "actual_direction": actual_dir,
            "was_correct": correct,
            "confidence": conf,
        })

    print(f"Predictions: {len(results)}")
    m = calc_metrics(results)
    print(f"\n{'='*50}")
    print("BACKTEST RESULTS")
    print(f"{'='*50}")
    print(f"Accuracy:    {m['rolling_accuracy']*100:.1f}% ({m['correct']}/{m['total']})")
    print(f"Conf (correct): {m['avg_confidence_when_correct']:.3f}")
    print(f"Conf (wrong):   {m['avg_confidence_when_wrong']:.3f}")
    return m


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--interval", type=int, default=2)
    args = parser.parse_args()

    if args.backtest:
        run_backtest(args.interval)
    else:
        run_eval(args.days, args.verbose)


if __name__ == "__main__":
    main()

