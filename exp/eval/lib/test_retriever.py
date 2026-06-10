"""Tests for retriever.py.

Fast tests use a mock encoder that returns deterministic random unit vectors
so the model weights are never loaded.  A single slow test (marked
``pytest.mark.slow``) loads the real model and does a smoke-check.

Run fast tests only:
    pytest exp/eval/lib/test_retriever.py -v

Run all including slow:
    pytest exp/eval/lib/test_retriever.py -v -m slow
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import torch
import torch.nn.functional as F

from exp.eval.lib.retriever import ByT5Retriever, Retriever, _encode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeBatchEncoding(dict):
    """dict subclass that adds .to() so it can be used like transformers BatchEncoding."""
    def to(self, device):
        return self


def _make_mock_retriever(n_dims: int = 8) -> ByT5Retriever:
    """Return a ByT5Retriever whose model/tokenizer are replaced with mocks.

    The mock model returns a deterministic hidden_state based on a hash of
    the tokenized input, producing distinct unit vectors per unique text.
    """
    retriever = object.__new__(ByT5Retriever)
    retriever._batch_size = 64
    retriever._device = torch.device("cpu")
    retriever._pool_cache = {}

    call_count = [0]  # mutable counter so fake_model_obj.call_count works

    def fake_tokenizer(texts, **kwargs):
        batch = [list(t.encode()) for t in texts]
        max_len = max(len(b) for b in batch)
        ids = torch.zeros(len(batch), max_len, dtype=torch.long)
        mask = torch.zeros(len(batch), max_len, dtype=torch.long)
        for i, b in enumerate(batch):
            ids[i, : len(b)] = torch.tensor(b, dtype=torch.long)
            mask[i, : len(b)] = 1
        return _FakeBatchEncoding({"input_ids": ids, "attention_mask": mask})

    class FakeModel:
        def __init__(self):
            self.call_count = 0

        def __call__(self, **kwargs):
            self.call_count += 1
            input_ids = kwargs["input_ids"]  # (B, L)
            B, L = input_ids.shape
            hidden = torch.zeros(B, L, n_dims)
            for i in range(B):
                seed = int(input_ids[i].sum().item()) % (2**31)
                g = torch.Generator()
                g.manual_seed(seed)
                vec = torch.randn(n_dims, generator=g)
                hidden[i] = vec.unsqueeze(0).expand(L, -1)
            out = MagicMock()
            out.last_hidden_state = hidden
            return out

    retriever._tokenizer = fake_tokenizer
    retriever._model = FakeModel()
    return retriever


# ---------------------------------------------------------------------------
# Fast tests (no model weights needed)
# ---------------------------------------------------------------------------

def test_protocol_satisfied():
    """ByT5Retriever satisfies the Retriever Protocol."""
    r = _make_mock_retriever()
    assert isinstance(r, Retriever)


def test_top_k_length_respected():
    pool = [f"stmt_{i}" for i in range(10)]
    r = _make_mock_retriever()
    result = r.retrieve("(x: Nat) : x = x", pool, k=3)
    assert len(result) == 3


def test_top_k_capped_at_pool_size():
    pool = ["stmt_a", "stmt_b"]
    r = _make_mock_retriever()
    result = r.retrieve("(x: Nat) : x = x", pool, k=100)
    assert len(result) == 2


def test_empty_pool_returns_empty():
    r = _make_mock_retriever()
    assert r.retrieve("(x: Nat) : x = x", [], k=5) == []


def test_results_are_subset_of_pool():
    pool = [f"(x_{i}: Nat) : x_{i} > 0" for i in range(8)]
    r = _make_mock_retriever()
    result = r.retrieve("(n: Nat) : n ≥ 0", pool, k=4)
    assert all(s in pool for s in result)


def test_pool_cache_hit():
    """Second call with the same pool must not re-encode (cache hit)."""
    pool = ["stmt_a", "stmt_b", "stmt_c"]
    r = _make_mock_retriever()
    _ = r.retrieve("(x: Nat) : x = x", pool, k=2)
    encode_call_count_after_first = r._model.call_count

    _ = r.retrieve("(y: Nat) : y > 0", pool, k=2)
    # Model should NOT have been called again for the pool (only for the query).
    assert r._model.call_count == encode_call_count_after_first + 1


def test_different_pools_both_cached():
    pool_a = ["lemma_a", "lemma_b"]
    pool_b = ["lemma_c", "lemma_d", "lemma_e"]
    r = _make_mock_retriever()
    r.retrieve("(x: Nat) : x = x", pool_a, k=1)
    r.retrieve("(x: Nat) : x = x", pool_b, k=1)
    assert tuple(pool_a) in r._pool_cache
    assert tuple(pool_b) in r._pool_cache


def test_k_equals_pool_size_returns_all():
    pool = ["a", "b", "c"]
    r = _make_mock_retriever()
    result = r.retrieve("(x: Nat) : x = x", pool, k=3)
    assert sorted(result) == sorted(pool)


# ---------------------------------------------------------------------------
# Slow test: real model weights
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_real_model_smoke():
    """Load the real ByT5 model and verify retrieve returns sensible results."""
    r = ByT5Retriever()
    pool = [
        "(xs: List Nat) : xs.length ≥ 0",
        "(x: Nat) (xs: List Nat) : x ∈ (x :: xs)",
        "(n m: Nat) : n + m = m + n",
    ]
    goal = "(x: Nat) (xs: List Nat) : x ∈ ins x xs"
    result = r.retrieve(goal, pool, k=2)
    assert len(result) == 2
    assert all(s in pool for s in result)
