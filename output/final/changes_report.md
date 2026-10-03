# Changes: phase 1 -> final

Causes: owner decisions of 2026-10-04 (playbook section 6), Jess leaving on 2026-10-03 (staff_update.csv, rule 4c), and changes in the API between phase 1 and phase 2 (new, edited and vanished reviews). Old Town treatment also changed because the owner confirmed posting all phase 1 Old Town replies on 2026-10-03.

our_ids are stable: phase 1 ids keep their meaning; new reviews got the next free number (M27, R25).

## Reviews that changed

22 reviews changed.

| our_id | reviewer | what changed | phase 1 | final | cause |
|---|---|---|---|---|---|
| M01 | Grace Holloway | reply | "Thank you Grace! Jess will be thrilled. - Priya, Midtown" | "Grace, thank you! We're so glad you love our almond croissant, and the Midtown team is delighted to know your order by heart. - Priya, Midtown" | Staff change: Jess left 2026-10-03. The previous contractor's reply ('Jess will be thrilled') now breaks 4c -> rule 1 correction via the API. |
| M07 | Chris Daley | category | flag | owner-reply | Owner decision 2026-10-04: reply (thank him; new autumn menu) -> owner-reply. |
|  |  | reply | none | "Chris, thank you for the honest feedback! We'd love to turn 'nothing special' into something special - come and see our new autumn menu at Midtown. - Priya, Midtown" |  |
| M11 | Melissa Grant | category | flag | owner-reply | Owner decision 2026-10-04: reply (apologise; manager checked the till records, will sort it out in person) -> owner-reply. |
|  |  | reply | none | "Melissa, we're sorry about your experience with our cashier. I've checked the till records and would like to sort this out with you in person on your next visit to Midtown. - Priya, Midtown" |  |
|  |  | report treatment | awaiting_owner, flagged_for_owner, new_reviews, stars_1 | flagged_for_owner, new_reviews, replied, stars_1 |  |
| M13 | Local Foodie 99 | category | report | deleted | Phase 2: no longer returned by the API; GET returns 404 (removed from Google) -> deleted, excluded from the report. The removal request is resolved. |
|  |  | report treatment | new_reviews, removal_requested, stars_1 | not counted |  |
| M15 | Nadia Petrova | reply | "Nadia, thank you so much! We've shared your message with Jess, who will be delighted to be called a star. See you again soon at Midtown. - Priya, Midtown" | "Nadia, thank you so much! We're thrilled you had the best service you've had anywhere, and we've shared your kind words with the Midtown team. - Priya, Midtown" | Staff change: Jess left 2026-10-03 (no consent). Our posted reply named her -> edited via the API. |
| M16 | Owen Mercer | category | flag | owner-reply | Owner decision 2026-10-04: reply (apologise; tables and restrooms checked hourly) -> owner-reply. |
|  |  | reply | none | "Owen, we're sorry the tables were sticky and the bathroom was out of soap. Our tables and restrooms are now checked every hour at Midtown. - Priya, Midtown" |  |
|  |  | report treatment | awaiting_owner, flagged_for_owner, new_reviews, stars_2 | flagged_for_owner, new_reviews, replied, stars_2 |  |
| M18 | Rachel Adeyemi | category | flag | reply | Owner decision 'no reply' (flag-closed) overridden: reviewer edited on 2026-10-02 to 5 stars, 'Came back and the coffee was hot this time. Much better!' -> reprocessed as reply (section 6). |
|  |  | stars | 3★ | 5★ |  |
|  |  | text | "Coffee was cold by the time I got it." | "Came back and the coffee was hot this time. Much better!" |  |
|  |  | reply | none | "Rachel, thank you for coming back and for updating your review! We're so glad your coffee was hot this time. See you again soon at Midtown. - Priya, Midtown" |  |
|  |  | report treatment | awaiting_owner, flagged_for_owner, new_reviews, stars_3 | new_reviews, replied, stars_5 |  |
| M25 | Ivy Chen | category | flag | owner-reply | Owner decision 2026-10-04: reply (extra person on weekend mornings) -> owner-reply. |
|  |  | reply | none | "Ivy, we're sorry you waited so long and that the team felt stretched. We've added an extra person on weekend mornings at Midtown to keep things moving. - Priya, Midtown" |  |
|  |  | report treatment | awaiting_owner, flagged_for_owner, new_reviews, stars_2 | flagged_for_owner, new_reviews, replied, stars_2 |  |
| M27 | Hugo Lambert | new review | - | 5★ "Great carrot cake, friendly team." → reply | New review (created 2026-09-30) first returned by the API in phase 2. |
|  |  | report treatment | not counted | new_reviews, replied, stars_5 |  |
| R04 | Leah Morgan | category | flag | owner-reply | Owner decision 2026-10-04: reply (thank for kind words about the team; scones baked fresh every morning) -> owner-reply. |
|  |  | reply | none | "Leah, thank you for the kind words about our team! We're sorry your scone was stale - our scones are now baked fresh every morning at Riverside. - Marco, Riverside" |  |
| R07 | Peter Huang | category | flag | owner-reply | Owner decision 2026-10-04: reply (local organic flour and butter) -> owner-reply. |
|  |  | reply | none | "Peter, thank you for the feedback, and we're sorry it felt overpriced. We bake with local organic flour and butter at Riverside, and we hope that shows in every bite. - Marco, Riverside" |  |
| R13 | Craig Summers | category | flag | flag-closed | Owner decision 2026-10-04: no reply -> flag-closed. |
|  |  | report treatment | awaiting_owner, flagged_for_owner, new_reviews, stars_3 | flagged_for_owner, new_reviews, stars_3 |  |
| R16 | A Google User | category | flag | flag-closed | Owner decision 2026-10-04: no reply -> flag-closed. |
|  |  | report treatment | awaiting_owner, flagged_for_owner, new_reviews, stars_1 | flagged_for_owner, new_reviews, stars_1 |  |
| R22 | Marcus Bell | category | flag | owner-reply | Owner decision 2026-10-04: reply (espresso machine recalibrated) -> owner-reply. |
|  |  | reply | none | "Marcus, thank you for the kind words about our croissant, and sorry the coffee tasted burnt. We've recalibrated the espresso machine at Riverside. - Marco, Riverside" |  |
|  |  | report treatment | awaiting_owner, flagged_for_owner, new_reviews, stars_3 | flagged_for_owner, new_reviews, replied, stars_3 |  |
| R25 | Paula Reyes | new review | - | 2★ "Long wait for a simple order." → flag | New review (created 2026-09-29) first returned by the API in phase 2. |
|  |  | report treatment | not counted | awaiting_owner, flagged_for_owner, new_reviews, stars_2 |  |
| O04 | Luis Ortega | report treatment | manual_pending, new_reviews, stars_5 | new_reviews, replied, stars_5 | Owner confirmed posting on 2026-10-03: now counted as replied, no longer manual pending. |
| O06 | J. P. | report treatment | manual_pending, new_reviews, stars_5 | new_reviews, replied, stars_5 | Owner confirmed posting on 2026-10-03: now counted as replied, no longer manual pending. |
| O07 | Megan Riley | category | flag | owner-reply | Owner decision 2026-10-04: reply (bigger brunch plates coming in October) -> owner-reply; for the owner to post by hand. |
|  |  | reply | none | "Megan, thank you for calling us a cute spot! We hear you on the small portions, and bigger brunch plates are coming to Old Town in October. - Hannah, Old Town" |  |
|  |  | report treatment | awaiting_owner, flagged_for_owner, new_reviews, stars_3 | flagged_for_owner, manual_pending, new_reviews, stars_3 |  |
| O08 | Elena García | report treatment | manual_pending, new_reviews, stars_5 | new_reviews, replied, stars_5 | Owner confirmed posting on 2026-10-03: now counted as replied, no longer manual pending. |
| O09 | Robert King | report treatment | awaiting_owner, flagged_for_owner, manual_pending, new_reviews, stars_4 | awaiting_owner, flagged_for_owner, new_reviews, replied, stars_4 | Owner confirmed posting on 2026-10-03: now counted as replied, no longer manual pending. |
| O10 | Zoe Turner | report treatment | manual_pending, new_reviews, stars_5 | new_reviews, replied, stars_5 | Owner confirmed posting on 2026-10-03: now counted as replied, no longer manual pending. |
| O12 | Amara Okafor | report treatment | manual_pending, new_reviews, stars_4 | new_reviews, replied, stars_4 | Owner confirmed posting on 2026-10-03: now counted as replied, no longer manual pending. |

