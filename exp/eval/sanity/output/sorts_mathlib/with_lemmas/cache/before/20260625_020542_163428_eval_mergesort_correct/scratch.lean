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

theorem eval_mergesort_correct (T : Type) [Preorder T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] : SortCorrect (mergesort : List T -> List T) := by
  intro l
  unfold mergesort
  by_cases h : l.length < 2
  · simp [h]
    constructor
    · cases l with
      | nil =>
        exact Sorted.nil
      | cons x xs =>
        cases xs with
        | nil =>
          exact Sorted.singleton
        | cons y ys =>
          simp at h
    · exact lemma_hint_0 l
  · simp [h]
    constructor
    · cases hml : merge (mergesort (left l)) (mergesort (right l)) with
      | nil =>
        exact Sorted.nil
      | cons x xs =>
        cases xs with
        | nil =>
          exact Sorted.singleton
        | cons y ys =>
          apply Sorted.cons
          · cases ys with
            | nil =>
              exact Sorted.singleton
            | cons z zs =>
              exact Sorted.cons (Sorted.cons Sorted.singleton (by intro hlt; exact False.elim (lt_irrefl _ hlt))) (by intro hlt; exact False.elim (lt_irrefl _ hlt))
          · intro hlt
            exact False.elim (lt_irrefl _ hlt)
    · exact lemma_hint_0 l


/- lean_check result: FAIL
error:
location:
              exact Sorted.singleton
            | cons y ys =>
                       ^
              simp at h
error: unsolved goals
case pos.left.cons.cons
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
x y : T
ys : List T
h : ys.length + 1 + 1 < 2
⊢ Sorted (x :: y :: ys)

location:
                | cons z zs =>
                  exact Sorted.cons (Sorted.cons Sorted.singleton (by intro hlt; exact False.elim (lt_irrefl _ hlt))) (by intro hlt; exact False.elim (lt_irrefl _ hlt))
                                                                  ^
              · intro hlt
error: unsolved goals
T : Type
inst✝² : Preorder T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
l : List T
h : ¬l.length < 2
x y z : T
zs : List T
hml : merge (mergesort (left l)) (mergesort (right l)) = x :: y :: z :: zs
hlt : ?m.248 < ?m.248
⊢ False

location:
                | cons z zs =>
                  exact Sorted.cons (Sorted.cons Sorted.singleton (by intro hlt; exact False.elim (lt_irrefl _ hlt))) (by intro hlt; exact False.elim (lt_irrefl _ hlt))
                                                                                                                                                                  ^
              · intro hlt
error: Application type mismatch: The argument
  hlt
has type
  z < y
but is expected to have type
  ?m.269 < ?m.269
in the application
  lt_irrefl ?m.269 hlt

location:
              · intro hlt
                exact False.elim (lt_irrefl _ hlt)
                                             ^
        · exact lemma_hint_0 l
error: Application type mismatch: The argument
  hlt
has type
  y < x
but is expected to have type
  ?m.276 < ?m.276
in the application
  lt_irrefl ?m.276 hlt

location:
                exact False.elim (lt_irrefl _ hlt)
        · exact lemma_hint_0 l
         ^
error: Type mismatch
  lemma_hint_0 l
has type
  Permut l l
but is expected to have type
  Permut (merge (mergesort (left l)) (mergesort (right l))) l
-/
