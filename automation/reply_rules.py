"""Local validator for playbook section 4 (reply rules).

Usage from code:
    rules = ReplyRules.from_csv("staff.csv", "locations.csv")
    problems = rules.validate(reply_text, location="Midtown", reviewer="Jonas Weber",
                              review_text="Perfect sourdough.", other_replies=[...])
`problems` is a list of (rule, message) tuples; an empty list means the draft passes.

CLI:  python3 -m automation.reply_rules replies.csv inventory.csv decisions.csv
"""
import csv
import re
import sys
import unicodedata

MAX_CHARS = 350
LOCATIONS = ("Midtown", "Riverside", "Old Town")

COMPENSATION_PATTERNS = [
    r"\brefund", r"\bdiscount", r"(?<!-)\bfree\b(?!-)", r"\bfreebie", r"\bon the house\b",
    r"\bcompensat", r"\bvoucher", r"\bcoupon", r"\bgift card", r"\breimburs", r"\bcredit\b",
    r"\b\d+\s?% off\b", r"\bmoney back\b", r"\bcomplimentary\b", r"\bnext (one|coffee|visit) is on us\b",
    r"\bon us\b", r"\breembols", r"\bdescuento", r"\bgratis\b", r"\bcup[oó]n", r"\bcompensaci[oó]n",
    r"\bte invitamos\b", r"\bdevoluci[oó]n",
]
LEGAL_FAULT_PATTERNS = [
    r"\bour fault\b", r"\bliab(le|ility)\b", r"\bnegligen", r"\bwe admit\b", r"\bwe are responsible\b",
    r"\bwe were responsible\b", r"\bculpa nuestra\b", r"\bnuestra culpa\b",
]
CONTACT_PATTERNS = [
    r"https?://", r"\bwww\.", r"\b[\w.-]+\.(com|net|org|io|co|test|uk|es|info|biz)\b",
    r"[\w.+-]+@[\w-]+\.[\w.]+", r"@\w+", r"(?:\+?\d[\s().-]?){7,}",
]
SPANISH_WORDS = {"el", "la", "los", "las", "de", "del", "que", "y", "muy", "es", "con", "por", "para",
                 "una", "un", "gracias", "mejor", "excelente", "pan", "servicio", "rápido", "me",
                 "encantó", "amables", "zona", "café", "nos", "alegra", "visita", "esperamos", "pronto",
                 "su", "tu", "tus", "sus", "equipo", "patio", "muchas", "valoración", "estrellas", "en",
                 "nuestro", "nuestra", "volver", "verte", "le", "les", "al", "lo", "se", "más", "todo"}
ENGLISH_WORDS = {"the", "and", "is", "was", "a", "an", "to", "of", "for", "with", "thank", "thanks",
                 "you", "your", "we", "our", "it", "in", "on", "but", "so", "best", "great", "good",
                 "love", "loved", "glad", "see", "soon", "this", "that", "my", "i", "here", "were",
                 "be", "are", "at", "back", "really", "very", "will", "had", "have", "they", "their"}
# Function and filler words ignored when checking that a reply mentions something specific (4b).
STOPWORDS = {_w for _w in """
the and is was a an to of for with thank thanks you your we our it in on but so this that my i here
were be are at back really very will had have they their just again always every time been much such
what from about there would could came went visit visited though team staff service nice amazing
wonderful perfect best great good love loved glad soon them then than when where which while into
also more most some other ones only even ever over hope come coming next look forward thrilled
delighted happy kind words means everyone everything sorry passed shared feedback
el la los las de del que y muy es con por para una un gracias me nos su tu sus tus en al lo se le les
mas todo esta este esto pero como muchas mucho equipo esperamos pronto alegra""".split()}
NAME_WHITELIST = {"Lantern", "Loaf", "Google", "Old", "Town", "Midtown", "Riverside", "Saturday",
                  "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "I"}


def _norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s or "")).strip()


