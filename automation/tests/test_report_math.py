import unittest

from automation.build_report import compute


def inv(oid, loc, stars, date, source="api", rid=None, existing=""):
    return {"our_id": oid, "location": loc, "stars": str(stars), "create_date": date, "source": source,
            "review_id": rid or (oid if source == "api" else ""), "existing_reply": existing}


class ReportMathTest(unittest.TestCase):
    def setUp(self):
        self.inventory = [
            inv("M01", "Midtown", 5, "2026-08-30"),                 # August: excluded from September
            inv("M02", "Midtown", 5, "2026-09-01"),                 # reply
            inv("M03", "Midtown", 2, "2026-09-02"),                 # flag
            inv("M04", "Midtown", 4, "2026-09-03"),                 # reply+flag; live stars changed to 3
            inv("M05", "Midtown", 1, "2026-09-04"),                 # urgent
            inv("M06", "Midtown", 5, "2026-09-05"),                 # deleted: excluded everywhere
            inv("R01", "Riverside", 1, "2026-09-10"),               # report
            inv("R02", "Riverside", 4, "2026-09-11"),               # owner-reply
            inv("R03", "Riverside", 3, "2026-09-12"),               # flag-closed
            inv("O01", "Old Town", 5, "2026-09-03", "screenshot"),  # reply, confirmed posted
            inv("O02", "Old Town", 4, "2026-09-04", "screenshot"),  # reply, not confirmed -> pending
            inv("O03", "Old Town", 3, "2026-09-05", "screenshot"),  # flag
        ]
        cats = {"M01": "reply", "M02": "reply", "M03": "flag", "M04": "reply+flag", "M05": "urgent",
                "M06": "deleted", "R01": "report", "R02": "owner-reply", "R03": "flag-closed",
                "O01": "reply", "O02": "reply", "O03": "flag"}
        self.decisions = [{"our_id": k, "category": v} for k, v in cats.items()]
        self.replies = [{"our_id": k} for k in ("M02", "M04", "R02", "O01", "O02")]
        self.live = {"M01": {"stars": 5, "reply": "x"}, "M02": {"stars": 5, "reply": "y"},
                     "M03": {"stars": 2, "reply": None}, "M04": {"stars": 3, "reply": "z"},
                     "M05": {"stars": 1, "reply": None}, "M06": {"stars": 5, "reply": None},
                     "R01": {"stars": 1, "reply": None}, "R02": {"stars": 4, "reply": "w"},
                     "R03": {"stars": 3, "reply": None}}
        self.rep = compute("2026-09", self.inventory, self.decisions, self.replies, self.live, {"O01"})

    def test_midtown(self):
        m = self.rep["by_location"]["Midtown"]
        self.assertEqual(m["new_reviews"], 4)                    # M02-M05; M01 is August, M06 deleted
        self.assertEqual(m["average_rating"], round((5 + 2 + 3 + 1) / 4, 2))  # uses current stars (M04 = 3)
        self.assertEqual([m[f"stars_{s}"] for s in range(1, 6)], [1, 1, 1, 0, 1])
        self.assertEqual(m["replied"], 2)
        self.assertEqual(m["reply_rate"], 50.0)
        self.assertEqual(m["flagged_for_owner"], 2)
        self.assertEqual(m["awaiting_owner"], 2)
        self.assertEqual(m["urgent"], 1)
        self.assertEqual(m["manual_pending"], 0)

    def test_riverside_owner_decision_categories(self):
        r = self.rep["by_location"]["Riverside"]
        self.assertEqual(r["new_reviews"], 3)
        self.assertEqual(r["average_rating"], 2.67)
        self.assertEqual(r["flagged_for_owner"], 2)   # owner-reply + flag-closed
        self.assertEqual(r["awaiting_owner"], 0)
        self.assertEqual(r["removal_requested"], 1)
        self.assertEqual(r["reply_rate"], 33.3)

    def test_old_town_manual(self):
        o = self.rep["by_location"]["Old Town"]
        self.assertEqual(o["replied"], 1)
        self.assertEqual(o["manual_pending"], 1)
        self.assertEqual(o["ids"]["manual_pending"], ["O02"])
        self.assertEqual(o["average_rating"], 4.0)

    def test_total_is_sum_of_locations(self):
        t = self.rep["total"]
        self.assertEqual(t["new_reviews"], 10)
        for k in ("new_reviews", "replied", "manual_pending", "flagged_for_owner", "awaiting_owner", "urgent",
                  "removal_requested", "stars_1", "stars_2", "stars_3", "stars_4", "stars_5"):
            self.assertEqual(t[k], sum(self.rep["by_location"][l][k] for l in self.rep["by_location"]), k)
        self.assertEqual(t["average_rating"], round((5 + 2 + 3 + 1 + 1 + 4 + 3 + 5 + 4 + 3) / 10, 2))
        self.assertEqual(t["reply_rate"], 40.0)
        self.assertNotIn("M06", t["ids"]["new_reviews"])

    def test_rounding_half_up(self):
        inv1 = [inv("X1", "Midtown", 5, "2026-09-01"), inv("X2", "Midtown", 4, "2026-09-01"),
                inv("X3", "Midtown", 4, "2026-09-01"), inv("X4", "Midtown", 4, "2026-09-01"),
                inv("X5", "Midtown", 4, "2026-09-01"), inv("X6", "Midtown", 4, "2026-09-01"),
                inv("X7", "Midtown", 4, "2026-09-01"), inv("X8", "Midtown", 4, "2026-09-01")]
        dec = [{"our_id": r["our_id"], "category": "reply"} for r in inv1]
        rep = compute("2026-09", inv1, dec, [], {}, set())
        self.assertEqual(rep["by_location"]["Midtown"]["average_rating"], 4.13)  # 4.125 -> 4.13
        self.assertEqual(rep["by_location"]["Old Town"]["new_reviews"], 0)
        self.assertIsNone(rep["by_location"]["Old Town"]["average_rating"])


if __name__ == "__main__":
    unittest.main()
