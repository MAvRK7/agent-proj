#============================
# This is the basic version of the project 
#============================

import requests
import datetime
from statistics import mean
import json
import math
import random
import time
from openai import OpenAI
from mistralai import Mistral
import os
from dotenv import load_dotenv

# ===============================
# CONFIG and CACHE
# ===============================

PRIMARY_URL = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/{api_version}/currencies/{base}.json"
FALLBACK_URL = (
    "https://{date}.currency-api.pages.dev/{api_version}/currencies/{base}.json"
)
# ---Cache part---
CACHE_FILE = "fx_cache.json"


def load_cache():
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


# ---End Cache part---
# --AI Part--
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY missing in environment")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY missing in environment")

# ===============================
# FX Data Fetching
# ===============================


def get_current_rate(base="inr", target="aud", date="latest", api_version="v1"):
    # Cache check first
    cache = load_cache()
    cache_key = f"{date}_{base}_{target}"
    if cache_key in cache:
        return cache[cache_key]

    primary_url = PRIMARY_URL.format(date=date, api_version=api_version, base=base)
    fallback_url = FALLBACK_URL.format(date=date, api_version=api_version, base=base)

    try:
        response = requests.get(primary_url, timeout=5)
        response.raise_for_status()
        rate = response.json()[base][target]

    except Exception:
        response = requests.get(fallback_url, timeout=5)
        response.raise_for_status()
        rate = response.json()[base][target]

    # save to cache if its not latest
    if date != "latest":
        cache[cache_key] = rate
        save_cache(cache)

    return rate


def get_historical_rates(base="inr", target="aud", days=40):
    rates = []
    # Using a cache means this loop will eventually run instantly
    cache = load_cache()

    # identify which dates we need to fetch
    print(f"Checking cache for {days} days of history...")

    for i in range(days, 0, -1):
        date = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime(
            "%Y-%m-%d"
        )
        try:
            # We use the same get_current_rate function but pass a specific date
            rate = get_current_rate(base=base, target=target, date=date)
            rates.append(rate)
        except Exception as e:
            print(f"Skipping {date} due to fetch error.{e}")
            continue
    return rates


# ===============================
# ANALYSIS
# ===============================


def compute_moving_average(rates, window):
    if len(rates) < window:
        raise ValueError(f"Need {window} days of data, but only have {len(rates)}.")
    return [mean(rates[i : i + window]) for i in range(len(rates) - window + 1)]


def analyze_fx():
    current_rate = get_current_rate()
    # Fetch 40 days to ensure we have enough for a 30-day window
    historical_data = get_historical_rates(days=40)

    # Convert rates into log returns
    log_returns = [
        math.log(historical_data[i] / historical_data[i - 1])
        for i in range(1, len(historical_data))
    ]
    drift = mean(log_returns)
    volatility = (
        sum((x - drift) ** 2 for x in log_returns) / len(log_returns)
    ) ** 0.5  # stdev of log returns

    # Calculate Moving Avgs
    ma7_list = compute_moving_average(historical_data, window=7)
    ma30_list = compute_moving_average(historical_data, window=30)

    # Get the latest values from the lists
    latest_ma7 = ma7_list[-1]
    latest_ma30 = ma30_list[-1]

    # Momentum
    momentum = current_rate - latest_ma7

    # Trend slope (last 7 days)
    slope = historical_data[-1] - historical_data[-8]

    # Volatility (std dev of last 30 days)
    volatility = (
        sum((x - mean(historical_data[-30:])) ** 2 for x in historical_data[-30:]) / 30
    ) ** 0.5

    forecast7d = monte_carlo_simulation(current_rate, drift, volatility, days=7)
    scenario = scenario_comparison(current_rate, forecast7d, amount_aud=1000)

    expected_future = mean(forecast7d)
    prob_up = sum(1 for x in forecast7d if x > current_rate) / len(forecast7d)

    # Risk band analysis
    risk_band_confidence = risk_band_analysis(forecast7d, current_rate)

    # Decision Logic

    if prob_up > 0.6:
        decision = "wait (expected improvement)"
    elif prob_up < 0.4:
        decision = "send now (expected decline)"
    else:
        decision = "neutral"

    if risk_band_confidence < 0.5:
        risk = "high volatility (low confidence)"
    elif risk_band_confidence < 0.75:
        risk = "moderate volatility (medium confidence)"
    else:
        risk = "low volatility (higher confidence)"

    # IMPORTANT: These keys must match generate_response exactly
    return {
        "current_rate": current_rate,
        "ma_7": latest_ma7,
        "ma_30": latest_ma30,
        "momentum": momentum,
        "slope": slope,
        "volatility": volatility,
        "decision": decision,
        "prob_up": prob_up,
        "drift": drift,
        "risk_band_confidence": risk_band_confidence,
        "risk": risk,
        "forecast7d": forecast7d,
        "expected_7d": expected_future,
        "scenario": scenario,
    }


