import base64
import argparse
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import uvicorn
from openai import OpenAI
from PIL import Image
import os

from prompts import get_prompt_for_system

# Show key sanity check
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError("OPENAI_API_KEY not found in environment variables.")
print(f"🔐 Using OpenAI API Key: {api_key[:8]}...")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# FastAPI app
app = FastAPI()

# file format check
def ensure_supported_format(image_path):
    supported_extensions = [".jpg", ".jpeg", ".png"]
    ext = os.path.splitext(image_path)[1].lower()

    if ext in supported_extensions:
        return image_path, False  # No conversion needed

    converted_path = os.path.splitext(image_path)[0] + "_converted.jpg"
    with Image.open(image_path) as img:
        img.convert("RGB").save(converted_path, "JPEG")
    return converted_path, True

# Base64 encoding helper
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Vision test to validate key
def validate_key_vision():
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "https://i.imgur.com/ZcLLrkY.jpg",
                                "detail": "low",
                            },
                        },
                    ],
                }
            ],
            max_tokens=20
        )
        return "image" in response.choices[0].message.content.lower()
    except Exception as e:
        print(f"❌ Vision access test failed: {e}")
        return False

# Main image analysis
def analyze_image_base64(base64_image, system_type="general"):
    prompt_text = get_prompt_for_system(system_type)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                                "detail": "high"
                            },
                        },
                    ],
                }
            ],
        )
        content = response.choices[0].message.content
        if "unable to view" in content.lower():
            return "⚠️ GPT-4o responded it cannot view the image. Check your API key's vision access."
        return content
    except Exception as e:
        return f"❌ Error analyzing image: {e}"

@app.post("/analyze")
async def analyze_endpoint(file: UploadFile = File(...)):
    image_bytes = await file.read()
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    result = analyze_image_base64(base64_image)
    return JSONResponse(content={"analysis": result})

# CLI mode
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze home inspection image")
    parser.add_argument("image_path", help="Path to the image file")
    parser.add_argument("--serve", action="store_true", help="Run as API server")
    parser.add_argument(
        "--system",
        type=str,
        default="general",
        help="Type of structural system to analyze (e.g., roofing, hvac, electrical, plumbing, foundation)"
    )

    args = parser.parse_args()

    if args.serve:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        print("🧪 Validating API key for vision access...")
        if validate_key_vision():
            print("✅ Vision API access confirmed.")
        else:
            print("⚠️ Vision access NOT confirmed. GPT-4o may not be able to see images.")

        # Ensure image is in a supported format and note if conversion was done
        safe_path, was_converted = ensure_supported_format(args.image_path)

        base64_image = encode_image(safe_path)
        result = analyze_image_base64(base64_image)
        print(result)

        # Delete temporary converted file if created
        if was_converted and os.path.exists(safe_path):
            os.remove(safe_path)
