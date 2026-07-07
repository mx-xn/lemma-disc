import LeanSrc.Sorts_Mathlib

theorem expB_merge_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (xs ys : List T) : Permut (merge xs ys) (xs ++ ys) := by
  unfold Permut
  induction xs with
  | nil =>
      intro t
      simp [merge, count1]
  | cons x xs ih =>
      induction ys with
      | nil =>
          intro t
          simp [merge, count1]
      | cons y ys ihy =>
          intro t
          simp [merge, count1]
          by_cases hxy : x < y
          · simp [merge, hxy, count1]
            simpa [Permut] using ih (y :: ys) t
          · simp [merge, hxy, count1]
            simpa [Permut] using ihy t


/- lean_check result: FAIL
error:
location:
              · simp [merge, hxy, count1]
                simpa [Permut] using ih (y :: ys) t
                                       ^
              · simp [merge, hxy, count1]
error: Application type mismatch: The argument
  y :: ys
has type
  List T
but is expected to have type
  T
in the application
  ih (y :: ys)

location:
              · simp [merge, hxy, count1]
                simpa [Permut] using ihy t
                                        ^
error: Application type mismatch: The argument
  t
has type
  T
of sort `Type u_1` but is expected to have type
  ∀ (t : T), count1 (merge xs ys) t = count1 (xs ++ ys) t
of sort `Prop` in the application
  ihy t

location:
          intro t
          simp [merge, count1]
                      ^
      | cons x xs ih =>
error: This simp argument is unused:
  count1
Hint: Omit it from the simp argument list.
  simp [merge,̵ ̵c̵o̵u̵n̵t̵1̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
              by_cases hxy : x < y
              · simp [merge, hxy, count1]
                     ^
                simpa [Permut] using ih (y :: ys) t
error: This simp argument is unused:
  merge
Hint: Omit it from the simp argument list.
  simp [m̵e̵r̵g̵e̵,̵ ̵hxy, count1]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
                simpa [Permut] using ih (y :: ys) t
              · simp [merge, hxy, count1]
                     ^
                simpa [Permut] using ihy t
error: This simp argument is unused:
  merge
Hint: Omit it from the simp argument list.
  simp [m̵e̵r̵g̵e̵,̵ ̵hxy, count1]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
