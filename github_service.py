import os
import httpx
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

def get_pull_requests():
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    # PRs assigned to you or created by you
    response = httpx.get(
        f"https://api.github.com/search/issues?q=is:pr+is:open+involves:{GITHUB_USERNAME}",
        headers=headers
    )

    data = response.json()
    prs = []

    for item in data.get("items", []):
        prs.append({
            "title": item["title"],
            "repo": item["repository_url"].split("/repos/")[1],
            "url": item["html_url"],
            "author": item["user"]["login"],
            "created_at": item["created_at"][:10]
        })

    return prs