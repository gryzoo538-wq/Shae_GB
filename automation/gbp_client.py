"""Minimal Google Business Profile (v4 subset) client for the Lantern & Loaf gateway."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:8765"
DEFAULT_TOKEN = "ll-test-token"
DEFAULT_ACCOUNT = "118"

STAR_VALUES = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}


class GBPError(Exception):
    """Base error. `status` is the HTTP status, `details` the decoded error body."""

    def __init__(self, status, message, details=None):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message
        self.details = details or {}


class BadRequestError(GBPError):
    """400: the gateway rejected the request (usually a house-rule violation)."""


class NotFoundError(GBPError):
    """404: the review (or location) no longer exists."""


class ConflictError(GBPError):
    """409: the write conflicts with existing state (e.g. a duplicate reply)."""


class RateLimitError(GBPError):
    """429 that persisted after all retries."""


_ERRORS = {400: BadRequestError, 404: NotFoundError, 409: ConflictError, 429: RateLimitError}


def stars_of(review):
    """Integer star rating of an API review dict."""
    return STAR_VALUES[review["starRating"]]


class GBPClient:
    def __init__(self, base_url=DEFAULT_BASE_URL, token=DEFAULT_TOKEN, account=DEFAULT_ACCOUNT,
                 max_retries=5, sleep=time.sleep, opener=None, page_size=10, on_response=None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.account = account
        self.max_retries = max_retries
        self.sleep = sleep
        self.page_size = page_size
        # `opener(request) -> (status, headers, body_bytes)`; injectable for tests.
        self._opener = opener or self._urllib_open
        # `on_response(method, path, status, payload, headers)` is called for every HTTP attempt.
        self.on_response = on_response

    @staticmethod
    def _urllib_open(req):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def _request(self, method, path, params=None, body=None):
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        attempt = 0
        while True:
            req = urllib.request.Request(url, data=data, method=method)
            req.add_header("Authorization", f"Bearer {self.token}")
            if data is not None:
                req.add_header("Content-Type", "application/json; charset=utf-8")
            status, headers, raw = self._opener(req)
            payload = {}
            if raw:
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except ValueError:
                    payload = {"raw": raw.decode("utf-8", "replace")}
            if self.on_response:
                self.on_response(method, path, status, payload, headers)
            if status == 429 and attempt < self.max_retries:
                attempt += 1
                self.sleep(self._retry_after(headers, attempt))
                continue
            if 200 <= status < 300:
                return payload
            err = payload.get("error", payload) if isinstance(payload, dict) else {}
            message = (err.get("message") or err.get("status") or "request failed") if isinstance(err, dict) else str(err)
            raise _ERRORS.get(status, GBPError)(status, message, err)

    @staticmethod
    def _retry_after(headers, attempt):
        for k, v in headers.items():
            if k.lower() == "retry-after":
                try:
                    return max(0.0, float(v))
                except ValueError:
                    break
        return min(2 ** attempt, 30)

    # --- endpoints -------------------------------------------------------
    def list_locations(self):
        return self._request("GET", f"/v4/accounts/{self.account}/locations").get("locations", [])

    def list_reviews(self, location_id):
        """Return every review for a location, following nextPageToken to the end."""
        reviews, token, seen = [], None, set()
        while True:
            params = {"pageSize": self.page_size}
            if token:
                params["pageToken"] = token
            page = self._request("GET", f"/v4/accounts/{self.account}/locations/{location_id}/reviews", params)
            reviews.extend(page.get("reviews", []))
            token = page.get("nextPageToken")
            if not token:
                return reviews
            if token in seen:
                raise GBPError(0, f"pagination loop on token {token!r}")
            seen.add(token)

    def get_review(self, location_id, review_id):
        return self._request("GET", f"/v4/accounts/{self.account}/locations/{location_id}/reviews/{review_id}")

    def put_reply(self, location_id, review_id, comment):
        return self._request("PUT", f"/v4/accounts/{self.account}/locations/{location_id}/reviews/{review_id}/reply",
                             body={"comment": comment})

    def delete_reply(self, location_id, review_id):
        return self._request("DELETE", f"/v4/accounts/{self.account}/locations/{location_id}/reviews/{review_id}/reply")
