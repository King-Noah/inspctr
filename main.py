import argparse
import base64
import fitz  # PyMuPDF
import os
import re
import uvicorn

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from rapidfuzz import fuzz
from openai import OpenAI
from PIL import Image

from prompts import get_prompt, SYSTEM_NAME_MAPPING

# Show key sanity check
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError("OPENAI_API_KEY not found in environment variables.")
print(f"🔐 Using OpenAI API Key: {api_key[:8]}...")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)
app = FastAPI()

# 🧠 Load SOP PDF into memory once
SOP_PDF_PATH = "SOP.pdf"  # Change this if your file name differs
if not os.path.exists(SOP_PDF_PATH):
    raise FileNotFoundError("SOP PDF not found. Please place 'SOP.pdf' in the root folder.")

def extract_sop_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

SOP_TEXT = extract_sop_text(SOP_PDF_PATH)

def get_descriptions_from_input(system_types):
    descs = []
    for s in system_types:
        if s.upper() in SYSTEM_NAME_MAPPING:
            descs.extend(SYSTEM_NAME_MAPPING[s.upper()].values())
        elif s.lower() in SYSTEM_NAME_MAPPING:
            descs.append(SYSTEM_NAME_MAPPING[s.lower()])
    return descs

def find_sop_references(analysis_text, sop_text, system_types):
    filter_phrases = []
    for desc in get_descriptions_from_input(system_types):
        parts = re.split(r",|\band\b", desc.lower())
        phrases = [p.strip() for p in parts if len(p.strip()) >= 4]
        filter_phrases.extend(phrases)

    print(f"🎯 Filtering SOP text for system phrases: {filter_phrases}")

    filtered_sop = "\n".join(
        line for line in sop_text.splitlines()
        if any(phrase in line.lower() for phrase in filter_phrases)
    )

    print(f"📁 Filtered SOP text contains {len(filtered_sop.splitlines())} lines.")
    sop_matches = re.findall(r"(?:§)?535\.\d+(?:\([a-zA-Z0-9]+\))*", filtered_sop)

    print(f"📄 Extracted {len(sop_matches)} SOP sections after filtering.")

    titles = re.findall(r"### Deficiency \d+: (.+)", analysis_text)
    relevant_refs = set()

    for title in titles:
        print(f"\n🔍 Searching for SOP matches related to full title: '{title}'")
        title_lower = title.lower()

        for match in sop_matches:
            match_lower = match.lower()
            if title_lower in match_lower:
                print(f"    ✅ Direct match found: '{match.strip()}'")
                relevant_refs.add(match.strip())
                continue

            similarity = fuzz.partial_ratio(title_lower, match_lower)
            if similarity > 80:
                print(f"    🤏 Fuzzy match ({similarity}) found: '{match.strip()}'")
                relevant_refs.add(match.strip())

    print(f"\n📚 Total SOP references matched: {len(relevant_refs)}")
    return sorted(relevant_refs)

# File conversion
def ensure_supported_format(image_path):
    supported_extensions = [".jpg", ".jpeg", ".png"]
    ext = os.path.splitext(image_path)[1].lower()

    if ext in supported_extensions:
        return image_path, False

    converted_path = os.path.splitext(image_path)[0] + "_converted.jpg"
    with Image.open(image_path) as img:
        img.convert("RGB").save(converted_path, "JPEG")
    return converted_path, True

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def validate_key_vision():
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": "Describe this image"},
                    {"type": "image_url", "image_url": {"url": "https://i.imgur.com/ZcLLrkY.jpg", "detail": "low"}},
                ]}
            ],
            max_tokens=20
        )
        return "image" in response.choices[0].message.content.lower()
    except Exception as e:
        print(f"❌ Vision access test failed: {e}")
        return False

# 🔍 Analyze with GPT and search SOP
def analyze_image_base64(base64_image, system_types=["GENERAL"]):
    prompt_text = get_prompt(system_types)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a licensed home inspector and must strictly follow the Texas Real Estate Commission "
                        "(TREC) Standards of Practice. Your responses must be formatted using the following structure:\n\n"
                        "### Deficiency {{number}}: {{Concise Title}}\n"
                        "- **Description:** {{Explanation of the deficiency and why it matters}}\n"
                        "- **Severity:** {{Cosmetic | Functional | Safety Concern | Major Structural}}\n"
                        "- **Recommended Action:** {{Advice for the client}}\n"
                        "- **TREC SOP Reference:** {{e.g., 535.228(d)(1)(B)}}\n\n"
                        "Use only this format. If no deficiencies are observed, respond with:\n"
                        "**No visible deficiencies found based on the image provided.**"
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        }},
                    ]
                }
            ],
        )

        content = response.choices[0].message.content
        if "unable to view" in content.lower():
            return "⚠️ GPT-4o responded it cannot view the image. Check your API key's vision access."

        sop_refs = find_sop_references(content, SOP_TEXT, system_types)

        if sop_refs:
            content += "\n\n📚 **SOP Code References:**\n" + "\n".join(f"- {ref}" for ref in sop_refs)
        else:
            content += "\n\n📚 **NO SOP Code References**\n"
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
    parser.add_argument("--system", type=str, nargs="+", default=["GENERAL"], help="System types to analyze (e.g., --system hvac foundation plumbing)")

    args = parser.parse_args()

    if args.serve:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        print("🦚 Validating API key for vision access...")
        if validate_key_vision():
            print("✅ Vision API access confirmed.")
        else:
            print("⚠️ Vision access NOT confirmed. GPT-4o may not be able to see images.")

        safe_path, was_converted = ensure_supported_format(args.image_path)
        base64_image = encode_image(safe_path)
        result = analyze_image_base64(base64_image, args.system)
        print(result)

        if was_converted and os.path.exists(safe_path):
            os.remove(safe_path)
