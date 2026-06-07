"""Unit tests for the safe calculator tool."""

from __future__ import annotations

import math

import pytest

from supervisor.tools import UnsafeExpressionError, safe_eval


class TestSafeEvalArithmetic:
    def test_add(self) -> None:
        assert safe_eval("2 + 2") == 4.0

    def test_sub(self) -> None:
        assert safe_eval("10 - 3") == 7.0

    def test_mul(self) -> None:
        assert safe_eval("17 * 32") == 544.0

    def test_div(self) -> None:
        assert safe_eval("10 / 4") == 2.5

    def test_floor_div(self) -> None:
        assert safe_eval("10 // 3") == 3.0

    def test_mod(self) -> None:
        assert safe_eval("10 % 3") == 1.0

    def test_pow(self) -> None:
        assert safe_eval("2 ** 10") == 1024.0

    def test_unary_neg(self) -> None:
        assert safe_eval("-5") == -5.0

    def test_unary_pos(self) -> None:
        assert safe_eval("+5") == 5.0

    def test_parens(self) -> None:
        assert safe_eval("(2 + 3) * 4") == 20.0

    def test_nested(self) -> None:
        assert safe_eval("((1 + 2) * (3 + 4)) - 5") == 16.0


class TestSafeEvalFunctions:
    def test_pi(self) -> None:
        assert safe_eval("pi") == math.pi

    def test_e(self) -> None:
        assert safe_eval("e") == math.e

    def test_sqrt(self) -> None:
        assert safe_eval("sqrt(16)") == 4.0

    def test_log(self) -> None:
        assert safe_eval("log(e)") == pytest.approx(1.0, abs=1e-9)

    def test_min_max(self) -> None:
        assert safe_eval("min(1, 2, 3)") == 1.0
        assert safe_eval("max(1, 2, 3)") == 3.0

    def test_abs(self) -> None:
        assert safe_eval("abs(-5)") == 5.0

    def test_round(self) -> None:
        assert safe_eval("round(3.7)") == 4.0


class TestSafeEvalRejects:
    def test_empty(self) -> None:
        with pytest.raises(UnsafeExpressionError):
            safe_eval("")

    def test_whitespace(self) -> None:
        with pytest.raises(UnsafeExpressionError):
            safe_eval("   ")

    def test_attribute_access(self) -> None:
        with pytest.raises(UnsafeExpressionError):
            safe_eval("__import__('os').system('echo pwned')")

    def test_unknown_function(self) -> None:
        with pytest.raises(UnsafeExpressionError):
            safe_eval("eval('2+2')")

    def test_string_literal(self) -> None:
        with pytest.raises(UnsafeExpressionError):
            safe_eval("'hello'")

    def test_unknown_name(self) -> None:
        with pytest.raises(UnsafeExpressionError):
            safe_eval("x")

    def test_bool_rejected(self) -> None:
        with pytest.raises(UnsafeExpressionError):
            safe_eval("True")

    def test_keyword_args_rejected(self) -> None:
        with pytest.raises(UnsafeExpressionError):
            safe_eval("round(1.5, ndigits=0)")

    def test_incomplete_expression(self) -> None:
        with pytest.raises(UnsafeExpressionError):
            safe_eval("1 +")

    def test_list_literal_rejected(self) -> None:
        with pytest.raises(UnsafeExpressionError):
            safe_eval("[1, 2, 3]")

    def test_dict_literal_rejected(self) -> None:
        with pytest.raises(UnsafeExpressionError):
            safe_eval("{'a': 1}")
