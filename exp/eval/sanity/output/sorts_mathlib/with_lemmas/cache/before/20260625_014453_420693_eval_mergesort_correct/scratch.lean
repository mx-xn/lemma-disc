import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [DecidableEq T] (l : List T) (t' : T) (h1 : count1 l t' = count1 l t') : Permut l l := by admit
theorem lemma_hint_1 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_3 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut ([] : List T) [] := by admit
theorem lemma_hint_4 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_5 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_6 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (IH : ∀ (t : T), count1 (insertionsort xs) t = count1 xs t) (t : T) : count1 (x :: insertionsort xs) t = count1 (x :: xs) t := by admit
theorem lemma_hint_7 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (h1 : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : Permut (insert_ x (insertionsort xs)) (x :: xs)) : Permut (insertionsort (x :: xs)) (x :: xs) := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : Permut (insertionsort ([] : List T)) [] := by admit

theorem eval_mergesort_correct (T : Type) [Preorder T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : SortCorrect (mergesort : List T -> List T) := by
  intro l
  constructor
  case left =>
    unfold mergesort
    split
    ·
      have hlen : l.length < 2 := by assumption
      cases l with
      | nil =>
        exact Sorted.nil
      | cons a xs =>
        cases xs with
        | nil =>
          exact Sorted.singleton
        | cons b ys =>
          simp at hlen
    ·
      have hlen : ¬ l.length < 2 := by assumption
      have hfalse : False := by
        linarith [Nat.zero_le l.length]
      exact False.elim hfalse
  case right =>
    unfold Permut
    intro t
    unfold mergesort
    split
    · simp
    ·
      have hlen : ¬ l.length < 2 := by assumption
      have hfalse : False := by
        linarith [Nat.zero_le l.length]
      exact False.elim hfalse


/- lean_check result: FAIL
error:
location:
              exact Sorted.singleton
            | cons b ys =>
                       ^
              simp at hlen
error: unsolved goals
case isTrue.cons.cons
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
a b : T
ys : List T
h✝ : (a :: b :: ys).length < 2
hlen : ys.length + 1 + 1 < 2
⊢ Sorted (a :: b :: ys)

location:
          have hfalse : False := by
            linarith [Nat.zero_le l.length]
           ^
          exact False.elim hfalse
error: linarith failed to find a contradiction
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
h✝ hlen : ¬l.length < 2
⊢ False
failed

location:
          have hfalse : False := by
            linarith [Nat.zero_le l.length]
           ^
          exact False.elim hfalse
error: linarith failed to find a contradiction
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
t : T
h✝ hlen : ¬l.length < 2
⊢ False
failed
-/
