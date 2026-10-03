"""Build the monthly report (playbook section 5) from decisions.csv, the inventory and live API state.

    python3 -m automation.build_report --dir output/phase1 [--month 2026-09] \
        [--old-town-posted O02,O04] [--baseline-inventory output/phase1/review_inventory.csv]

Reads <dir>/review_inventory.csv, <dir>/decisions.csv, <dir>/replies.csv; fetches live reviews for the
API-connected locations; writes <dir>/report.json and <dir>/report.html. Every count in the JSON is
backed by the list of our_ids it was counted from (`ids`), so it can be traced to decisions.csv.
"""
import argparse
import calendar
import csv
import html
import json
import os

from .gbp_client import GBPClient, stars_of

LOCATIONS = ["Midtown", "Riverside", "Old Town"]
FLAGGED = {"flag", "reply+flag", "owner-reply", "flag-closed"}
AWAITING = {"flag", "reply+flag"}
COLORS = {"Midtown": ("#2a78d6", "#3987e5"), "Riverside": ("#eb6834", "#d95926"),
          "Old Town": ("#1baf7a", "#199e70")}


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def live_state(client, locations):
    """{review_id: {'stars': int, 'reply': str|None}} for every API-connected location."""
    state = {}
    for loc in locations:
        if loc["api_connected"].strip().lower() == "yes":
            for r in client.list_reviews(loc["gbp_location_id"]):
                state[r["reviewId"]] = {"stars": stars_of(r),
                                        "reply": (r.get("reviewReply") or {}).get("comment")}
    return state


def compute(month, inventory, decisions, replies, live, old_town_posted):
    """Pure report math. Returns {'by_location': {...}, 'total': {...}}."""
    dec = {d["our_id"]: d for d in decisions}
    drafted = {r["our_id"] for r in replies}
    buckets = {loc: [] for loc in LOCATIONS}
    for r in inventory:
        if not r["create_date"].startswith(month):
            continue
        d = dec[r["our_id"]]
        if d["category"] == "deleted":
            continue
        if r["source"] == "api":
            lv = live.get(r["review_id"])
            stars = lv["stars"] if lv else int(r["stars"])
            replied = bool(lv and lv["reply"])
        else:
            stars = int(r["stars"])
            replied = bool(r.get("existing_reply")) or r["our_id"] in old_town_posted
        pending = r["location"] == "Old Town" and r["our_id"] in drafted and not replied
        buckets[r["location"]].append(dict(id=r["our_id"], stars=stars, replied=replied, pending=pending,
                                           cat=d["category"]))

    def summarize(rows):
        ids = lambda pred: [x["id"] for x in rows if pred(x)]  # noqa: E731
        n = len(rows)
        out = {"new_reviews": n,
               "average_rating": round(sum(x["stars"] for x in rows) / n + 1e-9, 2) if n else None}
        for s in range(1, 6):
            out[f"stars_{s}"] = sum(x["stars"] == s for x in rows)
        out["replied"] = sum(x["replied"] for x in rows)
        out["manual_pending"] = sum(x["pending"] for x in rows)
        out["reply_rate"] = round(100 * out["replied"] / n + 1e-9, 1) if n else None
        out["flagged_for_owner"] = sum(x["cat"] in FLAGGED for x in rows)
        out["awaiting_owner"] = sum(x["cat"] in AWAITING for x in rows)
        out["urgent"] = sum(x["cat"] == "urgent" for x in rows)
        out["removal_requested"] = sum(x["cat"] == "report" for x in rows)
        out["ids"] = {"new_reviews": ids(lambda x: True), "replied": ids(lambda x: x["replied"]),
                      "manual_pending": ids(lambda x: x["pending"]),
                      "flagged_for_owner": ids(lambda x: x["cat"] in FLAGGED),
                      "awaiting_owner": ids(lambda x: x["cat"] in AWAITING),
                      "urgent": ids(lambda x: x["cat"] == "urgent"),
                      "removal_requested": ids(lambda x: x["cat"] == "report")}
        for s in range(1, 6):
            out["ids"][f"stars_{s}"] = ids(lambda x, s=s: x["stars"] == s)
        return out

    by_loc = {loc: summarize(buckets[loc]) for loc in LOCATIONS}
    total = summarize([x for loc in LOCATIONS for x in buckets[loc]])
    return {"by_location": by_loc, "total": total}


