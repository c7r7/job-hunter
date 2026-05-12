"""
Job Hunter Scraper — Charan Somalaraju
Scrapes LinkedIn, Indeed, Handshake and scores each job against resume using Claude API.
Saves results to data/jobs.json for the dashboard.
"""

import json
import os
import time
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ── Resume profile ────────────────────────────────────────────────────────────
RESUME = """
Name: Charan Somalaraju
Education: Masters in Artificial Intelligence, University at Buffalo (2024–present)
           B.Tech Computer Science (AI & ML), VIT Chennai (2019–2023)

Skills: Python, SQL, C++, Java, Docker, AWS, GCP, Kubernetes
        PyTorch, TensorFlow, Scikit-learn, Hugging Face, LangChain, Spark, Pandas, XGBoost
        LLMs (GPT, BERT), RAG, Prompt Engineering, FAISS, OpenAI APIs, LangChain Agents
        MLflow, Airflow, CI/CD, AWS SageMaker, GCP Vertex, n8n, CrewAI

Experience:
- AI Research Contributor @ Handshake (Sep 2025–present): LLM reasoning experiments, multimodal tasks, agent pipeline validation
- ML Research Assistant @ UB (Dec 2024–Aug 2025): LLM chatbot for AAC using RAG, GPT-2 fine-tuning with LoRA
- Associate Data Analyst @ Oracle (Jun 2023–Aug 2024): Loan fraud detection, contract analytics, EMEA deployments
- Data Scientist Intern @ AB-InBev (Jun 2022–May 2023): Forecasting model 91% accuracy, supply chain optimization

Target roles: ML Engineer, AI Engineer, LLM Engineer, Data Scientist, MLOps Engineer, AI Research Engineer
"""

SEARCH_QUERIES = [
    "ML Engineer",
    "AI Engineer",
    "LLM Engineer",
    "Machine Learning Engineer",
    "Data Scientist AI",
    "MLOps Engineer",
    "AI Research Engineer",
]

DATA_FILE = Path(__file__).parent.parent / "data" / "jobs.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def job_id(title: str, company: str, url: str) -> str:
    """Stable dedup key."""
    return hashlib.md5(f"{title.lower()}{company.lower()}{url}".encode()).hexdigest()[:12]


def load_existing() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"jobs": [], "last_updated": None, "meta": {"total": 0}}


