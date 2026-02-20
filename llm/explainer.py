from .client import chat_with_fallback

def generate_fx_explanation(fx_data, scenario, conversation_history):
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
    messages = [
        {"role": "system", "content": "You are a helpful financial assistant."}
    ] + conversation_history[-6:] + [
        {"role": "user", "content": prompt}
    ]

    response = chat_with_fallback(messages)
    tokens = response["tokens"]

    return {
        "content": response["content"],   # text
        "input_tokens":tokens["input"],
        "output_tokens":tokens["output"],
        "total_tokens":tokens["total"],
        "latency": response.get("latency", 0.0),
        "model": response.get("model", "unknown")
    }