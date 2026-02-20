import ast
import operator as op
import re

# supported operators
operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.USub: op.neg,
}

def extract_math_expression(text):
    # Keep digits, operators, decimal points, parentheses and spaces
    matches = re.findall(r"[0-9+\-*/().^ ]+", text)

    if not matches:
        return None

    # Join all math-like parts
    expr = "".join(matches).strip()

    if expr == "":
        return None

    return expr


def safe_eval(expr):
    """
    Safely evaluate a mathematical expression using AST.
    Only allows basic arithmetic operations.
    """
    def eval_node(node):
        if isinstance(node, ast.Constant):  # <number>
            return node.value
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            return operators [type(node.op)](eval_node(node.left), eval_node(node.right))
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
            return operators [type(node.op)](eval_node(node.operand))
        else:
            raise TypeError(f"Unsupported expression: {ast.dump(node)}")
        
    return eval_node(ast.parse(expr, mode='eval').body)