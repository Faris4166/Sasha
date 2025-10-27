import customtkinter as ctk
import os
import requests
from io import BytesIO
from google import genai
from PIL import Image
from tkinter import filedialog, messagebox
import pyttsx3 
import threading 
import re 

# --- Global Variables ---
GEMINI_API_KEY = None 
MODEL_NAME = "gemini-2.5-flash"

# --- Text-to-Speech Engine Initialization ---
tts_engine = None
try:
    # การเริ่มต้น TTS Engine 
    tts_engine = pyttsx3.init()
    voices = tts_engine.getProperty('voices')
    
    # พิมพ์รายชื่อเสียงทั้งหมดที่ระบบรองรับออกมาในคอนโซล (PowerShell)
    print("--------------------------------------------------")
    print("รายชื่อเสียง TTS ที่พบในระบบของคุณ:")
    
    thai_voice_id = None
    for i, voice in enumerate(voices):
        # พิมพ์รายละเอียดเสียงทั้งหมดเพื่อช่วยในการแก้ไขปัญหา
        print(f"[{i}] ID: {voice.id[:50]}..., Name: {voice.name[:50]}..., Lang: {voice.languages}")
        
        # พยายามค้นหาเสียงภาษาไทย
        if 'th' in voice.id.lower() or 'thai' in voice.name.lower() or any('th-' in lang.lower() for lang in voice.languages):
            thai_voice_id = voice.id
    
    print("--------------------------------------------------")
    
    if thai_voice_id:
        tts_engine.setProperty('voice', thai_voice_id)
        print(f"**ตั้งค่าเสียงภาษาไทยสำเร็จ!** ID ที่เลือก: {thai_voice_id[:30]}...")
    elif voices:
        # ถ้าไม่พบภาษาไทย ให้ใช้เสียงเริ่มต้นที่พบ
        tts_engine.setProperty('voice', voices[0].id)
        print("**ไม่พบเสียงภาษาไทย ใช้เสียงเริ่มต้นแทน** (โปรดติดตั้งชุดภาษาไทยในระบบปฏิบัติการ)")
        
except Exception as e:
    print(f"ข้อผิดพลาดในการเริ่มต้น Text-to-Speech Engine: {e}")


# --- Helper Functions for Threading ---

def clean_analysis_text(text):
    """ลบอักขระพิเศษและทำความสะอาดข้อความ"""
    # ลบสัญลักษณ์ Markdown ที่ใช้จัดรูปแบบ (เช่น ###, ---, *, และเครื่องหมายอื่นๆ)
    text = re.sub(r'#+\s*|--+|\*{1,2}|@+|^\s*[-*]\s*', '', text, flags=re.MULTILINE)
    text = text.strip()
    return text

def start_tts_thread(text_to_read):
    """ฟังก์ชันสำหรับอ่านออกเสียงในเธรดแยก"""
    try:
        if tts_engine and tts_engine.isBusy():
            tts_engine.stop()
        
        clean_text = clean_analysis_text(text_to_read)
        
        tts_engine.say(clean_text)
        tts_engine.runAndWait() 
    except Exception as e:
        print(f"เกิดข้อผิดพลาดใน TTS Thread: {e}")

def start_analyze_thread(image, prompt):
    """ฟังก์ชันสำหรับการเรียกใช้ Gemini API ในเธรดแยก"""
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[image, prompt]
        )
        
        cleaned_response_text = clean_analysis_text(response.text)
        
        app.after(0, lambda: display_analysis_result(cleaned_response_text)) 

    except Exception as e:
        app.after(0, lambda: display_analysis_error(f"ข้อผิดพลาดจาก Gemini API: {e}"))
        
    finally:
        app.after(0, lambda: analyze_button.configure(state="normal"))

def display_analysis_result(text):
    """แสดงผลลัพธ์บนกล่องข้อความในเธรดหลัก"""
    result_textbox.delete("1.0", ctk.END)
    result_textbox.insert(ctk.END, text)

def display_analysis_error(error_message):
    """แสดงข้อผิดพลาดบนกล่องข้อความในเธรดหลัก"""
    result_textbox.delete("1.0", ctk.END)
    result_textbox.insert(ctk.END, error_message + "\n\nตรวจสอบว่า: 1. API Key ถูกต้อง 2. การเชื่อมต่ออินเทอร์เน็ตเสถียร")


# --- Main Logic Functions ---

