
import os
from google import genai

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing.")

client = genai.Client(api_key=api_key)

# We'll verify this model is available to your account.
MODEL = "gemini-3.8-flash"

try:
    response = client.models.generate_content(
        model=MODEL,
        contents=(
            "You are the cloud brain of Ahmad Intelligence. "
            "Introduce yourself and explain how you can help "
            "with coding, learning, and everyday questions."
        ),
    )

    print("\n=== AHMAD INTELLIGENCE CLOUD AI ===\n")
    print(response.text or "No text response received.")

except Exception as error:
    print("Gemini request failed.")
    print(type(error).__name__, str(error))

