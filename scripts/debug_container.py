import sys
import os

print("--- System Info ---")
print(f"Python: {sys.version}")

try:
    from google import genai
    import google.genai
    print(f"google-genai imported successfully.")
    # Try to get version
    try:
        from importlib.metadata import version
        print(f"google-genai version: {version('google-genai')}")
    except:
        print("Could not retrieve version.")
except ImportError as e:
    print(f"FAILED to import google-genai: {e}")
    sys.exit(1)

KEY = "AIzaSyAGbYPKbY_5kwQ3ew-b9rARIUcroybjyQQ"
MODEL = "gemini-2.5-flash"

print(f"\n--- Testing Gemini API inside Container ---")
print(f"Key: {KEY[:5]}...")
print(f"Model: {MODEL}")

try:
    client = genai.Client(api_key=KEY)
    print("Client initialized.")
    
    response = client.models.generate_content(
        model=MODEL,
        contents="Hello from Docker Container"
    )
    print(f"✅ SUCCESS! Response: {response.text}")
except Exception as e:
    print(f"❌ FAILURE!")
    print(f"Type: {type(e).__name__}")
    print(f"Error: {e}")
    # Print detailed attributes if available
    if hasattr(e, 'status_code'):
        print(f"Status Code: {e.status_code}")
    if hasattr(e, 'details'):
        print(f"Details: {e.details}")
