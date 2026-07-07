import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (l : List T) : Permut (mergesort l) l := by
  intro t
  induction l using List.rec with
  | nil =>
      simp [mergesort, Permut, count1]
  | cons x xs ih =>
      unfold mergesort
      split
      · simp [count1]
      · simp [count1]


/- lean_check result: FAIL
error:
location:
          · simp [count1]
          · simp [count1]
         ^
error: unsolved goals
case cons.isFalse
T : Type u_1
inst✝² : LT T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
t x : T
xs : List T
ih : count1 (mergesort xs) t = count1 xs t
h✝ : ¬(x :: xs).length < 2
⊢ count1 (merge (mergesort (left (x :: xs))) (mergesort (right (x :: xs)))) t = (if x = t then 1 else 0) + count1 xs t

location:
      | nil =>
          simp [mergesort, Permut, count1]
                          ^
      | cons x xs ih =>
error: This simp argument is unused:
  Permut
Hint: Omit it from the simp argument list.
  simp [mergesort, P̵e̵r̵m̵u̵t̵,̵ ̵count1]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
