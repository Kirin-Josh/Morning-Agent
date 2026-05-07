import os
from groq import Groq
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_ai(user_message, context=""):
    prompt = f"""You are Joshua's personal assistant bot.
You help him with his work as a developer.
You are concise, helpful and friendly.
{f"Context about Joshua's day: {context}" if context else ""}
User: {user_message}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content