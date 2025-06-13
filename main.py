import base64
import argparse
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import uvicorn
from openai import OpenAI

client = OpenAI()
app = FastAPI()

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def analyze_image_base64(base64_image):
    prompt_text = """
        Analyze the following image and identify any visible deficiencies that would be reportable in a home inspection report. For each deficiency found, provide:

        - A short title
        - A description of the issue
        - The relevant TREC SOP reference if known
        - The severity (e.g. cosmetic, functional, safety concern)
        - Recommended action for the client

        Be specific and use inspection terminology.
    """

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
    return response.choices[0].message.content

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
    args = parser.parse_args()

    if args.serve:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        base64_image = encode_image(args.image_path)
        result = analyze_image_base64(base64_image)
        print(result)
