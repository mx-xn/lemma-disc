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
            rw [ih ys t]
            simp [count1]


/- lean_check result: FAIL
error:
location:
              · simp [merge, hxy, count1]
                rw [ih ys t]
                   ^
                simp [count1]
error: Tactic `rewrite` failed: Did not find an occurrence of the pattern
  count1 (merge xs ys) t
in the target expression
  (if y = t then 1 else 0) + count1 (merge (x :: xs) ys) t = (if x = t then 1 else 0) + count1 (xs ++ y :: ys) t
case neg
T : Type u_1
inst✝² : LT T
inst✝¹ : DecidableEq T
inst✝ : DecidableRel LT.lt
x : T
xs : List T
ih : ∀ (ys : List T) (t : T), count1 (merge xs ys) t = count1 (xs ++ ys) t
y : T
ys : List T
ihy : ∀ (t : T), count1 (merge (x :: xs) ys) t = count1 (x :: xs ++ ys) t
t : T
hxy : ¬x < y
⊢ (if y = t then 1 else 0) + count1 (merge (x :: xs) ys) t = (if x = t then 1 else 0) + count1 (xs ++ y :: ys) t
-/
