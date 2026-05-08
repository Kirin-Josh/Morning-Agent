import os
import httpx
from dotenv import load_dotenv

load_dotenv()
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")

query = """
{
  viewer {
    assignedIssues(filter: { state: { type: { nin: ["completed", "cancelled"] } } }) {
      nodes {
        title
        priority
        state {
          name
        }
        url
      }
    }
  }
}
"""

def get_linear_issues(api_key=None):
    key = api_key or LINEAR_API_KEY
    response = httpx.post(
        "https://api.linear.app/graphql",
        headers={"Authorization": key},
        json={"query": query}
    )
    data = response.json()
    issues = data["data"]["viewer"]["assignedIssues"]["nodes"]

    def priority_order(issue):
        p = issue.get("priority", 0)
        return 999 if p == 0 else p

    return sorted(issues, key=priority_order)