import json
import os
import uuid
import unittest
from urllib import error, request


BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000")


def http_json(method: str, path: str, body: dict | None = None):
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = request.Request(f"{BASE_URL}{path}", method=method, data=data, headers=headers)
    try:
        with request.urlopen(req, timeout=10) as resp:
            payload = resp.read().decode("utf-8")
            return resp.status, json.loads(payload) if payload else None
    except error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        parsed = None
        try:
            parsed = json.loads(payload) if payload else None
        except json.JSONDecodeError:
            parsed = {"raw": payload}
        return exc.code, parsed


class Phase3SmokeTests(unittest.TestCase):
    def test_health_and_docs(self):
        status, payload = http_json("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")

        status, payload = http_json("GET", "/openapi.json")
        self.assertEqual(status, 200)
        self.assertIn("paths", payload)
        self.assertIn("/api/search/", payload["paths"])

    def test_search_endpoint(self):
        status, payload = http_json("GET", "/api/search/?q=campus&scope=all&limit=5")
        self.assertEqual(status, 200)
        self.assertIn("confessions", payload)
        self.assertIn("events", payload)
        self.assertIn("clubs", payload)

    def test_hot_feed_shape_and_repeatability(self):
        status1, payload1 = http_json("GET", "/api/confessions/?sort=hot&limit=5")
        status2, payload2 = http_json("GET", "/api/confessions/?sort=hot&limit=5")

        self.assertEqual(status1, 200)
        self.assertEqual(status2, 200)
        self.assertIn("items", payload1)
        self.assertIn("next_cursor", payload1)
        self.assertIn("items", payload2)

    def test_events_attendees_pagination_shape(self):
        fake_event = uuid.uuid4()
        status, payload = http_json("GET", f"/api/events/{fake_event}/attendees?limit=5")
        self.assertEqual(status, 200)
        self.assertIn("items", payload)
        self.assertIn("next_cursor", payload)
        self.assertIn("has_more", payload)
        self.assertIn("total", payload)

    def test_club_members_pagination_shape(self):
        fake_club = uuid.uuid4()
        status, payload = http_json("GET", f"/api/clubs/{fake_club}/members?limit=5")
        self.assertEqual(status, 200)
        self.assertIn("items", payload)
        self.assertIn("next_cursor", payload)
        self.assertIn("has_more", payload)
        self.assertIn("total", payload)

    def test_polls_list_pagination_shape(self):
        status, payload = http_json("GET", "/api/polls/?limit=5")
        self.assertEqual(status, 200)
        self.assertIn("items", payload)
        self.assertIn("next_cursor", payload)
        self.assertIn("has_more", payload)

    def test_otp_rate_limit_enforced(self):
        statuses = []
        for i in range(6):
            phone = f"+91990000{1000 + i}"
            status, _ = http_json("POST", "/api/auth/request-otp", {"phone": phone})
            statuses.append(status)

        self.assertIn(429, statuses, msg=f"Expected at least one 429, got {statuses}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
