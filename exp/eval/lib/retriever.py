"""Premise retriever for the eval pipeline.

``Retriever`` is a Protocol: any object with a ``retrieve(goal, pool, k)``
method satisfies it, making it easy to swap implementations or inject mocks in
tests.

``ByT5Retriever`` uses the LeanDojo encoder
'kaiyuy/leandojo-lean4-retriever-byt5-small' to embed both the query (the
theorem's proof state) and the lemma pool, then returns the top-K lemmas by
cosine similarity.

Pool embeddings are cached by pool identity (tuple of statements) so that
repeated calls with the same pool (i.e. all theorems in one round) do not
re-encode the corpus.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import torch
import torch.nn.functional as F

from exp.eval.lib.proof_state import statement_to_proof_state

_MODEL_NAME = "kaiyuy/leandojo-lean4-retriever-byt5-small"


@runtime_checkable
class Retriever(Protocol):
    def retrieve(self, goal: str, pool: list[str], k: int) -> list[str]:
        """Return up to k lemma statements from pool most relevant to goal."""
        ...


def _encode(model, tokenizer, texts: list[str], device: torch.device) -> torch.Tensor:
    """Masked-average-pool the encoder's last hidden states into unit vectors."""
    tokenized = tokenizer(texts, return_tensors="pt", padding=True, truncation=True,
                          max_length=512).to(device)
    with torch.no_grad():
        hidden = model(**tokenized).last_hidden_state        # (B, L, D)
    mask = tokenized["attention_mask"].unsqueeze(-1).float() # (B, L, 1)
    summed = (hidden * mask).sum(dim=1)                      # (B, D)
    lengths = mask.sum(dim=1).clamp(min=1e-9)               # (B, 1)
    embeddings = summed / lengths                            # (B, D)
    return F.normalize(embeddings, dim=-1)


class ByT5Retriever:
    """Retriever backed by the LeanDojo ByT5 encoder.

    Args:
        model_name: HuggingFace model ID (default: LeanDojo retriever).
        device:     torch device string; defaults to 'cuda' if available.
        batch_size: encoding batch size for large pools.
    """

    def __init__(
        self,
        model_name: str = _MODEL_NAME,
        device: str | None = None,
        batch_size: int = 64,
    ) -> None:
        from transformers import AutoTokenizer, T5EncoderModel  # lazy import

        self._device = torch.device(
            device if device is not None else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = T5EncoderModel.from_pretrained(model_name).to(self._device).eval()
        self._batch_size = batch_size
        # Cache: pool_key (tuple of stmts) -> Tensor of shape (N, D)
        self._pool_cache: dict[tuple[str, ...], torch.Tensor] = {}

    def _encode_batched(self, texts: list[str]) -> torch.Tensor:
        """Encode a list of texts in batches, return (N, D) unit-norm tensor."""
        chunks = [
            texts[i : i + self._batch_size]
            for i in range(0, len(texts), self._batch_size)
        ]
        parts = [_encode(self._model, self._tokenizer, chunk, self._device)
                 for chunk in chunks]
        return torch.cat(parts, dim=0)

    def retrieve(self, goal: str, pool: list[str], k: int) -> list[str]:
        """Return up to k lemmas from pool most relevant to goal.

        Args:
            goal: theorem statement_text (binder syntax); converted to proof-
                  state format internally before encoding.
            pool: list of lemma statement strings to rank.
            k:    number of lemmas to return (capped at len(pool)).
        """
        if not pool:
            return []
        k = min(k, len(pool))

        # Encode query.
        proof_state = statement_to_proof_state(goal)
        query_emb = _encode(self._model, self._tokenizer, [proof_state], self._device)  # (1, D)

        # Encode pool (cached by identity).
        pool_key = tuple(pool)
        if pool_key not in self._pool_cache:
            self._pool_cache[pool_key] = self._encode_batched(pool)
        pool_emb = self._pool_cache[pool_key]  # (N, D)

        scores = (query_emb @ pool_emb.T).squeeze(0)  # (N,)
        top_indices = scores.topk(k).indices.tolist()
        return [pool[i] for i in top_indices]
