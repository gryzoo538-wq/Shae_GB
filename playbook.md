# Lantern & Loaf: Google review playbook

Three locations: Midtown and Riverside (connected to the Business Profile API) and Old Town (not connected; the owner sends phone screenshots and posts replies by hand). Today is 2026-10-01. The report month is September 2026.

## 1. Which reviews to process
- Process every review that has no owner reply, whatever its date.
- A review that already has an owner reply is skipped, unless the reviewer edited it after that reply (review updateTime later than the reply's updateTime). An edited review is processed again, as if it were new, using its current text and stars.
- Our existing replies must follow rule 4 too. If an existing reply names someone who may not be named (see 4c), replace it with a corrected version (API locations) or list it for the owner to edit (Old Town).

## 2. Routing (each processed review gets exactly one category; check in this order)
1. **urgent**: any mention of illness, an allergic reaction, a foreign object in food, or pests, whatever the stars. Do not reply. The owner must phone the manager within 24 hours.
2. **report**: request removal from Google, and do not reply. Use this for reviews that are not about our business (wrong business), are written by someone with a conflict of interest (staff, family, competitors), promote a competitor or contain links, contain only profanity, or describe no actual visit.
3. **reply**: 4–5 stars with no complaint, including star-only reviews (no text).
4. **reply+flag**: 4–5 stars that also mention a specific problem (waiting or queues, price, cleanliness, wrong order, stock running out, noise, wifi, parking, payment options), or a review clearly about a different one of our locations. Draft a reply, and also flag the review for the owner.
5. **flag**: 1–3 stars (with or without text). No reply until the owner decides.
If a review was found deleted when you tried to reply (API 404), its category is **deleted**. List it and exclude it from all report numbers.

## 3. Flags for the owner
Each flag lists the review, the location, the issue in one line, and a priority:
- **high**: 1–2 stars that mention staff behaviour or money.
- **normal**: everything else.
Urgent items go in their own section at the top of the owner digest.

## 4. Reply rules (all replies)
a. Start with the reviewer's first name (the first word of their display name). If the name is only initials, or "A Google User", use no name.
b. Mention one specific thing from the review. For a review with stars only, thank them for the rating.
c. Name a staff member only if staff.csv shows them as current at that location with public_mention_consent = yes. Otherwise refer to "the team".
d. Never offer refunds, discounts, freebies or compensation in public. Never admit legal fault.
e. No links, email addresses or phone numbers.
f. Reply in the language of the review.
g. End with: `- <manager first name>, <location name>` (managers are in locations.csv). The location name must appear in the reply.
h. At most 350 characters. Every reply must be unique; no two replies may have identical text.
i. For a review about a different one of our locations, thank them and mention that location by name, as well as signing off with the posting location.

## 5. Monthly report (September 2026)
Count a review in September if its createTime date is in September 2026. Use each review's current star rating. Include all three locations. Exclude reviews in category deleted.
Per location, and in total:
- new_reviews; average_rating (2 decimals); stars_1 … stars_5
- replied: reviews with an owner reply visible at report time (API data for Midtown and Riverside; for Old Town, replies the owner has confirmed as posted)
- manual_pending: Old Town replies drafted but not yet confirmed as posted
- reply_rate: replied ÷ new_reviews, as a percentage with 1 decimal
- flagged_for_owner: categories flag, reply+flag, owner-reply and flag-closed
- awaiting_owner: categories flag and reply+flag
- urgent; removal_requested (category report)
Also list the deleted reviews (excluded), the reviews with replies corrected under rule 1, and an August comparison. Recompute August from the data by the same definitions and compare it with august_report.json, explaining any difference.

## 6. Categories added after owner decisions
When the owner decides on a flagged review: "reply" makes it **owner-reply** (draft the reply under rule 4, using the owner's points); "no reply" makes it **flag-closed**. If a flagged review is edited later, rule 1 applies, and the edit overrides an earlier owner decision.