def august_comparison(inventory, decisions, replies, live, old_town_posted, previous, baseline_inventory):
    month = previous.get("month", "2026-08")
    full = compute(month, inventory, decisions, replies, live, old_town_posted)
    api_rows = [r for r in inventory if r["source"] == "api"]
    api_only = compute(month, api_rows, decisions, replies, live, set())
    mt, rv = api_only["by_location"]["Midtown"], api_only["by_location"]["Riverside"]
    api_n = mt["new_reviews"] + rv["new_reviews"]
    api_sum = sum(s * (mt[f"stars_{s}"] + rv[f"stars_{s}"]) for s in range(1, 6))
    end = f"{month}-{calendar.monthrange(int(month[:4]), int(month[5:]))[1]}"
    dec = {d["our_id"]: d for d in decisions}
    base = baseline_inventory or inventory
    replied_at_month_end = [r["our_id"] for r in base
                            if r["create_date"].startswith(month) and r["source"] == "api"
                            and dec.get(r["our_id"], {}).get("category") != "deleted"
                            and r.get("existing_reply") and r.get("existing_reply_date", "9") <= end]
    t = full["total"]
    explanation = []
    if previous.get("new_reviews") != t["new_reviews"]:
        explanation.append(
            f"new_reviews: the previous report counted {previous.get('new_reviews')} reviews, from the API only "
            f"(Midtown {mt['new_reviews']} + Riverside {rv['new_reviews']} = {api_n}). Section 5 includes all three "
            f"locations, so Old Town's {full['by_location']['Old Town']['new_reviews']} screenshot reviews "
            f"are added: {t['new_reviews']}.")
    api_avg = round(api_sum / api_n + 1e-9, 2) if api_n else None
    if previous.get("average_rating") != t["average_rating"]:
        explanation.append(
            f"average_rating: API-only data recomputes to {api_sum}/{api_n} = {api_avg}"
            + (" (matches the previous report)" if api_avg == previous.get("average_rating") else
               f" (previous report said {previous.get('average_rating')})")
            + f"; with Old Town ({full['by_location']['Old Town']['average_rating']} avg) it is {t['average_rating']}.")
    if previous.get("replied") != t["replied"]:
        explanation.append(
            f"replied: {len(replied_at_month_end)} API reviews from {month} had an owner reply by {end} "
            f"({', '.join(replied_at_month_end)})"
            + (" - this matches the previous report" if len(replied_at_month_end) == previous.get("replied") else "")
            + f". Section 5 counts replies visible at report time, which adds the replies posted this run to "
              f"older unanswered reviews and Old Town's owner reply: {t['replied']}.")
    return {"month": month, "previous_report": {k: previous.get(k) for k in ("new_reviews", "average_rating", "replied")},
            "recomputed": full, "recomputed_api_only": {"new_reviews": api_n, "average_rating": api_avg,
                                                        "replied_at_month_end": len(replied_at_month_end)},
            "differences": {k: {"previous": previous.get(k), "recomputed": t[k]}
                            for k in ("new_reviews", "average_rating", "replied")},
            "explanation": explanation}


