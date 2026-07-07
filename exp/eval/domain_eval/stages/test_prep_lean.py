from exp.eval.domain_eval.stages.prep_lean import (
    _Block,
    _keep_block,
    _matches_train,
    _segment,
)

_SAMPLE = """\
import Foo

def helper : Nat := 42

-- a comment
theorem train_one (n : Nat) : n = n := by
  rfl

theorem test_one (n : Nat) : n + 0 = n := by
  simp

theorem train_two (n : Nat) : 0 + n = n := by
  simp
"""


def test_segment_identifies_theorems():
    blocks = _segment(_SAMPLE)
    names = [b.theorem_name for b in blocks if b.theorem_name is not None]
    assert names == ["train_one", "test_one", "train_two"]


def test_segment_non_theorem_blocks_have_no_name():
    blocks = _segment(_SAMPLE)
    # import, def, and the comment+blank preamble blocks should have no name
    non_thm = [b for b in blocks if b.theorem_name is None]
    combined = "".join("".join(b.lines) for b in non_thm)
    assert "import Foo" in combined
    assert "def helper" in combined
    assert "-- a comment" in combined


def test_filter_removes_test_theorems():
    train_ids = {"train_one", "train_two"}
    blocks = _segment(_SAMPLE)
    kept = [b for b in blocks if _keep_block(b, train_ids)]
    result = "".join("".join(b.lines) for b in kept)
    assert "train_one" in result
    assert "train_two" in result
    assert "test_one" not in result
    assert "def helper" in result
    assert "import Foo" in result
    assert "-- a comment" in result


def test_matches_train_exact():
    assert _matches_train("foo", {"foo", "bar"})
    assert not _matches_train("baz", {"foo", "bar"})


def test_matches_train_qualified():
    # theorem_id "MyNs.foo" should match source name "foo"
    assert _matches_train("foo", {"MyNs.foo"})
    assert not _matches_train("bar", {"MyNs.foo"})


def test_last_theorem_no_trailing_newline():
    # Edge case: file ends without trailing newline
    source = "theorem only (n : Nat) : n = n := by\n  rfl"
    blocks = _segment(source)
    assert len(blocks) == 1
    assert blocks[0].theorem_name == "only"


def test_inline_attribute():
    source = "@[simp] theorem attr_thm (n : Nat) : n = n := by rfl\n"
    blocks = _segment(source)
    assert blocks[0].theorem_name == "attr_thm"
