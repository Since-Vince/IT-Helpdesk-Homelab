#!/usr/bin/env python3
"""Generate fictional corporate IT help-desk tickets for a private osTicket lab.

Python 3 standard library only. Preview by default. Network requests require
--send and a separate API credential (OSTICKET_API_KEY or --api-key-file).
"""
import argparse
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib import error, parse, request

SCENARIOS = [
    # (category, subject, employee report, priority, applicable departments)
    ("VPN", "Unable to connect to VPN", "My test workstation can browse websites but fails to connect to the company VPN. It worked yesterday.", "High", []),
    ("Identity", "Account locked after repeated sign-in attempts", "My training account is locked after several incorrect passwords. Please follow the identity verification procedure.", "Medium", []),
    ("Networking", "DNS resolution fails on one workstation", "I can reach an IP address but can't reach the same test service by hostname. Other workstations work normally.", "High", []),
    ("Software", "Application crashes on startup", "Our fictional reporting app closes immediately on launch. Restarting the workstation didn't help.", "Medium", []),
    ("Software", "Cannot install approved business application", "My test workstation says I don't have permission to install an approved application.", "Low", []),
    ("Security", "Suspicious email reported", "I received a simulated phishing email asking me to confirm my password. I did not click the link.", "High", []),
    ("Security", "Unexpected MFA notification", "I got an unexpected MFA approval prompt for my lab identity account and denied it.", "High", []),
    ("Networking", "Test network printer unavailable", "My workstation cannot reach the shared office printer, but another workstation can.", "Medium", []),
    ("IT Infrastructure", "Linux web service unavailable", "Our internal training site stopped responding. Can someone check the service and web server logs?", "High", ["IT", "Operations"]),
    ("IT Infrastructure", "Docker container repeatedly restarts", "The test container repeatedly exits after startup. Please review its logs and configuration.", "High", ["IT", "Operations"]),
    ("Storage", "Lab server disk space warning", "A lab application warns the storage volume is almost full. Please investigate safe cleanup options.", "Medium", ["IT", "Operations"]),
    ("Database", "Database connection error", "The mock inventory tool cannot connect to its database following a service restart.", "High", ["IT", "Operations"]),
    ("Access", "Read-only shared folder access request", "Please grant my test account read-only access to the operations documents after manager approval.", "Low", ["Operations", "IT"]),
    ("Identity", "New employee account provisioning", "A fictional teammate starts tomorrow. Please create a least-privilege test account and verify login.", "Low", ["HR", "IT"]),
    ("Identity", "Employee offboarding access removal", "A fictional employee has left the company. Please disable their lab access and record completion.", "High", ["HR", "IT"]),
    ("Security", "Unusual failed login events", "Our simulated logs show several failed sign-ins for a test employee. Please investigate and document the pattern.", "High", ["IT", "Operations"]),
    ("Finance", "Finance shared report access denied", "I can sign in but am denied access to a fictional monthly reconciliation report.", "Medium", ["Finance"]),
    ("Finance", "Spreadsheet opens in read-only mode", "The budget training spreadsheet unexpectedly opens in read-only mode.", "Low", ["Finance"]),
    ("Sales", "CRM login repeatedly times out", "My mock CRM session times out shortly after login. Can you check authentication and browser troubleshooting steps?", "Medium", ["Sales"]),
    ("Sales", "Demo laptop cannot connect to Wi-Fi", "Our test presentation laptop sees the SSID but won't connect to the training network.", "Medium", ["Sales"]),
    ("Marketing", "Shared creative folder not syncing", "Changes to a simulated marketing folder aren't appearing on a second test workstation.", "Medium", ["Marketing"]),
    ("Marketing", "Large image upload fails", "The fictional marketing portal fails when uploading a large test file.", "Low", ["Marketing"]),
    ("Support", "Help desk portal sign-in fails", "Our mock support user can't sign in to the training help desk portal.", "High", ["Support"]),
    ("Support", "Ticket notification isn't arriving", "I created a lab ticket but didn't receive the expected notification in the test mailbox.", "Low", ["Support"]),
]


