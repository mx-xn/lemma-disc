The following Lean 4 proof attempt failed. Fix the proof.

Imports in scope: <<imports>>.

### Input

* `<local_ctx>`: Local definitions from the same file that precede the target theorem. You may freely reference any of them without redefining them.
* `<broken_theorem>`: The theorem declaration and the proof body that produced an error.
* `<error>`: The Lean compiler error.
* `<hint_lemmas>`: Admitted lemmas available in scope. You may use any of them in your fix.

<local_ctx>
<<local_ctx>>
</local_ctx>

<broken_theorem>
theorem <<statement>> := by
<<proof_body>>
</broken_theorem>

<error>
<<error>>
</error>

<hint_lemmas>
<<hints>>
</hint_lemmas>

### Repair Requirements

1. Identify where and why the error occurs from the error message.
2. You MUST NOT change the theorem statement — only the proof body may be modified.
3. Make the minimal, most idiomatic Lean 4 change necessary to resolve the error.
4. The hint lemmas above are admitted and in scope — you may freely apply any of them.

### Output Format & Requirements

Your output MUST follow this structure exactly:

<reasoning>
...
</reasoning>

<lean4_proof>
-- fixed tactic proof body only
</lean4_proof>

**Requirements:**
1. `<reasoning>` is OPTIONAL. Include it only if it aids proof construction.
2. `<lean4_proof>` is REQUIRED. It must contain ONLY the fixed tactic body — no `theorem` declaration, no `:= by`, no ``` fences. All top-level tactics (`intro`, `induction`, `simp`, `exact`, `apply`, case branches `| foo =>`, etc.) must start at **column 0** (no leading whitespace). Sub-tactics inside case branches are indented by 2 or 4 spaces relative to the branch. 
3. No `sorry` or `admit` in the proof body. All Lean 4 code must type-check (the admitted hints are provided in the environment separately).
4. Follow the tag structure exactly. No extra text before, between, or after the tags.

Emit your response now.
