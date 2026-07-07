import LeanSrc.Sorts_Mathlib

theorem expB_merge_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (xs ys : List T) : Permut (merge xs ys) (xs ++ ys) := by
  unfold Permut
  revert ys
  induction xs with
  | nil =>
      intro ys t
      simp [merge]
  | cons x xs ih =>
      intro ys
      induction ys generalizing x xs with
      | nil =>
          intro t
          simp [merge, count1]
      | cons y ys ihy =>
          intro t
          by_cases hxy : x < y
          · simp [merge, hxy, count1]
            simpa using ih (y :: ys) t
          · simp [merge, hxy, count1]
            simpa using ih ys t


/- lean_check result: FAIL
error:
location:
              · simp [merge, hxy, count1]
                simpa using ih ys t
               ^
error: Type mismatch: After simplification, term
  ih ys t
 has type
  count1 (merge xs ys) t = count1 (xs ++ ys) t
but is expected to have type
  (if y = t then 1 else 0) + count1 (merge (x :: xs) ys) t = (if x = t then 1 else 0) + count1 (xs ++ y :: ys) t
-/
