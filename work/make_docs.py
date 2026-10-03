"""Write old_town_replies.md, owner_digest.md and removal_requests.csv for a phase.
    python3 work/make_docs.py phase1|final
"""
import csv
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "work"))

CFG = {
    "phase1": dict(date="2026-10-01", deadline="2026-10-02"),
    "final": dict(date="2026-10-02", deadline="2026-10-03"),
}


def load(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def main(phase):
    out = os.path.join(ROOT, "output", phase)
    cfg = CFG[phase]
    T = importlib.import_module(f"triage_{phase}").T
    extra = getattr(importlib.import_module(f"triage_{phase}"), "DIGEST_EXTRA", {})
    inv = {r["our_id"]: r for r in load(os.path.join(out, "review_inventory.csv"))}
    dec = load(os.path.join(out, "decisions.csv"))
    rep = {r["our_id"]: r for r in load(os.path.join(out, "replies.csv"))}
    locs = {r["location"]: r for r in load(os.path.join(out, "locations_used.csv") if os.path.exists(os.path.join(out, "locations_used.csv")) else os.path.join(ROOT, "locations.csv"))}

    def head(oid):
        r = inv[oid]
        return f"**{oid}** · {r['location']} · {r['reviewer']} · {r['stars']}★ · {r['create_date']}"

    # ---- removal requests
    rem = [d for d in dec if d["category"] == "report"]
    with open(os.path.join(out, "removal_requests.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["our_id", "location", "review_id", "reviewer", "stars", "create_date", "reason", "playbook_basis", "text"])
        for d in rem:
            r = inv[d["our_id"]]
            w.writerow([d["our_id"], d["location"], r["review_id"], r["reviewer"], r["stars"], r["create_date"],
                        T[d["our_id"]]["removal"], "playbook 2.2 (report): " + T[d["our_id"]]["why"], r["text"]])

    # ---- Old Town replies
    ot = [f"# Old Town replies to post by hand ({phase})\n",
          "Old Town is not connected to the API, so these replies are for the owner to paste into Google "
          "Business Profile. Each one passed reply_rules.py (playbook section 4).\n",
          "Once you've posted them, tell us which ones went up so the report can move them from *manual pending* to *replied*.\n"]
    new_ot = [d for d in dec if d["location"] == "Old Town" and d["our_id"] in rep and "[corrected]" not in d["notes"]]
    corr_ot = [d for d in dec if d["location"] == "Old Town" and "[corrected]" in d["notes"]]
    ot.append("## New replies\n")
    for d in new_ot:
        r = inv[d["our_id"]]
        status = T[d["our_id"]].get("ot_status", "to post")
        ot.append(f"### {d['our_id']} · {r['reviewer']} · {r['stars']}★ · {r['create_date']} · {status}\n")
        ot.append(f"> {r['text'] or '(stars only, no text)'}\n")
        ot.append(f"Reply to post ({rep[d['our_id']]['language']}, {rep[d['our_id']]['char_count']} chars):\n")
        ot.append(f"```\n{rep[d['our_id']]['reply_text']}\n```\n")
    ot.append("## Existing Old Town replies to correct\n")
    if corr_ot:
        for d in corr_ot:
            r = inv[d["our_id"]]
            ot.append(f"### {d['our_id']} · {r['reviewer']} · {r['stars']}★\n")
            ot.append(f"Current reply: `{r['existing_reply']}`  \nWhy: {T[d['our_id']].get('odd', '')}\n")
            ot.append(f"Replace with:\n```\n{rep[d['our_id']]['reply_text']}\n```\n")
    else:
        ot.append("None. The only existing Old Town reply (O01, Isabel Moreau: \"Thank you Isabel! - Hannah, Old Town\") "
                  "names no one who may not be named.\n")
    ot.append("## Old Town reviews with no reply\n")
    for d in dec:
        if d["location"] == "Old Town" and d["our_id"] not in rep:
            ot.append(f"- {head(d['our_id'])}: {d['category']}" + (f" ({d['issue']})" if d['issue'] else ""))
    with open(os.path.join(out, "old_town_replies.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(ot) + "\n")

    # ---- Owner digest
    g = [f"# Owner digest: Lantern & Loaf Google reviews ({phase}, {cfg['date']})\n"]
    if extra.get("intro"):
        g.append(extra["intro"] + "\n")
    g.append("## 1. URGENT: phone the location manager within 24 hours\n")
    g.append(f"Per playbook section 2, each item below needs a call to the manager by **{cfg['deadline']}** "
             f"(24 hours from this digest). We have not replied publicly to any of them.\n")
    for d in [d for d in dec if d["category"] == "urgent"]:
        r = inv[d["our_id"]]
        mgr = locs[d["location"]]["manager"]
        g.append(f"- {head(d['our_id'])}  \n  **Why urgent:** {T[d['our_id']]['why']}  \n"
                 f"  **Issue:** {d['issue']}  \n  **Review:** \"{r['text']}\"  \n"
                 f"  **Action:** call {mgr} ({d['location']} manager) by {cfg['deadline']}.")
    g.append("\n## 2. Flags for your decision\n")
    g.append("Tell us *reply* (with any points to include) or *no reply* for each. Reviews marked reply+flag "
             "already have a public reply; the flag is the operational issue.\n")
    for pri in ("high", "normal"):
        items = [d for d in dec if d["flag_priority"] == pri]
        g.append(f"### Priority: {pri} ({len(items)})\n")
        for d in items:
            r = inv[d["our_id"]]
            state = "replied publicly" if d["category"] == "reply+flag" else "no reply until you decide"
            g.append(f"- {head(d['our_id'])} · {d['category']} ({state})  \n  {d['issue']}")
        g.append("")
    if extra.get("closed"):
        g.append("### Owner decisions applied\n")
        g.extend(extra["closed"])
        g.append("")
    g.append("## 3. Removal requests (ask Google to remove; we have not replied)\n")
    g.append("Also in `removal_requests.csv`.\n")
    for d in rem:
        g.append(f"- {head(d['our_id'])}: {T[d['our_id']]['removal']}. \"{inv[d['our_id']]['text']}\"")
    g.append("\n## 4. Reply corrections made\n")
    corr = [d for d in dec if "[corrected]" in d["notes"]]
    if not corr:
        g.append("None.")
    for d in corr:
        r = inv[d["our_id"]]
        how = "posted via the API" if d["location"] != "Old Town" else "for you to edit by hand (see old_town_replies.md)"
        old = T[d["our_id"]].get("old_reply") or r["existing_reply"]
        g.append(f"- {head(d['our_id'])} ({how})  \n  Why: {T[d['our_id']].get('odd', '')}  \n"
                 f"  Was: \"{old}\"  \n  Now: \"{rep[d['our_id']]['reply_text']}\"")
    g.append("\n## 5. Other notes\n")
    deleted = [d for d in dec if d["category"] == "deleted"]
    for d in deleted:
        g.append(f"- {head(d['our_id'])} was removed from Google (404 when replying). Listed as deleted and excluded from the report.")
    for line in extra.get("notes", []):
        g.append(f"- {line}")
    n_ot = len(new_ot)
    g.append(f"- {n_ot} Old Town replies are ready for you to post by hand: see `old_town_replies.md`.")
    with open(os.path.join(out, "owner_digest.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(g) + "\n")
    print(f"docs -> {out}: {len(rem)} removal requests, {n_ot} Old Town replies")


if __name__ == "__main__":
    main(sys.argv[1])
