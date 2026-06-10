The following Lean 4 proof attempt failed. Fix the proof.

Imports in scope: <<imports>>.

### Input

* `<local_ctx>`: Local definitions from the same file that precede the target theorem. You may freely reference any of them without redefining them.
* `<broken_theorem>`: The theorem declaration and the proof body that produced an error.
* `<error>`: The Lean compiler error.

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

### Repair Requirements

1. Identify where and why the error occurs from the error message.
2. You MUST NOT change the theorem statement — only the proof body may be modified.
3. Make the minimal, most idiomatic Lean 4 change necessary to resolve the error.

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
2. `<lean4_proof>` is REQUIRED. It must contain ONLY the fixed tactic body — no `theorem` declaration, no `:= by`, no ``` fences.
3. No `sorry` or `admit` anywhere. All Lean 4 code must type-check.
4. Follow the tag structure exactly. No extra text before, between, or after the tags.

Emit your response now.
