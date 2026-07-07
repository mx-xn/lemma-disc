import LeanSrc.Sorts_Mathlib

theorem lemma_hint_0 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_1 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) : Permut (e :: x :: xs) (e :: x :: xs) := by admit
theorem lemma_hint_2 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (h1 : ∀ (t : T), count1 (e :: x :: xs) t = count1 (e :: x :: xs) t) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_3 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_4 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) (p : ¬e < x) : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit
theorem lemma_hint_5 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (IH : Permut (insert_ e xs) (e :: xs)) : Permut (insert_ e (x :: xs)) (e :: x :: xs) := by admit
theorem lemma_hint_6 [DecidableEq T] (l : List T) : Permut l l := by admit
theorem lemma_hint_7 [DecidableEq T] {a b c : List T} (ab : Permut a b) (bc : Permut b c) : Permut a c := by admit
theorem lemma_hint_8 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (x : T) (xs : List T) (h : Permut (insert_ x (insertionsort xs)) (x :: insertionsort xs)) (h1 : ∀ (t : T), count1 (insert_ x (insertionsort xs)) t = count1 (x :: xs) t) : Permut (insert_ x (insertionsort xs)) (x :: xs) := by admit
theorem lemma_hint_9 [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (e : T) (x : T) (xs : List T) (p : e < x) (t' : T) (h1 : count1 (e :: x :: xs) t' = count1 (e :: x :: xs) t') : Permut (if e < x then e :: x :: xs else x :: insert_ e xs) (e :: x :: xs) := by admit

theorem eval_merge_permut [LT T] [DecidableEq T] [DecidableRel (LT.lt (α := T))] (xs ys : List T) : Permut (merge xs ys) (xs ++ ys) := by
  induction xs with
  | nil =>
    intro ys
    simp [merge, Permut]
  | cons x xs ih =>
    intro ys
    cases ys with
    | nil =>
      simp [merge, Permut]
    | cons y ys =>
      by_cases h : x < y
      · simp [merge, h]
        have hrec : Permut (merge xs (y :: ys)) (xs ++ y :: ys) := ih (y :: ys)
        exact
          fun t => by
            specialize hrec t
            simp [Permut, count1, hrec]
      · simp [merge, h]
        have hrec : Permut (merge (x :: xs) ys) ((x :: xs) ++ ys) := by
          simpa using (ih ys)
        exact
          fun t => by
            specialize hrec t
            simp [Permut, count1, hrec]


/- lean_check result: FAIL
error:
location:
        intro ys
        cases ys with
       ^
        | nil =>
error: Tactic `cases` failed: major premise type is not an inductive type
  T
Explanation: the `cases` tactic is for constructor-based reasoning as well as for applying custom cases principles with a 'using' clause or a registered '@[cases_eliminator]' theorem. The above type neither is an inductive type nor has a registered theorem.
case cons
T : Type u_1
inst✝² : LT T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
ys✝ : List T
x : T
xs : List T
ih : Permut (merge xs ys✝) (xs ++ ys✝)
ys : T
⊢ count1 (merge (x :: xs) ys✝) ys = count1 (x :: xs ++ ys✝) ys

location:
        intro ys
        simp [merge, Permut]
                    ^
      | cons x xs ih =>
error: This simp argument is unused:
  Permut
Hint: Omit it from the simp argument list.
  simp [merge,̵ ̵P̵e̵r̵m̵u̵t̵]
Note: This linter can be disabled with `set_option linter.unusedSimpArgs false`
-/
