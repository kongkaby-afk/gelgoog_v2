import pyautogui
import time
import cv2
import numpy as np
from mss import MSS
import os
import sys
import random

CONFIDENCE = 0.8 

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def click_image(image_name, timeout=10, delay_after=0.5):
    actual_path = resource_path(image_name)
    print(f"🔍 กำลังหาและคลิก [{image_name}]...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            box = pyautogui.locateOnScreen(actual_path, confidence=CONFIDENCE)
            if box is not None:
                left, top, width, height = box
                pad_x = int(width * 0.15)
                pad_y = int(height * 0.15)
                target_x = random.randint(left + pad_x, left + width - pad_x)
                target_y = random.randint(top + pad_y, top + height - pad_y)

                chance = random.randint(1, 100)
                if chance <= 20:
                    reaction_time = random.uniform(0.15, 0.3)
                elif chance <= 80:
                    reaction_time = random.uniform(0.4, 0.8)
                else:
                    reaction_time = random.uniform(0.85, 1.2)

                pyautogui.moveTo(target_x, target_y, duration=reaction_time, tween=pyautogui.easeOutQuad)
                pyautogui.click()
                print(f"✅ คลิก {image_name} สำเร็จ! (ดีเลย์ {reaction_time:.2f}s)")
                time.sleep(delay_after)
                return True
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.3)
    print(f"❌ หมดเวลา! หา {image_name} ไม่เจอ")
    return False

