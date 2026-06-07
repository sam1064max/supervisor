"""Safe arithmetic evaluator.

The Calculator agent uses :func:`safe_eval` instead of Python's ``eval``.
The implementation parses the expression with :mod:`ast` and walks the tree,
rejecting any construct outside a strict whitelist of operators, constants,
and math functions.
"""

from __future__ import annotations

import ast
import math
import operator
from collections.abc import Callable
from typing import Any


class UnsafeExpressionError(ValueError):
    """Raised when the expression contains unsupported syntax."""


# A map from AST operator node type to the Python callable that evaluates it.
# We use a single Any-typed mapping here because ``ast.operator`` is a
# discriminated union and the operator module's callables have different
# signatures. The functions in this mapping are only ever invoked with the
# right argument types because the AST walker guarantees the shape.
_BIN_OPS: dict[type[ast.AST], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS: dict[type[ast.AST], Callable[[float], float]] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_FUNCS: dict[str, Callable[..., Any]] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sqrt": math.sqrt,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
}


def safe_eval(expression: str) -> float:
    """Evaluate a numeric expression safely.

    Supports arithmetic, parentheses, and a small whitelist of math functions.
    Rejects attribute access, subscripts, names outside the whitelist, and any
    other Python construct.
    """
    if not expression or not expression.strip():
        raise UnsafeExpressionError("empty expression")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise UnsafeExpressionError(f"invalid syntax: {exc.msg}") from exc
    return _eval_node(tree.body)


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        value = node.value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UnsafeExpressionError(f"unsupported constant: {value!r}")
        return float(value)
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise UnsafeExpressionError(f"unsupported operator: {type(node.op).__name__}")
        return float(op(_eval_node(node.left), _eval_node(node.right)))
    if isinstance(node, ast.UnaryOp):
        unary_op = _UNARY_OPS.get(type(node.op))
        if unary_op is None:
            raise UnsafeExpressionError(f"unsupported unary op: {type(node.op).__name__}")
        return float(unary_op(_eval_node(node.operand)))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise UnsafeExpressionError(f"unsupported function call: {ast.dump(node.func)}")
        args = [_eval_node(arg) for arg in node.args]
        if node.keywords:
            raise UnsafeExpressionError("keyword arguments are not supported")
        return float(_FUNCS[node.func.id](*args))
    if isinstance(node, ast.Name):
        if node.id == "pi":
            return math.pi
        if node.id == "e":
            return math.e
        raise UnsafeExpressionError(f"unsupported name: {node.id}")
    raise UnsafeExpressionError(f"unsupported node: {type(node).__name__}")
