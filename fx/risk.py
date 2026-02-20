

def risk_band_analysis(forecast, current_rate):
    lower_band = current_rate * 0.98  # 2% below current
    upper_band = current_rate * 1.02  # 2% above current

    within_band = sum(1 for x in forecast if lower_band <= x <= upper_band) / len(
        forecast
    )
    return within_band

def confidence_score(result):
    prob_strength = abs(result["prob_up"] - 0.5) * 2  # scaled 0-1
    volatility_penalty = result["volatility"]

    score = 0.5 + (prob_strength * 0.4) - (volatility_penalty * 0.1)
    return round(max(min(score, 1.0), 0.1), 2)