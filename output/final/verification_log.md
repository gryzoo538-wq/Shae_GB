# Verification log

Run on 2026-10-03 (container clock) against the mock API in phase 2, after all final posts.
Re-run any time with `python3 work/verify.py` (exit 0 = every check passes).

## 1. Screenshots re-read by eye against the inventory

All six screenshots were opened again and compared field by field with `output/final/review_inventory.csv`
(no OCR is installed, so this was done visually; star counts were taken from the gold vs grey stars).

| our_id | screenshot | reviewer | stars | date | text | existing reply | result |
|---|---|---|---|---|---|---|---|
| O01 | IMG_4445 | Isabel Moreau | 5 | 2026-08-08 | The courtyard is magical. | "Thank you Isabel! - Hannah, Old Town" | match |
| O02 | IMG_4445 | Ravi Menon | 4 | 2026-08-21 | Rosa recommended the rye - delicious. | none in screenshot | match |
| O03 | IMG_4438 | Gwen Harper | 1 | 2026-08-29 | Dirty floors and a cockroach near the counter. | none | match |
| O04 | IMG_4438 | Luis Ortega | 5 | 2026-09-03 | Dev's latte art is on another level. | none in screenshot | match |
| O05 | IMG_4431 | Anna Schultz | 2 | 2026-09-06 | Ordered gluten-free but got regular bread, now feeling awful. | none | match |
| O06 | IMG_4431 | J. P. | 5 | 2026-09-09 | (no text) | none in screenshot | match |
| O07 | IMG_4424 | Megan Riley | 3 | 2026-09-12 | Cute spot, small portions. | none | match |
| O08 | IMG_4424 | Elena García | 5 | 2026-09-15 | Me encantó el patio. | none in screenshot | match |
| O09 | IMG_4417 | Robert King | 4 | 2026-09-18 | Great bread, but cash only was annoying. | none in screenshot | match |
| O10 | IMG_4417 | Zoe Turner | 5 | 2026-09-22 | Best bakery in Old Town. | none in screenshot | match |
| O11 | IMG_4410 | Darren Pike | 1 | 2026-09-25 | Never been here but I've heard bad things. | none | match |
| O12 | IMG_4410 | Amara Okafor | 4 | 2026-09-30 | Lovely, will come back. | none in screenshot | match |

12/12 match. In the final inventory, O02, O04, O06, O08, O09, O10 and O12 also carry the reply the owner confirmed
posting on 2026-10-03 (her email); the screenshots (taken 2026-10-01) predate that.

## 2. Mismatches and defects found during the work, and what was changed

| # | Found by | Problem | Fix (upstream first, then rebuilt everything downstream) |
|---|---|---|---|
| 1 | Code re-read before first post | `post_replies` built its uniqueness list with `t != reply_text`, which would have hidden a true duplicate | Exclude by position instead; covered by a unit test. Fixed before any reply was posted. |
| 2 | Phase 1 posting | M23 (Simone Laurent) and R15 (Liam Walsh) returned 404 on reply although still listed | Category -> `deleted` in the phase 1 triage, drafts dropped from replies.csv, decisions/report/digest rebuilt. |
| 3 | Reconcile script review | The HTML check decided "all match" from the last 3 log lines, not a counter | Real per-cell mismatch counter. |
| 4 | Visual check of report.html | The "Total row bold" style also bolded the last row of the August tables | CSS scoped to `#by-location`. |
| 5 | Phase 2 intake diff | Re-numbering by createTime shifted almost every id (M19 -> M18 ...), breaking traceability | `intake --previous-inventory` keeps phase 1 ids, gives new reviews the next free number (M27, R25) and carries vanished reviews over so they can be marked deleted. |
| 6 | Own slip | Rebuilding the phase 1 report after the phase 2 restart read the phase 2 live API | Restored the committed phase 1 report.json/html (built under phase 1); added `build_report --snapshot` for offline rebuilds; phase 1 numbers are now verified offline (section 3C). |
| 7 | Reading the final digest | Correction "Was:" text came from the final inventory, where R01's existing reply is already our corrected one; M15's old text was our own phase 1 post | `build_report` and the digest take the replaced text from the post log history, else the phase 1 inventory. |
| 8 | Reading old_town_replies.md | O01 (already replied) listed under "reviews with no reply" | Section renamed and filtered. |
| 9 | changes_report review | M01's phase 1 reply shown as "none" (compared drafts, not the reply in effect) | Compare reply in effect (draft/post, else existing reply). |
| 10 | Unit test after staff change | `test_loads_real_csvs` asserted Jess may be named | Test updated to the new staff list (Jess former, Lena allowed only at Riverside). |
| 11 | verify.py | Final digest "Flags for your decision" also listed owner-decided reviews (owner-reply / flag-closed) | Digest filters by category flag / reply+flag. |
| 12 | verify.py | Validator detected "Nice patio." (R02) as Spanish | Removed words shared by both languages from the Spanish list; new test case. |
| 13 | verify.py | Validating phase 1 replies now flagged M15 (Jess) because staff.csv was updated | Validator CLI uses the delivery's own `staff_used.csv` (phase 1: original staff list; final: with Jess as former). This also confirms that M15 needed the correction. |
| 14 | staff.csv diff | Rewriting staff.csv changed its CRLF line endings (every line in the diff) | Restored CRLF; the diff is now the single Jess line. |

