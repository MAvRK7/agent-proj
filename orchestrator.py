from fx.analysis import analyze_fx
from fx.risk import confidence_score
from logger import log_event
from llm.intent import classify_intent
from llm.calc import safe_eval
from llm.calc import extract_math_expression
from llm.explainer import generate_fx_explanation
from llm.general import general_llm_chat
from pricing import estimate_model_cost
import re


def run_fx_pipeline():
    data = analyze_fx()
    data["confidence"] = confidence_score(data)
    return data

def extract_expression(text):
    match = re.search(r"[-+*/().^0-9]+", text)
    if match:
        return match.group().strip()
    return None



def orchestrator(user_input: str, conversation_history):
    conversation_history.append({
        "role":"user",
        "content":user_input
        })
    intent = classify_intent(user_input)
    final_response = None
    expr = extract_expression(user_input)

    # ------------
    # math/calc route
    # ------------

    if intent == "math":
        try: 
            result = safe_eval(user_input)
            final_response = f"The result of '{user_input} is: {result}'"
            # return f"The result of '{user_input}' is: {result}"
        except Exception as e:
            return f"Sorry, I couldn't evaluate that expression. Please make sure it's a valid mathematical expression. Error: {str(e)}"
        

    # ------------
    # fx route
    # ------------

    if intent == "fx":
        fx_data = run_fx_pipeline()

        llm_response = generate_fx_explanation(fx_data, fx_data["scenario"], conversation_history)

        final_response = llm_response["content"]

        input_tokens = llm_response["input_tokens"]
        output_tokens = llm_response["output_tokens"]
        total_tokens = llm_response["total_tokens"]
        model_used = llm_response["model"]

        cost_estimate = estimate_model_cost(
            model_used,
            input_tokens,
            output_tokens,
        )

        # Determine predicted direction based on prob_up
        predicted_direction = "up" if fx_data["prob_up"] > 0.5 else "down"
        predicted_rate = fx_data["current_rate"]

        # logging
        log_event(
            user_query=user_input,
            intent="fx",
            decision=fx_data["decision"],
            prob_up=fx_data["prob_up"],
            confidence=fx_data["confidence"],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_estimate=cost_estimate,
            latency=llm_response["latency"],
            model_used=llm_response["model"],
            predicted_rate=predicted_rate,
            predicted_direction=predicted_direction,
        )

        return llm_response["content"]

    # ------------
    # general explain route
    # ------------

    elif intent == "explain":
        llm_response = general_llm_chat(conversation_history)
        final_response = llm_response["content"]

        input_tokens = llm_response["input_tokens"]
        output_tokens = llm_response["output_tokens"]
        total_tokens = llm_response["total_tokens"]
        model_used = llm_response["model"]

        cost_estimate = estimate_model_cost(
            model_used,
            input_tokens,
            output_tokens,
        )

        log_event(
            user_query=user_input,
            intent="explain",
            decision="N/A",
            prob_up=0.0,
            confidence=0.0,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_estimate=cost_estimate,
            latency=llm_response["latency"],
            model_used=llm_response["model"],
        )

        return llm_response["content"]

    # ------------
    # Fallback
    # ------------


    else:
        return "Sorry, I couldn't understand your query. Please ask about foreign exchange decisions or request an explanation on a topic."
    
    '''
    conversation_history.append({
        "role":"assistant",
        "content":final_response,
    })

    return final_response
    '''