"""Final triage = phase 1 judgments + owner decisions (2026-10-04), staff change (Jess left 2026-10-03)
and API phase 2 changes. Every override records its cause in `history` (used for changes_report.md)."""
import copy

from triage_phase1 import T as T1

T = copy.deepcopy(T1)
OT_POSTED = ["O02", "O04", "O06", "O08", "O09", "O10", "O12"]  # owner confirmed posted 2026-10-03, as written


def change(oid, cause, **kw):
    T[oid].update(kw)
    T[oid]["history"] = (T[oid].get("history", "") + " " + cause).strip()


# ---- owner decisions (playbook section 6)
change("M07", "Owner decision 2026-10-04: reply (thank him; new autumn menu) -> owner-reply.",
       cat="owner-reply", owner="reply: thank him, invite him to see the new autumn menu",
       reply="Chris, thank you for the honest feedback! We'd love to turn 'nothing special' into something special - come and see our new autumn menu at Midtown. - Priya, Midtown")
change("M11", "Owner decision 2026-10-04: reply (apologise; manager checked the till records, will sort it out in person) -> owner-reply.",
       cat="owner-reply", owner="reply: apologise; manager checked till records and will sort it out in person next visit",
       reply="Melissa, we're sorry about your experience with our cashier. I've checked the till records and would like to sort this out with you in person on your next visit to Midtown. - Priya, Midtown")
change("M16", "Owner decision 2026-10-04: reply (apologise; tables and restrooms checked hourly) -> owner-reply.",
       cat="owner-reply", owner="reply: apologise; tables and restrooms now checked every hour",
       reply="Owen, we're sorry the tables were sticky and the bathroom was out of soap. Our tables and restrooms are now checked every hour at Midtown. - Priya, Midtown")
change("M25", "Owner decision 2026-10-04: reply (extra person on weekend mornings) -> owner-reply.",
       cat="owner-reply", owner="reply: we've added a person on weekend mornings",
       reply="Ivy, we're sorry you waited so long and that the team felt stretched. We've added an extra person on weekend mornings at Midtown to keep things moving. - Priya, Midtown")
change("R04", "Owner decision 2026-10-04: reply (thank for kind words about the team; scones baked fresh every morning) -> owner-reply.",
       cat="owner-reply", owner="reply: thank her for the kind words about the team; scones now baked fresh every morning",
       odd="Mentions Theo (former, no consent): the owner-reply thanks 'the team' and does not name him.",
       reply="Leah, thank you for the kind words about our team! We're sorry your scone was stale - our scones are now baked fresh every morning at Riverside. - Marco, Riverside")
change("R07", "Owner decision 2026-10-04: reply (local organic flour and butter) -> owner-reply.",
       cat="owner-reply", owner="reply: explain we use local organic flour and butter",
       reply="Peter, thank you for the feedback, and we're sorry it felt overpriced. We bake with local organic flour and butter at Riverside, and we hope that shows in every bite. - Marco, Riverside")
change("R13", "Owner decision 2026-10-04: no reply -> flag-closed.", cat="flag-closed", owner="no reply")
change("R16", "Owner decision 2026-10-04: no reply -> flag-closed.", cat="flag-closed", owner="no reply")
change("R22", "Owner decision 2026-10-04: reply (espresso machine recalibrated) -> owner-reply.",
       cat="owner-reply", owner="reply: we've recalibrated the espresso machine",
       reply="Marcus, thank you for the kind words about our croissant, and sorry the coffee tasted burnt. We've recalibrated the espresso machine at Riverside. - Marco, Riverside")
change("O07", "Owner decision 2026-10-04: reply (bigger brunch plates coming in October) -> owner-reply; for the owner to post by hand.",
       cat="owner-reply", owner="reply: bigger brunch plates are coming in October",
       reply="Megan, thank you for calling us a cute spot! We hear you on the small portions, and bigger brunch plates are coming to Old Town in October. - Hannah, Old Town")

# ---- M18: owner said "no reply", but the review was edited on 2026-10-02 (rule 1 + section 6: edit overrides)
change("M18", "Owner decision 'no reply' (flag-closed) overridden: reviewer edited on 2026-10-02 to 5 stars, "
              "'Came back and the coffee was hot this time. Much better!' -> reprocessed as reply (section 6).",
       cat="reply", pri="", issue="", owner="no reply (superseded by the 2026-10-02 edit)",
       why="Edited 2026-10-02 to 5 stars with no complaint; the edit overrides the owner's earlier 'no reply'.",
       odd="Edited after the owner's decision (3 stars -> 5 stars).",
       reply="Rachel, thank you for coming back and for updating your review! We're so glad your coffee was hot this time. See you again soon at Midtown. - Priya, Midtown")

