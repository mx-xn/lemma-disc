Prove the following Lean 4 theorem. One or more hint lemmas are provided — they are available as admitted theorems in scope. Use any that are helpful.

Imports in scope: <<imports>>.

### Input

* `<local_ctx>`: Local definitions from the same file that precede the target theorem. You may freely reference any of them without redefining them.

<local_ctx>
<<local_ctx>>
</local_ctx>

Theorem statement:

    <<statement>>

### Hint Lemmas

The following lemmas are admitted and available in scope under the names shown. Apply any that are useful to close the proof.

<<hints>>

### Output Format & Requirements

Your output MUST follow this structure exactly:

<reasoning>
...
</reasoning>

<lean4_proof>
-- tactic proof body only
</lean4_proof>

**Requirements:**
1. `<reasoning>` is OPTIONAL. Include it only if it aids proof construction.
2. `<lean4_proof>` is REQUIRED. It must contain ONLY the tactic body — no `theorem` declaration, no `:= by`, no ``` fences. All top-level tactics (`intro`, `induction`, `simp`, `exact`, `apply`, case branches `| foo =>`, etc.) must start at **column 0** (no leading whitespace). Sub-tactics inside case branches are indented by 2 or 4 spaces relative to the branch. 
3. No `sorry` or `admit` in the proof body. All Lean 4 code must type-check (the admitted hints are provided in the environment separately).
4. Follow the tag structure exactly. No extra text before, between, or after the tags.

Emit your response now.
