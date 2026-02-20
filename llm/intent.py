from llm.client import chat_with_fallback

def classify_intent(user_input):
    prompt = f"""You are an intent classification model. Classify the user's intent into one of the following categories based on the query:
1. fx - related to foreign exchange decisions
2. explain - asking for an explanation of a concept 
3. math - asking for a mathematical calculation (e.g., 2+2, 5*7, 10/3)

Respond with ONLY one word: fx, explain or math.

User query: "{user_input}"
"""

    response = chat_with_fallback(
        messages=[
            {"role": "system", "content": "You are a helpful assistant that classifies user intent."},
            {"role": "user", "content": prompt},
        ]
    )

    intent = response["content"].strip().lower()
    if intent not in ["fx", "explain", "math"]:
        return "unknown"
    return intent

