import LeanSrc.Sorts_Mathlib

theorem expB_merge_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (xs ys : List T) : Permut (merge xs ys) (xs ++ ys) := by
  unfold Permut
  revert ys
  induction xs with
  | nil =>
      intro ys t
      simp [merge, count1]
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
            simpa using ihy t


/- lean_check result: FAIL
error:
location:
              · simp [merge, hxy, count1]
                simpa using ihy t
               ^
error: Type mismatch: After simplification, term
  ihy t
 has type
  count1 (merge (x :: xs) ys) t = count1 (x :: (xs ++ ys)) t
but is expected to have type
  (if y = t then 1 else 0) + count1 (merge (x :: xs) ys) t = (if x = t then 1 else 0) + count1 (xs ++ y :: ys) t

location:
          intro ys t
          simp [merge, count1]
                      ^
      | cons x xs ih =>
error: This simp argument is unused:
  count1
Hint: Omit it from the simp argument list.
  simp [merge,̵ ̵c̵o̵u̵n̵t̵1̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
