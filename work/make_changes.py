"""changes_report.md: every review whose category, stars, text, reply or report treatment changed between
phase 1 and final (with cause), and every report number that changed (old -> new)."""
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "work"))
from triage_final import T as TF  # noqa: E402


def load(ph, name):
    return {r["our_id"]: r for r in csv.DictReader(open(os.path.join(ROOT, "output", ph, name), encoding="utf-8"))}


def treatment(rep):
    out = {}
    for scope in list(rep["by_location"]) + ["total"]:
        d = rep["total"] if scope == "total" else rep["by_location"][scope]
        if scope == "total":
            continue
        for metric, ids in d["ids"].items():
            for i in ids:
                out.setdefault(i, set()).add(metric)
    return out


def main():
    i1, i2 = load("phase1", "review_inventory.csv"), load("final", "review_inventory.csv")
    d1, d2 = load("phase1", "decisions.csv"), load("final", "decisions.csv")
    r1, r2 = load("phase1", "replies.csv"), load("final", "replies.csv")
    rep1 = json.load(open(os.path.join(ROOT, "output/phase1/report.json"), encoding="utf-8"))
    rep2 = json.load(open(os.path.join(ROOT, "output/final/report.json"), encoding="utf-8"))
    t1, t2 = treatment(rep1), treatment(rep2)
    L = ["# Changes: phase 1 -> final\n",
         "Causes: owner decisions of 2026-10-04 (playbook section 6), Jess leaving on 2026-10-03 (staff_update.csv, rule 4c), "
         "and changes in the API between phase 1 and phase 2 (new, edited and vanished reviews). Old Town treatment also changed "
         "because the owner confirmed posting all phase 1 Old Town replies on 2026-10-03.\n",
         "our_ids are stable: phase 1 ids keep their meaning; new reviews got the next free number (M27, R25).\n",
         "## Reviews that changed\n",
         "| our_id | reviewer | what changed | phase 1 | final | cause |", "|---|---|---|---|---|---|"]
    count = 0
    for oid in sorted(set(i1) | set(i2), key=lambda x: ("MRO".index(x[0]), int(x[1:]))):
        a, b = i1.get(oid), i2.get(oid)
        rows = []
        if a is None:
            rows.append(("new review", "-", f"{b['stars']}★ \"{b['text']}\" → {d2[oid]['category']}"))
        else:
            if d1[oid]["category"] != d2[oid]["category"]:
                rows.append(("category", d1[oid]["category"], d2[oid]["category"]))
            if a["stars"] != b["stars"]:
                rows.append(("stars", a["stars"] + "★", b["stars"] + "★"))
            if a["text"] != b["text"]:
                rows.append(("text", f"\"{a['text']}\"", f"\"{b['text']}\""))
            # reply in effect: our draft/post if any, else the pre-existing owner reply
            ra = r1.get(oid, {}).get("reply_text") or a["existing_reply"]
            rb = r2.get(oid, {}).get("reply_text") or b["existing_reply"]
            if ra != rb:
                rows.append(("reply", f"\"{ra}\"" if ra else "none", f"\"{rb}\"" if rb else "none"))
        ta, tb = t1.get(oid, set()), t2.get(oid, set())
        if ta != tb:
            fmt = lambda s: ", ".join(sorted(s)) or "not counted"  # noqa: E731
            rows.append(("report treatment", fmt(ta), fmt(tb)))
        if rows:
            count += 1
            cause = TF.get(oid, {}).get("history", "") or "see above"
            name = (b or a)["reviewer"]
            for j, (what, old, new) in enumerate(rows):
                L.append(f"| {oid if j == 0 else ''} | {name if j == 0 else ''} | {what} | {old} | {new} | {cause if j == 0 else ''} |")
    L.insert(4, f"{count} reviews changed.\n")
    L += ["", "## Report numbers that changed (September 2026)\n", "| scope | metric | phase 1 | final |", "|---|---|---|---|"]
    n = 0
    for scope in ["Midtown", "Riverside", "Old Town", "total"]:
        a = rep1["total"] if scope == "total" else rep1["by_location"][scope]
        b = rep2["total"] if scope == "total" else rep2["by_location"][scope]
        for k in a:
            if k != "ids" and a[k] != b[k]:
                n += 1
                L.append(f"| {scope} | {k} | {a[k]} | {b[k]} |")
    L.append(f"\n{n} numbers changed.")
    L += ["", "## Other report sections\n"]
    L.append(f"- Deleted reviews: phase 1 {[d['our_id'] for d in rep1['deleted_reviews']]} → final "
             f"{[d['our_id'] for d in rep2['deleted_reviews']]} (M13 removed from Google in phase 2).")
    L.append("- M23 (Simone Laurent) and R15 (Liam Walsh) were already deleted in phase 1 (404 on reply); in phase 2 the API "
             "no longer lists them at all. Their category and report treatment (excluded) are unchanged.")
    L.append(f"- Reply corrections: phase 1 {[c['our_id'] for c in rep1['reply_corrections']]} → final "
             f"{[c['our_id'] for c in rep2['reply_corrections']]} (M01 and M15 named Jess).")
    for k, v in rep2["august_comparison"]["differences"].items():
        o = rep1["august_comparison"]["differences"][k]["recomputed"]
        if o != v["recomputed"]:
            L.append(f"- August comparison, recomputed {k}: {o} → {v['recomputed']} (replies posted since phase 1 to August "
                     f"reviews, see owner decisions, plus Old Town O02 confirmed posted). august_report.json values unchanged.")
    with open(os.path.join(ROOT, "output/final/changes_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"{count} reviews, {n} numbers")


if __name__ == "__main__":
    main()
