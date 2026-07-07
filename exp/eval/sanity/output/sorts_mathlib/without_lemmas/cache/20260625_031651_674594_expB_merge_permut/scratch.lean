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
      induction ys with
      | nil =>
          intro t
          simp [merge, count1]
      | cons y ys ihy =>
          intro t
          by_cases hxy : x < y
          · simp [merge, hxy, count1]
            simpa using ih (y :: ys) t
          · simp [merge, hxy, count1]
            rw [ihy t]
            omega


/- lean_check result: FAIL
error:
location:
                rw [ihy t]
                omega
               ^
error: omega could not prove the goal:
a possible counterexample may satisfy the constraints
  d ≥ 0
  c ≥ 0
  b ≥ 0
  a ≥ 0
  a + b - c - d ≥ 1
where
 a := ↑(if x = t then 1 else 0)
 b := ↑(count1 (xs ++ y :: ys) t)
 c := ↑(if y = t then 1 else 0)
 d := ↑(count1 (x :: xs ++ ys) t)
-/
