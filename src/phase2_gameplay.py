import cv2
import numpy as np
import time
import pydirectinput
from mss import MSS
import pyautogui
import os
import sys

# ==========================================
# ⚙️ การตั้งค่าหลักของ Phase 2
# ==========================================
pydirectinput.PAUSE = 0.0

Y_START = 286
Y_END = 940
X_START = 165
X_END = 1842

AI_WIDTH = 300
AI_HEIGHT = 100

KEY_JUMP = 'f'   
KEY_SLIDE = 'j'   

# ตัวแปรเก็บสมองกล (โหลดแค่ครั้งเดียว)
global_model = None

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_model():
    """โหลดโมเดล AI เฉพาะตอนที่เรียกใช้ (ประหยัด VRAM ถ้ารันโหมด AFK)"""
    global global_model
    if global_model is None:
        import tensorflow as tf # โหลด TF ตอนนี้เลย
        print("📦 กำลังโหลดสมองกล V2 'bot_brain_v2.h5' (โหลดเข้า GPU ครั้งเดียว)...")
        model_path = resource_path('models/bot_brain_v2.h5')
        global_model = tf.keras.models.load_model(model_path)
        print("✅ โหลดสมองกลสำเร็จ!")
    return global_model

# ==========================================
# 🎁 ระบบรันโหมด AFK (ยืนนิ่งๆ รอกล่อง)
# ==========================================
def run_afk_mode():
    print("💤 [AFK MODE] ปล่อยตัวละครวิ่งอัตโนมัติ รอจนกว่าจะเจอกล่อง (1 Box)...")
    # เคลียร์ปุ่มค้างก่อนเริ่ม
    pydirectinput.keyUp(KEY_JUMP)
    pydirectinput.keyUp(KEY_SLIDE)
    
    # รูปไอคอนกล่องที่ต้องการหา (นำไปใส่ไว้ใน assets/ui/ ด้วยนะครับ)
    box_icon_path = resource_path('assets/ui/box_icon.png') 
    relay_btn_path = resource_path('assets/ui/relay_btn.png')

    frame_count = 0
    while True:
        # โหมด AFK ไม่ต้องแคปจอถี่มาก ใช้วิธีหน่วง 0.5 วิ ช่วยประหยัด CPU ได้มหาศาล
        time.sleep(0.5) 
        frame_count += 1
        
        # 1. เช็คว่าเจอกล่องหรือยัง
        try:
            if pyautogui.locateOnScreen(box_icon_path, confidence=0.75):
                print("🎁 [AFK] เจอกล่องแล้วเป้าหมายบรรลุ! หยุดการรอคอย...")
                print("="*50)
                print("🏁 จบการทำงาน Phase 2 ส่งไม้ต่อให้ Phase 3 (แบบออกเกมทันที)")
                print("="*50)
                return "BOX_FOUND"
        except pyautogui.ImageNotFoundException:
            pass

        # 2. เช็คว่าตายก่อนเจอกล่องหรือเปล่า (กันบั๊กวิ่งชนตายก่อนกล่องมา)
        # ตรวจสอบปุ่ม Relay ทุกๆ 2 วินาที (frame_count % 4)
        if frame_count % 4 == 0: 
            try:
                if pyautogui.locateOnScreen(relay_btn_path, confidence=0.8):
                    print("💀 [AFK] ตัวละครหมดแรง/ตายก่อนที่จะเจอกล่อง...")
                    return "DIED"
            except pyautogui.ImageNotFoundException:
                pass

# ==========================================
# 🧠 ระบบรันโหมด AI (บังคับด้วย CNN)
# ==========================================
def run_ai_mode():
    model = get_model()
    print("🧠 [AI MODE] บอทวิ่งรับช่วงต่อแล้ว! ลุยเต็มกำลัง...")
    
    from collections import deque
    current_action_state = -1  
    frame_buffer = deque(maxlen=3)
    frame_count = 0 
    
    relay_btn_path = resource_path('assets/ui/relay_btn.png')

    with MSS() as sct:
        monitor = sct.monitors[1]
        
        while True:
            start_time = time.time()
            
            # เช็คตัวแตก
            if frame_count % 20 == 0:
                try:
                    if pyautogui.locateOnScreen(relay_btn_path, confidence=0.8):
                        print("\n💀 ตรวจพบว่าตัวละครหมดแรง/ตายแล้ว! หยุดการบังคับ...")
                        pydirectinput.keyUp(KEY_JUMP)
                        pydirectinput.keyUp(KEY_SLIDE)
                        print("="*50)
                        print("🏁 จบการทำงาน Phase 2 ส่งไม้ต่อให้ Phase 3")
                        print("="*50)
                        return "DIED"
                except pyautogui.ImageNotFoundException:
                    pass 
                    
            frame_count += 1
            
            screenshot = np.array(sct.grab(monitor))
            gray_screen = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
            
            roi_screen = gray_screen[Y_START:Y_END, X_START:X_END]
            final_ai_vision = cv2.resize(roi_screen, (AI_WIDTH, AI_HEIGHT))
            
            frame_buffer.append(final_ai_vision)
            
            # เมื่อเก็บเฟรมครบ 3 เฟรม ให้ส่งเข้า AI
            if len(frame_buffer) == 3:
                stacked_frames = np.stack(frame_buffer, axis=-1)
                input_frame = stacked_frames.reshape(1, AI_HEIGHT, AI_WIDTH, 3) / 255.0
                
                prediction = model(input_frame, training=False)[0].numpy()
                action_idx = np.argmax(prediction)
                
                if action_idx != current_action_state:
                    if action_idx == 0:  
                        pydirectinput.keyUp(KEY_SLIDE)  
                        pydirectinput.keyDown(KEY_JUMP) 
                    elif action_idx == 1: 
                        pydirectinput.keyUp(KEY_JUMP)
                        pydirectinput.keyDown(KEY_SLIDE)
                    else:                
                        pydirectinput.keyUp(KEY_JUMP)
                        pydirectinput.keyUp(KEY_SLIDE)
                        
                    current_action_state = action_idx
            
            # ควบคุม Framerate ให้คงที่
            elapsed = time.time() - start_time
            time.sleep(max(0.001, 0.033 - elapsed))

# ==========================================
# 🚀 ฟังก์ชันหลัก Phase 2 (รับ config จาก main)
# ==========================================
def run_phase_2(config):
    mode = config.get('mode', 'AI')
    print("="*50)
    print(f"🤖 [PHASE 2] เริ่มการทำงานด้วยโหมด: {mode}")
    print("="*50)

    # ส่งกลับสถานะ ("BOX_FOUND" หรือ "DIED") เพื่อให้ Phase 3 ตัดสินใจต่อ
    if mode == "AFK 1 Box":
        return run_afk_mode()
    else:
        return run_ai_mode()

if __name__ == "__main__":
    print("ทดสอบรัน Phase 2 แบบเดี่ยวๆ บอทจะเริ่มใน 3 วิ...")
    time.sleep(3)
    # จำลอง Config
    run_phase_2({"mode": "AI"})