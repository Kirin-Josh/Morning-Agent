import os
from slack_sdk import WebClient
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

def send_slack_dm(slack_id: str, message: str):
    client.chat_postMessage(
        channel=slack_id,
        text=message
    )

if __name__ == '__main__':
    send_slack_dm("YOUR_SLACK_ID", "👋 Morning Agent is connected to Slack!")
    print("Slack DM sent successfully!")