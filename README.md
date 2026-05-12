# ⚡ Job Hunt Dashboard — Charan Somalaraju

A personal job hunting automation tool that scrapes LinkedIn, Indeed, and Handshake daily, scores each job against your resume using Claude AI, and shows everything in a web dashboard.

## How it works

```
GitHub Actions (7 AM daily)
  → scraper/scraper.py runs
  → Scrapes LinkedIn + Indeed + Handshake
  → Scores each job vs your resume via Anthropic API
  → Commits updated data/jobs.json to repo
  → Triggers dashboard rebuild
  → Dashboard deploys to GitHub Pages
```

---

## Setup (one-time, ~10 minutes)

### 1. Create a GitHub repository

```bash
git init job-hunter
cd job-hunter
# Copy all these files in, then:
git add .
git commit -m "init"
git remote add origin https://github.com/YOUR_USERNAME/job-hunter.git
git push -u origin main
```

### 2. Add your Anthropic API key as a secret

1. Go to your repo on GitHub
2. Settings → Secrets and variables → Actions
3. Click **New repository secret**
4. Name: `ANTHROPIC_API_KEY`
5. Value: your key from https://console.anthropic.com

### 3. Enable GitHub Pages

1. Repo Settings → Pages
2. Source: **GitHub Actions** (or `Deploy from branch` → `gh-pages` branch)

### 4. Run the workflow for the first time

1. Go to **Actions** tab in your repo
2. Click **Daily Job Hunt**
3. Click **Run workflow**
4. Wait ~5 minutes for it to complete

### 5. View your dashboard

Your dashboard will be live at:
```
https://YOUR_USERNAME.github.io/job-hunter/
```

---

## Customizing searches

Edit `scraper/scraper.py` and modify the `SEARCH_QUERIES` list:

```python
SEARCH_QUERIES = [
    "ML Engineer",
    "AI Engineer",
    "LLM Engineer",
    # Add or remove queries here
]
```

## Adjusting the cron schedule

Edit `.github/workflows/daily-job-hunt.yml`:

```yaml
- cron: "0 12 * * *"   # 7 AM EST = 12 UTC
```

Use https://crontab.guru to pick a different time.

## Updating your resume

Edit the `RESUME` variable at the top of `scraper/scraper.py`. The AI scorer uses this to match every job.

---

## Cost estimate

| Service | Cost |
|---|---|
| GitHub Actions | Free (2,000 min/month free tier) |
| Anthropic API (scoring ~100 jobs/day) | ~$0.50–2/day |
| GitHub Pages | Free |

**Estimated monthly cost: $15–60** depending on how many jobs are found per day.

To reduce costs, raise the minimum score threshold before calling Claude by pre-filtering with keyword matching first.

---

## Troubleshooting

**Scraper gets 0 results from LinkedIn:**  
LinkedIn heavily blocks scrapers. Add a residential proxy service (Bright Data, Oxylabs) and set the `HTTP_PROXY` / `HTTPS_PROXY` env vars in the workflow.

**Dashboard shows "No jobs found":**  
Make sure the workflow ran successfully (Actions tab → check for green checkmark) and that `data/jobs.json` was committed.

**`ANTHROPIC_API_KEY` error:**  
Double-check the secret name is exactly `ANTHROPIC_API_KEY` (case-sensitive).