# ---------------------------------------------------------------------------- HTML
def _svg_chart(by_loc):
    W, H, left, top, bottom = 640, 300, 44, 30, 46
    plot_w, plot_h = W - left - 16, H - top - bottom
    vmax = max(1, max(by_loc[l][f"stars_{s}"] for l in LOCATIONS for s in range(1, 6)))
    step = 2 if vmax > 6 else 1
    ymax = ((vmax + step - 1) // step) * step
    group_w = plot_w / 5
    bar_w, gap = 22, 2
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="chart-title" class="chart">',
             '<title id="chart-title">Star distribution by location</title>']
    for v in range(0, ymax + 1, step):
        y = top + plot_h - v / ymax * plot_h
        parts.append(f'<line x1="{left}" x2="{W - 16}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>'
                     f'<text x="{left - 8}" y="{y + 4:.1f}" class="axis" text-anchor="end">{v}</text>')
    for si, s in enumerate(range(1, 6)):
        gx = left + si * group_w + (group_w - (3 * bar_w + 2 * gap)) / 2
        for li, loc in enumerate(LOCATIONS):
            v = by_loc[loc][f"stars_{s}"]
            x = gx + li * (bar_w + gap)
            h = v / ymax * plot_h
            y = top + plot_h - h
            cls = "s" + str(li + 1)
            if v:
                r = min(4, h)
                parts.append(f'<path class="bar {cls}" d="M{x:.1f},{top + plot_h:.1f} V{y + r:.1f} '
                             f'Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} H{x + bar_w - r:.1f} '
                             f'Q{x + bar_w:.1f},{y:.1f} {x + bar_w:.1f},{y + r:.1f} V{top + plot_h:.1f} Z">'
                             f'<title>{loc}, {s}★: {v} review{"s" if v != 1 else ""}</title></path>')
            parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 5:.1f}" class="val" text-anchor="middle">{v}</text>')
        parts.append(f'<text x="{left + si * group_w + group_w / 2:.1f}" y="{top + plot_h + 20}" class="axis" '
                     f'text-anchor="middle">{s}★</text>')
    parts.append(f'<line x1="{left}" x2="{W - 16}" y1="{top + plot_h}" y2="{top + plot_h}" class="base"/>')
    parts.append(f'<text x="{left + plot_w / 2}" y="{H - 6}" class="axis" text-anchor="middle">Current star rating</text>')
    parts.append("</svg>")
    return "".join(parts)


def render_html(report):
    e = html.escape
    by_loc, tot = report["by_location"], report["total"]
    cols = [("new_reviews", "New reviews"), ("average_rating", "Avg rating")] + \
           [(f"stars_{s}", f"{s}★") for s in range(1, 6)] + \
           [("replied", "Replied"), ("manual_pending", "Manual pending"), ("reply_rate", "Reply rate %"),
            ("flagged_for_owner", "Flagged for owner"), ("awaiting_owner", "Awaiting owner"),
            ("urgent", "Urgent"), ("removal_requested", "Removal requested")]

    def fmt(k, v):
        if v is None:
            return "–"
        return f"{v:.2f}" if k == "average_rating" else (f"{v:.1f}" if k == "reply_rate" else str(v))

    rows = "".join(
        f'<tr><th scope="row">{e(name)}</th>' + "".join(f'<td data-key="{k}">{fmt(k, d[k])}</td>' for k, _ in cols) + "</tr>"
        for name, d in [(l, by_loc[l]) for l in LOCATIONS] + [("Total", tot)])
    head = "".join(f"<th scope=\"col\">{e(lbl)}</th>" for _, lbl in cols)
    legend = "".join(f'<span class="key"><i class="sw s{i + 1}"></i>{e(l)}</span>' for i, l in enumerate(LOCATIONS))
    deleted = "".join(f"<li>{e(d['our_id'])} · {e(d['location'])} · {e(d['reviewer'])} · {d['stars']}★ · "
                      f"{e(d['create_date'])}</li>" for d in report["deleted_reviews"]) or "<li>None</li>"
    corr = "".join(f"<li><b>{e(c['our_id'])}</b> · {e(c['location'])} · {e(c['reason'])}<br>"
                   f"<span class=\"muted\">Was:</span> {e(c['old_reply'])}<br>"
                   f"<span class=\"muted\">Now:</span> {e(c['new_reply'])}</li>"
                   for c in report["reply_corrections"]) or "<li>None</li>"
    aug = report["august_comparison"]
    at = aug["recomputed"]["total"]
    aug_rows = "".join(f"<tr><th scope=\"row\">{k}</th><td>{fmt(k, v['previous'])}</td><td>{fmt(k, v['recomputed'])}</td></tr>"
                       for k, v in aug["differences"].items())
    aug_loc = "".join(f"<tr><th scope=\"row\">{l}</th><td>{aug['recomputed']['by_location'][l]['new_reviews']}</td>"
                      f"<td>{fmt('average_rating', aug['recomputed']['by_location'][l]['average_rating'])}</td>"
                      f"<td>{aug['recomputed']['by_location'][l]['replied']}</td></tr>" for l in LOCATIONS)
    expl = "".join(f"<li>{e(x)}</li>" for x in aug["explanation"]) or "<li>No differences.</li>"
    data_json = json.dumps({"by_location": {l: {k: v for k, v in by_loc[l].items() if k != "ids"} for l in LOCATIONS},
                            "total": {k: v for k, v in tot.items() if k != "ids"}}).replace("</", "<\\/")
    css_l = "".join(f"--s{i + 1}:{COLORS[l][0]};" for i, l in enumerate(LOCATIONS))
    css_d = "".join(f"--s{i + 1}:{COLORS[l][1]};" for i, l in enumerate(LOCATIONS))
    dark = f"color-scheme:dark;--bg:#1a1a19;--fg:#fff;--fg2:#c3c2b7;--line:#3a3a37;--grid:#2c2c2a;--card:#232322;{css_d}"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lantern &amp; Loaf {e(report['month'])} Reviews</title>
