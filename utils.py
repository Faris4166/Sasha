import base64, io

def image_to_bytes(pil_image):
    """
    แปลง PIL Image object ให้เป็น bytes buffer สำหรับส่งไปยัง Gemini API โดยตรง
    """
    buf = io.BytesIO()
    pil_image.save(buf, format="JPEG")
    return buf.getvalue()