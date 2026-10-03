"""Fetch every review for the connected locations and merge the Old Town screenshot transcription
into one inventory (playbook: Midtown/Riverside via API, Old Town via screenshots).

    python3 -m automation.intake --out output/phase1 [--old-town old_town_transcription.csv]
Writes review_inventory.csv and api_snapshot.json (the raw API data used).
"""
import argparse
import csv
import json
import os

from .gbp_client import GBPClient, stars_of

PREFIX = {"Midtown": "M", "Riverside": "R", "Old Town": "O"}
FIELDS = ["our_id", "source", "location", "review_id", "reviewer", "stars", "create_date",
          "update_date", "text", "existing_reply", "existing_reply_date"]


def load_locations(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def api_rows(client, locations):
    rows, raw = [], {}
    for loc in locations:
        if loc["api_connected"].strip().lower() != "yes":
            continue
        reviews = client.list_reviews(loc["gbp_location_id"])
        raw[loc["location"]] = reviews
        for r in reviews:
            reply = r.get("reviewReply") or {}
            rows.append({
                "source": "api", "location": loc["location"], "review_id": r["reviewId"],
                "reviewer": r["reviewer"]["displayName"], "stars": stars_of(r),
                "create_time": r["createTime"],
                "create_date": r["createTime"][:10],
                "update_date": r["updateTime"][:10] if r["updateTime"] != r["createTime"] else "",
                "update_time": r["updateTime"],
                "text": r.get("comment", ""), "existing_reply": reply.get("comment", ""),
                "existing_reply_date": (reply.get("updateTime") or "")[:10],
                "existing_reply_time": reply.get("updateTime", ""),
            })
    return rows, raw


def screenshot_rows(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "source": "screenshot", "location": "Old Town", "review_id": "",
                "reviewer": r["reviewer"], "stars": int(r["stars"]),
                "create_time": r["create_date"], "create_date": r["create_date"], "update_date": "",
                "text": r["text"], "existing_reply": r["existing_reply"],
                "existing_reply_date": "", "screenshot": r["screenshot"],
            })
    return rows


def number(rows):
    out = []
    for loc, p in PREFIX.items():
        mine = sorted((r for r in rows if r["location"] == loc), key=lambda r: r["create_time"])
        for i, r in enumerate(mine, 1):
            r["our_id"] = f"{p}{i:02d}"
            out.append(r)
    return out


def number_stable(rows, previous):
    """Keep our_ids from a previous inventory (matched by review_id, or location+reviewer for screenshots).
    New reviews get the next free number per location, in createTime order. Previous rows that the API no
    longer returns are carried over (marked `missing_from_api`) so their ids keep their meaning."""
    key = lambda r: (r["location"], r["review_id"] or r["reviewer"])  # noqa: E731
    prev = {key(r): r for r in previous}
    nxt = {}
    for r in previous:
        p = r["our_id"][0]
        nxt[p] = max(nxt.get(p, 0), int(r["our_id"][1:]))
    out, seen = [], set()
    for loc, p in PREFIX.items():
        mine = sorted((r for r in rows if r["location"] == loc), key=lambda r: r["create_time"])
        for r in mine:
            k = key(r)
            if k in prev:
                r["our_id"] = prev[k]["our_id"]
            else:
                nxt[p] = nxt.get(p, 0) + 1
                r["our_id"] = f"{p}{nxt[p]:02d}"
                r["new_since_previous"] = True
            seen.add(k)
            out.append(r)
    for k, r in prev.items():
        if k not in seen and r["source"] == "api":
            carried = dict(r, missing_from_api=True)
            out.append(carried)
    out.sort(key=lambda r: ("MRO".index(r["our_id"][0]), int(r["our_id"][1:])))
    return out


def write_inventory(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--old-town", default="old_town_transcription.csv")
    ap.add_argument("--base-url", default="http://127.0.0.1:8765")
    ap.add_argument("--previous-inventory", help="keep our_ids stable against an earlier inventory")
    a = ap.parse_args()
    locs = load_locations(os.path.join(a.root, "locations.csv"))
    rows, raw = api_rows(GBPClient(a.base_url), locs)
    rows += screenshot_rows(os.path.join(a.root, a.old_town))
    if a.previous_inventory:
        with open(a.previous_inventory, newline="", encoding="utf-8") as f:
            rows = number_stable(rows, list(csv.DictReader(f)))
        for r in rows:
            if r.get("missing_from_api"):
                print(f"carried over (no longer returned by the API): {r['our_id']} {r['reviewer']}")
            if r.get("new_since_previous"):
                print(f"new: {r['our_id']} {r['location']} {r['reviewer']} {r['create_date']}")
    else:
        rows = number(rows)
    os.makedirs(a.out, exist_ok=True)
    write_inventory(rows, os.path.join(a.out, "review_inventory.csv"))
    with open(os.path.join(a.out, "api_snapshot.json"), "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=1, ensure_ascii=False)
    print(f"{len(rows)} reviews -> {a.out}/review_inventory.csv")


if __name__ == "__main__":
    main()