def set_api_key():
    """ตั้งค่า API Key จากช่องป้อนข้อมูล (ไม่บันทึก)"""
    global GEMINI_API_KEY
    key = api_key_entry.get().strip()
    if key:
        GEMINI_API_KEY = key
        status_label.configure(text="สถานะ: API Key ตั้งค่าเรียบร้อยแล้ว", text_color="green")
        api_key_entry.delete(0, ctk.END)
        analyze_button.configure(state="normal")
    else:
        status_label.configure(text="สถานะ: กรุณาป้อน API Key", text_color="red")
        messagebox.showerror("ข้อผิดพลาด", "กรุณาป้อน Gemini API Key เพื่อใช้งาน")
        analyze_button.configure(state="disabled")

def clear_last_search():
    """ล้างช่องป้อนรูปภาพและผลลัพธ์ แต่คง API Key ไว้"""
    url_entry.delete(0, ctk.END)
    image_path_label.configure(text="ไม่มีไฟล์ที่เลือก")
    result_textbox.delete("1.0", ctk.END)
    result_textbox.insert(ctk.END, "ผลการวิเคราะห์จะแสดงที่นี่...")
    
    global tts_engine
    if tts_engine and tts_engine.isBusy():
        tts_engine.stop()
        
    messagebox.showinfo("ล้างข้อมูล", "ล้างข้อมูลรูปภาพและผลลัพธ์เรียบร้อยแล้ว (API Key ยังคงอยู่)")


def read_analysis():
    """เริ่มเธรดสำหรับอ่านข้อความออกเสียง"""
    global tts_engine
    
    if not tts_engine:
        messagebox.showerror("ข้อผิดพลาด", "ไม่สามารถใช้งานฟังก์ชัน Text-to-Speech ได้ โปรดตรวจสอบการติดตั้ง pyttsx3")
        return

    text_to_read = result_textbox.get("1.0", ctk.END).strip()
    
    if not text_to_read or text_to_read == "ผลการวิเคราะห์จะแสดงที่นี่...":
        messagebox.showwarning("คำเตือน", "ไม่มีข้อความสำหรับอ่านออกเสียง")
        return
    
    tts_thread = threading.Thread(target=start_tts_thread, args=(text_to_read,), daemon=True)
    tts_thread.start()


def analyze_food():
    """เตรียมข้อมูลและเริ่มเธรดสำหรับวิเคราะห์อาหาร"""
    result_textbox.delete("1.0", ctk.END)

    if not GEMINI_API_KEY:
        result_textbox.insert(ctk.END, "ข้อผิดพลาด: กรุณาตั้งค่า Gemini API Key ก่อนใช้งาน")
        return

    # 1. เตรียมรูปภาพ
    image = None
    image_source = url_entry.get().strip()
    image_filepath = image_path_label.cget("text")

    if image_source.startswith("http"):
        # ดาวน์โหลดจาก URL
        result_textbox.insert(ctk.END, "กำลังดาวน์โหลดรูปภาพจาก URL...\n")
        app.update() 
        try:
            response = requests.get(image_source, timeout=15)
            response.raise_for_status() 
            image = Image.open(BytesIO(response.content))
        except Exception as e:
            result_textbox.insert(ctk.END, f"ข้อผิดพลาดในการดาวน์โหลดรูปภาพ: {e}")
            return
    elif image_filepath and image_filepath != "ไม่มีไฟล์ที่เลือก":
        # โหลดจากไฟล์ที่เลือก
        try:
            image = Image.open(image_filepath)
        except Exception as e:
            result_textbox.insert(ctk.END, f"ข้อผิดพลาดในการเปิดไฟล์: {e}")
            return
    else:
        result_textbox.insert(ctk.END, "ข้อผิดพลาด: กรุณาป้อน URL หรือเลือกไฟล์รูปภาพเพื่อวิเคราะห์")
        return

    # 2. กำหนด Prompt 
    prompt = """
    โปรดวิเคราะห์อาหารในรูปภาพนี้อย่างละเอียดในภาษาไทย:
    
    1. อาหารคืออะไร: ระบุชื่ออาหารและส่วนประกอบหลักโดยสังเขป
    2. คุณค่าอาหารโดยละเอียด: ให้ข้อมูลโภชนาการ (Nutrition Facts) โดยประมาณ เช่น แคลอรี่, โปรตีน, คาร์โบไฮเดรต, ไขมัน โดยแยกเป็น ไขมันอิ่มตัว และไขมันไม่อิ่มตัว พร้อมทั้งวิตามินและแร่ธาตุสำคัญ
    3. ประโยชน์และข้อดี: อธิบายข้อดีต่อสุขภาพเมื่อบริโภคอาหารชนิดนี้
    4. ข้อเสียและข้อควรระวัง: อธิบายข้อเสีย หรือข้อควรระวังในการบริโภค
    5. คำแนะนำในการบริโภค: ให้คำแนะนำในการบริโภคที่เหมาะสม
    
    ข้อสำคัญ: โปรดใช้การจัดรูปแบบข้อความให้น้อยที่สุดและหลีกเลี่ยงการใช้อักขระพิเศษสำหรับจัดรูปแบบ Markdown เช่น ###, ---, *, ** ในคำตอบ เพื่อให้ง่ายต่อการประมวลผลและการอ่านออกเสียง
    """

    # 3. ล็อกปุ่มและแจ้งสถานะ
    analyze_button.configure(state="disabled")
    result_textbox.insert(ctk.END, "กำลังส่งรูปภาพและวิเคราะห์ด้วย Gemini AI... โปรดรอสักครู่\n")
    app.update() 
    
    # 4. เริ่มเธรดใหม่สำหรับการเรียกใช้ API
    api_thread = threading.Thread(target=start_analyze_thread, args=(image, prompt), daemon=True)
    api_thread.start()


