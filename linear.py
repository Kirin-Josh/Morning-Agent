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

response = httpx.post(
    "https://api.linear.app/graphql",
    headers={"Authorization": LINEAR_API_KEY},
    json={"query": query}
)

data = response.json()
issues = data["data"]["viewer"]["assignedIssues"]["nodes"]

for issue in issues:
    print(f"• {issue['title']} — {issue['state']['name']}")
    
def get_linear_issues():
    return issues