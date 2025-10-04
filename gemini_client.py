from google import genai
from google.genai.types import Part
import json

def analyze_image_with_gemini(api_key, image_bytes):
    """
    วิเคราะห์รูปภาพอาหารด้วย Gemini API โดยใช้ image_bytes
    """
    client = genai.Client(api_key=api_key)
    model = "gemini-2.5-flash"

    prompt = (
        "Analyze the food image and return ONLY a JSON object with keys: "
        "calories_kcal, protein_g, fat_g, carbs_g, fiber_g, estimated_portion, confidence. "
        "Ensure the output is valid JSON."
    )

    image_part = Part.from_bytes(
        data=image_bytes,
        mime_type='image/jpeg'
    )

    response = client.models.generate_content(
        model=model,
        contents=[image_part, prompt]
    )

    raw = getattr(response, "text", str(response))

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        json_string = raw[start:end]
        if not json_string:
             raise ValueError("ไม่พบโครงสร้าง JSON ในการตอบกลับของ Gemini")
        return json.loads(json_string)
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการแยก JSON: {e}")
        print(f"การตอบกลับดิบ: {raw}")
        raise