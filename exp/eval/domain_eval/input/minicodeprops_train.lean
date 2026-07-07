import LeanSrc.Definitions

-- Scoring guidelines:
-- anything that doesn't involve programs (i.e. list operations) can be at max a 3/5

-- besides that, 5/5 is for properties that don't directly follow from the program definition, and often
-- involve multiple programs. 4/5 is generally only a step beyond following from definition. 3/5 is a
-- statement about programs thats trivial, or a math statement that's nontrivial. 2 and 1 follow the
-- decreases in interestingness for math that we saw for 4 and 3 for programs.

-- take returns a list with the first n elements of the input list
-- drop deletes the first n elements of the input list


-- score: 5/5: keeping elements while a custom function that returns true returns true yields the original list.
theorem prop_36 (xs: List α) :
  (takeWhile (fun _ => True) xs = xs) := by
  induction xs with
  | nil => simp [takeWhile]
  | cons x xs ih =>
    simp [takeWhile]
    exact ih

theorem prop_58 (n: Nat) (xs: List α) (ys: List β) :
  (drop n (zip' xs ys) = zip' (drop n xs) (drop n ys)) := by
  induction n generalizing xs ys with
  | zero => simp [drop]
  | succ n ih =>
    cases xs with
    | nil => simp [zip', drop]
    | cons x xs =>
      cases ys with
      | nil => simp [zip', drop]; cases drop n xs <;> rfl
      | cons y ys =>
        simp only [zip', drop]
        exact ih xs ys

theorem prop_77 (x: Nat) (xs: List Nat) :
  (sorted xs → sorted (insort x xs)) := by
  induction xs with
  | nil => simp [insort, sorted]
  | cons y ys ih =>
    intro h
    by_cases hle : x ≤ y
    · simp [insort, sorted, hle, h]
    · have hyx : y ≤ x := Nat.le_of_lt (Nat.lt_of_not_le hle)
      simp only [insort, if_neg hle]
      cases ys with
      | nil => simp [sorted, insort, hyx]
      | cons z zs =>
        simp [sorted] at h
        obtain ⟨hyz, hzs⟩ := h
        by_cases hxz : x ≤ z
        · rw [show insort x (z :: zs) = x :: z :: zs from by simp [insort, hxz]]
          simp [sorted, hyx, hxz, hzs]
        · have hins : insort x (z :: zs) = z :: insort x zs := by simp [insort, hxz]
          rw [hins]
          simp [sorted, hyz, show sorted (z :: insort x zs) = true from by rw [← hins]; exact ih hzs]

theorem prop_78 (xs: List Nat) : sorted (sort xs) := by
  induction xs with
  | nil => simp [sort, sorted]
  | cons x xs ih =>
    simp [sort]
    generalize hsort : sort xs = sorted_xs at ih ⊢
    clear hsort
    induction sorted_xs with
    | nil => simp [insort, sorted]
    | cons y ys ih' =>
      -- intro h
      by_cases hle : x ≤ y
      · simp [insort, sorted, hle, ih]
      · have hyx : y ≤ x := Nat.le_of_lt (Nat.lt_of_not_le hle)
        simp only [insort, if_neg hle]
        cases ys with
        | nil => simp [sorted, insort, hyx]
        | cons z zs =>
          simp [sorted] at ih
          obtain ⟨hyz, hzs⟩ := ih
          by_cases hxz : x ≤ z
          · rw [show insort x (z :: zs) = x :: z :: zs from by simp [insort, hxz]]
            simp [sorted, hyx, hxz, hzs]
          · have hins : insort x (z :: zs) = z :: insort x zs := by simp [insort, hxz]
            rw [hins]
            simp [sorted, hyz]
            rw [← hins]
            apply ih' hzs

theorem prop_53 (n: Nat) (xs: List Nat) :
  (count n xs = count n (sort xs)) := by
  induction xs with
  | nil => simp [sort]
  | cons x xs ih =>
    simp only [sort, count_insort, count]
    rw [ih]

theorem prop_55 (n: Nat) (xs: List α) (ys: List α) :
  (drop n (xs ++ ys) = drop n xs ++ drop (n - length xs) ys) := by
  induction xs generalizing n with
  | nil =>
    simp [length]
    induction n with
    | zero => simp [drop]
    | succ n => simp [drop]
  | cons x xs ih =>
    cases n with
    | zero => simp [drop, length]
    | succ n =>
      simp only [List.cons_append, drop, length]
      rw [ih n]
      have key : n - length xs = n + 1 - (1 + length xs) := by omega
      rw [key]

-- score: 5/5: taking m from a list and then dropping n is equivalent to dropping n and then taking m minus n
theorem prop_57 (n: Nat) (m: Nat) (xs: List α) :
  (drop n (take m xs) = take (m - n) (drop n xs)) := by
  induction xs generalizing n m with
  | nil =>
    have take_nil : ∀ k, take k ([] : List α) = [] := by
      intro k
      cases k with
      | zero => rfl
      | succ k => rfl
    have drop_nil : ∀ k, drop k ([] : List α) = [] := by
      intro k
      cases k with
      | zero => rfl
      | succ k => rfl
    rw [take_nil, drop_nil, take_nil]
  | cons x xs ih =>
    cases n with
    | zero => simp [drop]
    | succ n =>
      cases m with
      | zero => simp [drop, take]
      | succ m =>
        simp only [take, drop, Nat.succ_sub_succ_eq_sub]
        exact ih n m

theorem prop_85 (xs: List α) (ys: List β) :
  (length xs = length ys) →
    (zip' (reverse xs) (reverse ys) = reverse (zip' xs ys)) := by
  induction xs generalizing ys with
  | nil =>
    intro h; cases ys with
    | nil => simp [reverse, zip']
    | cons _ _ => simp only [length] at h; omega
  | cons x xs ih =>
    intro h; cases ys with
    | nil => simp only [length] at h; omega
    | cons y ys =>
      have h' : length xs = length ys := by simp only [length] at h; omega
      have hL : length (reverse xs) = length (reverse ys) := by admit
      simp only [reverse, zip']
      admit
