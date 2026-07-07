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
            simpa using ihy (x :: xs) t


/- lean_check result: FAIL
error:
location:
              · simp [merge, hxy, count1]
                simpa using ihy (x :: xs) t
                               ^
error: Application type mismatch: The argument
  x :: xs
has type
  List T
but is expected to have type
  T
in the application
  ihy (x :: xs)
-/