# ---- Jess left 2026-10-03 (staff_update.csv): no reply may name her
change("M15", "Staff change: Jess left 2026-10-03 (no consent). Our posted reply named her -> edited via the API.",
       staff=[("Jess", False)], correction=True, old_reply=T1["M15"]["reply"],
       odd="Names Jess, who left on 2026-10-03 and may no longer be named; our phase 1 reply named her, so it was replaced.",
       reply="Nadia, thank you so much! We're thrilled you had the best service you've had anywhere, and we've shared your kind words with the Midtown team. - Priya, Midtown")
change("M01", "Staff change: Jess left 2026-10-03. The previous contractor's reply ('Jess will be thrilled') now breaks 4c -> rule 1 correction via the API.",
       staff=[("Jess", False)], correction=True,
       odd="Existing reply names Jess, who left on 2026-10-03 and may no longer be named -> rule 1 correction posted.",
       reply="Grace, thank you! We're so glad you love our almond croissant, and the Midtown team is delighted to know your order by heart. - Priya, Midtown")

# ---- reviews that disappeared from the API (GET returns 404)
change("M13", "Phase 2: no longer returned by the API; GET returns 404 (removed from Google) -> deleted, excluded from the report. "
              "The removal request is resolved.",
       cat="deleted", why=T1["M13"]["why"] + " Removed from Google by phase 2 (GET 404).",
       odd="Was a removal request; the review is gone. Excluded from all report numbers.", note="removed from Google (GET 404 in phase 2)")
for _id in ("M23", "R15"):
    T[_id]["odd"] += " No longer listed by the API in phase 2 (GET 404)."

# ---- new reviews in phase 2
T["M27"] = dict(cat="reply", why="New in phase 2. 5 stars, praise only.", history="New review (created 2026-09-30) first returned by the API in phase 2.",
                odd="New since phase 1.",
                reply="Hugo, thank you! We're so glad you enjoyed the carrot cake, and we'll pass your kind words on to our friendly crew at Midtown. - Priya, Midtown")
T["R25"] = dict(cat="flag", pri="normal", issue="Long wait for a simple order",
                why="New in phase 2. 2 stars; about waiting, not staff behaviour or money -> normal.",
                history="New review (created 2026-09-29) first returned by the API in phase 2.",
                odd="New since phase 1. Numbered R25 (not by createTime) so that phase 1 ids keep their meaning.")

# ---- Old Town replies confirmed posted by the owner
for _id in OT_POSTED:
    T[_id]["ot_status"] = "posted by owner 2026-10-03 (confirmed)"
    T[_id]["history"] = (T[_id].get("history", "") + " Owner confirmed posting on 2026-10-03: now counted as replied, no longer manual pending.").strip()

DIGEST_EXTRA = {
    "intro": "This digest reflects your decisions of 2026-10-04, Jess leaving on 2026-10-03, and what changed on "
             "Google since our first delivery. Thank you for posting the Old Town replies!",
    "closed": [
        "- **M18** · Midtown · Rachel Adeyemi: you said *no reply*, but she edited her review on 2026-10-02 to 5★ "
        "(\"Came back and the coffee was hot this time. Much better!\"). Under section 6 the edit overrides the earlier "
        "decision, so we replied to thank her.",
        "- **R13** Craig Summers and **R16** A Google User: *no reply*, closed (flag-closed).",
        "- Replied as you asked (owner-reply): M07 Chris Daley, M11 Melissa Grant, M16 Owen Mercer, M25 Ivy Chen, "
        "R04 Leah Morgan, R07 Peter Huang, R22 Marcus Bell (posted via the API) and O07 Megan Riley (for you to post).",
    ],
    "notes": [
        "M13 (Local Foodie 99, competitor promotion with a link) has been removed from Google, so that removal "
        "request is resolved. It now counts as deleted and is excluded from the report.",
        "New on Google since our first pass: M27 Hugo Lambert (5★, replied) and R25 Paula Reyes (2★, long wait) - "
        "R25 needs your decision.",
        "Reply+flag items M09, M14, M24, R09, R19, R20 and O09 already have public replies. We still need your call on the "
        "operational issues (wifi, queue, oat milk stock, parking, music volume, Old Town mention, cash only).",
        "M05 (Derek Pruitt) was edited after our 2026-08-16 reply and is urgent; the old reply names no one and stays up.",
        "Older replies from the previous contractor open with 'Thank you <name>' or 'Sorry ...' rather than the first name. "
        "Rule 1 only requires replacing replies that name someone who may not be named, so we left them as they are.",
    ],
}