def monte_carlo_simulation(current_rate, drift, volatility, days=30, simulations=1000):
    results = []
    for _ in range(simulations):
        price = current_rate
        for _ in range(days):
            shock = random.gauss(drift, volatility)
            price *= math.exp(shock)
        results.append(price)
    return results


def risk_band_analysis(forecast, current_rate):
    lower_band = current_rate * 0.98  # 2% below current
    upper_band = current_rate * 1.02  # 2% above current

    within_band = sum(1 for x in forecast if lower_band <= x <= upper_band) / len(
        forecast
    )
    return within_band


def scenario_comparison(current_rate, forecast_results, amount_aud=1000):
    expected_rate = sum(forecast_results) / len(forecast_results)

    inr_today = amount_aud * current_rate
    inr_expected = amount_aud * expected_rate

    difference = inr_expected - inr_today

    return {
        "amount_aud": amount_aud,
        "inr_today": round(inr_today, 2),
        "inr_expected_7d": round(inr_expected, 2),
        "difference": round(difference, 2),
    }


# ===============================
# Confidence Model
# ===============================


def confidence_score(result):
    prob_strength = abs(result["prob_up"] - 0.5) * 2  # scaled 0-1
    volatility_penalty = result["volatility"]

    score = 0.5 + (prob_strength * 0.4) - (volatility_penalty * 0.1)
    return round(max(min(score, 1.0), 0.1), 2)


# ===============================
# LLM client
# ===============================
openrouter = OpenAI(  # Primary
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

mistral = Mistral(  # secondary
    api_key=os.getenv("MISTRAL_API_KEY", "")
)

# ===============================
# 7. Chat with fallback
# ===============================


def chat_with_fallback(messages, model_primary="stepfun/step-3.5-flash:free"):
    try:
        # PRIMARY: OpenRouter
        response = openrouter.chat.completions.create(
            model=model_primary,
            messages=messages,
        )
        return response.choices[0].message.content

    except Exception as e:
        print("⚠️ OpenRouter failed, falling back to Mistral:", e)

        # Optional small delay so you don't immediately re-hit limits
        time.sleep(1 + random.random())

        # FALLBACK: Mistral
        res = mistral.chat.complete(
            model="mistral-small-latest",
            messages=messages,
            stream=False,
        )
        return res.choices[0].message.content


# ===============================
# RESPONSE GENERATOR
# ===============================


def generate_response(result):
    """
    recommendation_map = {
        "very strong uptrend": "Send INR, Its Great!",
        "strong uptrend": "INR is strengthening consistently. Consider sending soon.",
        "strong downtrend": "INR is weakening consistently. Hold off on sending.",
        "short-term spike": "INR has spiked recently. Monitor closely for a potential pullback.",
        "short-term dip": "INR has dipped recently. Monitor closely for a potential rebound.",
        "stable": "INR is stable. No strong signals either way."
    }

    rec = recommendation_map.get(result["decision"].lower())
    """

    return f"""
INR → AUD Analysis
------------------
Current Rate:     {result["current_rate"]:.6f}
7-Day Average:    {result["ma_7"]:.6f}
30-Day Average:   {result["ma_30"]:.6f}


Decision:         {result["decision"]}
Confidence:       {int(result["confidence"] * 100)}%
drift:            {result["drift"]:.6f}
volatility:       {result["volatility"]:.4f}
Risk Level:       {result["risk"]}
"""


def generate_fx_explanation(fx_data, scenario):
    prompt = f"""
You are a financial assistant helping an international student decide when to send money from INR to AUD.

Current rate: {fx_data["current_rate"]}
Expected 7-day rate: {fx_data["expected_7d"]}
Probability rate improves: {round(fx_data["prob_up"] * 100, 2)}%
Volatility: {fx_data["volatility"]}

If sending {scenario["amount_aud"]} AUD:
INR today: {scenario["inr_today"]}
INR expected in 7 days: {scenario["inr_expected_7d"]}
Difference: {scenario["difference"]}

Decision model suggests: {fx_data["decision"]}

Explain:
1. What this means in simple words
2. Whether waiting makes sense
3. Risks involved
Keep it concise but intelligent.
"""

    response = chat_with_fallback(
        messages=[
            {"role": "system", "content": "You are a helpful financial assistant."},
            {"role": "user", "content": prompt},
        ]
    )

    return response


# ===============================
# MAIN EXECUTION
# ===============================

if __name__ == "__main__":
    try:
        # 1. Run Analysis
        data = analyze_fx()

        # 2. Add Confidence
        data["confidence"] = confidence_score(data)

        # 3. Print Result
        print(generate_response(data))

        # 4. Generate AI explanation
        explanation = generate_fx_explanation(data, data["scenario"])
        print("\n" + "=" * 50)
        print("AI Explanation:")
        print("=" * 50)
        print(explanation)

        # 5. Final structured output
        result = {
            "fx_data": data,
            "scenario": data["scenario"],
            "explanation": explanation,
        }

    except Exception as e:
        print(f"Execution Error: {e}")
