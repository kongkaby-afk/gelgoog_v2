import pyautogui
import time
import cv2

CONFIDENCE = 0.8 

def click_image(image_path, timeout=10, delay_after=0.5):
    print(f"🔍 กำลังหาและคลิก [{image_path}]...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=CONFIDENCE)
            if location is not None:
                pyautogui.moveTo(location.x, location.y, duration=0.2)
                pyautogui.click()
                print(f"✅ คลิก {image_path} สำเร็จ!")
                time.sleep(delay_after)
                return True
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.3)
    print(f"❌ หมดเวลา! หา {image_path} ไม่เจอ")
    return False

def wait_for_image(image_path, timeout=60):
    print(f"⏳ กำลังรอให้ [{image_path}] ปรากฏขึ้นมา...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            location = pyautogui.locateCenterOnScreen(image_path, confidence=CONFIDENCE)
            if location is not None:
                print(f"👀 เจอ {image_path} แล้ว!")
                return location
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.2)
    print(f"❌ หมดเวลาคอย! ไม่พบ {image_path}")
    return None

def wait_until_gone(image_path, timeout=15):
    print(f"⏳ กำลังรอให้ [{image_path}] หายไปจากหน้าจอ...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            pyautogui.locateOnScreen(image_path, confidence=CONFIDENCE)
            time.sleep(0.3) 
        except pyautogui.ImageNotFoundException:
            print(f"✅ [{image_path}] หายไปแล้ว! ระบบพร้อมลุยสเต็ปต่อไป")
            return True
    print(f"❌ หมดเวลา! หน้าจอยังค้างอยู่ที่เดิม")
    return False

def run_phase_1():
    print("="*50)
    print("🚀 [PHASE 1] เริ่มต้นกระบวนการเตรียมตัว")
    print("="*50)
    
    # 1. กดปุ่ม Play! หน้าหลัก (ใช้รูปแรก)
    if not click_image('assets/play_btn_main.png'): return False
    
    # ยืนยันว่าเข้าหน้า Shop 
    if not wait_until_gone('assets/main_menu_sign.png', timeout=15):
        print("⚠️ โหลดเข้าหน้า Shop ไม่สำเร็จ ยกเลิกการทำงาน")
        return False
    
    # 2. ซื้อ item_boost
    click_image('assets/item_boost.png')
    click_image('assets/buy_btn.png')
    wait_for_image('assets/purchase_complete.png', timeout=10)
    
    # 3. ซื้อ item_relay
    click_image('assets/item_relay.png')
    click_image('assets/buy_btn.png')
    wait_for_image('assets/purchase_complete.png', timeout=10)
    
    # 4. ซื้อสุ่ม Multi จนกว่าจะได้ Double Coin
    click_image('assets/item_random.png')
    click_image('assets/multi_btn.png')
    click_image('assets/multi_buy_btn.png')
    
    # 5. รอจนกว่าคำว่า Double Coin จะโผล่มา
    if not wait_for_image('assets/double_coin.png', timeout=60): 
        print("⚠️ ไม่ได้ Double Coin ตามเวลาที่กำหนด ยกเลิกการทำงาน")
        return False
        
    # 6. กด Play! อีกครั้งเพื่อเข้าเกม (ใช้รูปที่สอง)
    if not click_image('assets/play_btn_shop.png'): return False
    
    # 7. เข้าเกมและกด Boost
    print("🎮 กำลังโหลดเข้าเกม เตรียมตัวกด Boost...")
    boost_location = wait_for_image('assets/in_game_boost.png', timeout=30)
    
    if boost_location:
        print("⚡ เจอปุ่ม Boost แล้ว! หน่วงเวลา 1.5 วินาที...")
        time.sleep(1.5)
        
        pyautogui.moveTo(boost_location.x, boost_location.y, duration=0.1)
        pyautogui.click()
        print("✅ กดใช้ Boost ในเกมสำเร็จ!")
        
        print("="*50)
        print("🏁 จบการทำงาน Phase 1 ส่งไม้ต่อให้ Phase 2")
        print("="*50)
        return True
    else:
        print("❌ หาปุ่ม Boost ในเกมไม่เจอ บอทอาจจะทำงานต่อไม่ได้")
        return False

if __name__ == "__main__":
    print("🕒 กรุณาสลับไปยังหน้าต่างเกม... บอทจะเริ่มใน 3 วินาที")
    time.sleep(3)
    run_phase_1()