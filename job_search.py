#!/usr/bin/env python3
"""
Automated Job Search Pipeline
Searches Reed + Adzuna APIs and delivers results via Telegram bot.
Triggers: cron (7am GMT daily) + on-demand Telegram listener.
"""

import requests
import json
import os
import sys
import time
import logging
from datetime import datetime, timezone

logging.basicConfig(
    filename="jobsearch.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

# ── Credentials (set in .env or environment) ───────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID   = os.environ["TELEGRAM_CHAT_ID"]
REED_API_KEY       = os.environ["REED_API_KEY"]
ADZUNA_APP_ID      = os.environ["ADZUNA_APP_ID"]
ADZUNA_APP_KEY     = os.environ["ADZUNA_APP_KEY"]

STATE_FILE = "state.json"

# ── Job tiers (example roles — configure for your own search) ──────────────────
LEVEL_1 = [
    "Materials Scientist", "Formulation Chemist",
    "R&D Chemist", "Computational Materials Scientist",
]

LEVEL_2 = [
    "Graduate Materials Scientist", "Junior R&D Chemist",
    "Research Associate", "Associate Scientist",
]

LEVEL_3 = [
    "ML Engineer", "Digital Twin Engineer",
    "Materials Informatics Scientist",
]

TIER_MAP = {
    "jobs level 1": LEVEL_1,
    "jobs bracket 1": LEVEL_1,
    "jobs level 2": LEVEL_2,
    "jobs bracket 2": LEVEL_2,
    "jobs level 3": LEVEL_3,
    "jobs bracket 3": LEVEL_3,
    "jobs": LEVEL_1 + LEVEL_2 + LEVEL_3,
}

TIER_LABELS = {
    "jobs level 1": "Level 1 — Current/Bridging",
    "jobs bracket 1": "Level 1 — Current/Bridging",
    "jobs level 2": "Level 2 — Junior/Entry",
    "jobs bracket 2": "Level 2 — Junior/Entry",
    "jobs level 3": "Level 3 — AI/ML",
    "jobs bracket 3": "Level 3 — AI/ML",
    "jobs": "All Levels",
}

# ── State management ───────────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"sent_ids": [], "date": ""}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def reset_if_new_day(state):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("date") != today:
        state["sent_ids"] = []
        state["date"] = today
        log.info("New day — state reset")
    return state

# ── API fetchers ───────────────────────────────────────────────────────────────
def fetch_reed(roles):
    jobs = []
    for role in roles:
        try:
            resp = requests.get(
                "https://www.reed.co.uk/api/1.0/search",
                auth=(REED_API_KEY, ""),
                params={
                    "keywords": role,
                    "locationName": "UK",
                    "distancefromlocation": 30,
                    "resultsToTake": 5,
                    "minimumSalary": 30000,
                },
                timeout=10
            )
            resp.raise_for_status()
            for j in resp.json().get("results", []):
                salary_raw = j.get("minimumSalary")
                salary = f"£{salary_raw:,.0f}" if salary_raw else "Salary TBC"
                jobs.append({
                    "id": f"reed_{j['jobId']}",
                    "title": j.get("jobTitle", ""),
                    "company": j.get("employerName", ""),
                    "location": j.get("locationName", "UK"),
                    "salary": salary,
                    "url": j.get("jobUrl", ""),
                    "board": "Reed",
                })
        except Exception as e:
            log.warning(f"Reed error for '{role}': {e}")
    return jobs

def fetch_adzuna(roles):
    jobs = []
    for role in roles:
        try:
            resp = requests.get(
                "https://api.adzuna.com/v1/api/jobs/gb/search/1",
                params={
                    "app_id": ADZUNA_APP_ID,
                    "app_key": ADZUNA_APP_KEY,
                    "what": role,
                    "where": "UK",
                    "distance": 30,
                    "results_per_page": 5,
                    "max_days_old": 1,
                    "salary_min": 30000,
                },
                timeout=10
            )
            resp.raise_for_status()
            for j in resp.json().get("results", []):
                salary_raw = j.get("salary_min")
                salary = f"£{salary_raw:,.0f}" if salary_raw else "Salary TBC"
                jobs.append({
                    "id": f"adzuna_{j['id']}",
                    "title": j.get("title", ""),
                    "company": j.get("company", {}).get("display_name", ""),
                    "location": j.get("location", {}).get("display_name", "London"),
                    "salary": salary,
                    "url": j.get("redirect_url", ""),
                    "board": "Adzuna",
                })
        except Exception as e:
            log.warning(f"Adzuna error for '{role}': {e}")
    return jobs

def deduplicate(jobs):
    seen, unique = set(), []
    for j in jobs:
        if j["id"] not in seen:
            seen.add(j["id"])
            unique.append(j)
    return unique

# ── Telegram ───────────────────────────────────────────────────────────────────
def format_message(jobs, label, tier_label=""):
    header = f"<b>🔍 {label}</b>"
    if tier_label:
        header += f" — {tier_label}"
    lines = [header, ""]
    for i, j in enumerate(jobs, 1):
        lines.append(
            f"<b>{i}. {j['title']}</b>\n"
            f"🏢 {j['company']} · 📍 {j['location']}\n"
            f"💰 {j['salary']} · 📋 {j['board']}\n"
            f"🔗 {j['url']}"
        )
        lines.append("")
    return "\n".join(lines)

def send_telegram(text):
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10
        )
        resp.raise_for_status()
        log.info("Telegram message sent")
    except Exception as e:
        log.error(f"Telegram send failed: {e}")

# ── Core logic ─────────────────────────────────────────────────────────────────
def get_next_batch(roles, label, tier_label=""):
    state = reset_if_new_day(load_state())
    all_jobs = deduplicate(fetch_reed(roles) + fetch_adzuna(roles))
    unsent = [j for j in all_jobs if j["id"] not in state["sent_ids"]]
    batch = unsent[:10]
    if not batch:
        send_telegram(f"⚠️ No new unsent jobs found for {label}. Check back tomorrow!")
        log.info(f"No new jobs for {label}")
        return
    send_telegram(format_message(batch, label, tier_label))
    state["sent_ids"].extend(j["id"] for j in batch)
    save_state(state)
    log.info(f"Sent {len(batch)} jobs for {label}")

def run_cron():
    log.info("Cron trigger — sending daily 7am alert")
    get_next_batch(LEVEL_1 + LEVEL_2 + LEVEL_3, "7am Daily Job Alert", "All Levels")

def start_listener():
    log.info("Telegram listener started")
    offset = 0
    while True:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=40
            )
            for update in resp.json().get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {}).get("text", "").lower().strip()
                log.info(f"Received: '{msg}'")
                if msg in TIER_MAP:
                    get_next_batch(TIER_MAP[msg], "Manual Job Search", TIER_LABELS.get(msg, ""))
        except Exception as e:
            log.error(f"Listener error: {e}")
        time.sleep(2)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "listen":
        start_listener()
    else:
        run_cron()
