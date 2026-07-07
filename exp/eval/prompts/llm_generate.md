The following Lean 4 corpus contains theorem proofs. Some proofs may contain `admit` where a previous proof attempt failed. Generate reusable lemmas, as many as possible, that would be broadly useful as proof hints for proving similar goals from this corpus. Aim to generate at least 2-3 lemmas per target theorems - you are highly encouraged to generate more than that. Each lemma must include a complete, correct Lean 4 proof.

Imports in scope: <<imports>>.

### Input

* `<corpus>`: Concatenated Lean 4 source files produced by the eval corpus builder. Solved theorems contain real proof bodies. Unsolved theorems may contain `admit` in failing proof locations.

<corpus>
<<corpus>>
</corpus>

### Generation Requirements

1. Use ordinary Lean 4 binder syntax, for example `(x : T) (h : P x) : Q x`.
2. Prefer lemmas that expose reusable proof facts, intermediate obligations, algebraic rewrites, logical decompositions, or bridge facts that appear useful across multiple goals.
3. You may extract statements suggested by the proof bodies, or invent modest generalizations that are clearly supported by the corpus.
4. Prefer broadly useful lemmas over theorem-specific restatements.
5. Avoid duplicating the original target theorem statements. For example, if original theorem is `(x y : T) (h : P x) : Q x`, do NOT generate `(x y : T) (h : P x) : Q x` or `(x : T) (y : T) (h : P x) : Q x` as lemmas.
6. DO NOT include theorem names in the proof body for any learned lemmas. 
7. Each proof must be a complete, correct Lean 4 proof body that follows `:=`. Write only proofs you are confident are correct. Do no use `admit` or `sorry` in any lemma proofs you learn.

### Output Format & Requirements

Emit one block per lemma using exactly the following delimiters:

```
<<<STATEMENT>>>
<lemma statement in binder syntax>
<<<PROOF>>>
<proof body — what follows `:=`, e.g. `by simp` or `by\n  intro h\n  exact h`>
<<<END>>>
```

**Example output (two lemmas):**

```
<<<STATEMENT>>>
(n : Nat) : n + 0 = n
<<<PROOF>>>
by simp
<<<END>>>

<<<STATEMENT>>>
(n m : Nat) (xs : List α) : (xs.take n).length = min n xs.length
<<<PROOF>>>
by exact List.length_take n xs
<<<END>>>
```

Do not include:
* `lemma` or `theorem` keywords
* generated names such as `generated_N`
* markdown fences around the delimiter blocks
* bullets, numbering, labels, commentary, reasoning, or extra text outside the delimiter blocks

Emit the lemma blocks now.
