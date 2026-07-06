import pyautogui
import time
import os

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
                pyautogui.moveTo(location.x, location.y, duration=0.2)
                pyautogui.click()
                time.sleep(delay_after)
                return True
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.3)
    
    print(f"❌ หมดเวลา! หา {image_name} ไม่เจอ")
    return False