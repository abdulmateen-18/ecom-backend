from groq import Groq
import json
import os
from pathlib import Path
from dotenv import load_dotenv
# Load .env from project root
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)


print("Initializing Groq client...")

client = Groq(
    api_key=os.getenv("api_key")
)

print("Groq client initialized.")


def generate_completion(prompt: str):

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # or "llama3-8b-8192" for faster/cheaper
        messages=[
            {
                "role": "system",
                "content": "You are an expert biomedical research assistant. Return structured, accurate scientific content."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7
    )

    return response.choices[0].message.content