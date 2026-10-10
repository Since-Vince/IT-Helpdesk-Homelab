#!/usr/bin/env python3
"""Create fictional practice tickets in osTicket. Python 3, no pip dependencies.

Use --dry-run to preview. Live posts require --send, OSTICKET_API_KEY, and
an explicitly supplied OSTICKET_URL pointing at your trusted local server.
"""
import argparse
import json
import os
import random
import sys
import time
from urllib import request, error, parse

EMPLOYEES = [
    ("Alex Morgan", "alex.morgan@example.com"),
    ("Taylor Brooks", "taylor.brooks@example.com"),
    ("Jordan Rivera", "jordan.rivera@example.com"),
    ("Sam Patel", "sam.patel@example.com"),
    ("Morgan Lee", "morgan.lee@example.com"),
    ("Casey Nguyen", "casey.nguyen@example.com"),
    ("Riley Chen", "riley.chen@example.com"),
    ("Jamie Carter", "jamie.carter@example.com"),
]

SCENARIOS = [
    ("VPN", "Cannot connect to the company VPN", "I keep getting a connection failure when signing into our VPN from my work laptop. It worked yesterday. I can browse ordinary websites.", "High"),
    ("Identity", "Account locked after password attempts", "My test employee account is locked after several failed password attempts. I need help getting back into the training environment.", "Medium"),
    ("Linux", "Internal web application not loading", "Our test web application is not responding. The browser reports that the connection timed out.", "High"),
    ("Networking", "DNS resolution seems broken", "I can reach a test IP address but cannot resolve the corresponding hostname. Other test machines still work.", "High"),
    ("Access", "Access to shared folder requested", "I joined the operations team and need read-only access to the training shared folder. Please confirm approval and grant least-privilege access.", "Low"),
    ("Security", "Potential phishing email received", "A suspicious training email claims I need to reset my password immediately. I have not clicked its link. Can IT review it?", "High"),
    ("Storage", "Server disk space warning", "Our lab server is reporting low disk space. Recent test files might be consuming too much storage.", "Medium"),
    ("Database", "Application database connection error", "The training application displays a database connection error after a restart. Can someone check its service configuration?", "High"),
    ("Software", "Application crashes when opened", "The reporting application closes as soon as I open it on the test workstation. Restarting has not helped.", "Medium"),
    ("Identity", "New employee onboarding access", "Our fictional new hire starts tomorrow. Please prepare their test account with standard employee permissions.", "Low"),
    ("Security", "Repeated failed login alerts", "The security dashboard shows multiple failed sign-ins for a test account. Please review the activity and document the findings.", "High"),
    ("Networking", "Cannot reach network printer", "The test workstation cannot communicate with the office printer. Other users can access it normally.", "Medium"),
]


def generate(count, seed):
    rng = random.Random(seed)
    tickets = []
    for i in range(count):
        name, email = rng.choice(EMPLOYEES)
        category, title, description, priority = rng.choice(SCENARIOS)
        payload = {
            "name": name,
            "email": email,
            "subject": f"[LAB] {title} ({i + 1:02d})",
            "message": "data:text/plain;charset=utf-8," + parse.quote(
                "SIMULATED HOME LAB TICKET — no real employee or incident.\n\n"
                f"Category: {category}\nSuggested priority: {priority}\n\n"
                f"Employee report:\n{description}\n\n"
                "IT technician: investigate, record findings, implement a safe lab fix, "
                "and document how you verified resolution.", safe=""
            ),
            "source": "API",
            "alert": False,
            "autorespond": False,
        }
        tickets.append((payload, category, priority))
    return tickets


def main():
    parser = argparse.ArgumentParser(description="Generate simulated osTicket IT tickets")
    parser.add_argument("--count", type=int, default=5, help="tickets to generate, 1–20 (default: 5)")
    parser.add_argument("--seed", type=int, default=None, help="optional repeatable random seed")
    parser.add_argument("--send", action="store_true", help="actually submit tickets; default is preview only")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between POSTs (default: 1)")
    args = parser.parse_args()
    if not 1 <= args.count <= 20:
        parser.error("--count must be between 1 and 20")
    if args.delay < 0:
        parser.error("--delay cannot be negative")

    tickets = generate(args.count, args.seed)
    if not args.send:
        print("PREVIEW ONLY — no tickets submitted. Use --send to submit.\n")
        for i, (payload, category, priority) in enumerate(tickets, 1):
            print(f"{i:2}. {payload['subject']} | {category} | {priority} | {payload['name']}")
        return 0

    url = os.environ.get("OSTICKET_URL", "").strip().rstrip("/")
    api_key = os.environ.get("OSTICKET_API_KEY", "").strip()
    if not url or not api_key:
        print("ERROR: Set OSTICKET_URL and OSTICKET_API_KEY before using --send.", file=sys.stderr)
        return 2
    parsed = parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        print("ERROR: OSTICKET_URL must be a simple http(s) base URL, e.g. http://127.0.0.1:8085", file=sys.stderr)
        return 2
    if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost"):
        print("WARNING: HTTP to a non-loopback address exposes the API key on the network. Prefer local loopback or HTTPS.", file=sys.stderr)
        return 2

    endpoint = url + "/api/tickets.json"
    successes = 0
    for i, (payload, category, priority) in enumerate(tickets, 1):
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"X-API-Key": api_key, "Content-Type": "application/json", "Accept": "text/plain"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=15) as response:
                body = response.read(500).decode("utf-8", errors="replace").strip()
                if response.status != 201:
                    print(f"[{i}] Unexpected HTTP {response.status}: {body}")
                    continue
                successes += 1
                print(f"[{i}] CREATED ticket #{body or '(number not returned)'}: {payload['subject']}")
        except error.HTTPError as exc:
            info = exc.read(500).decode("utf-8", errors="replace").strip()
            print(f"[{i}] HTTP {exc.code}: {info}", file=sys.stderr)
            if exc.code in (401, 403):
                print("Check API key, enabled status, and the source IP configured in osTicket.", file=sys.stderr)
                break
        except error.URLError as exc:
            print(f"[{i}] Connection error: {exc.reason}", file=sys.stderr)
            break
        if i < len(tickets):
            time.sleep(args.delay)
    print(f"\nCreated {successes} of {len(tickets)} requested lab tickets.")
    return 0 if successes == len(tickets) else 1


if __name__ == "__main__":
    sys.exit(main())
