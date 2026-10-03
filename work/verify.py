"""Final verification checks; prints markdown. Exit 1 if any check fails."""
import csv
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from automation.gbp_client import GBPClient, stars_of  # noqa: E402
from automation.reconcile import run as reconcile  # noqa: E402
from automation.reply_rules import ReplyRules, detect_language  # noqa: E402

OT_POSTED = ["O02", "O04", "O06", "O08", "O09", "O10", "O12"]
fails = []


def load(ph, n):
    return list(csv.DictReader(open(os.path.join(ROOT, "output", ph, n), encoding="utf-8")))


def check(name, ok, detail=""):
    print(f"- {'PASS' if ok else 'FAIL'}: {name}" + (f" ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


inv = {r["our_id"]: r for r in load("final", "review_inventory.csv")}
dec = {r["our_id"]: r for r in load("final", "decisions.csv")}
rep = {r["our_id"]: r for r in load("final", "replies.csv")}
c = GBPClient()
live = {}
for loc, lid in (("Midtown", "4471"), ("Riverside", "4472")):
    pages = c.list_reviews(lid)
    for r in pages:
        live[r["reviewId"]] = (loc, r)

print("### A. Live API vs final inventory and replies\n")
by_rid = {r["review_id"]: k for k, r in inv.items() if r["review_id"]}
field_mismatch, reply_mismatch = [], []
for rid, (loc, r) in live.items():
    oid = by_rid.get(rid)
    if not oid:
        field_mismatch.append(f"{rid} not in inventory"); continue
    i = inv[oid]
    if (i["location"], int(i["stars"]), i["text"], i["create_date"]) != (loc, stars_of(r), r.get("comment", ""), r["createTime"][:10]):
        field_mismatch.append(oid)
    want = rep[oid]["reply_text"] if oid in rep else (i["existing_reply"] or None)
    got = (r.get("reviewReply") or {}).get("comment")
    if got != want:
        reply_mismatch.append(f"{oid}: live={got!r} want={want!r}")
api_inv = [k for k, r in inv.items() if r["source"] == "api"]
check(f"every live review ({len(live)}) is in the inventory with the same location, stars, text and create date",
      not field_mismatch, ", ".join(field_mismatch))
check("every live reply equals replies.csv (or the untouched existing reply); reviews without a reply have none",
      not reply_mismatch, "; ".join(reply_mismatch))
missing = sorted(set(api_inv) - {by_rid[r] for r in live})
check("inventory API rows not returned live are exactly the deleted ones", all(dec[m]["category"] == "deleted" for m in missing),
      f"not live: {missing}")
for m in missing:
    try:
        c.get_review(inv[m]["location"] == "Midtown" and "4471" or "4472", inv[m]["review_id"]); check(f"{m} GET is 404", False)
    except Exception as e:
        check(f"{m} GET returns 404", "404" in str(e))

print("\n### B. Every reply that is live or for the owner to post follows section 4\n")
rules = ReplyRules.from_csv(os.path.join(ROOT, "staff.csv"), os.path.join(ROOT, "locations.csv"))
all_texts = {}
for rid, (loc, r) in live.items():
    if r.get("reviewReply"):
        all_texts[by_rid[rid]] = r["reviewReply"]["comment"]
for k in rep:
    all_texts.setdefault(k, rep[k]["reply_text"])
all_texts["O01"] = inv["O01"]["existing_reply"]
ours, legacy = [], []
for oid, text in sorted(all_texts.items()):
    others = [t for k, t in all_texts.items() if k != oid]
    about = (re.search(r"about_location=([A-Za-z ]+?)(;|$)", dec[oid]["notes"]) or [None, None])[1]
    probs = rules.validate(text, inv[oid]["location"], inv[oid]["reviewer"], inv[oid]["text"], others, about)
    if oid in rep:
        ours.append((oid, probs))
    else:
        legacy.append((oid, [p for p in probs if p[0] in ("4c", "4d", "4e", "4h")], probs))
check(f"all {len(ours)} replies we wrote pass every rule (4a-4i)", all(not p for _, p in ours),
      "; ".join(f"{o}: {p}" for o, p in ours if p))
check(f"the {len(legacy)} untouched older replies break no hard rule (4c staff, 4d compensation, 4e contact, 4h unique)",
      all(not p for _, p, _ in legacy), "; ".join(f"{o}: {p}" for o, p, _ in legacy if p))
soft = [f"{o} [{','.join(sorted({c for c, _ in allp}))}]" for o, _, allp in legacy if allp]
print(f"- NOTE: older replies left as written (rule 1 mandates replacing only 4c breaches): {', '.join(soft)}")
jess = [k for k, t in all_texts.items() if re.search(r"\bJess\b", t)]
check("no live or pending reply names Jess (left 2026-10-03)", not jess, str(jess))
theo = [k for k, t in all_texts.items() if re.search(r"\b(Theo|Omar|Ana)\b", t)]
check("no reply names Theo, Omar or Ana", not theo, str(theo))
es = [k for k in rep if detect_language(inv[k]["text"]) == "es"]
check("Spanish reviews get Spanish replies", all(rep[k]["language"] == "es" and detect_language(rep[k]["reply_text"]) == "es" for k in es), ", ".join(es))
no_reply_cats = {"urgent", "report", "flag", "flag-closed", "deleted"}
bad = [k for k in rep if dec[k]["category"] in no_reply_cats and "[corrected]" not in dec[k]["notes"]]
check("no reply drafted for urgent / report / flag / flag-closed / deleted", not bad, str(bad))
need = [k for k, d in dec.items() if d["category"] in ("reply", "reply+flag", "owner-reply") and k not in rep]
check("every reply / reply+flag / owner-reply review has a reply", not need, str(need))
check("Old Town replies never posted via the API", not any(r["location"] == "Old Town" and r["result"] == "posted" for r in load("final", "post_log.csv")))

print("\n### C. Reports vs decisions.csv (independent recount), HTML vs JSON\n")
bad_final, text = reconcile(os.path.join(ROOT, "output/final"), ROOT, OT_POSTED, c)
open(os.path.join(ROOT, "output/final/reconciliation.md"), "w").write("# Reconciliation: output/final\n\n" + text + "\n")
n_ok = text.count("| OK |")
check(f"final: post log vs live, live replies accounted for, {n_ok} report numbers recounted by location and total, HTML table vs JSON",
      bad_final == 0, f"{bad_final} mismatches; see output/final/reconciliation.md")

# phase 1 offline recount (the phase 1 API state no longer exists; replied = existing reply or a successful phase 1 post)
r1 = json.load(open(os.path.join(ROOT, "output/phase1/report.json")))
i1 = {r["our_id"]: r for r in load("phase1", "review_inventory.csv")}
d1 = {r["our_id"]: r for r in load("phase1", "decisions.csv")}
posted1 = {r["our_id"] for r in load("phase1", "post_log.csv") if r["result"] == "posted"}
rp1 = {r["our_id"] for r in load("phase1", "replies.csv")}
mism = []
for scope in ["Midtown", "Riverside", "Old Town", None]:
    rows = [k for k, r in i1.items() if r["create_date"].startswith("2026-09") and d1[k]["category"] != "deleted"
            and (scope is None or r["location"] == scope)]
    got = r1["total"] if scope is None else r1["by_location"][scope]
    replied = [k for k in rows if i1[k]["existing_reply"] or k in posted1]
    exp = {"new_reviews": len(rows), "replied": len(replied),
           "average_rating": round(sum(int(i1[k]["stars"]) for k in rows) / len(rows) + 1e-9, 2),
           "reply_rate": round(100 * len(replied) / len(rows) + 1e-9, 1),
           "manual_pending": sum(i1[k]["location"] == "Old Town" and k in rp1 and not i1[k]["existing_reply"] for k in rows),
           "flagged_for_owner": sum(d1[k]["category"] in ("flag", "reply+flag", "owner-reply", "flag-closed") for k in rows),
           "awaiting_owner": sum(d1[k]["category"] in ("flag", "reply+flag") for k in rows),
           "urgent": sum(d1[k]["category"] == "urgent" for k in rows),
           "removal_requested": sum(d1[k]["category"] == "report" for k in rows),
           **{f"stars_{s}": sum(int(i1[k]["stars"]) == s for k in rows) for s in range(1, 6)}}
    for k, v in exp.items():
        if got[k] != v:
            mism.append(f"{scope or 'total'}.{k}: {got[k]} vs {v}")
check("phase 1 report.json recounted offline from phase 1 decisions + inventory + post log (15 metrics x 4 scopes)",
      not mism, "; ".join(mism))
for ph in ("phase1", "final"):
    html = open(os.path.join(ROOT, "output", ph, "report.html"), encoding="utf-8").read()
    data = json.loads(re.search(r'<script type="application/json" id="report-data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
    rj = json.load(open(os.path.join(ROOT, "output", ph, "report.json")))
    same = data["total"] == {k: v for k, v in rj["total"].items() if k != "ids"} and all(
        data["by_location"][l] == {k: v for k, v in rj["by_location"][l].items() if k != "ids"} for l in rj["by_location"])
    bars = len(re.findall(r'<path class="bar', html))
    nonzero = sum(1 for l in rj["by_location"].values() for s in range(1, 6) if l[f"stars_{s}"])
    check(f"{ph}: report.html embedded data equals report.json; SVG has one bar per non-zero cell ({bars}/{nonzero})",
          same and bars == nonzero)
    a = rj["august_comparison"]
    check(f"{ph}: August recomputed = sum of locations, compared to august_report.json (16/3.69/7)",
          a["recomputed"]["total"]["new_reviews"] == sum(v["new_reviews"] for v in a["recomputed"]["by_location"].values())
          and a["previous_report"] == {"new_reviews": 16, "average_rating": 3.69, "replied": 7}
          and a["recomputed_api_only"]["new_reviews"] == 16 and a["recomputed_api_only"]["average_rating"] == 3.69
          and a["recomputed_api_only"]["replied_at_month_end"] == 7,
          f"recomputed {a['differences']}")

print("\n### D. Owner documents agree with decisions\n")
for ph in ("phase1", "final"):
    d = {r["our_id"]: r for r in load(ph, "decisions.csv")}
    rr = load(ph, "removal_requests.csv")
    check(f"{ph}: removal_requests.csv = category report", sorted(r["our_id"] for r in rr) == sorted(k for k, v in d.items() if v["category"] == "report"),
          ", ".join(r["our_id"] for r in rr))
    dig = open(os.path.join(ROOT, "output", ph, "owner_digest.md"), encoding="utf-8").read()
    urg = dig.split("## 2.")[0]
    ids_urg = sorted(set(re.findall(r"\*\*([MRO]\d\d)\*\*", urg)))
    check(f"{ph}: digest urgent section = category urgent", ids_urg == sorted(k for k, v in d.items() if v["category"] == "urgent"), ", ".join(ids_urg))
    flags = dig.split("## 2.")[1].split("## 3.")[0].split("### Owner decisions")[0]
    ids_fl = sorted(set(re.findall(r"\*\*([MRO]\d\d)\*\*", flags)))
    check(f"{ph}: digest flags = categories flag + reply+flag", ids_fl == sorted(k for k, v in d.items() if v["category"] in ("flag", "reply+flag")), ", ".join(ids_fl))
    otm = open(os.path.join(ROOT, "output", ph, "old_town_replies.md"), encoding="utf-8").read()
    rp = load(ph, "replies.csv")
    check(f"{ph}: every Old Town reply text in old_town_replies.md matches replies.csv",
          all(r["reply_text"] in otm for r in rp if r["location"] == "Old Town"))
    check(f"{ph}: char_count column equals len(reply_text)", all(int(r["char_count"]) == len(r["reply_text"]) for r in rp))

print("\n### E. Unit tests\n")
t = subprocess.run([sys.executable, "-m", "unittest", "discover", "-v", "automation/tests"], cwd=ROOT, capture_output=True, text=True)
check("python3 -m unittest discover automation/tests", t.returncode == 0)
print("\n```\n" + t.stderr.strip() + "\n```")
print(f"\n**{len(fails)} failing check(s)**" + (": " + "; ".join(fails) if fails else ""))
sys.exit(1 if fails else 0)
