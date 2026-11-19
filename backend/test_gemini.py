import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

print("Starting Gemini API test...", flush=True)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Gemini API key not found!")

print("API key loaded successfully.", flush=True)

client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(
        timeout=120000
    )
)


def test_gemini():

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    for attempt in range(1, 4):

        try:
            print(
                f"\nAttempt {attempt}/3 using {model_name}...",
                flush=True
            )

            response = client.models.generate_content(
                model=model_name,
                contents="Explain NLP in three simple sentences.",
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=128
                )
            )

            if not response.text:
                raise ValueError("Empty response from Gemini.")

            print("\n================================")
            print("GEMINI API CONNECTION SUCCESSFUL")
            print("================================")

            print(response.text)

            return

        except Exception as error:

            print(f"\nAttempt {attempt} failed:")
            print(error)

            if attempt < 3:
                wait_time = 5 * (2 ** (attempt - 1))

                print(
                    f"Retrying after {wait_time} seconds..."
                )

                time.sleep(wait_time)

    print("\nAll attempts failed.")
    print("Gemini API is currently unavailable.")


if __name__ == "__main__":
    test_gemini()