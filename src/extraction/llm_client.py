import os
import requests
import ollama
from dotenv import load_dotenv
import json
import time

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



def generate_with_groq(
    system_prompt: str,
    user_prompt: str,
    schema: dict
) -> str:
    """Generate invoice JSON using Groq with automatic retries."""

    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")

    structured_system_prompt = (
        system_prompt
        + "\n\nReturn a single valid JSON object matching this schema:\n"
        + json.dumps(schema)
        + """

STRICT OUTPUT RULES:
- Return JSON only. No markdown or code fences.
- Include every required field from the schema.
- Use null for unavailable optional values.
- Use [] for missing line items.
- Use {} for missing evidence.
- Do not add comments or explanations.
- Ensure all strings and keys use valid JSON double quotes.
- Do not leave trailing commas.
- Do not truncate the JSON response.
"""
    )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
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
        "temperature": 0,
        "max_completion_tokens": 4096
    }

    last_error = None

    for attempt in range(3):

        try:
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=90
            )

            if response.ok:
                content = response.json()["choices"][0]["message"]["content"]

                if content and content.strip():
                    return content

                raise RuntimeError("Groq returned an empty response.")

            try:
                error_detail = response.json()
            except ValueError:
                error_detail = response.text

            error_text = str(error_detail)

            # Retry JSON generation failures and temporary server errors.
            retryable = (
                "json_validate_failed" in error_text
                or response.status_code in (429, 500, 502, 503, 504)
            )

            if not retryable:
                raise RuntimeError(
                    f"Groq API Error ({response.status_code}): "
                    f"{error_detail}"
                )

            last_error = RuntimeError(
                f"Groq API Error ({response.status_code}): "
                f"{error_detail}"
            )

        except requests.exceptions.RequestException as error:
            last_error = error

        except RuntimeError as error:
            if "empty response" not in str(error):
                raise
            last_error = error

        if attempt < 2:
            time.sleep(2 ** attempt)

    raise RuntimeError(
        f"Groq extraction failed after 3 attempts: {last_error}"
    )
