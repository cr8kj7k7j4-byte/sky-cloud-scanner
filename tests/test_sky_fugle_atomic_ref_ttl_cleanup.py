import unittest
from unittest.mock import Mock
from research.sky_fugle_atomic_ref_ttl_cleanup import (
    PREFIX, SECONDS_PER_SLOT, MIN_AGE_SECONDS, eligible_refs, prune,
)


class AtomicTtlCleanupTests(unittest.TestCase):
    def setUp(self):
        self.now = 1_800_000_000
        self.sha = "a" * 40
        self.old = PREFIX + "1" * 32 + "-" + str((self.now - MIN_AGE_SECONDS - 300) // 300)
        self.recent = PREFIX + "2" * 32 + "-" + str((self.now - 60) // 300)
        self.future = PREFIX + "3" * 32 + "-" + str((self.now + 600) // 300)

    def test_old_only_and_future_preserved(self):
        raw = "\n".join(f"{self.sha}\t{x}" for x in
                        (self.old, self.recent, self.future))
        self.assertEqual(eligible_refs(raw, now=self.now), [(self.old, self.sha)])

    def test_reject_unsafe_ttl_and_malformed_refs(self):
        with self.assertRaises(ValueError):
            eligible_refs("", now=self.now, ttl=60)
        with self.assertRaises(RuntimeError):
            eligible_refs(f"{self.sha}\trefs/tags/production-keep", now=self.now)
        with self.assertRaises(RuntimeError):
            eligible_refs(f"{self.sha}\t{self.old}\n{self.sha}\t{self.old}", now=self.now)

    def test_only_exact_old_ref_deleted_with_readback(self):
        refs = {self.old: self.sha, self.recent: self.sha}
        commands = []
        def git(argv, **kwargs):
            commands.append(argv)
            if argv[1] == "ls-remote" and argv[2] == "--refs" and argv[3] == "--tags":
                return Mock(stdout="".join(f"{v}\t{k}\n" for k,v in refs.items()))
            if argv[1] == "ls-remote":
                ref = argv[-1]
                return Mock(stdout=f"{refs[ref]}\t{ref}\n" if ref in refs else "")
            if argv[1] == "push":
                ref = argv[-1].removeprefix(":")
                refs.pop(ref)
                return Mock(stdout="")
            raise AssertionError(argv)
        result = prune(now=self.now, git=git)
        self.assertEqual(result["deletion_count"], 1)
        self.assertEqual(refs, {self.recent: self.sha})
        self.assertEqual(sum(1 for c in commands if c[1] == "push"), 1)

    def test_changed_sha_aborts_without_delete(self):
        refs = {self.old: self.sha}
        def git(argv, **kwargs):
            if argv[1] == "ls-remote" and argv[3] == "--tags":
                return Mock(stdout=f"{self.sha}\t{self.old}\n")
            if argv[1] == "ls-remote":
                return Mock(stdout=f"{'b'*40}\t{self.old}\n")
            raise AssertionError("unexpected deletion")
        with self.assertRaisesRegex(RuntimeError, "REMOTE_TEST_REF_CHANGED"):
            prune(now=self.now, git=git)


if __name__ == "__main__":
    unittest.main()