The gateway rejected none of our replies (no 400 or 409) in either phase, because every draft passed `reply_rules.py`
first. The API did return 429 several times per run; the client honoured `Retry-After` (3 s) and every
post then succeeded; each 429 is recorded in post_log.csv.

## 3. Final automated checks (`python3 work/verify.py`)

### A. Live API vs final inventory and replies

- PASS: every live review (49) is in the inventory with the same location, stars, text and create date
- PASS: every live reply equals replies.csv (or the untouched existing reply); reviews without a reply have none
- PASS: inventory API rows not returned live are exactly the deleted ones (not live: ['M13', 'M23', 'R15'])
- PASS: M13 GET returns 404
- PASS: M23 GET returns 404
- PASS: R15 GET returns 404

### B. Every reply that is live or for the owner to post follows section 4

- PASS: all 43 replies we wrote pass every rule (4a-4i)
- PASS: the 6 untouched older replies break no hard rule (4c staff, 4d compensation, 4e contact, 4h unique)
- NOTE: older replies left as written (rule 1 mandates replacing only 4c breaches): M02 [4a], M03 [4a,4b], M05 [4a,4b], O01 [4a,4b], R02 [4a], R03 [4a]
- PASS: no live or pending reply names Jess (left 2026-10-03) ([])
- PASS: no reply names Theo, Omar or Ana ([])
- PASS: Spanish reviews get Spanish replies (M12, R08, O08)
- PASS: no reply drafted for urgent / report / flag / flag-closed / deleted ([])
- PASS: every reply / reply+flag / owner-reply review has a reply ([])
- PASS: Old Town replies never posted via the API

### C. Reports vs decisions.csv (independent recount), HTML vs JSON

- PASS: final: post log vs live, live replies accounted for, 56 report numbers recounted by location and total, HTML table vs JSON (0 mismatches; see output/final/reconciliation.md)
- PASS: phase 1 report.json recounted offline from phase 1 decisions + inventory + post log (15 metrics x 4 scopes)
- PASS: phase1: report.html embedded data equals report.json; SVG has one bar per non-zero cell (15/15)
- PASS: phase1: August recomputed = sum of locations, compared to august_report.json (16/3.69/7) (recomputed {'new_reviews': {'previous': 16, 'recomputed': 19}, 'average_rating': {'previous': 3.69, 'recomputed': 3.63}, 'replied': {'previous': 7, 'recomputed': 14}})
- PASS: final: report.html embedded data equals report.json; SVG has one bar per non-zero cell (14/14)
- PASS: final: August recomputed = sum of locations, compared to august_report.json (16/3.69/7) (recomputed {'new_reviews': {'previous': 16, 'recomputed': 19}, 'average_rating': {'previous': 3.69, 'recomputed': 3.63}, 'replied': {'previous': 7, 'recomputed': 18}})

### D. Owner documents agree with decisions

- PASS: phase1: removal_requests.csv = category report (M13, M22, R12, R24, O11)
- PASS: phase1: digest urgent section = category urgent (M05, M20, O03, O05, R10, R18)
- PASS: phase1: digest flags = categories flag + reply+flag (M07, M09, M11, M14, M16, M18, M24, M25, O07, O09, R04, R07, R09, R13, R16, R19, R20, R22)
- PASS: phase1: every Old Town reply text in old_town_replies.md matches replies.csv
- PASS: phase1: char_count column equals len(reply_text)
- PASS: final: removal_requests.csv = category report (M22, R12, R24, O11)
- PASS: final: digest urgent section = category urgent (M05, M20, O03, O05, R10, R18)
- PASS: final: digest flags = categories flag + reply+flag (M09, M14, M24, O09, R09, R19, R20, R25)
- PASS: final: every Old Town reply text in old_town_replies.md matches replies.csv
- PASS: final: char_count column equals len(reply_text)

### E. Unit tests

- PASS: python3 -m unittest discover automation/tests

