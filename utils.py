import pyautogui
import time
import os
import random
import datetime

CONFIDENCE = 0.8 

def get_asset_path(filename):
    """หาตำแหน่งโฟลเดอร์ assets อัตโนมัติ"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'assets', filename)

def click_image(image_name, timeout=10, delay_after=0.5):
    """ฟังก์ชันคลิกรูปภาพอัจฉริยะ (สุ่มจิ้มทั่วบริเวณปุ่มแบบ Bounding Box)"""
    actual_path = get_asset_path(image_name)
    
    start_time = time.time()
    if not os.path.exists(actual_path):
        print(f"❌ ERROR: ไม่พบไฟล์รูปภาพที่ {actual_path}")
        return False
        
    while time.time() - start_time < timeout:
        try:
            # ใช้ locateOnScreen เพื่อดึงกรอบ (Box) ของปุ่มมาใช้งาน
            box = pyautogui.locateOnScreen(actual_path, confidence=CONFIDENCE)
            if box is not None:
                left, top, width, height = box
                
                # 🎯 หดขอบเข้ามา 15% ป้องกันการคลิกโดนขอบมนๆ
                pad_x = int(width * 0.15)
                pad_y = int(height * 0.15)
                
                # 🎲 สุ่มจุดคลิกกระจายไปทั่วทั้งปุ่ม
                target_x = random.randint(left + pad_x, left + width - pad_x)
                target_y = random.randint(top + pad_y, top + height - pad_y)

                # ⏱️ สุ่มเวลาตอบสนอง 20/60/20 แบบมนุษย์
                chance = random.randint(1, 100)
                if chance <= 20:
                    reaction_time = random.uniform(0.15, 0.3)
                elif chance <= 80:
                    reaction_time = random.uniform(0.4, 0.8)
                else:
                    reaction_time = random.uniform(0.85, 1.2)

                pyautogui.moveTo(target_x, target_y, duration=reaction_time, tween=pyautogui.easeOutQuad)
                pyautogui.click()
                print(f"✅ คลิก {image_name} สำเร็จ! (ดีเลย์ {reaction_time:.2f}s, พิกัด: {target_x}, {target_y})")
                time.sleep(delay_after)
                return True
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.3)
    
    print(f"❌ หมดเวลา! หา {image_name} ไม่เจอ")
    return False

def write_log(message, level="INFO"):
    """ระบบบันทึกประวัติการทำงานลงไฟล์ .log"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, 'logs')
    
    # สร้างโฟลเดอร์ logs ถ้ายังไม่มี
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # ชื่อไฟล์แยกตามวัน เช่น bot_2024-05-20.log
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"bot_{date_str}.log")
    
    # สร้างข้อความ เช่น [2024-05-20 14:30:05] [WARNING] เจอหน้าตรวจ AFK
    time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{time_str}] [{level}] {message}\n"
    
    # เปิดไฟล์แล้วเขียนต่อท้าย (Append)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_entry)