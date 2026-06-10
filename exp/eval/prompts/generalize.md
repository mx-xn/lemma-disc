The following Lean 4 lemma statement is valid but may be overly specialized. Produce a strictly more general Lean 4 lemma statement when a natural generalization is available.

Imports in scope: <<imports>>.

### Input

* `<statement>`: A valid Lean 4 lemma statement in binder syntax. It is intended to be used after a generated declaration prefix of the form `lemma validate_N : ... := by sorry`.

<statement>
<<statement>>
</statement>

### Generalization Requirements

1. Return a statement that can appear immediately after `lemma validate_N :`.
2. Use ordinary Lean 4 binder syntax, for example `(x : T) (h : P x) : Q x`.
3. Prefer replacing concrete types, concrete values, repeated constants, or unnecessarily fixed parameters with universally quantified variables.
4. Preserve all assumptions needed for the conclusion to remain meaningful and type-correct.
5. Keep the generalized statement close to the original theorem shape. Do not invent a different theorem.
6. Do not weaken the conclusion, add unrelated hypotheses, or make the statement vacuous.
7. If no clear strictly more general version is available, return the original statement unchanged.
8. Do not include a proof.

### Examples

Specialized statement:

    (n : Nat) : n * 2 > 0 /\ (n * 2 > 0 -> Even (n * 2)) -> Even (n * 2)

Generalized statement:

    (p q : Prop) : p /\ (p -> q) -> q

Specialized statement:

    (n : Nat) : 0 <= n * n + n * n

Generalized statement:

    (m : Nat) : 0 <= m + m

### Output Format & Requirements

Return ONLY the generalized statement string.

Do not include:
* `lemma` or `theorem`
* a generated name such as `validate_N`
* `:= by`
* `sorry` or `admit`
* markdown fences
* commentary, reasoning, labels, or extra text

Emit the statement now.