def load_employees(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Can't read employee roster {path}: {exc}") from exc
    if not isinstance(data, list) or not data:
        raise ValueError("Employee roster must be a nonempty JSON list")
    for i, emp in enumerate(data, start=1):
        if not isinstance(emp, dict) or any(not isinstance(emp.get(k), str) or not emp[k].strip() for k in ("name", "email", "department")):
            raise ValueError(f"Employee {i} requires name, email, and department strings")
        if not emp["email"].lower().endswith("@example.com"):
            raise ValueError(f"Employee {i} email must use reserved @example.com domain")
    return data


def generate(count, seed, employees):
    rng = random.Random(seed)
    tickets = []
    for _ in range(count):
        employee = rng.choice(employees)
        applicable = [s for s in SCENARIOS if not s[4] or employee["department"] in s[4]]
        category, subject, report, priority, _allowed = rng.choice(applicable)
        case_id = uuid.uuid4().hex[:8].upper()
        message = (
            "SIMULATED HOME LAB REQUEST — No real employee or incident.\n\n"
            f"Employee: {employee['name']}\nDepartment: {employee['department']}\n"
            f"Category: {category}\nSuggested priority: {priority}\n"
            f"Case reference: LAB-{case_id}\n\n"
            f"EMPLOYEE REPORT:\n{report}\n\n"
            "TECHNICIAN ASSIGNMENT:\n"
            "1. Verify and scope the reported issue.\n"
            "2. Reproduce safely using a disposable lab environment; do not disrupt production services.\n"
            "3. Record commands, evidence, and root cause.\n"
            "4. Resolve or document escalation and verify the result.\n"
        )
        payload = {
            "name": employee["name"],
            "email": employee["email"],
            "subject": f"[LAB] [{employee['department']}] {subject} ({case_id})",
            "message": "data:text/plain;charset=utf-8," + parse.quote(message, safe=""),
            "source": "API",
            "alert": False,
            "autorespond": False,
        }
        tickets.append((payload, employee["department"], category, priority))
    return tickets


def read_api_key(args):
    if args.api_key_file:
        try:
            return Path(args.api_key_file).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ValueError(f"Could not read API key file: {exc}") from exc
    return os.environ.get("OSTICKET_API_KEY", "").strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate simulated corporate IT tickets in osTicket")
    parser.add_argument("--count", type=int, default=3, help="number of tickets, 1-20 (default: 3)")
    parser.add_argument("--seed", type=int, help="repeatable employee and scenario selection")
    parser.add_argument("--send", action="store_true", help="submit tickets to osTicket (preview is default)")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between ticket submissions")
    parser.add_argument("--employees", default=str(Path(__file__).resolve().parent / "employees.json"), help="path to fictional employee roster")
    parser.add_argument("--api-key-file", help="path to file containing API key; used by systemd LoadCredential")
    parser.add_argument("--list-employees", action="store_true", help="display fictional employees, then exit")
    args = parser.parse_args(argv)
    if not 1 <= args.count <= 20:
        parser.error("--count must be between 1 and 20")
    if args.delay < 0:
        parser.error("--delay cannot be negative")
    try:
        employees = load_employees(args.employees)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.list_employees:
        for emp in employees:
            print(f"{emp['name']:22} {emp['department']:12} {emp['email']}")
        return 0

    tickets = generate(args.count, args.seed, employees)
    if not args.send:
        print(f"PREVIEW ONLY — no tickets submitted. {len(employees)} fictional employees available.\n")
        for i, (payload, dept, category, priority) in enumerate(tickets, 1):
            print(f"{i:2}. {payload['subject']} | {category} | {priority} | {payload['name']}")
        return 0

    url = os.environ.get("OSTICKET_URL", "").strip().rstrip("/")
    try:
        api_key = read_api_key(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not url or not api_key:
        print("ERROR: Set OSTICKET_URL and provide OSTICKET_API_KEY or --api-key-file.", file=sys.stderr)
        return 2
    parsed = parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        print("ERROR: OSTICKET_URL must be a simple http(s) base URL", file=sys.stderr)
        return 2
    if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost"):
        print("ERROR: Non-local plain HTTP disallowed. Use 127.0.0.1 or HTTPS.", file=sys.stderr)
        return 2

    endpoint = url + "/api/tickets.json"
    successes = 0
    for i, (payload, dept, category, priority) in enumerate(tickets, 1):
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
                    print(f"[{i}] Unexpected HTTP {response.status}: {body}", file=sys.stderr)
                    continue
                successes += 1
                print(f"[{i}] CREATED ticket #{body or '(not returned)'}: {payload['subject']}")
        except error.HTTPError as exc:
            info = exc.read(500).decode("utf-8", errors="replace").strip()
            print(f"[{i}] HTTP {exc.code}: {info}", file=sys.stderr)
            if exc.code in (401, 403):
                print("Verify the API key, Ticket Creation permission, and source IP.", file=sys.stderr)
                break
        except error.URLError as exc:
            print(f"[{i}] Connection error: {exc.reason}", file=sys.stderr)
            break
        if i < len(tickets):
            time.sleep(args.delay)
    print(f"\nCreated {successes} of {len(tickets)} requested lab tickets at {datetime.now().isoformat(timespec='seconds')}.")
    return 0 if successes == len(tickets) else 1


if __name__ == "__main__":
    sys.exit(main())
