
import ollama

response = ollama.chat(
    model="qwen2.5:1.5b",
    messages=[
        {
            "role": "user",
            "content": "What is an invoice? Explain in two sentences."
        }
    ]
)

print(response.message.content)
