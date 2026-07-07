import LeanSrc.Sorts_Mathlib

theorem expB_mergesort_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (l : List T) : Permut (mergesort l) l := by
  intro t
  unfold mergesort
  split
  · simp [Permut, count1]
  · simp [Permut, count1]


/- lean_check result: FAIL
error:
location:
      · simp [Permut, count1]
      · simp [Permut, count1]
     ^
error: unsolved goals
case isFalse
T : Type u_1
inst✝² : LT T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
t : T
h✝ : ¬l.length < 2
⊢ count1 (merge (mergesort (left l)) (mergesort (right l))) t = count1 l t

location:
      split
      · simp [Permut, count1]
             ^
      · simp [Permut, count1]
error: This simp argument is unused:
  Permut
Hint: Omit it from the simp argument list.
  simp [P̵e̵r̵m̵u̵t̵,̵ ̵count1]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
      split
      · simp [Permut, count1]
                     ^
      · simp [Permut, count1]
error: This simp argument is unused:
  count1
Hint: Omit it from the simp argument list.
  simp [Permut,̵ ̵c̵o̵u̵n̵t̵1̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
      · simp [Permut, count1]
      · simp [Permut, count1]
             ^
error: This simp argument is unused:
  Permut
Hint: Omit it from the simp argument list.
  simp [P̵e̵r̵m̵u̵t̵,̵ ̵count1]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
      · simp [Permut, count1]
      · simp [Permut, count1]
                     ^
error: This simp argument is unused:
  count1
Hint: Omit it from the simp argument list.
  simp [Permut,̵ ̵c̵o̵u̵n̵t̵1̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
