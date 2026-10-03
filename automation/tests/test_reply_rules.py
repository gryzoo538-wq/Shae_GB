import os
import unittest

from automation.reply_rules import ReplyRules, detect_language, reviewer_first_name

STAFF = [
    {"first_name": "Priya", "location": "Midtown", "status": "current (manager)", "public_mention_consent": "yes"},
    {"first_name": "Jess", "location": "Midtown", "status": "current", "public_mention_consent": "yes"},
    {"first_name": "Omar", "location": "Midtown", "status": "current", "public_mention_consent": "no"},
    {"first_name": "Marco", "location": "Riverside", "status": "current (manager)", "public_mention_consent": "yes"},
    {"first_name": "Theo", "location": "Riverside", "status": "former (left 2026-09-10)", "public_mention_consent": "no"},
    {"first_name": "Hannah", "location": "Old Town", "status": "current (manager)", "public_mention_consent": "yes"},
]
LOCS = [{"location": "Midtown", "manager": "Priya"}, {"location": "Riverside", "manager": "Marco"},
        {"location": "Old Town", "manager": "Hannah"}]
GOOD = "Jonas, thank you! We're so glad you loved our sourdough. - Priya, Midtown"


class RuleCase(unittest.TestCase):
    def setUp(self):
        self.r = ReplyRules(STAFF, LOCS)

    def codes(self, reply, location="Midtown", reviewer="Jonas Weber", text="Perfect sourdough.", others=(), about=None):
        return [c for c, _ in self.r.validate(reply, location, reviewer, text, others, about)]

    def test_good_reply_passes(self):
        self.assertEqual(self.codes(GOOD), [])

    # 4a name rule
    def test_4a_must_start_with_first_name(self):
        self.assertIn("4a", self.codes("Thanks Jonas, we're so glad you loved our sourdough. - Priya, Midtown"))

    def test_4a_initials_get_no_name(self):
        ok = "Thank you for the five-star rating! - Priya, Midtown"
        self.assertEqual(self.codes(ok, reviewer="K. W.", text=""), [])
        self.assertIsNone(reviewer_first_name("K. W."))
        self.assertIsNone(reviewer_first_name("A Google User"))
        self.assertEqual(reviewer_first_name("Mei Lin"), "Mei")

    # 4b specific thing
    def test_4b_generic_reply_fails(self):
        self.assertIn("4b", self.codes("Jonas, thank you so much, see you soon! - Priya, Midtown"))

    def test_4b_star_only_must_thank_for_rating(self):
        self.assertIn("4b", self.codes("Jonas, thank you so much! - Priya, Midtown", text=""))
        self.assertNotIn("4b", self.codes("Jonas, thank you for the rating! - Priya, Midtown", text=""))

    # 4c staff consent
    def test_4c_no_consent(self):
        self.assertIn("4c", self.codes("Jonas, Omar loved making your sourdough. - Priya, Midtown"))

    def test_4c_former_staff(self):
        self.assertIn("4c", self.codes("Martin, Theo says hi and thanks for the espresso. - Marco, Riverside",
                                       location="Riverside", reviewer="Martin Cole", text="Great espresso."))

    def test_4c_wrong_location(self):
        self.assertIn("4c", self.codes("Jonas, Hannah loved your sourdough note. - Priya, Midtown"))

    def test_4c_consenting_staff_ok(self):
        self.assertEqual(self.codes("Jonas, Jess loved hearing about the sourdough. - Priya, Midtown"), [])

    def test_4c_unknown_name_from_review(self):
        self.assertIn("4c", self.codes("Sophie, Ana at the counter was sweet to you. - Marco, Riverside",
                                       location="Riverside", reviewer="Sophie Durand", text="Ana at the counter was so sweet."))

    def test_4c_reviewer_sharing_staff_name_ok(self):
        self.assertEqual(self.codes("Hannah, sorry parking was a hassle. - Marco, Riverside", location="Riverside",
                                    reviewer="Hannah Fisher", text="Parking is a nightmare."), [])

    # 4d compensation / legal fault
    def test_4d_compensation(self):
        for bad in ("your next coffee is free", "we'd like to offer a refund", "a 20% off voucher",
                    "a discount next time", "the next one is on us"):
            self.assertIn("4d", self.codes(f"Jonas, thanks for the sourdough note, {bad}. - Priya, Midtown"), bad)

    def test_4d_spanish_compensation(self):
        self.assertIn("4d", self.codes("Mateo, gracias por tu visita, el próximo pan es gratis. - Marco, Riverside",
                                       location="Riverside", reviewer="Mateo Alvarez", text="Excelente pan y servicio rápido."))

    def test_4d_gluten_free_is_not_an_offer(self):
        self.assertNotIn("4d", self.codes("Jonas, glad you loved our gluten-free sourdough. - Priya, Midtown"))

    def test_4d_legal_fault(self):
        self.assertIn("4d", self.codes("Jonas, the sourdough issue was our fault and we are liable. - Priya, Midtown"))

    # 4e contact details
    def test_4e_contact_details(self):
        for bad in ("email us at hello@lanternloaf.com", "call 555-123-4567", "see www.lanternloaf.test",
                    "visit https://x.example"):
            self.assertIn("4e", self.codes(f"Jonas, thanks for the sourdough note, {bad}. - Priya, Midtown"), bad)

    # 4f language
    def test_4f_spanish_review_needs_spanish_reply(self):
        txt = "¡El mejor café de la zona! Muy amables."
        self.assertIn("4f", self.codes("Carmen, thank you, glad you liked the coffee in the zona! - Priya, Midtown",
                                       reviewer="Carmen Ruiz", text=txt))
        self.assertNotIn("4f", self.codes("Carmen, ¡muchas gracias! Nos alegra que te guste el café de la zona. - Priya, Midtown",
                                          reviewer="Carmen Ruiz", text=txt))
        self.assertEqual(detect_language("Me encantó el patio."), "es")
        self.assertEqual(detect_language("Best bakery in Old Town."), "en")
        self.assertEqual(detect_language("Nice patio."), "en")       # 'patio' is English too
        self.assertEqual(detect_language("Excelente pan y servicio rápido."), "es")

    # 4g sign-off
    def test_4g_signoff(self):
        self.assertIn("4g", self.codes("Jonas, so glad you loved our sourdough. - Priya"))
        self.assertIn("4g", self.codes("Jonas, so glad you loved our sourdough. - Marco, Riverside"))
        self.assertIn("4g", self.codes("Jonas, so glad you loved our sourdough at Midtown. Priya"))

    # 4h length and uniqueness
    def test_4h_length(self):
        long = "Jonas, " + "we loved hearing about the sourdough " * 10 + "- Priya, Midtown"
        self.assertIn("4h", self.codes(long))

    def test_4h_uniqueness(self):
        self.assertIn("4h", self.codes(GOOD, others=["something else", GOOD]))
        self.assertIn("4h", self.codes(GOOD, others=["  " + GOOD.upper() + " "]))
        self.assertNotIn("4h", self.codes(GOOD, others=["something else"]))

    # 4i other location
    def test_4i_other_location(self):
        txt = "Visited your Old Town shop - loved the courtyard!"
        self.assertIn("4i", self.codes("Clara, glad you loved the courtyard! - Marco, Riverside", location="Riverside",
                                       reviewer="Clara Jensen", text=txt, about="Old Town"))
        self.assertNotIn("4i", self.codes("Clara, glad you loved the courtyard at Old Town! - Marco, Riverside",
                                          location="Riverside", reviewer="Clara Jensen", text=txt, about="Old Town"))

    def test_loads_real_csvs(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        r = ReplyRules.from_csv(os.path.join(root, "staff.csv"), os.path.join(root, "locations.csv"))
        self.assertTrue(r.may_name("Lena", "Riverside"))
        self.assertFalse(r.may_name("Lena", "Midtown"))      # current, but at another location
        self.assertFalse(r.may_name("Jess", "Midtown"))      # left 2026-10-03 (staff_update.csv)
        self.assertFalse(r.may_name("Omar", "Midtown"))
        self.assertFalse(r.may_name("Theo", "Riverside"))


if __name__ == "__main__":
    unittest.main()
