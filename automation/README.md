# Lantern & Loaf monthly review automation

Python 3 standard library only. Run from the folder that holds `playbook.md`, `staff.csv`, `locations.csv`.

| Step | Command |
|---|---|
| 1. Intake (API, all pages, plus the Old Town transcription) | `python3 -m automation.intake --out output/2026-10 [--previous-inventory output/<last>/review_inventory.csv]` |
| 2. Triage | Write `decisions.csv` and `replies.csv` by playbook section 2 (judgment; see `work/` for how September was done) |
| 3. Validate drafts (section 4) | `python3 -m automation.reply_rules output/2026-10/replies.csv output/2026-10/review_inventory.csv output/2026-10/decisions.csv` |
| 4. Post (never Old Town) | `python3 -m automation.post_replies output/2026-10/replies.csv --inventory output/2026-10/review_inventory.csv --decisions output/2026-10/decisions.csv --log output/2026-10/post_log.csv [--dry-run] [--only M04,R01]` |
| 5. Report (section 5) | `python3 -m automation.build_report --dir output/2026-10 --month 2026-10 --old-town-posted O02,... [--snapshot saved.json]` |
| 6. Reconcile | `python3 -m automation.reconcile --dir output/2026-10 --old-town-posted O02,... --md output/2026-10/reconciliation.md` |
| Tests | `python3 -m unittest discover automation/tests` |

* `gbp_client.py`: bearer auth, full pagination (with loop guard), retry on 429 honouring `Retry-After`, and
  `BadRequestError` (400), `NotFoundError` (404), `ConflictError` (409).
* `post_replies.py`: re-validates each draft before sending, logs every HTTP attempt (including each 429) to the post log,
  and marks a 404 as `deleted` and a 400/409 as `rejected` with the gateway's details.
* When staff change, update `staff.csv`; the validator reads it (or a delivery's `staff_used.csv`) on every run.
