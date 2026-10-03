"""Reconcile a delivery folder against the live API and its own decisions.

    python3 -m automation.reconcile --dir output/phase1 [--old-town-posted O02,...] [--md reconciliation.md]

Checks
 1. post log -> live: the last successful post for each review is the reply visible on that review.
 2. live -> files: every live owner reply is either one we posted or an untouched existing reply.
 3. report.json -> decisions.csv: every number is recounted independently (by location and total)
    from decisions.csv + the inventory (+ live replies/stars), and its id list matches.
 4. report.html -> report.json: the per-location table shows the same values.
Exit 1 on any mismatch.
"""
import argparse
import csv
import html.parser
import json
import os
import sys

from .gbp_client import GBPClient, stars_of

LOCS = ["Midtown", "Riverside", "Old Town"]


def load(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class _Table(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.cur, self.cell, self.inside = [], None, None, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table" and a.get("id") == "by-location":
            self.inside = True
        if self.inside and tag == "tr":
            self.cur = []
        if self.inside and tag in ("td", "th"):
            self.cell = [a.get("data-key"), ""]

    def handle_endtag(self, tag):
        if self.inside and tag in ("td", "th") and self.cell is not None:
            self.cur.append(tuple(self.cell)); self.cell = None
        if self.inside and tag == "tr" and self.cur is not None:
            self.rows.append(self.cur); self.cur = None
        if tag == "table":
            self.inside = False

    def handle_data(self, d):
        if self.cell is not None:
            self.cell[1] += d


def run(out_dir, root=".", old_town_posted=(), client=None, month="2026-09"):
    client = client or GBPClient()
    lines, bad = [], 0
    locations = load(os.path.join(root, "locations.csv"))
    inv = {r["our_id"]: r for r in load(os.path.join(out_dir, "review_inventory.csv"))}
    dec = {r["our_id"]: r for r in load(os.path.join(out_dir, "decisions.csv"))}
    replies = {r["our_id"]: r for r in load(os.path.join(out_dir, "replies.csv"))}
    log = load(os.path.join(out_dir, "post_log.csv"))
    live = {}
    for l in locations:
        if l["api_connected"] == "yes":
            for r in client.list_reviews(l["gbp_location_id"]):
                live[r["reviewId"]] = r
    by_rid = {r["review_id"]: oid for oid, r in inv.items() if r["review_id"]}

    # 1. post log -> live
    last = {}
    for row in log:
        if row["result"] == "posted":
            last[row["our_id"]] = row
    lines.append(f"## 1. Post log vs live API ({len(last)} reviews with a successful post)\n")
    for oid, row in sorted(last.items()):
        lv = live.get(row["review_id"])
        got = (lv or {}).get("reviewReply", {}).get("comment") if lv else None
        want = row["reply_text"] if row["action"] == "put" else None
        ok = got == want
        bad += not ok
        lines.append(f"- {'OK ' if ok else 'MISMATCH'} {oid} {row['review_id'][-8:]}: "
                     + ("live reply matches post log" if ok else f"live={got!r} log={want!r}"))
    # 2. live -> files
    lines.append("\n## 2. Every live owner reply accounted for\n")
    for rid, lv in sorted(live.items(), key=lambda kv: by_rid.get(kv[0], "~")):
        oid = by_rid.get(rid)
        got = (lv.get("reviewReply") or {}).get("comment")
        if oid is None:
            bad += 1
            lines.append(f"- MISMATCH review {rid} is live but not in the inventory")
            continue
        if oid in last:
            expected, why = (last[oid]["reply_text"] if last[oid]["action"] == "put" else None), "our post"
        else:
            expected, why = (inv[oid]["existing_reply"] or None), "existing reply, untouched"
        ok = got == expected
        bad += not ok
        if not ok or got:
            lines.append(f"- {'OK ' if ok else 'MISMATCH'} {oid}: {why}" + ("" if ok else f" live={got!r} expected={expected!r}"))
        if got and oid in replies and replies[oid]["reply_text"] != got and dec[oid]["category"] != "deleted":
            bad += 1
            lines.append(f"- MISMATCH {oid}: live reply differs from replies.csv")
        if oid in replies and not got and inv[oid]["location"] != "Old Town" and dec[oid]["category"] != "deleted":
            bad += 1
            lines.append(f"- MISMATCH {oid}: replies.csv has a reply but nothing is live")
    # 3. report.json recount
    rep = json.load(open(os.path.join(out_dir, "report.json"), encoding="utf-8"))
    lines.append(f"\n## 3. report.json recounted from decisions.csv ({month})\n")
    lines.append("| location | metric | report.json | recount | ok |\n|---|---|---|---|---|")
    posted = set(old_town_posted)
    rows = []
    for oid, d in dec.items():
        r = inv[oid]
        if not r["create_date"].startswith(month) or d["category"] == "deleted":
            continue
        if r["source"] == "api":
            lv = live.get(r["review_id"])
            stars, replied = stars_of(lv), bool(lv.get("reviewReply"))
        else:
            stars, replied = int(r["stars"]), bool(r["existing_reply"]) or oid in posted
        rows.append(dict(id=oid, loc=d["location"], cat=d["category"], stars=stars, replied=replied,
                         pending=d["location"] == "Old Town" and oid in replies and not replied))
    metrics = {
        "new_reviews": lambda x: True, "replied": lambda x: x["replied"], "manual_pending": lambda x: x["pending"],
        "flagged_for_owner": lambda x: x["cat"] in ("flag", "reply+flag", "owner-reply", "flag-closed"),
        "awaiting_owner": lambda x: x["cat"] in ("flag", "reply+flag"), "urgent": lambda x: x["cat"] == "urgent",
        "removal_requested": lambda x: x["cat"] == "report",
        **{f"stars_{s}": (lambda x, s=s: x["stars"] == s) for s in range(1, 6)}}
    for loc in LOCS + ["total"]:
        sub = [x for x in rows if loc == "total" or x["loc"] == loc]
        got = rep["total"] if loc == "total" else rep["by_location"][loc]
        for k, pred in metrics.items():
            ids = sorted(x["id"] for x in sub if pred(x))
            ok = got[k] == len(ids) and sorted(got["ids"][k]) == ids
            bad += not ok
            lines.append(f"| {loc} | {k} | {got[k]} | {len(ids)} | {'OK' if ok else 'MISMATCH'} |")
        n = len(sub)
        avg = round(sum(x["stars"] for x in sub) / n + 1e-9, 2) if n else None
        rr = round(100 * sum(x["replied"] for x in sub) / n + 1e-9, 1) if n else None
        for k, v in (("average_rating", avg), ("reply_rate", rr)):
            ok = got[k] == v
            bad += not ok
            lines.append(f"| {loc} | {k} | {got[k]} | {v} | {'OK' if ok else 'MISMATCH'} |")
    # 4. HTML vs JSON
    lines.append("\n## 4. report.html table vs report.json\n")
    p = _Table()
    p.feed(open(os.path.join(out_dir, "report.html"), encoding="utf-8").read())
    checked = html_bad = 0
    for tr in p.rows[1:]:
        name = tr[0][1].strip()
        got = rep["total"] if name == "Total" else rep["by_location"][name]
        for key, txt in tr[1:]:
            v = got[key]
            exp = "–" if v is None else (f"{v:.2f}" if key == "average_rating" else f"{v:.1f}" if key == "reply_rate" else str(v))
            checked += 1
            if txt.strip() != exp:
                bad += 1
                html_bad += 1
                lines.append(f"- MISMATCH {name} {key}: html={txt.strip()} json={exp}")
    lines.append(f"- {checked} table cells compared across {len(p.rows) - 1} rows; "
                 f"{html_bad} mismatch(es).")
    lines.append(f"\n**Result: {bad} mismatch(es).**")
    return bad, "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--old-town-posted", default="")
    ap.add_argument("--md")
    a = ap.parse_args(argv)
    bad, text = run(a.dir, a.root, [x for x in a.old_town_posted.split(",") if x])
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(f"# Reconciliation: {a.dir}\n\n" + text + "\n")
    print(text[-400:])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
