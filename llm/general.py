from llm.client import chat_with_fallback

def general_llm_chat(conversation_history):
    messages=[
            {"role": "system", "content": "You are a helpful assistant that answers general questions."}
        ]+ conversation_history[-6:]
    response = chat_with_fallback(messages=messages)
    tokens = response["tokens"]
    return {
        "content":response["content"],
        "input_tokens":tokens["input"],
        "output_tokens":tokens["output"],
        "total_tokens":tokens["total"],
        "latency":response.get("latency",0.0),
        "model":response.get("model","unknown"),
    }