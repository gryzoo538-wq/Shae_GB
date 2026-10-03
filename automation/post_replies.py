"""Post approved replies through the GBP client and record every attempt in a post log.

    python3 -m automation.post_replies replies.csv --inventory review_inventory.csv \
        --log post_log.csv [--only M04,R01] [--dry-run]

Input CSV needs our_id, location, reply_text; optional columns review_id (else looked up in the
inventory) and approved (rows with approved=no are skipped). Old Town is never posted: it is not
connected and the owner posts those replies by hand. Every draft is re-checked with reply_rules
before it is sent. Exit status 1 if any reply was not posted.
"""
import argparse
import csv
import datetime as dt
import os
import sys

from .gbp_client import BadRequestError, ConflictError, GBPClient, GBPError, NotFoundError
from .reply_rules import ReplyRules

LOG_FIELDS = ["timestamp", "our_id", "location", "review_id", "action", "attempt", "http_status",
              "result", "detail", "reply_text"]
NEVER_POST = {"Old Town"}


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class PostLog:
    def __init__(self, path):
        self.path = path
        new = not os.path.exists(path) or os.path.getsize(path) == 0
        self.f = open(path, "a", newline="", encoding="utf-8")
        self.w = csv.DictWriter(self.f, fieldnames=LOG_FIELDS)
        if new:
            self.w.writeheader()

    def write(self, **row):
        row.setdefault("timestamp", _now())
        self.w.writerow({k: row.get(k, "") for k in LOG_FIELDS})
        self.f.flush()

    def close(self):
        self.f.close()


def post_all(rows, client, rules, log, inventory, location_ids, existing_texts=(), action="put",
             dry_run=False):
    """Post each row. Returns {our_id: result} with result in
    posted / rejected / deleted / blocked-local / skipped-old-town / skipped-unapproved / error."""
    results = {}
    texts = [r["reply_text"] for r in rows]
    for i, row in enumerate(rows):
        oid, loc = row["our_id"], row["location"]
        rv = inventory.get(oid, {})
        review_id = row.get("review_id") or rv.get("review_id", "")
        base = dict(our_id=oid, location=loc, review_id=review_id, action=action, reply_text=row["reply_text"])
        if loc in NEVER_POST:
            log.write(**base, result="skipped-old-town", detail="not API-connected; owner posts by hand")
            results[oid] = "skipped-old-town"
            continue
        if (row.get("approved") or "yes").strip().lower() not in ("yes", "y", "true", "1"):
            log.write(**base, result="skipped-unapproved")
            results[oid] = "skipped-unapproved"
            continue
        others = texts[:i] + texts[i + 1:] + list(existing_texts)
        if rv.get("existing_reply") and rv["existing_reply"] in others:
            others.remove(rv["existing_reply"])  # the reply being replaced does not count
        problems = rules.validate(row["reply_text"], loc, rv.get("reviewer", ""), rv.get("text", ""), others,
                                  row.get("about_location") or None)
        if problems:
            log.write(**base, result="blocked-local", detail=" | ".join(f"[{c}] {m}" for c, m in problems))
            results[oid] = "blocked-local"
            continue
        if dry_run:
            log.write(**base, result="dry-run")
            results[oid] = "dry-run"
            continue
        attempts = []

        def hook(method, path, status, payload, headers, _a=attempts):
            _a.append(status)
            if status == 429:
                ra = next((v for k, v in headers.items() if k.lower() == "retry-after"), "")
                log.write(**base, attempt=len(_a), http_status=429, result="rate-limited",
                          detail=f"Retry-After {ra}s; retrying")
        client.on_response = hook
        try:
            if action == "delete":
                client.delete_reply(location_ids[loc], review_id)
            else:
                client.put_reply(location_ids[loc], review_id, row["reply_text"])
            log.write(**base, attempt=len(attempts), http_status=attempts[-1], result="posted")
            results[oid] = "posted"
        except NotFoundError as e:
            log.write(**base, attempt=len(attempts), http_status=404, result="deleted",
                      detail="review no longer exists (404)")
            results[oid] = "deleted"
        except (BadRequestError, ConflictError) as e:
            log.write(**base, attempt=len(attempts), http_status=e.status, result="rejected",
                      detail=f"{e.message} {e.details}")
            results[oid] = "rejected"
        except GBPError as e:
            log.write(**base, attempt=len(attempts), http_status=e.status, result="error", detail=str(e))
            results[oid] = "error"
        finally:
            client.on_response = None
    return results


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("replies")
    ap.add_argument("--inventory", required=True)
    ap.add_argument("--decisions", help="decisions.csv (for about_location notes)")
    ap.add_argument("--log", required=True)
    ap.add_argument("--root", default=".", help="folder with staff.csv and locations.csv")
    ap.add_argument("--staff", help="override staff.csv")
    ap.add_argument("--only", help="comma-separated our_ids")
    ap.add_argument("--action", choices=["put", "delete"], default="put")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--base-url", default="http://127.0.0.1:8765")
    a = ap.parse_args(argv)
    locs = load_csv(os.path.join(a.root, "locations.csv"))
    rules = ReplyRules.from_csv(a.staff or os.path.join(a.root, "staff.csv"), os.path.join(a.root, "locations.csv"))
    inv = {r["our_id"]: r for r in load_csv(a.inventory)}
    rows = load_csv(a.replies)
    if a.decisions:
        import re
        dec = {r["our_id"]: r for r in load_csv(a.decisions)}
        for r in rows:
            m = re.search(r"about_location=([A-Za-z ]+?)(;|$)", dec.get(r["our_id"], {}).get("notes", ""))
            if m:
                r["about_location"] = m.group(1).strip()
    if a.only:
        keep = set(a.only.split(","))
        rows_to_post = [r for r in rows if r["our_id"] in keep]
    else:
        rows_to_post = rows
    others = [r["reply_text"] for r in rows if r not in rows_to_post]
    others += [v["existing_reply"] for v in inv.values() if v.get("existing_reply")]
    ids = {l["location"]: l["gbp_location_id"] for l in locs}
    log = PostLog(a.log)
    try:
        res = post_all(rows_to_post, GBPClient(a.base_url), rules, log, inv, ids, others, a.action, a.dry_run)
    finally:
        log.close()
    for k, v in res.items():
        print(f"{k}: {v}")
    ok = {"posted", "skipped-old-town", "skipped-unapproved", "dry-run"}
    return 0 if all(v in ok for v in res.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
