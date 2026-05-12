"""
Job Hunter Scraper — Charan Somalaraju
Hits public ATS APIs (Greenhouse, Lever, Workday) for Fortune 500 tech companies
+ LinkedIn public search. Scores each job against resume using Claude AI.
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

# ── Resume profile ─────────────────────────────────────────────────────────────
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

# Keywords to filter relevant jobs before scoring (saves API cost)
RELEVANT_KEYWORDS = [
    "machine learning", "ml engineer", "ai engineer", "data scientist",
    "llm", "nlp", "deep learning", "artificial intelligence", "mlops",
    "research engineer", "applied scientist", "computer vision",
    "generative ai", "large language", "foundation model", "pytorch",
    "tensorflow", "python", "data engineer", "analytics engineer",
]

# ── Fortune 500 companies by ATS platform ─────────────────────────────────────
# Greenhouse: use public API  https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
# Lever:      use public API  https://api.lever.co/v0/postings/{slug}?mode=json
# Workday:    scrape careers page (no public API, use requests)

GREENHOUSE_COMPANIES = [
    # Big Tech & AI
    ("anthropic", "Anthropic"),
    ("openai", "OpenAI"),
    ("scale-ai", "Scale AI"),
    ("cohere", "Cohere"),
    ("huggingface", "Hugging Face"),
    ("mistral-ai", "Mistral AI"),
    ("perplexityai", "Perplexity AI"),
    ("together-ai", "Together AI"),
    ("modal-labs", "Modal Labs"),
    ("weights-biases", "Weights & Biases"),
    ("databricks", "Databricks"),
    ("snowflake", "Snowflake"),
    ("confluent", "Confluent"),
    ("dbt-labs", "dbt Labs"),
    ("fivetran", "Fivetran"),
    ("airbyte", "Airbyte"),
    # Fortune 500 Tech
    ("robinhood", "Robinhood"),
    ("coinbase", "Coinbase"),
    ("stripe", "Stripe"),
    ("plaid", "Plaid"),
    ("brex", "Brex"),
    ("figma", "Figma"),
    ("notion", "Notion"),
    ("airtable", "Airtable"),
    ("dropbox", "Dropbox"),
    ("twilio", "Twilio"),
    ("zendesk", "Zendesk"),
    ("hubspot", "HubSpot"),
    ("mongodb", "MongoDB"),
    ("elastic", "Elastic"),
    ("hashicorp", "HashiCorp"),
    ("datadog", "Datadog"),
    ("pagerduty", "PagerDuty"),
    ("cloudflare", "Cloudflare"),
    ("fastly", "Fastly"),
    ("docusign", "DocuSign"),
    ("okta", "Okta"),
    ("crowdstrike", "CrowdStrike"),
    ("sentinelone", "SentinelOne"),
    ("veeva", "Veeva Systems"),
    ("servicenow", "ServiceNow"),
    ("workday", "Workday"),
    ("splunk", "Splunk"),
    ("tableau", "Tableau"),
    ("alteryx", "Alteryx"),
    ("palantir", "Palantir"),
    ("c3ai", "C3.ai"),
    ("squarespace", "Squarespace"),
    ("eventbrite", "Eventbrite"),
    ("duolingo", "Duolingo"),
    ("reddit", "Reddit"),
    ("discord", "Discord"),
    ("roblox", "Roblox"),
    ("unity", "Unity"),
    ("epic-games", "Epic Games"),
    ("lyft", "Lyft"),
    ("doordash", "DoorDash"),
    ("instacart", "Instacart"),
    ("chime", "Chime"),
    ("affirm", "Affirm"),
    ("klarna", "Klarna"),
    ("marqeta", "Marqeta"),
    ("carta", "Carta"),
    ("lattice", "Lattice"),
    ("rippling", "Rippling"),
    ("gusto", "Gusto"),
    ("greenhouse", "Greenhouse"),
    ("lever", "Lever"),
    ("mixpanel", "Mixpanel"),
    ("amplitude", "Amplitude"),
    ("segment", "Segment"),
    ("heap", "Heap"),
    ("contentful", "Contentful"),
    ("sanity", "Sanity"),
    ("vercel", "Vercel"),
    ("netlify", "Netlify"),
    ("render", "Render"),
    ("railway", "Railway"),
    ("supabase", "Supabase"),
    ("planetscale", "PlanetScale"),
    ("neon", "Neon"),
]

LEVER_COMPANIES = [
    ("netflix", "Netflix"),
    ("twitter", "Twitter / X"),
    ("airbnb", "Airbnb"),
    ("pinterest", "Pinterest"),
    ("snap", "Snap"),
    ("shopify", "Shopify"),
    ("square", "Square"),
    ("box", "Box"),
    ("zoom", "Zoom"),
    ("slack", "Slack"),
    ("asana", "Asana"),
    ("monday", "Monday.com"),
    ("linear", "Linear"),
    ("retool", "Retool"),
    ("census", "Census"),
    ("hightouch", "Hightouch"),
    ("anomalo", "Anomalo"),
    ("covariant", "Covariant"),
    ("shield-ai", "Shield AI"),
    ("applied-intuition", "Applied Intuition"),
    ("nuro", "Nuro"),
    ("gatik", "Gatik"),
    ("aurora", "Aurora"),
    ("wayve", "Wayve"),
    ("luminar", "Luminar"),
    ("recursion", "Recursion Pharmaceuticals"),
    ("insitro", "Insitro"),
    ("ginkgo", "Ginkgo Bioworks"),
]

# LinkedIn public search (no auth, just public listings)
LINKEDIN_QUERIES = [
    "ML Engineer entry level",
    "AI Engineer new grad",
    "Data Scientist machine learning",
    "LLM Engineer",
    "MLOps Engineer",
]

DATA_FILE = Path(__file__).parent.parent / "data" / "jobs.json"

# ── Helpers ────────────────────────────────────────────────────────────────────

def job_id(title: str, company: str, url: str = "") -> str:
    return hashlib.md5(f"{title.lower().strip()}{company.lower().strip()}{url}".encode()).hexdigest()[:12]


def is_relevant(title: str, description: str = "") -> bool:
    text = (title + " " + description).lower()
    return any(kw in text for kw in RELEVANT_KEYWORDS)


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
    prompt = f"""You are a job matching assistant. Score this job against the candidate resume.