```
test_400 (test_gbp_client.ErrorTest.test_400) ... ok
test_404 (test_gbp_client.ErrorTest.test_404) ... ok
test_409 (test_gbp_client.ErrorTest.test_409) ... ok
test_follows_next_page_token_to_the_end (test_gbp_client.PaginationTest.test_follows_next_page_token_to_the_end) ... ok
test_pagination_loop_is_detected (test_gbp_client.PaginationTest.test_pagination_loop_is_detected) ... ok
test_429_gives_up_after_max_retries (test_gbp_client.RetryTest.test_429_gives_up_after_max_retries) ... ok
test_429_retries_honouring_retry_after (test_gbp_client.RetryTest.test_429_retries_honouring_retry_after) ... ok
test_on_response_sees_every_attempt (test_gbp_client.RetryTest.test_on_response_sees_every_attempt) ... ok
test_every_attempt_logged (test_post_replies.PostRepliesTest.test_every_attempt_logged) ... ok
test_old_town_and_blocked_never_hit_api (test_post_replies.PostRepliesTest.test_old_town_and_blocked_never_hit_api) ... ok
test_results (test_post_replies.PostRepliesTest.test_results) ... ok
test_4a_initials_get_no_name (test_reply_rules.RuleCase.test_4a_initials_get_no_name) ... ok
test_4a_must_start_with_first_name (test_reply_rules.RuleCase.test_4a_must_start_with_first_name) ... ok
test_4b_generic_reply_fails (test_reply_rules.RuleCase.test_4b_generic_reply_fails) ... ok
test_4b_star_only_must_thank_for_rating (test_reply_rules.RuleCase.test_4b_star_only_must_thank_for_rating) ... ok
test_4c_consenting_staff_ok (test_reply_rules.RuleCase.test_4c_consenting_staff_ok) ... ok
test_4c_former_staff (test_reply_rules.RuleCase.test_4c_former_staff) ... ok
test_4c_no_consent (test_reply_rules.RuleCase.test_4c_no_consent) ... ok
test_4c_reviewer_sharing_staff_name_ok (test_reply_rules.RuleCase.test_4c_reviewer_sharing_staff_name_ok) ... ok
test_4c_unknown_name_from_review (test_reply_rules.RuleCase.test_4c_unknown_name_from_review) ... ok
test_4c_wrong_location (test_reply_rules.RuleCase.test_4c_wrong_location) ... ok
test_4d_compensation (test_reply_rules.RuleCase.test_4d_compensation) ... ok
test_4d_gluten_free_is_not_an_offer (test_reply_rules.RuleCase.test_4d_gluten_free_is_not_an_offer) ... ok
test_4d_legal_fault (test_reply_rules.RuleCase.test_4d_legal_fault) ... ok
test_4d_spanish_compensation (test_reply_rules.RuleCase.test_4d_spanish_compensation) ... ok
test_4e_contact_details (test_reply_rules.RuleCase.test_4e_contact_details) ... ok
test_4f_spanish_review_needs_spanish_reply (test_reply_rules.RuleCase.test_4f_spanish_review_needs_spanish_reply) ... ok
test_4g_signoff (test_reply_rules.RuleCase.test_4g_signoff) ... ok
test_4h_length (test_reply_rules.RuleCase.test_4h_length) ... ok
test_4h_uniqueness (test_reply_rules.RuleCase.test_4h_uniqueness) ... ok
test_4i_other_location (test_reply_rules.RuleCase.test_4i_other_location) ... ok
test_good_reply_passes (test_reply_rules.RuleCase.test_good_reply_passes) ... ok
test_loads_real_csvs (test_reply_rules.RuleCase.test_loads_real_csvs) ... ok
test_midtown (test_report_math.ReportMathTest.test_midtown) ... ok
test_old_town_manual (test_report_math.ReportMathTest.test_old_town_manual) ... ok
test_riverside_owner_decision_categories (test_report_math.ReportMathTest.test_riverside_owner_decision_categories) ... ok
test_rounding_half_up (test_report_math.ReportMathTest.test_rounding_half_up) ... ok
test_total_is_sum_of_locations (test_report_math.ReportMathTest.test_total_is_sum_of_locations) ... ok

----------------------------------------------------------------------
Ran 38 tests in 0.009s

OK
```

**0 failing check(s)**

## 4. Validator output on both reply sets

```
$ python3 -m automation.reply_rules output/phase1/replies.csv ...
staff list: output/phase1/staff_used.csv
32/32 replies pass
$ python3 -m automation.reply_rules output/final/replies.csv ...
staff list: output/final/staff_used.csv
43/43 replies pass
```

## 5. Final result

No unresolved mismatch remains. The live API holds exactly the replies in `output/final/post_log.csv` (last successful post per review)
plus the untouched older replies; every report number in both folders equals the recount from decisions.csv by location and in total;
HTML and JSON agree; 38 unit tests pass.

Judgment call to note: six older replies by the previous contractor (M02, M03, M05, R02, R03, O01) don't open with the
reviewer's first name (4a), and some don't mention a specific detail (4b). Rule 1 mandates replacing an existing reply only when it names
someone who may not be named (4c), so they were left as written and mentioned to the owner. None of them breaks 4c, 4d, 4e or 4h.
