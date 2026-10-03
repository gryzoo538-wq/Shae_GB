# Mock Google Business Profile API

A local stand-in for the Business Profile API (v4 subset) with the client's reply gateway in front of it. Treat it as a black box. Talk to it over HTTP only, and do not read or edit its files.

    python3 mock_gbp/server.py --phase 1        # http://127.0.0.1:8765

Auth header on every request: `Authorization: Bearer ll-test-token`

| Method | Path | Notes |
|---|---|---|
| GET | /v4/accounts/118/locations | connected locations |
| GET | /v4/accounts/118/locations/{id}/reviews?pageSize=10&pageToken=… | paginated, newest update first |
| GET | /v4/accounts/118/locations/{id}/reviews/{reviewId} | one review |
| PUT | /v4/accounts/118/locations/{id}/reviews/{reviewId}/reply | body `{"comment": "..."}`. Creates or replaces the owner reply |
| DELETE | /v4/accounts/118/locations/{id}/reviews/{reviewId}/reply | removes the owner reply |

Like the real API, it rate-limits writes (429 with Retry-After), returns 404 for reviews that have been removed, and the gateway rejects replies that break the house rules (400/409 with details). Posted replies persist in mock_gbp/state.json across restarts.
