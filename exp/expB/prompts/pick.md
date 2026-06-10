Prove the following Lean 4 theorem. A set of candidate lemmas is provided — they are available as named theorems in scope (admitted elsewhere). Use any that are helpful.

Imports in scope: <<imports>>.

### Input

* `<local_ctx>`: Local definitions from the same file that precede the target theorem. You may freely reference any of them without redefining them.

<local_ctx>
<<local_ctx>>
</local_ctx>

Theorem statement:

    <<statement>>

### Candidate Lemmas

The following lemmas are admitted and in scope under the names shown. Apply any that are useful to close the proof.

<<candidates>>

### Output Format & Requirements

Your output MUST follow this structure exactly:

<reasoning>
...
</reasoning>

<used_lemmas>
comma-separated 0-based indices, or: none
</used_lemmas>

<lean4_proof>
-- tactic proof body only
</lean4_proof>

**Requirements:**
1. `<reasoning>` is OPTIONAL. Include it only if it aids proof construction.
2. `<used_lemmas>` is REQUIRED. List the **0-based indices** of the candidate lemmas you applied (e.g. `0,2`), or `none` if you did not use any.
3. `<lean4_proof>` is REQUIRED. It must contain ONLY the tactic body — no `theorem` declaration, no `:= by`, no ``` fences. Your output is indented and placed directly after `:= by` in the compiled file.
4. No `sorry` or `admit` in the proof body. All Lean 4 code must type-check (the admitted candidates are provided in the environment separately).
5. Follow the tag structure exactly. No extra text before, between, or after the tags.

Emit your response now.