def wait_for_image(image_name, timeout=60):
    actual_path = resource_path(image_name)
    print(f"⏳ กำลังรอให้ [{image_name}] ปรากฏขึ้นมา...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            box = pyautogui.locateOnScreen(actual_path, confidence=CONFIDENCE)
            if box is not None:
                print(f"👀 เจอ {image_name} แล้ว!")
                return box 
        except pyautogui.ImageNotFoundException:
            pass
        time.sleep(0.2)
    print(f"❌ หมดเวลาคอย! ไม่พบ {image_name}")
    return None

def wait_until_gone(image_name, timeout=15):
    actual_path = resource_path(image_name)
    print(f"⏳ กำลังรอให้ [{image_name}] หายไปจากหน้าจอ...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            pyautogui.locateOnScreen(actual_path, confidence=CONFIDENCE)
            time.sleep(0.3) 
        except pyautogui.ImageNotFoundException:
            print(f"✅ [{image_name}] หายไปแล้ว! ระบบพร้อมลุยสเต็ปต่อไป")
            return True
    print(f"❌ หมดเวลา! หน้าจอยังค้างอยู่ที่เดิม")
    return False

def clear_popups_before_start():
    print("\n🧹 [CLEANUP] กวาดล้าง Pop-up ก่อนเริ่ม Phase 1...")
    popup_buttons = [
        "assets/ui/ok_btn.png", 
        "assets/ui/confirm_btn.png", 
        "assets/ui/green_confirm_btn.png",
        "assets/ui/level_up_confirm_btn.png", 
        "assets/ui/treasure_confirm_btn.png",
        "assets/ui/relic_cross_btn.png"
    ]
    for _ in range(3):
        clicked = False
        for btn in popup_buttons:
            if click_image(btn, timeout=0.2, delay_after=0.5):
                clicked = True
        if not clicked:
            break
    print("✅ เคลียร์หน้าจอสะอาดพร้อมเริ่ม Phase 1")

# ==========================================
# 🏺 ฟังก์ชันตรวจสอบและสุ่ม Relic อัตโนมัติ (รองรับหลายด่าน)
# ==========================================
def check_and_claim_relic():
    print("\n🏺 [RELIC CHECK] กำลังสแกนหาไอคอนสมุด Relic (7/7)...")
    try:
        # ใช้ MSS แคปหน้าจอเพื่อความไวและแม่นยำ
        with MSS() as sct:
            screenshot = np.array(sct.grab(sct.monitors[1]))
            screen_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
            
        # ลิสต์รายชื่อไฟล์ไอคอน Relic ของแต่ละด่าน (เพิ่มได้อีกถ้ามีด่าน 4, 5)
        relic_icons = [
            "assets/ui/relic_full_icon_1.png",
            "assets/ui/relic_full_icon_2.png",
            "assets/ui/relic_full_icon_3.png"
        ]
        
        found_relic = False
        matched_icon_path = ""
        best_confidence = 0
        
        # ลูปเช็คทีละด่าน
        for icon_path in relic_icons:
            actual_path = resource_path(icon_path)
            
            # ถ้าไม่มีไฟล์รูปด่านนี้ ให้ข้ามไปเช็คด่านถัดไป
            if not os.path.exists(actual_path):
                continue
                
            template_gray = cv2.imread(actual_path, cv2.IMREAD_GRAYSCALE)
            res = cv2.matchTemplate(screen_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            
            # ถ้าเจอไอคอนของด่านไหนที่เหมือนเกิน 85% ให้จดจำไว้แล้วหยุดหา
            if max_val >= 0.85:
                found_relic = True
                matched_icon_path = icon_path
                best_confidence = max_val
                break
        
        if found_relic:
            print(f"🎉 เจอกรอบ Relic  แล้ว! (ความมั่นใจ {best_confidence:.2%} จาก {matched_icon_path}) กำลังกดรับ...")
            
            # 1. กดไอคอนสมุด Relic "ด่านที่ตรวจเจอ"
            click_image(matched_icon_path, timeout=3)
            time.sleep(2)
            
            # 2. กดปุ่ม Claim หรือ สุ่ม (ใช้ปุ่มเดียวกันทุกด่าน)
            click_image("assets/ui/relic_claim_btn.png", timeout=5)
            print("⏳ รอแอนิเมชันเปิด Relic 3 วินาที...")
            time.sleep(3)
            
            # 3. กดกากบาทปิดหน้าต่าง
            click_image("assets/ui/relic_cross_btn.png", timeout=5)
            time.sleep(1)
            
            # เคลียร์ซ้ำเผื่อมีอะไรเด้ง
            clear_popups_before_start()
        else:
            print(f"➖ กรอบ Relic ยังไม่เต็ม หรือไม่พบไอคอน ข้ามไปสเต็ปต่อไป")
            
    except Exception as e:
        print(f"⚠️ ระบบเช็ค Relic ขัดข้อง: {e}")

# ==========================================
# 🚀 ฟังก์ชันหลัก Phase 1 (รับ config จาก main)
# ==========================================
def run_phase_1(config):
    print("="*50)
    print("🚀 [PHASE 1] เริ่มต้นกระบวนการเตรียมตัว")
    print("="*50)
    
    # 0. สั่งเคลียร์ Pop-up ก่อนเริ่มกันเหนียว
    clear_popups_before_start()
    
    # 🌟 [NEW] เช็ค Relic ถ้าผู้ใช้เปิดโหมด Auto Claim
    if config.get('auto_claim_relic', True):
        check_and_claim_relic()
    
    # 1. กดปุ่ม Play! หน้าหลัก
    if not click_image('assets/ui/play_btn_main.png'): return False
    
    # ยืนยันว่าเข้าหน้า Shop 
    if not wait_until_gone('assets/ui/main_menu_sign.png', timeout=15):
        print("⚠️ โหลดเข้าหน้า Shop ไม่สำเร็จ ยกเลิกการทำงาน")
        return False
    
    # 2. ซื้อ item_boost (เช็ค Config)
    if config.get('buy_boost', False):
        print("🛒 ซื้อ Item: Boost (ตามการตั้งค่า)")
        click_image('assets/items/item_boost.png', timeout=3)
        click_image('assets/ui/buy_btn.png', timeout=3)
        wait_for_image('assets/ui/purchase_complete.png', timeout=5)
    
    # 3. ซื้อ item_relay (เช็ค Config)
    if config.get('buy_relay', False):
        print("🛒 ซื้อ Item: Relay (ตามการตั้งค่า)")
        click_image('assets/items/item_relay.png', timeout=3)
        click_image('assets/ui/buy_btn.png', timeout=3)
        wait_for_image('assets/ui/purchase_complete.png', timeout=5)
    
    # 4. สุ่ม Double Coin (เช็ค Config)
    if config.get('roll_double_coin', False):
        print("🎲 สุ่ม Item: ทอยหา Double Coin (ตามการตั้งค่า)")
        click_image('assets/items/item_random.png', timeout=3)
        click_image('assets/ui/multi_btn.png', timeout=3)
        click_image('assets/ui/multi_buy_btn.png', timeout=3)
        if not wait_for_image('assets/items/double_coin.png', timeout=60): 
            print("⚠️ ไม่ได้ Double Coin ตามเวลาที่กำหนด ยกเลิกการทำงาน")
            return False
        
    # 5. กด Play! อีกครั้งเพื่อเข้าเกม
    if not click_image('assets/ui/play_btn_shop.png'): return False
    
    # 6. เข้าเกมและกด Boost (เช็ค Config)
    if config.get('use_in_game_boost', False):
        print("🎮 กำลังโหลดเข้าเกม เตรียมตัวพุ่งกด Boost...")
        boost_box = wait_for_image('assets/items/in_game_boost.png', timeout=30)
        
        if boost_box:
            print("⚡ เจอปุ่ม Boost แล้ว! หน่วงเวลา 1.5 วินาที...")
            time.sleep(1.5)
            
            left, top, width, height = boost_box
            pad_x, pad_y = int(width * 0.15), int(height * 0.15)
            target_x = random.randint(left + pad_x, left + width - pad_x)
            target_y = random.randint(top + pad_y, top + height - pad_y)
            
            fast_reaction = random.uniform(0.08, 0.2)
            pyautogui.moveTo(target_x, target_y, duration=fast_reaction, tween=pyautogui.easeOutQuad)
            pyautogui.click()
            print("✅ กดใช้ Boost ในเกมสำเร็จ!")
        else:
            print("❌ หาปุ่ม Boost ในเกมไม่เจอ (อาจโหลดนาน หรือไม่ได้ซื้อไว้)")
    else:
        print("⏭️ [ข้าม] การตั้งค่าไม่ให้กด Boost ในเกม รอโหลดเข้าด่าน...")
        time.sleep(5) # เผื่อเวลาโหลดฉากนิดนึง
        
    print("="*50)
    print("🏁 จบการทำงาน Phase 1 ส่งไม้ต่อให้ Phase 2")
    print("="*50)
    return True