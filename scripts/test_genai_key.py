import asyncio
import os
try:
    from google import genai
except ImportError:
    print("google-genai not installed. Installing...")
    import subprocess
    subprocess.check_call(["pip", "install", "google-genai"])
    from google import genai

KEY = "AIzaSyAGbYPKbY_5kwQ3ew-b9rARIUcroybjyQQ"

async def test_model(model_name):
    print(f"\n--- Testing Model: {model_name} ---")
    try:
        client = genai.Client(api_key=KEY)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model_name,
            contents='Hello, strictly answer "OK" if you see this.'
        )
        print(f"✅ Success! Response: {response.text}")
    except Exception as e:
        print(f"❌ Failed to call {model_name}")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {e}")

async def main():
    print(f"Testing API Key: {KEY[:10]}******")
    
    # Test 1: gemini-2.5-flash (User requested)
    await test_model('gemini-2.5-flash')

    # Test 2: gemini-1.5-flash (Stable)
    await test_model('gemini-1.5-flash')

if __name__ == "__main__":
    asyncio.run(main())