def _fold(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def reviewer_first_name(display_name):
    """First word of the display name, or None for initials-only names and 'A Google User'."""
    name = _norm(display_name)
    if not name or name.lower() == "a google user":
        return None
    tokens = name.split()
    if all(re.fullmatch(r"[A-Za-z]\.?", t) for t in tokens):
        return None
    first = tokens[0]
    if re.fullmatch(r"[A-Za-z]\.?", first):
        return None
    return first


def detect_language(text):
    """'es' or 'en' by stopword vote; None if the text is empty."""
    words = re.findall(r"[a-záéíóúñü¡¿']+", (text or "").lower())
    if not words:
        return None
    if any(c in (text or "") for c in "¡¿ñ"):
        return "es"
    es = sum(w in SPANISH_WORDS for w in words)
    en = sum(w in ENGLISH_WORDS for w in words)
    return "es" if es > en else "en"


def _content_words(text):
    out = set()
    for w in re.findall(r"[a-z]+", _fold(text)):
        if len(w) >= 4 and w not in STOPWORDS:
            out.add(w[:5])  # crude stem: "scones"/"scone", "pastries"/"pastr"
    return out


def signoff(manager, location):
    return f"- {manager}, {location}"


class ReplyRules:
    def __init__(self, staff_rows, location_rows):
        self.staff = [dict(r) for r in staff_rows]
        self.managers = {r["location"]: r["manager"] for r in location_rows}

    @classmethod
    def from_csv(cls, staff_csv, locations_csv):
        with open(staff_csv, newline="", encoding="utf-8") as f:
            staff = list(csv.DictReader(f))
        with open(locations_csv, newline="", encoding="utf-8") as f:
            locs = list(csv.DictReader(f))
        return cls(staff, locs)

    # --- staff consent (4c) -------------------------------------------------
    def staff_names(self):
        return {r["first_name"] for r in self.staff}

    def may_name(self, first_name, location):
        for r in self.staff:
            if (r["first_name"].lower() == first_name.lower() and r["location"] == location
                    and r["status"].strip().lower().startswith("current")
                    and r["public_mention_consent"].strip().lower() == "yes"):
                return True
        return False

    def names_in(self, reply, location, reviewer="", review_text=""):
        """Person names used in the reply other than the reviewer's own first name."""
        reviewer_first = reviewer_first_name(reviewer)
        found = []
        for name in sorted(self.staff_names()):
            if reviewer_first and name.lower() == reviewer_first.lower():
                continue
            if re.search(rf"\b{re.escape(name)}\b", reply):
                found.append(name)
        # Names the reviewer used that are not in staff.csv (e.g. "Ana at the counter").
        review_caps = set(re.findall(r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b", review_text or ""))
        for m in re.finditer(r"(?<![.!?¡¿]\s)(?<!^)\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b", reply):
            w = m.group(1)
            if (w in review_caps and w not in NAME_WHITELIST and w not in found
                    and w not in self.staff_names() and (not reviewer_first or w != reviewer_first)
                    and w not in LOCATIONS):
                found.append(w)
        return found

    # --- main entry --------------------------------------------------------
    def validate(self, reply, location, reviewer, review_text="", other_replies=(),
                 about_location=None):
        reply_n = _norm(reply)
        problems = []
        first = reviewer_first_name(reviewer)

        # a. name rule
        if first:
            if not re.match(rf"^{re.escape(first)}\b", reply_n):
                problems.append(("4a", f"reply must start with the reviewer's first name '{first}'"))
        else:
            words = [w for w in _norm(reviewer).replace(".", " ").split() if w]
            if reviewer and _norm(reviewer).lower() != "a google user":
                for w in words:
                    if len(w) > 1 and re.search(rf"\b{re.escape(w)}\b", reply_n):
                        problems.append(("4a", f"reviewer has no usable first name; do not use '{w}'"))

        manager = self.managers.get(location)
        expected = signoff(manager, location)
        body = reply_n[: -len(expected)].strip() if reply_n.endswith(expected) else reply_n

        # b. one specific thing / thank for rating
        if not (review_text or "").strip():
            if not re.search(r"\b(rating|stars?|valoraci[oó]n|estrellas)\b", body, re.I):
                problems.append(("4b", "star-only review: thank them for the rating"))
        elif not (_content_words(review_text) & _content_words(body)):
            problems.append(("4b", "reply does not mention anything specific from the review"))

        # c. staff consent
        for name in self.names_in(reply_n, location, reviewer, review_text):
            if not self.may_name(name, location):
                problems.append(("4c", f"'{name}' may not be named publicly at {location}; say 'the team'"))

        # d. compensation / legal fault
        low = reply_n.lower()
        for pat in COMPENSATION_PATTERNS:
            if re.search(pat, low):
                problems.append(("4d", f"compensation offer ({pat})"))
                break
        for pat in LEGAL_FAULT_PATTERNS:
            if re.search(pat, low):
                problems.append(("4d", f"admission of legal fault ({pat})"))
                break

        # e. contact details
        for pat in CONTACT_PATTERNS:
            if re.search(pat, reply_n, re.I):
                problems.append(("4e", f"contact detail or link ({pat})"))
                break

        # f. language
        want = detect_language(review_text)
        if want:
            got = detect_language(body)
            if got != want:
                problems.append(("4f", f"reply language {got} does not match review language {want}"))

        # g. sign-off and location name
        if not reply_n.endswith(expected):
            problems.append(("4g", f"must end with '{expected}'"))
        if location not in reply_n:
            problems.append(("4g", f"location name '{location}' missing"))

        # h. length and uniqueness
        if len(reply_n) > MAX_CHARS:
            problems.append(("4h", f"{len(reply_n)} characters (max {MAX_CHARS})"))
        if any(_norm(o).lower() == reply_n.lower() for o in other_replies if o is not None):
            problems.append(("4h", "identical to another reply"))

        # i. review about a different one of our locations
        if about_location and about_location != location:
            if about_location not in body:
                problems.append(("4i", f"review is about {about_location}; mention it by name"))
        return problems


def main(argv):
    """Validate replies.csv against inventory and decisions. Exit 1 on any failure."""
    import os
    if len(argv) < 3:
        print(__doc__)
        return 2
    replies_csv, inventory_csv, decisions_csv = argv[:3]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rules = ReplyRules.from_csv(os.path.join(root, "staff.csv"), os.path.join(root, "locations.csv"))
    inv = {r["our_id"]: r for r in csv.DictReader(open(inventory_csv, encoding="utf-8"))}
    dec = {r["our_id"]: r for r in csv.DictReader(open(decisions_csv, encoding="utf-8"))}
    replies = list(csv.DictReader(open(replies_csv, encoding="utf-8")))
    texts = [r["reply_text"] for r in replies]
    bad = 0
    for i, r in enumerate(replies):
        rv = inv[r["our_id"]]
        others = texts[:i] + texts[i + 1:] + [v["existing_reply"] for k, v in inv.items()
                                              if k != r["our_id"] and v.get("existing_reply")]
        about = None
        m = re.search(r"about_location=([A-Za-z ]+?)(;|$)", dec.get(r["our_id"], {}).get("notes", ""))
        if m:
            about = m.group(1).strip()
        probs = rules.validate(r["reply_text"], r["location"], rv["reviewer"], rv["text"], others, about)
        status = "PASS" if not probs else "FAIL"
        bad += bool(probs)
        print(f"{status} {r['our_id']} ({len(_norm(r['reply_text']))} chars)" +
              "".join(f"\n    [{c}] {m}" for c, m in probs))
    print(f"\n{len(replies) - bad}/{len(replies)} replies pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
