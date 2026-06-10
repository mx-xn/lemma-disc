Prove the following Lean 4 theorem.

Imports in scope: <<imports>>.

### Input

* `<local_ctx>`: Local definitions from the same file that precede the target theorem. You may freely reference any of them without redefining them.

<local_ctx>
<<local_ctx>>
</local_ctx>

Theorem statement:

    <<statement>>

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
2. `<lean4_proof>` is REQUIRED. It must contain ONLY the tactic body — no `theorem` declaration, no `:= by`, no ``` fences. Your output is indented and placed directly after `:= by` in the compiled file.
3. No `sorry` or `admit` anywhere. All Lean 4 code must type-check.
4. Follow the tag structure exactly. No extra text before, between, or after the tags.

Emit your response now.
