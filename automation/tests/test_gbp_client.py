import unittest

from automation.gbp_client import (BadRequestError, ConflictError, GBPClient, NotFoundError,
                                   RateLimitError)
from automation.tests._fakes import FakeServer


def review(i):
    return {"reviewId": f"r{i}", "reviewer": {"displayName": f"P{i}"}, "starRating": "FIVE",
            "createTime": "2026-09-01T00:00:00Z", "updateTime": "2026-09-01T00:00:00Z"}


class PaginationTest(unittest.TestCase):
    def test_follows_next_page_token_to_the_end(self):
        pages = {None: ([review(i) for i in range(10)], "p2"), "p2": ([review(i) for i in range(10, 20)], "p3"),
                 "p3": ([review(i) for i in range(20, 23)], None)}

        def handler(method, path, q, body, n):
            items, nxt = pages[q.get("pageToken")]
            payload = {"reviews": items}
            if nxt:
                payload["nextPageToken"] = nxt
            return 200, {}, payload
        srv = FakeServer(handler)
        got = GBPClient(opener=srv).list_reviews("4471")
        self.assertEqual([r["reviewId"] for r in got], [f"r{i}" for i in range(23)])
        self.assertEqual([c[2].get("pageToken") for c in srv.calls], [None, "p2", "p3"])
        self.assertTrue(all(c[2]["pageSize"] == "10" for c in srv.calls))
        self.assertTrue(all(c[4] == "Bearer ll-test-token" for c in srv.calls))

    def test_pagination_loop_is_detected(self):
        srv = FakeServer(lambda *a: (200, {}, {"reviews": [review(1)], "nextPageToken": "same"}))
        with self.assertRaises(Exception):
            GBPClient(opener=srv).list_reviews("4471")


class RetryTest(unittest.TestCase):
    def test_429_retries_honouring_retry_after(self):
        def handler(method, path, q, body, n):
            if n <= 2:
                return 429, {"Retry-After": "7"}, {"error": {"code": 429}}
            return 200, {}, {"comment": body["comment"]}
        srv, sleeps = FakeServer(handler), []
        res = GBPClient(opener=srv, sleep=sleeps.append).put_reply("4471", "r1", "hi")
        self.assertEqual(res, {"comment": "hi"})
        self.assertEqual(sleeps, [7.0, 7.0])
        self.assertEqual(len(srv.calls), 3)
        self.assertEqual(srv.calls[-1][3], {"comment": "hi"})

    def test_429_gives_up_after_max_retries(self):
        srv, sleeps = FakeServer(lambda *a: (429, {"retry-after": "2"}, {"error": {"code": 429}})), []
        with self.assertRaises(RateLimitError):
            GBPClient(opener=srv, sleep=sleeps.append, max_retries=3).put_reply("4471", "r1", "hi")
        self.assertEqual(sleeps, [2.0, 2.0, 2.0])
        self.assertEqual(len(srv.calls), 4)

    def test_on_response_sees_every_attempt(self):
        seq = iter([(429, {"Retry-After": "0"}, {}), (200, {}, {})])
        srv, seen = FakeServer(lambda *a: next(seq)), []
        c = GBPClient(opener=srv, sleep=lambda s: None, on_response=lambda m, p, s, pl, h: seen.append(s))
        c.put_reply("4471", "r1", "x")
        self.assertEqual(seen, [429, 200])


class ErrorTest(unittest.TestCase):
    def check(self, status, exc):
        srv = FakeServer(lambda *a: (status, {}, {"error": {"code": status, "message": "nope", "violations": ["4c"]}}))
        with self.assertRaises(exc) as cm:
            GBPClient(opener=srv, sleep=lambda s: None).put_reply("4471", "r1", "x")
        self.assertEqual(cm.exception.status, status)
        self.assertIn("nope", str(cm.exception))
        self.assertEqual(cm.exception.details.get("violations"), ["4c"])

    def test_400(self):
        self.check(400, BadRequestError)

    def test_404(self):
        self.check(404, NotFoundError)

    def test_409(self):
        self.check(409, ConflictError)


if __name__ == "__main__":
    unittest.main()