def select_file():
    """เปิดกล่องโต้ตอบให้เลือกไฟล์รูปภาพ"""
    filepath = filedialog.askopenfilename(
        title="เลือกไฟล์รูปภาพอาหาร",
        filetypes=(("Image files", "*.jpg;*.jpeg;*.png;*.webp"), ("All files", "*.*"))
    )
    if filepath:
        image_path_label.configure(text=filepath)
        url_entry.delete(0, ctk.END)
    else:
        image_path_label.configure(text="ไม่มีไฟล์ที่เลือก")
        
# --- GUI Setup ---

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("AI วิเคราะห์อาหารด้วย Gemini API")
app.geometry("800x800")

# --- API Key Section ---
api_frame = ctk.CTkFrame(app)
api_frame.pack(pady=10, padx=20, fill="x")

ctk.CTkLabel(api_frame, text="Gemini API Key:").pack(side=ctk.LEFT, padx=(10, 5), pady=10)
api_key_entry = ctk.CTkEntry(api_frame, width=350, show="*") 
api_key_entry.pack(side=ctk.LEFT, padx=5, pady=10)
set_key_button = ctk.CTkButton(api_frame, text="บึนทึก", command=set_api_key)
set_key_button.pack(side=ctk.LEFT, padx=5, pady=10)
status_label = ctk.CTkLabel(api_frame, text="สถานะ: ยังไม่ได้ตั้งค่า Key", text_color="red")
status_label.pack(side=ctk.LEFT, padx=(20, 10), pady=10)

# --- Input Section ---
input_frame = ctk.CTkFrame(app)
input_frame.pack(pady=10, padx=20, fill="x")

# URL Input
ctk.CTkLabel(input_frame, text="URL รูปภาพ:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
url_entry = ctk.CTkEntry(input_frame, width=400)
url_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

# File Input
ctk.CTkButton(input_frame, text="เลือกไฟล์รูปภาพ", command=select_file).grid(row=1, column=0, padx=10, pady=5, sticky="w")
image_path_label = ctk.CTkLabel(input_frame, text="ไม่มีไฟล์ที่เลือก", fg_color="gray20", width=400)
image_path_label.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

input_frame.grid_columnconfigure(1, weight=1)

# --- Control Buttons ---
control_frame = ctk.CTkFrame(app)
control_frame.pack(pady=5, padx=20, fill="x")

analyze_button = ctk.CTkButton(control_frame, text="วิเคราะห์อาหาร", command=analyze_food, height=40, font=ctk.CTkFont(size=16, weight="bold"), state="disabled")
analyze_button.pack(side=ctk.LEFT, padx=(0, 10), expand=True, fill="x")

clear_button = ctk.CTkButton(control_frame, text="ล้างข้อมูลล่าสุด", command=clear_last_search)
clear_button.pack(side=ctk.LEFT, padx=10, fill="x")

read_button = ctk.CTkButton(control_frame, text="อ่านออกเสียง", command=read_analysis)
read_button.pack(side=ctk.LEFT, padx=(10, 0), fill="x")

# --- Result Section ---
ctk.CTkLabel(app, text="ผลลัพธ์การวิเคราะห์:", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5), padx=20, anchor="w")
result_textbox = ctk.CTkTextbox(app, width=760, height=400, state="normal") 
result_textbox.pack(pady=(0, 20), padx=20, fill="both", expand=True)
result_textbox.insert(ctk.END, "ผลการวิเคราะห์จะแสดงที่นี่...")

# --- Run the application ---
app.mainloop()