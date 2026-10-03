import unittest

from automation.gbp_client import GBPClient
from automation.post_replies import post_all
from automation.reply_rules import ReplyRules
from automation.tests._fakes import FakeServer
from automation.tests.test_reply_rules import LOCS, STAFF


class MemLog:
    def __init__(self):
        self.rows = []

    def write(self, **row):
        self.rows.append(row)


class PostRepliesTest(unittest.TestCase):
    def setUp(self):
        self.inv = {"M01": {"review_id": "a", "reviewer": "Jonas Weber", "text": "Perfect sourdough."},
                    "M02": {"review_id": "gone", "reviewer": "Ivy Chen", "text": "Lovely scones."},
                    "M03": {"review_id": "b", "reviewer": "Greg Malone", "text": "Great croissant."},
                    "O01": {"review_id": "", "reviewer": "Zoe Turner", "text": "Best bakery in Old Town."}}
        self.rows = [
            {"our_id": "M01", "location": "Midtown", "reply_text": "Jonas, so glad you loved our sourdough. - Priya, Midtown"},
            {"our_id": "M02", "location": "Midtown", "reply_text": "Ivy, so glad you enjoyed the scones. - Priya, Midtown"},
            {"our_id": "M03", "location": "Midtown", "reply_text": "Greg, glad you liked the croissant! Omar says hi. - Priya, Midtown"},
            {"our_id": "O01", "location": "Old Town", "reply_text": "Zoe, thank you for calling us the best bakery in Old Town. - Hannah, Old Town"},
        ]

        def handler(method, path, q, body, n):
            if "/gone/" in path:
                return 404, {}, {"error": {"code": 404}}
            if n == 1:
                return 429, {"Retry-After": "0"}, {"error": {"code": 429}}
            return 200, {}, {"comment": body["comment"]}
        self.srv = FakeServer(handler)
        self.log = MemLog()
        self.res = post_all(self.rows, GBPClient(opener=self.srv, sleep=lambda s: None), ReplyRules(STAFF, LOCS),
                            self.log, self.inv, {"Midtown": "4471"})

    def test_results(self):
        self.assertEqual(self.res, {"M01": "posted", "M02": "deleted", "M03": "blocked-local", "O01": "skipped-old-town"})

    def test_old_town_and_blocked_never_hit_api(self):
        paths = [c[1] for c in self.srv.calls]
        self.assertFalse(any("/b/" in p for p in paths))  # M03 blocked locally (Omar)
        self.assertEqual(len(self.srv.calls), 3)            # M01 429 + 200, M02 404

    def test_every_attempt_logged(self):
        m01 = [r for r in self.log.rows if r["our_id"] == "M01"]
        self.assertEqual([r["result"] for r in m01], ["rate-limited", "posted"])
        self.assertEqual(m01[-1]["http_status"], 200)


if __name__ == "__main__":
    unittest.main()