RESUME:
{RESUME}

JOB:
Title: {title}
Company: {company}
Description: {description[:2500]}

Respond ONLY with JSON (no markdown):
{{
  "score": <0-100>,
  "match_reasons": [<up to 3 short strings>],
  "gaps": [<up to 2 short strings>],
  "seniority": "<entry|mid|senior|staff>",
  "remote": <true|false|null>
}}"""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = re.sub(r"^```json\s*|```$", "", response.content[0].text.strip(), flags=re.MULTILINE).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"  ⚠ Scoring failed: {e}")
        return {"score": 50, "match_reasons": [], "gaps": [], "seniority": "unknown", "remote": None}


# ── ATS scrapers ───────────────────────────────────────────────────────────────

def scrape_greenhouse(slug: str, company_name: str) -> list:
    """Greenhouse public API — no auth needed."""
    jobs = []
    try:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json().get("jobs", [])
        for j in data:
            title = j.get("title", "")
            if not is_relevant(title):
                continue
            jobs.append({
                "title": title,
                "company": company_name,
                "url": j.get("absolute_url", ""),
                "description": BeautifulSoup(j.get("content", ""), "html.parser").get_text()[:2000],
                "source": "Greenhouse",
            })
    except Exception as e:
        print(f"  Greenhouse [{slug}] error: {e}")
    return jobs


def scrape_lever(slug: str, company_name: str) -> list:
    """Lever public posting API — no auth needed."""
    jobs = []
    try:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json&limit=50"
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json()
        for j in data:
            title = j.get("text", "")
            if not is_relevant(title):
                continue
            desc = " ".join(
                snippet.get("content", "")
                for snippet in j.get("descriptionBody", {}).get("descriptionPlain", [])
                if isinstance(snippet, dict)
            )
            jobs.append({
                "title": title,
                "company": company_name,
                "url": j.get("hostedUrl", ""),
                "description": desc[:2000],
                "source": "Lever",
            })
    except Exception as e:
        print(f"  Lever [{slug}] error: {e}")
    return jobs


def scrape_linkedin(playwright, query: str) -> list:
    jobs = []
    try:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        url = (
            f"https://www.linkedin.com/jobs/search/"
            f"?keywords={requests.utils.quote(query)}"
            f"&location=United%20States&f_TPR=r86400&sortBy=DD"
        )
        page.goto(url, timeout=20000)
        page.wait_for_timeout(3000)
        cards = page.query_selector_all("div.base-card")[:10]
        for card in cards:
            try:
                title_el = card.query_selector("h3.base-search-card__title")
                company_el = card.query_selector("h4.base-search-card__subtitle")
                link_el = card.query_selector("a.base-card__full-link")
                if not title_el or not company_el:
                    continue
                title = title_el.inner_text().strip()
                if not is_relevant(title):
                    continue
                jobs.append({
                    "title": title,
                    "company": company_el.inner_text().strip(),
                    "url": link_el.get_attribute("href") if link_el else "",
                    "description": "",
                    "source": "LinkedIn",
                })
            except Exception:
                continue
        browser.close()
    except Exception as e:
        print(f"  LinkedIn error: {e}")
    return jobs


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"\n🚀 Job Hunter starting — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    client = anthropic.Anthropic(api_key=api_key)

    existing = load_existing()
    seen_ids = {j["id"] for j in existing.get("jobs", [])}
    new_jobs = []

    def process_listings(listings: list):
        for listing in listings:
            jid = job_id(listing["title"], listing["company"], listing["url"])
            if jid in seen_ids:
                continue
            seen_ids.add(jid)
            print(f"  📋 {listing['title']} @ {listing['company']} [{listing['source']}]")
            scored = score_job(client, listing["title"], listing["company"], listing.get("description", ""))
            new_jobs.append({
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
            })
            time.sleep(0.4)

    # 1. Greenhouse companies
    print(f"\n🏢 Scraping {len(GREENHOUSE_COMPANIES)} companies via Greenhouse API...")
    for slug, name in GREENHOUSE_COMPANIES:
        listings = scrape_greenhouse(slug, name)
        if listings:
            print(f"  ✓ {name}: {len(listings)} relevant jobs")
            process_listings(listings)
        time.sleep(0.3)

    # 2. Lever companies
    print(f"\n🏢 Scraping {len(LEVER_COMPANIES)} companies via Lever API...")
    for slug, name in LEVER_COMPANIES:
        listings = scrape_lever(slug, name)
        if listings:
            print(f"  ✓ {name}: {len(listings)} relevant jobs")
            process_listings(listings)
        time.sleep(0.3)

    # 3. LinkedIn
    print(f"\n🔗 Scraping LinkedIn...")
    with sync_playwright() as playwright:
        for query in LINKEDIN_QUERIES:
            print(f"  Searching: {query}")
            listings = scrape_linkedin(playwright, query)
            process_listings(listings)
            time.sleep(2)

    # Merge and save
    all_jobs = new_jobs + existing.get("jobs", [])
    all_jobs = all_jobs[:1000]

    result = {
        "jobs": all_jobs,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "total": len(all_jobs),
            "new_today": len(new_jobs),
            "sources": ["Greenhouse", "Lever", "LinkedIn"],
        },
    }
    save(result)
    print(f"\n✅ Done — {len(new_jobs)} new jobs added. Total: {len(all_jobs)}")


if __name__ == "__main__":
    main()