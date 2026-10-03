"""Write decisions.csv, triage_notes.md and replies.csv for a phase from its triage module.
    python3 work/make_outputs.py phase1|final
"""
import csv
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from automation.reply_rules import ReplyRules, detect_language  # noqa: E402

FLAG_CATS = {"flag", "reply+flag"}
LANG = {"en": "English", "es": "Spanish", None: "none (star-only)"}


def main(phase):
    out = os.path.join(ROOT, "output", phase)
    T = importlib.import_module(f"triage_{phase}").T
    staff_csv = os.path.join(out, "staff_used.csv") if os.path.exists(os.path.join(out, "staff_used.csv")) else os.path.join(ROOT, "staff.csv")
    loc_csv = os.path.join(out, "locations_used.csv") if os.path.exists(os.path.join(out, "locations_used.csv")) else os.path.join(ROOT, "locations.csv")
    rules = ReplyRules.from_csv(staff_csv, loc_csv)
    inv = list(csv.DictReader(open(os.path.join(out, "review_inventory.csv"), encoding="utf-8")))
    missing = {r["our_id"] for r in inv} ^ set(T)
    assert not missing, f"triage/inventory mismatch: {sorted(missing)}"

    dec_rows, reply_rows, notes = [], [], [f"# Triage notes ({phase})\n",
        "Category per playbook section 2 (rule 1 decides which reviews are processed). "
        "`already-replied` = has an owner reply and was not edited after it, so not processed.\n"]
    for r in inv:
        t = T[r["our_id"]]
        cat = t["cat"]
        reply = t.get("reply")
        lang = t.get("lang") or detect_language(r["text"])
        note_bits = []
        if t.get("about"):
            note_bits.append(f"about_location={t['about']}")
        if t.get("correction"):
            note_bits.append("[corrected] existing reply replaced under rule 1/4c")
        if t.get("removal"):
            note_bits.append(f"removal reason: {t['removal']}")
        if t.get("owner"):
            note_bits.append(f"owner decision: {t['owner']}")
        if t.get("note"):
            note_bits.append(t["note"])
        reply_needed = "yes" if reply else "no"
        if cat == "urgent":
            note_bits.append("call manager within 24h; do not reply")
        if r["location"] == "Old Town" and reply:
            note_bits.append("manual post by owner")
        dec_rows.append({"our_id": r["our_id"], "location": r["location"], "category": cat,
                         "flag_priority": t.get("pri", "") if cat in FLAG_CATS else "",
                         "issue": t.get("issue", ""), "reply_needed": reply_needed,
                         "notes": "; ".join(note_bits)})
        if reply:
            names = rules.names_in(reply, r["location"], r["reviewer"], r["text"])
            reply_rows.append({"our_id": r["our_id"], "location": r["location"], "reply_text": reply,
                               "char_count": len(reply), "language": lang or "en",
                               "names_used": ";".join(names)})
        staff = t.get("staff", [])
        staff_txt = ", ".join(f"{n} ({'may be named' if ok else 'may NOT be named'})" for n, ok in staff) or "none"
        notes.append(f"## {r['our_id']} · {r['location']} · {r['reviewer']} · {r['stars']}★ · {r['create_date']}\n")
        notes.append(f"- **Category:** {cat}" + (f" (priority {t['pri']})" if cat in FLAG_CATS and t.get("pri") else ""))
        notes.append(f"- **Reason:** {t['why']}")
        if t.get("issue"):
            notes.append(f"- **Issue:** {t['issue']}")
        notes.append(f"- **Staff mentioned:** {staff_txt}")
        notes.append(f"- **Language:** {LANG.get(detect_language(r['text']), lang)}")
        notes.append(f"- **Unusual:** {t.get('odd') or 'nothing'}")
        if t.get("history"):
            notes.append(f"- **History:** {t['history']}")
        notes.append("")

    with open(os.path.join(out, "decisions.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["our_id", "location", "category", "flag_priority", "issue", "reply_needed", "notes"])
        w.writeheader(); w.writerows(dec_rows)
    with open(os.path.join(out, "replies.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["our_id", "location", "reply_text", "char_count", "language", "names_used"])
        w.writeheader(); w.writerows(reply_rows)
    with open(os.path.join(out, "triage_notes.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes))
    print(f"{len(dec_rows)} decisions, {len(reply_rows)} replies -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