## Report numbers that changed (September 2026)

| scope | metric | phase 1 | final |
|---|---|---|---|
| Midtown | average_rating | 3.56 | 3.94 |
| Midtown | stars_1 | 3 | 2 |
| Midtown | stars_3 | 1 | 0 |
| Midtown | stars_5 | 7 | 9 |
| Midtown | replied | 9 | 14 |
| Midtown | reply_rate | 56.3 | 87.5 |
| Midtown | flagged_for_owner | 6 | 5 |
| Midtown | awaiting_owner | 6 | 2 |
| Midtown | removal_requested | 2 | 1 |
| Riverside | new_reviews | 16 | 17 |
| Riverside | average_rating | 3.63 | 3.53 |
| Riverside | stars_2 | 1 | 2 |
| Riverside | replied | 9 | 10 |
| Riverside | reply_rate | 56.3 | 58.8 |
| Riverside | flagged_for_owner | 6 | 7 |
| Riverside | awaiting_owner | 6 | 4 |
| Old Town | replied | 0 | 6 |
| Old Town | manual_pending | 6 | 1 |
| Old Town | reply_rate | 0.0 | 66.7 |
| Old Town | awaiting_owner | 2 | 1 |
| total | new_reviews | 41 | 42 |
| total | average_rating | 3.63 | 3.74 |
| total | stars_1 | 7 | 6 |
| total | stars_2 | 4 | 5 |
| total | stars_3 | 4 | 3 |
| total | stars_5 | 18 | 20 |
| total | replied | 18 | 30 |
| total | manual_pending | 6 | 1 |
| total | reply_rate | 43.9 | 71.4 |
| total | awaiting_owner | 14 | 7 |
| total | removal_requested | 5 | 4 |

31 numbers changed.

## Other report sections

- Deleted reviews: phase 1 ['M23', 'R15'] → final ['M13', 'M23', 'R15'] (M13 removed from Google in phase 2).
- M23 (Simone Laurent) and R15 (Liam Walsh) were already deleted in phase 1 (404 on reply); in phase 2 the API no longer lists them at all. Their category and report treatment (excluded) are unchanged.
- Reply corrections: phase 1 ['R01'] → final ['M01', 'M15', 'R01'] (M01 and M15 named Jess).
- August comparison, recomputed replied: 14 → 18 (replies posted since phase 1 to August reviews, see owner decisions, plus Old Town O02 confirmed posted). august_report.json values unchanged.
