# ===============================
# ANALYSIS
# ===============================
import math
from statistics import mean

from .sim import monte_carlo_simulation
from .data import get_current_rate, get_historical_rates
from .risk import risk_band_analysis

def compute_moving_average(rates, window):
    if len(rates) < window:
        raise ValueError(f"Need {window} days of data, but only have {len(rates)}.")
    return [mean(rates[i : i + window]) for i in range(len(rates) - window + 1)]

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