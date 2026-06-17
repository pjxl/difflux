"""Tests for hunks.py — diff parser. All use inline diffs; no network or API needed."""

from difflux.hunks import parse_diff, HunkIndex

SIMPLE_DIFF = """\
diff --git a/src/auth.py b/src/auth.py
index abc1234..def5678 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,6 +10,7 @@ class Auth:
     def login(self):
         pass

+    def logout(self):
+        pass
+
     def check(self):
         pass
@@ -20,4 +21,3 @@ class Auth:
     def helper(self):
-        return True
+        return False
         pass
"""

TWO_FILE_DIFF = """\
diff --git a/foo.py b/foo.py
index 0000000..1111111 100644
--- a/foo.py
+++ b/foo.py
@@ -1,3 +1,4 @@
+import os
 x = 1
 y = 2
 z = 3
diff --git a/bar.py b/bar.py
index 2222222..3333333 100644
--- a/bar.py
+++ b/bar.py
@@ -5,3 +5,4 @@
 a = 1
 b = 2
+c = 3
 d = 4
"""

DELETION_DIFF = """\
diff --git a/old.py b/old.py
deleted file mode 100644
index abc1234..0000000
--- a/old.py
+++ /dev/null
@@ -1,3 +0,0 @@
-x = 1
-y = 2
-z = 3
"""


def test_empty_diff_returns_empty_list():
    assert parse_diff("") == []
    assert parse_diff("   \n  ") == []


def test_simple_diff_produces_two_hunks():
    hunks = parse_diff(SIMPLE_DIFF)
    assert len(hunks) == 2


def test_hunk_ids_are_sequential_starting_at_one():
    hunks = parse_diff(SIMPLE_DIFF)
    assert [h.id for h in hunks] == [1, 2]


def test_file_path_extracted_correctly():
    hunks = parse_diff(SIMPLE_DIFF)
    assert all(h.file_path == "src/auth.py" for h in hunks)


def test_two_file_diff_produces_two_hunks_with_correct_paths():
    hunks = parse_diff(TWO_FILE_DIFF)
    assert len(hunks) == 2
    assert hunks[0].file_path == "foo.py"
    assert hunks[1].file_path == "bar.py"


def test_ids_increment_across_files():
    hunks = parse_diff(TWO_FILE_DIFF)
    assert hunks[0].id == 1
    assert hunks[1].id == 2


def test_deletion_falls_back_to_a_side_path():
    hunks = parse_diff(DELETION_DIFF)
    assert len(hunks) == 1
    assert hunks[0].file_path == "old.py"


def test_line_numbers_parsed():
    hunks = parse_diff(SIMPLE_DIFF)
    assert hunks[0].new_start == 10
    assert hunks[1].new_start == 21


def test_body_contains_diff_lines():
    hunks = parse_diff(SIMPLE_DIFF)
    assert "logout" in hunks[0].body
    assert "+        return False" in hunks[1].body


def test_header_is_verbatim_hunk_header():
    hunks = parse_diff(SIMPLE_DIFF)
    assert hunks[0].header.startswith("@@ -10")
    assert hunks[1].header.startswith("@@ -20")


def test_hunk_index_lookup():
    hunks = parse_diff(TWO_FILE_DIFF)
    index = HunkIndex(hunks)
    result = index.by_ids([2, 1])
    assert [h.id for h in result] == [2, 1]


def test_hunk_index_missing_ids_skipped():
    hunks = parse_diff(SIMPLE_DIFF)
    index = HunkIndex(hunks)
    result = index.by_ids([1, 99, 2])
    assert [h.id for h in result] == [1, 2]