<style>
:root{{color-scheme:light;--bg:#fcfcfb;--fg:#0b0b0b;--fg2:#52514e;--line:#dddcd6;--grid:#ecebe7;--card:#fff;{css_l}}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{{dark}}}}}
:root[data-theme="dark"]{{{dark}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1040px;margin:0 auto;padding:24px 16px 48px}}
h1{{font-size:1.5rem;margin:0 0 4px}} h2{{font-size:1.1rem;margin:32px 0 8px}}
.muted{{color:var(--fg2)}} .wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}
th,td{{padding:6px 10px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}
th[scope=row]{{text-align:left}} thead th{{font-weight:600;color:var(--fg2);font-size:.85rem}}
#by-location tbody tr:last-child th,#by-location tbody tr:last-child td{{font-weight:700;border-bottom:0}}
.chart{{width:100%;max-width:640px;height:auto;display:block}}
.grid{{stroke:var(--grid);stroke-width:1}} .base{{stroke:var(--fg2);stroke-width:1}}
.axis{{fill:var(--fg2);font-size:12px}} .val{{fill:var(--fg);font-size:11px}}
.bar{{stroke:var(--card);stroke-width:2;paint-order:stroke}} .bar:hover{{opacity:.8}}
.s1{{fill:var(--s1);background:var(--s1)}} .s2{{fill:var(--s2);background:var(--s2)}} .s3{{fill:var(--s3);background:var(--s3)}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;margin:8px 0}} .key{{display:inline-flex;align-items:center;gap:6px;color:var(--fg2)}}
.sw{{display:inline-block;width:12px;height:12px;border-radius:3px}}
ul{{padding-left:20px}} li{{margin:4px 0}}
</style></head><body><main>
<h1>Lantern &amp; Loaf · Google reviews · {e(report['month'])}</h1>
<p class="muted">Generated {e(report['generated_at'])} · reviews created in {e(report['month'])}, current star ratings, deleted reviews excluded (playbook section 5).</p>
<h2>By location</h2>
<div class="wrap"><table id="by-location"><thead><tr><th scope="col">Location</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>
<h2>Star distribution by location</h2>
<div class="legend">{legend}</div>
{_svg_chart(by_loc)}
<h2>Deleted reviews (excluded)</h2><ul>{deleted}</ul>
<h2>Replies corrected under rule 1</h2><ul>{corr}</ul>
<h2>August comparison</h2>
<div class="wrap"><table><thead><tr><th scope="col">Metric</th><th scope="col">august_report.json</th><th scope="col">Recomputed</th></tr></thead><tbody>{aug_rows}</tbody></table></div>
<p class="muted">Recomputed August by location:</p>
<div class="wrap"><table><thead><tr><th scope="col">Location</th><th scope="col">New reviews</th><th scope="col">Avg rating</th><th scope="col">Replied</th></tr></thead><tbody>{aug_loc}</tbody></table></div>
<ul>{expl}</ul>
<script type="application/json" id="report-data">{data_json}</script>
</main></body></html>"""


def build(out_dir, month="2026-09", root=".", old_town_posted=(), baseline_inventory=None, client=None,
          generated_at=None):
    import datetime as dt
    inventory = load_csv(os.path.join(out_dir, "review_inventory.csv"))
    decisions = load_csv(os.path.join(out_dir, "decisions.csv"))
    replies = load_csv(os.path.join(out_dir, "replies.csv"))
    locations = load_csv(os.path.join(root, "locations.csv"))
    previous = json.load(open(os.path.join(root, "august_report.json"), encoding="utf-8"))
    live = live_state(client or GBPClient(), locations)
    posted = set(old_town_posted)
    rep = compute(month, inventory, decisions, replies, live, posted)
    inv = {r["our_id"]: r for r in inventory}
    dec = {d["our_id"]: d for d in decisions}
    reply_text = {r["our_id"]: r["reply_text"] for r in replies}
    report = {
        "month": month,
        "generated_at": generated_at or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "definitions": "Playbook section 5: reviews with createTime in the month, current stars, all three locations, "
                       "category deleted excluded. replied = owner reply visible (API) or confirmed posted (Old Town).",
        "old_town_confirmed_posted": sorted(posted),
        **rep,
        "deleted_reviews": [{"our_id": d["our_id"], "location": d["location"], "reviewer": inv[d["our_id"]]["reviewer"],
                             "stars": int(inv[d["our_id"]]["stars"]), "create_date": inv[d["our_id"]]["create_date"]}
                            for d in decisions if d["category"] == "deleted"],
        "reply_corrections": [{"our_id": d["our_id"], "location": d["location"],
                               "reason": d["notes"].split("[corrected]", 1)[1].split(";")[0].strip() or "rule 1/4c",
                               "old_reply": (baseline_inventory and {r["our_id"]: r for r in baseline_inventory}.get(d["our_id"], {}).get("existing_reply"))
                                            or inv[d["our_id"]]["existing_reply"],
                               "new_reply": reply_text.get(d["our_id"], ""),
                               "posted_by": "owner (manual)" if d["location"] == "Old Town" else "API"}
                              for d in decisions if "[corrected]" in d["notes"]],
    }
    report["august_comparison"] = august_comparison(inventory, decisions, replies, live, posted, previous,
                                                    baseline_inventory)
    with open(os.path.join(out_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    with open(os.path.join(out_dir, "report.html"), "w", encoding="utf-8") as f:
        f.write(render_html(report))
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--month", default="2026-09")
    ap.add_argument("--root", default=".")
    ap.add_argument("--old-town-posted", default="", help="comma-separated Old Town our_ids the owner confirmed")
    ap.add_argument("--baseline-inventory", help="inventory captured before this run's posting (for August replied)")
    ap.add_argument("--base-url", default="http://127.0.0.1:8765")
    a = ap.parse_args(argv)
    base = load_csv(a.baseline_inventory) if a.baseline_inventory else None
    rep = build(a.dir, a.month, a.root, [x for x in a.old_town_posted.split(",") if x], base, GBPClient(a.base_url))
    for loc in LOCATIONS + ["total"]:
        d = rep["total"] if loc == "total" else rep["by_location"][loc]
        print(f"{loc:10} new={d['new_reviews']} avg={d['average_rating']} replied={d['replied']} "
              f"pending={d['manual_pending']} rate={d['reply_rate']} flagged={d['flagged_for_owner']} "
              f"awaiting={d['awaiting_owner']} urgent={d['urgent']} removal={d['removal_requested']}")


if __name__ == "__main__":
    main()
