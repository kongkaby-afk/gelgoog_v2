import pyautogui
import time
import os
import random  # <--- 1. เพิ่มบรรทัดนี้ด้านบนสุด

CONFIDENCE = 0.8 

def get_asset_path(filename):
    """หาตำแหน่งโฟลเดอร์ assets อัตโนมัติ"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'assets', filename)

def click_image(image_name, timeout=10, delay_after=0.5):
    """ฟังก์ชันคลิกรูปภาพอัจฉริยะ (เรียกใช้ได้จากทุกที่)"""
    actual_path = get_asset_path(image_name)
    
    start_time = time.time()
    if not os.path.exists(actual_path):
        print(f"❌ ERROR: ไม่พบไฟล์รูปภาพที่ {actual_path}")
        return False
        
    while time.time() - start_time < timeout:
        try:
            location = pyautogui.locateCenterOnScreen(actual_path, confidence=CONFIDENCE)
            if location is not None:
                # 🎲 สุ่มพฤติกรรมการตอบสนองแบบไม่มีแพทเทิร์น
                chance = random.randint(1, 100)
                if chance <= 20:
                    move_duration = random.uniform(0.15, 0.3)
                elif chance <= 80:
                    move_duration = random.uniform(0.4, 0.8)
                else:
                    move_duration = random.uniform(0.85, 1.2)

                pyautogui.moveTo(location.x, location.y, duration=move_duration)
                pyautogui.click()
                print(f"✅ คลิก {image_name} สำเร็จ!")
                time.sleep(delay_after)
                return True
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.3)
    
    print(f"❌ หมดเวลา! หา {image_name} ไม่เจอ")
    return False