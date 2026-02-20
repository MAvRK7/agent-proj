import json

MODEL_PRICING = {
    # in this project we're using the free one, but if the non free one had been used
    "stepfun/step-3.5-flash:free": { 
        "input_per_million":0.10,
        "output_per_million":0.30,
    },
    "mistral-small-latest": {
        # using conservative upper bound for safety
        "input_per_million":0.10,
        "output_per_million":0.20
    },
    # more can be added here
}

def estimate_model_cost(model:str, input_tokens:int, output_tokens:int) -> float:
    pricing = MODEL_PRICING.get(model)

    if not pricing:
        # default fallback pricing
        pricing = {
            "input_per_million":0.10,
            "output_per_million":0.30,
        }
    input_cost = (input_tokens/ 1_000_000) * pricing["input_per_million"]
    output_cost = (output_tokens/ 1_000_000) * pricing["output_per_million"]

    return round(input_cost + output_cost,6)

def summarize_costs(log_file="logs.jsonl"):
    total_cost=0
    total_queries=0

    with open(log_file,"r",encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                total_cost += entry.get("cost_estimate",0)
                total_queries+=1

    avg_cost = total_cost/total_queries if total_queries else 0

    return {
        "total_cost": round(total_cost,4),
        "avg_cost": round(avg_cost,6),
        "total_queries" : total_queries,
    }

if __name__ == "__main__":
    summary = summarize_costs()
    print(f"Monthly costs: ${summary['total_cost']}")
    print(f"Average cost per query: ${summary['avg_cost']}")
    print(f"Total queries: {summary['total_queries']}")


