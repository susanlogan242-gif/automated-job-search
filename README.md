# Automated Job Search Pipeline

**Python · REST APIs · Telegram Bot API · Linux VPS · cron**

Designed and deployed an automated vacancy retrieval system on a Linux VPS, integrating the Reed and Adzuna REST APIs with JSON response parsing, deduplication logic, and batch delivery via a custom Telegram bot. Implements cron scheduling for daily 7am alerts alongside an on-demand query interface. Manages the full deployment lifecycle including remote server administration and structured logging.

---

## Features

- **Dual-source aggregation** — queries Reed and Adzuna APIs in parallel per search role
- **Deduplication** — cross-board ID tracking prevents duplicate listings
- **3-tier role system** — Level 1 (current/bridging), Level 2 (junior/entry), Level 3 (AI/ML stretch)
- **Batch delivery** — delivers next 10 unseen jobs per request, with daily state reset
- **Cron mode** — automated 7am GMT daily alert across all tiers
- **Listener mode** — long-polls Telegram for on-demand queries by tier
- **Structured logging** — timestamped log file for all API calls, sends, and errors
- **Location & salary filtering** — configurable region, radius, and minimum salary

---

## Architecture

```
cron (7am GMT)          Telegram listener
      │                        │
      └──────────┬─────────────┘
                 ▼
          job_search.py
                 │
        ┌────────┴────────┐
        ▼                 ▼
   Reed API          Adzuna API
        │                 │
        └────────┬─────────┘
                 ▼
          Deduplicate + filter
                 │
                 ▼
          state.json (sent IDs)
                 │
                 ▼
          Telegram Bot API
```

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/YOUR_USERNAME/automated-job-search.git
cd automated-job-search
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env with your API keys
```

You will need:
- A [Telegram Bot Token](https://core.telegram.org/bots#botfather) (via BotFather)
- Your Telegram Chat ID
- A [Reed API key](https://www.reed.co.uk/developers/jobseeker)
- An [Adzuna App ID and Key](https://developer.adzuna.com/)

### 3. Load environment and run

```bash
export $(cat .env | xargs)

# Cron mode (sends daily alert)
python3 job_search.py

# Listener mode (responds to Telegram messages)
python3 job_search.py listen
```

---

## Cron Configuration

Add to crontab (`crontab -e`) for daily 7am GMT alerts:

```
TZ="Europe/London"
0 7 * * * cd /path/to/project && export $(cat .env | xargs) && /usr/bin/python3 job_search.py >> jobsearch.log 2>&1
```

---

## Telegram Commands

Send these messages to your bot:

| Command | Response |
|---|---|
| `jobs` | Next 10 unseen jobs across all tiers |
| `jobs level 1` | Level 1 — Current/Bridging roles |
| `jobs level 2` | Level 2 — Junior/Entry roles |
| `jobs level 3` | Level 3 — AI/ML Stretch roles |
| `jobs bracket 1/2/3` | Aliases for the above |

---

## Job Tiers

**Level 1 — Current/Bridging**
Polymer Scientist, Polymer Chemist, Formulation Chemist, R&D Chemist, Product Development Chemist, Materials Scientist, Computational Materials Scientist, Materials Informatics Scientist, Cheminformatics Scientist, Polymer Data Scientist

**Level 2 — Junior/Entry**
Junior Materials Scientist, Junior Polymer Chemist, Junior R&D Chemist, Graduate Materials Scientist, Research Associate Materials, Associate Scientist, Junior ML Engineer, Graduate Data Scientist, Junior Cheminformatics Scientist, Junior Computational Materials Scientist, Research Associate Cheminformatics

**Level 3 — AI/ML Stretch**
AI ML Engineer Materials, Digital Twin Engineer, Materials Informatics Lead, Sustainable Materials Innovation, Battery Materials Scientist, Nanomaterials Scientist, Technical Consultant Speciality Chemicals, Fuel Cell Materials

---

## Filters

- **Location:** London, 30-mile radius
- **Minimum salary:** £27,000
- **Adzuna:** `max_days_old=1` (fresh listings only)

---

## State Management

`state.json` tracks sent listing IDs per day and resets automatically at UTC midnight, ensuring no duplicate deliveries within a day while refreshing the pool daily.

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3 |
| Job boards | Reed API, Adzuna API |
| Delivery | Telegram Bot API |
| Scheduling | Linux cron |
| Deployment | Hostinger KVM Linux VPS |
| Logging | Python `logging` module |
