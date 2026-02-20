import time
import random
from openai import OpenAI
from mistralai import Mistral
import os
from dotenv import load_dotenv

# --LLM Part--
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY missing in environment")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY missing in environment")


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
        start = time.time()
        response = openrouter.chat.completions.create(
            model=model_primary,
            messages=messages,
        )

        latency = time.time() - start
        return {
            "content": response.choices[0].message.content,
            "tokens":{
                "input":response.usage.prompt_tokens,
                "output":response.usage.completion_tokens,
                "total":response.usage.total_tokens,
            },
            "latency": latency,
            "model": model_primary,
        }

    except Exception as e:
        print("⚠️ OpenRouter failed, falling back to Mistral:", e)

        # Optional small delay so you don't immediately re-hit limits
        time.sleep(1 + random.random())

        # FALLBACK: Mistral
        start = time.time()
        res = mistral.chat.complete(
            model="mistral-small-latest",
            messages=messages,
            stream=False,
        )
        latency = time.time() - start
        return {
            "content": res.choices[0].message.content,
            "tokens": {
                "input":res.usage.prompt_tokens,
                "output":res.usage.completion_tokens,
                "total":res.usage.total_tokens,
            },
            "latency": latency,
            "model": "mistral-small-latest",
        }
