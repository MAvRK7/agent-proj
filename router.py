'''
def auto_tool_router(user_input:str):

    # math detection
    expr = extract_math_expression(user_input)
    if expr:
        try:
            return calculator_tool(expr)
        except Exception as e:
            return f"Sorry, I couldn't evaluate that expression. Please make sure it's a valid mathematical expression. Error: {str(e)}"
        
    # fx detection
    if any(word in user_input.lower() for word in ["exchange rate", "forex", "currency", "fx"]):
        return fx_tool(user_input)
'''