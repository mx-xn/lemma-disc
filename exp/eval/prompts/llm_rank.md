Rank the following Lean 4 lemma statements by how broadly useful they are likely to be as proof hints for future theorem proving.

Imports in scope: <<imports>>.

### Candidates

Each candidate is indexed as `L0`, `L1`, ..., `Ln`. The lemma statements are already valid Lean 4 statements and must not be edited.

<<candidates>>

### Ranking Criteria

Prefer lemmas that are:
1. Broadly applicable across many goals rather than tailored to one narrow theorem.
2. Mathematically informative, with conclusions that simplify, rewrite, decompose, or bridge common structures.
3. Not merely restatements of assumptions or extremely specific ground facts.
4. Likely to help close proof obligations when available as admitted theorem hints.
5. Reasonably small and usable without requiring many specialized hypotheses.

### Output Format & Requirements

Return ONLY a newline-separated list of candidate indices, most useful first.

Use 0-based integer indices without the `L` prefix. For example:

0
3
1

Requirements:
1. Include each selected index at most once.
2. Do not mutate, restate, or explain any candidate.
3. Do not include markdown fences, commas, bullets, labels, commentary, or extra text.

Emit the ranking now.
