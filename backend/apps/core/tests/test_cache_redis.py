"""Temporary placeholder.

The previous TwoLevelCache integration lane was removed while the test
architecture is being decided, and because the cache module is expected to
change before the cache work is revisited.

This single happy-path check exists only so the CI job has something to run.
It asserts nothing about the application. Replace this module when the cache
work resumes.
"""


def test_smoke():
    assert 2 + 2 == 4
