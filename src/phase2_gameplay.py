import cv2
import numpy as np
import time
import pydirectinput
from mss import MSS
import tensorflow as tf
from collections import deque
import pyautogui

pydirectinput.PAUSE = 0.0

Y_START = 286
Y_END = 940
X_START = 165
X_END = 1842

AI_WIDTH = 300
AI_HEIGHT = 100

KEY_JUMP = 'f'   
KEY_SLIDE = 'j'   

print("📦 กำลังโหลดสมองกล V2 'bot_brain_v2.h5'...")
model = tf.keras.models.load_model('models/bot_brain_v2.h5')
print("✅ โหลดสมองกลสำเร็จ!")

def run_phase_2():
    print("="*50)
    print("🤖 [PHASE 2] บอทวิ่งรับช่วงต่อแล้ว! ลุยเต็มกำลัง...")
    print("="*50)

    current_action_state = -1  
    frame_buffer = deque(maxlen=3)
    frame_count = 0 

    with MSS() as sct:
        # ใช้ monitors[1] ตามโค้ดต้นฉบับของคุณ
        monitor = sct.monitors[1]
        
        while True:
            start_time = time.time()
            
            # 💡 เช็คว่าตายหรือยังทุกๆ 20 เฟรม (ลดภาระ CPU)
            if frame_count % 20 == 0:
                try:
                    # ถ้าเจอปุ่ม Relay ถือว่าเกมจบรอบแล้ว ให้ตัดจบ Phase 2 
                    if pyautogui.locateOnScreen('assets/relay_btn.png', confidence=0.8):
                        print("\n💀 ตรวจพบว่าตัวละครหมดแรง/ตายแล้ว! หยุดการบังคับ...")
                        pydirectinput.keyUp(KEY_JUMP)
                        pydirectinput.keyUp(KEY_SLIDE)
                        print("="*50)
                        print("🏁 จบการทำงาน Phase 2 ส่งไม้ต่อให้ Phase 3")
                        print("="*50)
                        return True
                except pyautogui.ImageNotFoundException:
                    pass 
                    
            frame_count += 1
            
            # 📸 1. ดักจับภาพหน้าจอปัจจุบัน
            screenshot = np.array(sct.grab(monitor))
            gray_screen = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
            
            # ครอบพิกัดภาพ (Crop ROI) ตามที่คุณตั้งไว้
            roi_screen = gray_screen[Y_START:Y_END, X_START:X_END]
            final_ai_vision = cv2.resize(roi_screen, (AI_WIDTH, AI_HEIGHT))
            
            # โยนภาพปัจจุบันเข้าไปใน Buffer ความจำ
            frame_buffer.append(final_ai_vision)
            
            # 🔮 2. ถ้าสะสมภาพครบ 3 เฟรมแล้ว ค่อยให้ AI ทำนาย
            if len(frame_buffer) == 3:
                stacked_frames = np.stack(frame_buffer, axis=-1)
                input_frame = stacked_frames.reshape(1, AI_HEIGHT, AI_WIDTH, 3) / 255.0
                
                prediction = model(input_frame, training=False)[0].numpy()
                action_idx = np.argmax(prediction)
                confidence = prediction[action_idx] * 100
                
                # 🕹️ 3. สั่งการคีย์บอร์ด
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
            
            # ⏱️ ระบบหน่วงเวลา FPS ตามโค้ดต้นฉบับ
            elapsed = time.time() - start_time
            time.sleep(max(0.001, 0.033 - elapsed))

if __name__ == "__main__":
    print("ทดสอบรัน Phase 2 แบบเดี่ยวๆ บอทจะเริ่มใน 3 วิ...")
    time.sleep(3)
    run_phase_2()