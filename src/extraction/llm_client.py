import os
import requests
import ollama
from dotenv import load_dotenv
import json

load_dotenv()
def get_setting(name: str, default=None):
    try:
        import streamlit as st

        if name in st.secrets:
            return st.secrets[name]

    except Exception:
        pass

    return os.getenv(name, default)

OLLAMA_BASE_URL = get_setting(
    "OLLAMA_BASE_URL",
    "http://localhost:11434"
)

OLLAMA_MODEL = get_setting(
    "OLLAMA_MODEL",
    "qwen2.5:1.5b"
)

GROQ_API_KEY = get_setting("GROQ_API_KEY")

GROQ_MODEL = get_setting(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)

GROQ_API_URL = get_setting(
    "GROQ_API_URL",
    "https://api.groq.com/openai/v1/chat/completions"
)


def generate_with_ollama(system_prompt: str, user_prompt: str, schema: dict) -> str:
    """Generate structured extraction using local Ollama."""

    client = ollama.Client(host=OLLAMA_BASE_URL)

    response = client.chat(
        model=OLLAMA_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        format=schema,
        options={"temperature": 0}
    )

    return response.message.content


def generate_with_groq(system_prompt: str, user_prompt: str, schema: dict) -> str:
    """Generate JSON extraction using the Groq API."""

    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    # Give Groq the same Pydantic schema used by Ollama.
    structured_system_prompt = (
        system_prompt
        + "\n\nReturn JSON matching this schema:\n"
        + json.dumps(schema)
        + "\nReturn only the JSON object. Do not include markdown."
    )

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": structured_system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0
        },
        timeout=90
    )

    if not response.ok:
        try:
            error_detail = response.json()
        except ValueError:
            error_detail = response.text

        raise RuntimeError(
            f"Groq API Error ({response.status_code}): {error_detail}"
        )

    return response.json()["choices"][0]["message"]["content"]