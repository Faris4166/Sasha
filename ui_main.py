import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from gemini_client import analyze_image_with_gemini
from utils import image_to_bytes # ใช้ image_to_bytes ตามที่แก้ไขก่อนหน้า
import traceback

class SashaApp:
    def __init__(self, root):
        self.root = root
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        root.title("Sasha - Food Nutrition Scanner")
        root.geometry("800x520")

        self.api_key = None
        self.image_pil = None
        self.image_tk = None

        self.ask_api_key()

        # layout
        self.frame_left = ctk.CTkFrame(root, width=250)
        self.frame_left.pack(side="left", fill="y", padx=12, pady=12)

        self.frame_right = ctk.CTkFrame(root)
        self.frame_right.pack(side="right", expand=True, fill="both", padx=12, pady=12)

        # Left controls
        self.btn_select = ctk.CTkButton(self.frame_left, text="เลือกภาพอาหาร", command=self.select_image)
        self.btn_select.pack(fill="x", pady=6)

        self.btn_analyze = ctk.CTkButton(self.frame_left, text="วิเคราะห์", command=self.analyze)
        self.btn_analyze.pack(fill="x", pady=6)

        # ***แก้ไขที่ 1: เปลี่ยนสีปุ่มล้างข้อมูลให้เข้มขึ้นเพื่อ Contrast ที่ดีขึ้น***
        self.btn_clear = ctk.CTkButton(self.frame_left, text="ล้างข้อมูล", fg_color="#3A4047", command=self.clear_all) 
        self.btn_clear.pack(fill="x", pady=6)

        self.text_output = ctk.CTkTextbox(self.frame_left, height=350, state="disabled")
        self.text_output.pack(fill="both", expand=True, pady=(10,0))

        # Right: image preview
        self.label_preview = ctk.CTkLabel(self.frame_right, text="Preview", anchor="w")
        self.label_preview.pack(fill="x")

        self.canvas = ctk.CTkCanvas(self.frame_right, width=500, height=300, bg="#f5f5f5", highlightthickness=0)
        self.canvas.pack(pady=(6,10))

        # Right: nutrition frame
        self.nutrition_frame = ctk.CTkFrame(self.frame_right)
        self.nutrition_frame.pack(fill="both", expand=True, pady=6)

    def ask_api_key(self):
        win = ctk.CTkInputDialog(text="ใส่ Gemini API Key (จะไม่เก็บไว้):", title="API Key")
        self.api_key = win.get_input()
        if not self.api_key:
            self.root.destroy()

    def select_image(self):
        file = filedialog.askopenfilename(filetypes=[("Images","*.png;*.jpg;*.jpeg")])
        if not file: return
        img = Image.open(file).convert("RGB")
        img.thumbnail((500,300))
        self.image_pil = img
        self.image_tk = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(250,150,image=self.image_tk)
        self.log(f"เลือกภาพ: {file}")

    def analyze(self):
        if not self.api_key or not self.image_pil:
            messagebox.showwarning("ขาดข้อมูล", "กรุณาใส่ API Key และเลือกรูปภาพก่อน")
            return
        try:
            img_bytes = image_to_bytes(self.image_pil)
            data = analyze_image_with_gemini(self.api_key, img_bytes)
            self.display_nutrition(data)
        except Exception as e:
            self.log("เกิดข้อผิดพลาด: " + str(e))
            traceback.print_exc()

    def display_nutrition(self, data: dict):
        # ล้างค่าเดิม
        for widget in self.nutrition_frame.winfo_children():
            widget.destroy()

        # ฟังก์ชันช่วยแปลงค่าเป็น float
        def safe_float(val):
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0

        # ฟังก์ชันแปลงความมั่นใจเป็นข้อความ
        def conf_text(val):
            val = safe_float(val)
            if val >= 0.8: return "สูง ✅"
            elif val >= 0.5: return "กลาง ⚠️"
            else: return "ต่ำ ❌"

        # ตรวจสอบค่าที่จะโชว์
        calories = safe_float(data.get('calories_kcal', 0))
        protein = safe_float(data.get('protein_g', 0))
        fat = safe_float(data.get('fat_g', 0))
        carbs = safe_float(data.get('carbs_g', 0))
        fiber = safe_float(data.get('fiber_g', 0))
        portion = data.get('estimated_portion', 'N/A')
        confidence = conf_text(data.get('confidence', 0))

        items = [
            ("พลังงาน", f"{calories} kcal 🍴"),
            ("โปรตีน", f"{protein} g 🥩"),
            ("ไขมัน", f"{fat} g 🥑"),
            ("คาร์โบไฮเดรต", f"{carbs} g 🌾"),
            ("ใยอาหาร", f"{fiber} g 🌿"),
            ("ขนาดประมาณ", f"{portion}"),
            ("ความมั่นใจ", confidence)
        ]

        # สร้าง Card สวย ๆ
        for label, value in items:
            # ***แก้ไขที่ 2: เปลี่ยนสีพื้นหลังของการ์ดให้เข้มขึ้นเพื่อ Contrast ที่ดีขึ้น***
            card = ctk.CTkFrame(self.nutrition_frame, corner_radius=12, fg_color="#404040") 
            card.pack(fill="x", pady=4, padx=6)
            # ***แก้ไขที่ 3: กำหนด text_color เป็นสีขาวเพื่อให้ชัดเจนบนพื้นหลังเข้ม***
            lbl = ctk.CTkLabel(card, text=f"{label}: {value}", anchor="w", font=ctk.CTkFont(size=14), text_color="#FFFFFF") 
            lbl.pack(padx=12, pady=6)

    def clear_all(self):
        self.canvas.delete("all")
        self.image_pil = None
        for widget in self.nutrition_frame.winfo_children():
            widget.destroy()
        self.text_output.configure(state="normal")
        self.text_output.delete("0.0","end")
        self.text_output.configure(state="disabled")
        self.log("ล้างข้อมูลเรียบร้อย")

    def log(self, text):
        self.text_output.configure(state="normal")
        self.text_output.insert("end", text + "\n")
        self.text_output.configure(state="disabled")
        self.text_output.see("end")