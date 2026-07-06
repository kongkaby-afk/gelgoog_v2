import pyautogui
import time
import cv2
import os
import sys
import random

CONFIDENCE = 0.8 

def resource_path(relative_path):
    """ฟังก์ชันหาที่อยู่ไฟล์รูปภาพ ไม่ว่าจะรันแบบ .py หรือ .exe"""
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
            # คืนค่ากลับเป็นกรอบ Box เพื่อให้ปุ่มสับไวเอาไปใช้ได้
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
    """กวาดล้าง Pop-up ทั้งหมดก่อนเริ่ม Phase 1 (กันเหนียว)"""
    print("\n🧹 [CLEANUP] กวาดล้าง Pop-up ก่อนเริ่ม Phase 1...")
    
    popup_buttons = [
        "assets/ok_btn.png", 
        "assets/confirm_btn.png", 
        "assets/green_confirm_btn.png",
        "assets/level_up_confirm_btn.png", 
        "assets/treasure_confirm_btn.png"
    ]
    
    for _ in range(3):
        clicked = False
        for btn in popup_buttons:
            if click_image(btn, timeout=0.2, delay_after=0.5):
                clicked = True
        if not clicked:
            break
    print("✅ เคลียร์หน้าจอสะอาดพร้อมเริ่ม Phase 1")

def run_phase_1():
    print("="*50)
    print("🚀 [PHASE 1] เริ่มต้นกระบวนการเตรียมตัว")
    print("="*50)
    
    # 0. สั่งเคลียร์ Pop-up ก่อนเริ่มกันเหนียว
    clear_popups_before_start()
    
    # 1. กดปุ่ม Play! หน้าหลัก
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
        
    # 6. กด Play! อีกครั้งเพื่อเข้าเกม
    if not click_image('assets/play_btn_shop.png'): return False
    
    # 7. เข้าเกมและกด Boost
    print("🎮 กำลังโหลดเข้าเกม เตรียมตัวกด Boost...")
    boost_box = wait_for_image('assets/in_game_boost.png', timeout=30)
    
    if boost_box:
        print("⚡ เจอปุ่ม Boost แล้ว! หน่วงเวลา 1.5 วินาที...")
        time.sleep(1.5)
        
        # ถอดรหัสกล่อง Box และสุ่มกดทั่วปุ่มแบบสายฟ้าแลบ
        left, top, width, height = boost_box
        pad_x, pad_y = int(width * 0.15), int(height * 0.15)
        target_x = random.randint(left + pad_x, left + width - pad_x)
        target_y = random.randint(top + pad_y, top + height - pad_y)
        
        fast_reaction = random.uniform(0.08, 0.2)
        print(f"   -> พุ่งกด Boost ด้วยความเร็ว {fast_reaction:.2f} วินาที")
        pyautogui.moveTo(target_x, target_y, duration=fast_reaction, tween=pyautogui.easeOutQuad)
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