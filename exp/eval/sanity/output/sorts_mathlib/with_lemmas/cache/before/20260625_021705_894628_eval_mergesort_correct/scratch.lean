import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [DecidableEq T] (l : List T) : Permut l l := by admit
theorem lemma_hint_1 [DecidableEq T] (l : List T) (t' : T) (h1 : count1 l t' = count1 l t') : Permut l l := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_3 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_4 [LT T] (x : T) (xs : List T) (s : Sorted (x :: xs)) : Sorted xs := by admit
theorem lemma_hint_5 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut ([] : List T) [] := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (IH : ∀ (t : T), count1 (insertionsort xs) t = count1 xs t) (t : T) : count1 (x :: insertionsort xs) t = count1 (x :: xs) t := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (h1 : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_10 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : Permut (insert_ x (insertionsort xs)) (x :: xs)) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_11 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut (insertionsort ([] : List T)) [] := by admit
theorem lemma_hint_12 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (x :: insertionsort xs) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_13 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_14 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_15 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_16 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (x :: insertionsort xs) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_17 [DecidableEq T] (l : List T) : ∀ (t : T), count1 l t = count1 l t := by admit
theorem lemma_hint_18 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_19 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_20 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (p : ¬t < x) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_21 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) (h1 : Sorted (h :: insert_ t xs)) : Sorted (x :: h :: insert_ t xs) := by admit
theorem lemma_hint_22 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (xs : List T) (IH : Sorted xs → Sorted (insert_ t xs)) (s : Sorted (x :: xs)) (p : t < x) : Sorted (if t < x then t :: x :: xs else x :: insert_ t xs) := by admit
theorem lemma_hint_23 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (p : ¬t < x) (h : T) (xs : List T) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) (s : Sorted (x :: h :: xs)) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_24 [Preorder T] [DecidableRel (LT.lt (α := T))] (x : T) (h : T) (xs : List T) (s : Sorted (x :: h :: xs)) : Sorted (h :: xs) := by admit
theorem lemma_hint_25 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (IH : ∀ (t : T), count1 (insertionsort xs) t = count1 xs t) (h : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: insertionsort xs) t) : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t := by admit
theorem lemma_hint_26 [Preorder T] [DecidableRel (LT.lt (α := T))] (t : T) (x : T) (h : T) (xs : List T) (p : ¬t < x) (IH : Sorted (h :: xs) → Sorted (insert_ t (h :: xs))) (s : Sorted (x :: h :: xs)) (p : ¬t < x) (a : ¬h < x) (h1 : Sorted (h :: xs)) : Sorted (insert_ t (h :: xs)) := by admit
theorem lemma_hint_27 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t := by admit
theorem lemma_hint_28 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_29 [DecidableEq T] (a : List T) (c : List T) (t' : T) (h1 : count1 a t' = count1 c t') : Permut a c := by admit
theorem lemma_hint_30 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_31 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : (if x = t then 1 else 0) + count1 (insertionsort xs) t = (if x = t then 1 else 0) + count1 xs t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_32 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : Permut (x :: insertionsort xs) (x :: xs)) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_33 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_34 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (t' : T) (h1 : count1 [] t' = count1 [] t') : Permut (insertionsort ([] : List T)) [] := by admit
theorem lemma_hint_35 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (t' : T) (h1 : count1 [] t' = count1 [] t') : Permut ([] : List T) [] := by admit
theorem lemma_hint_36 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : ¬e < x) (t : T) (h1 : count1 (x :: insert_ e xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_37 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) (t : T) : count1 (x :: insert_ e xs) t = count1 (e :: x :: xs) t := by admit
theorem lemma_hint_38 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_39 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (t : T) (h1 : count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit

theorem eval_mergesort_correct (T : Type) [Preorder T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : SortCorrect (mergesort : List T -> List T) := by
  intro l
  by_cases h : l.length < 2
  · cases l with
    | nil =>
        simp [mergesort, h]
        exact And.intro Sorted.nil (lemma_hint_0 ([] : List T))
    | cons x xs =>
        cases xs with
        | nil =>
            simp [mergesort, h]
            exact And.intro (Sorted.singleton : Sorted [x]) (lemma_hint_0 ([x] : List T))
        | cons y ys =>
            simp at h
            omega
  · cases l with
    | nil =>
        simp at h
    | cons x xs =>
        cases xs with
        | nil =>
            simp at h
        | cons y ys =>
            simp at h


/- lean_check result: FAIL
error:
location:
                simp at h
            | cons y ys =>
                       ^
                simp at h
error: unsolved goals
case neg.cons.cons
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
x y : T
ys : List T
h : True
⊢ Sorted (mergesort (x :: y :: ys)) ∧ Permut (mergesort (x :: y :: ys)) (x :: y :: ys)

location:
        | nil =>
            simp [mergesort, h]
                            ^
            exact And.intro Sorted.nil (lemma_hint_0 ([] : List T))
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [mergesort,̵ ̵h̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`

location:
            | nil =>
                simp [mergesort, h]
                                ^
                exact And.intro (Sorted.singleton : Sorted [x]) (lemma_hint_0 ([x] : List T))
error: This simp argument is unused:
  h
Hint: Omit it from the simp argument list.
  simp [mergesort,̵ ̵h̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