def save(data: dict):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def score_job(client: anthropic.Anthropic, title: str, company: str, description: str) -> dict:
    """Ask Claude to score this job against the resume."""
    prompt = f"""You are a job matching assistant. Score this job posting against the candidate's resume.

RESUME:
{RESUME}

JOB POSTING:
Title: {title}
Company: {company}
Description: {description[:3000]}

Respond ONLY with a JSON object (no markdown, no extra text):
{{
  "score": <integer 0-100>,
  "match_reasons": [<up to 3 short strings explaining why it matches>],
  "gaps": [<up to 2 short strings of missing skills>],
  "seniority": "<entry|mid|senior|staff>",
  "remote": <true|false|null>
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        raw = re.sub(r"^```json\s*|```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"  ⚠ Scoring failed: {e}")
        return {"score": 50, "match_reasons": [], "gaps": [], "seniority": "unknown", "remote": None}


# ── Indeed scraper (requests + BS4) ───────────────────────────────────────────

def scrape_indeed(query: str, location: str = "United States") -> list:
    jobs = []
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    }
    url = f"https://www.indeed.com/jobs?q={requests.utils.quote(query)}&l={requests.utils.quote(location)}&sort=date"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("div.job_seen_beacon")[:10]
        for card in cards:
            title_el = card.select_one("h2.jobTitle span")
            company_el = card.select_one("span[data-testid='company-name']")
            link_el = card.select_one("h2.jobTitle a")
            desc_el = card.select_one("div.underShelfFooter")
            if not title_el or not company_el:
                continue
            jobs.append({
                "title": title_el.get_text(strip=True),
                "company": company_el.get_text(strip=True),
                "url": "https://www.indeed.com" + (link_el["href"] if link_el else ""),
                "description": desc_el.get_text(strip=True) if desc_el else "",
                "source": "Indeed",
                "query": query,
            })
    except Exception as e:
        print(f"  Indeed error: {e}")
    return jobs


# ── LinkedIn scraper (Playwright) ─────────────────────────────────────────────

def scrape_linkedin(playwright, query: str) -> list:
    jobs = []
    try:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={requests.utils.quote(query)}&location=United%20States"
            f"&f_TPR=r86400&sortBy=DD"
        )
        page.goto(url, timeout=20000)
        page.wait_for_timeout(3000)
        cards = page.query_selector_all("div.base-card")[:8]
        for card in cards:
            try:
                title = card.query_selector("h3.base-search-card__title")
                company = card.query_selector("h4.base-search-card__subtitle")
                link = card.query_selector("a.base-card__full-link")
                if not title or not company:
                    continue
                jobs.append({
                    "title": title.inner_text().strip(),
                    "company": company.inner_text().strip(),
                    "url": link.get_attribute("href") if link else "",
                    "description": "",
                    "source": "LinkedIn",
                    "query": query,
                })
            except Exception:
                continue
        browser.close()
    except Exception as e:
        print(f"  LinkedIn error: {e}")
    return jobs


# ── Handshake scraper (requests) ──────────────────────────────────────────────

def scrape_handshake(query: str) -> list:
    """Handshake public job search (no login required for basic listings)."""
    jobs = []
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    try:
        url = (
            f"https://app.joinhandshake.com/jobs?"
            f"query={requests.utils.quote(query)}&page=1&per_page=10"
        )
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Handshake renders SSR listing cards
        cards = soup.select("li[data-hook='jobs-list-item']")[:10]
        for card in cards:
            title_el = card.select_one("[data-hook='job-title']")
            company_el = card.select_one("[data-hook='employer-name']")
            link_el = card.select_one("a")
            if not title_el or not company_el:
                continue
            href = link_el["href"] if link_el else ""
            jobs.append({
                "title": title_el.get_text(strip=True),
                "company": company_el.get_text(strip=True),
                "url": href if href.startswith("http") else "https://app.joinhandshake.com" + href,
                "description": "",
                "source": "Handshake",
                "query": query,
            })
    except Exception as e:
        print(f"  Handshake error: {e}")
    return jobs


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n🚀 Job Hunter starting — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    client = anthropic.Anthropic(api_key=api_key)

    existing = load_existing()
    seen_ids = {j["id"] for j in existing.get("jobs", [])}
    new_jobs = []

    with sync_playwright() as playwright:
        for query in SEARCH_QUERIES:
            print(f"\n🔍 Searching: {query}")

            raw_listings = []
            raw_listings += scrape_indeed(query)
            raw_listings += scrape_linkedin(playwright, query)
            raw_listings += scrape_handshake(query)

            for listing in raw_listings:
                jid = job_id(listing["title"], listing["company"], listing["url"])
                if jid in seen_ids:
                    print(f"  ↩ skip (dupe): {listing['title']} @ {listing['company']}")
                    continue
                seen_ids.add(jid)

                print(f"  📋 Scoring: {listing['title']} @ {listing['company']} [{listing['source']}]")
                scored = score_job(client, listing["title"], listing["company"], listing["description"])

                job_entry = {
                    "id": jid,
                    "title": listing["title"],
                    "company": listing["company"],
                    "url": listing["url"],
                    "source": listing["source"],
                    "score": scored.get("score", 50),
                    "match_reasons": scored.get("match_reasons", []),
                    "gaps": scored.get("gaps", []),
                    "seniority": scored.get("seniority", "unknown"),
                    "remote": scored.get("remote"),
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "applied": False,
                    "saved": False,
                }
                new_jobs.append(job_entry)
                time.sleep(0.5)  # rate limit Claude API

            time.sleep(2)  # be polite between queries

    # Merge: new jobs first, then existing, keep last 500
    all_jobs = new_jobs + existing.get("jobs", [])
    all_jobs = all_jobs[:500]

    result = {
        "jobs": all_jobs,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "total": len(all_jobs),
            "new_today": len(new_jobs),
            "sources": ["LinkedIn", "Indeed", "Handshake"],
        },
    }
    save(result)
    print(f"\n✅ Done — {len(new_jobs)} new jobs added. Total: {len(all_jobs)}")


if __name__ == "__main__":
    main()
