"""Unit tests for proof_state.statement_to_proof_state."""
import pytest
from exp.eval.lib.proof_state import statement_to_proof_state


def ps(stmt: str) -> str:
    return statement_to_proof_state(stmt)


# -- Single binder ------------------------------------------------------------

def test_single_binder_simple():
    assert ps("(x: Nat) : x > 0") == "x : Nat\n⊢ x > 0"


def test_single_binder_list_type():
    result = ps("(xs: List α) : (dropWhile (fun _ => False) xs = xs)")
    assert result == "xs : List α\n⊢ (dropWhile (fun _ => False) xs = xs)"


def test_single_binder_arrow_in_type():
    result = ps("(p: α → Bool) : p x = true")
    assert result == "p : α → Bool\n⊢ p x = true"


# -- Multiple binders ---------------------------------------------------------

def test_two_binders():
    result = ps("(x: Nat) (xs: List Nat) : x ∈ ins1 x xs")
    assert result == "x : Nat\nxs : List Nat\n⊢ x ∈ ins1 x xs"


def test_three_binders():
    result = ps("(p: α → Bool) (xs: List α) (ys: List α) : (filter p (xs ++ ys) = (filter p xs) ++ (filter p ys))")
    assert result == (
        "p : α → Bool\n"
        "xs : List α\n"
        "ys : List α\n"
        "⊢ (filter p (xs ++ ys) = (filter p xs) ++ (filter p ys))"
    )


def test_four_binders_mixed_types():
    result = ps("(n: Nat) (xs: List α) (ys: List β) : (drop n (zip' xs ys) = zip' (drop n xs) (drop n ys))")
    assert result == (
        "n : Nat\n"
        "xs : List α\n"
        "ys : List β\n"
        "⊢ (drop n (zip' xs ys) = zip' (drop n xs) (drop n ys))"
    )


# -- Multi-name binder --------------------------------------------------------

def test_multi_name_binder():
    result = ps("(x y: Nat) : x + y = y + x")
    assert result == "x : Nat\ny : Nat\n⊢ x + y = y + x"


def test_multi_name_binder_plus_single():
    result = ps("(x y: Nat) (xs: List Nat) : x + y ∈ xs")
    assert result == "x : Nat\ny : Nat\nxs : List Nat\n⊢ x + y ∈ xs"


# -- No binders ---------------------------------------------------------------

def test_no_binders_with_colon():
    result = ps(": True")
    assert result == "⊢ True"


def test_no_binders_no_colon():
    result = ps("True")
    assert result == "⊢ True"


# -- Colon inside conclusion --------------------------------------------------

def test_colon_in_conclusion_parens():
    # conclusion itself contains '=' inside parens — the top-level ':' is still found
    result = ps("(xs: List Nat) : (count 0 xs = count 0 (sort xs))")
    assert result == "xs : List Nat\n⊢ (count 0 xs = count 0 (sort xs))"


def test_implication_in_conclusion():
    result = ps(
        "(xs: List α) (ys: List β) : "
        "(length xs = length ys) → (zip' (reverse xs) (reverse ys) = reverse (zip' xs ys))"
    )
    assert result == (
        "xs : List α\n"
        "ys : List β\n"
        "⊢ (length xs = length ys) → (zip' (reverse xs) (reverse ys) = reverse (zip' xs ys))"
    )


def test_nested_implication_conclusion():
    result = ps("(x: Nat) (xs: List Nat) : (sorted xs → sorted (insort x xs))")
    assert result == "x : Nat\nxs : List Nat\n⊢ (sorted xs → sorted (insort x xs))"


# -- Whitespace tolerance -----------------------------------------------------

def test_leading_trailing_whitespace():
    result = ps("  (x: Nat) : x = x  ")
    assert result == "x : Nat\n⊢ x = x"


def test_space_around_colon_in_binder():
    result = ps("(x : Nat) : x = x")
    assert result == "x : Nat\n⊢ x = x"
