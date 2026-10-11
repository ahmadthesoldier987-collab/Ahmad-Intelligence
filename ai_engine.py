
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"

AVAILABLE_MODELS = {
    "Qwen Coder 3B": "qwen2.5-coder:3b",
    "Qwen 2.5 3B": "qwen2.5:3b",
    "DeepSeek R1 1.5B": "deepseek-r1:1.5b",
}

DEFAULT_MODEL = "qwen2.5-coder:3b"
MODEL_NAME = DEFAULT_MODEL

DEFAULT_INSTRUCTIONS = (
    "You are Ahmad Intelligence, a helpful personal AI assistant. "
    "Give clear, accurate, and useful answers. "
    "When appropriate, explain difficult concepts step by step."
)


def ask_ai(messages, project_instructions="", model=DEFAULT_MODEL):
    instructions = DEFAULT_INSTRUCTIONS

    if project_instructions.strip():
        instructions += (
            "\n\nAdditional instructions for the current project:\n"
            + project_instructions.strip()
        )

    ai_messages = [
        {"role": "system", "content": instructions},
        *messages,
    ]

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "messages": ai_messages,
            "stream": False,
        },
        timeout=300,
    )

    response.raise_for_status()
    return response.json()["message"]["content"]

