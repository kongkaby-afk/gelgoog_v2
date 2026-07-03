import cv2
import numpy as np
import pyautogui
import time
import keyboard
from mss import MSS

CONFIDENCE = 0.8 

# ==========================================
# 🎯 พิกัดและตั้งค่าระบบ Anti-AFK (อิงตามระบบของคุณเป๊ะๆ)
# ==========================================
cards_regions = [
    [568, 303, 222, 303],
    [838, 301, 223, 305],
    [1110, 302, 220, 304],
    [567, 657, 223, 304],
    [839, 656, 224, 305],
    [1109, 657, 223, 303]
]

def mse(imageA, imageB):
    err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
    err /= float(imageA.shape[0] * imageA.shape[1])
    return err

def capture_cards():
    with MSS() as sct:
        images = []
        for region in cards_regions:
            top, left, width, height = int(region[1]), int(region[0]), int(region[2]), int(region[3])
            monitor = {"top": top, "left": left, "width": width, "height": height}
            
            img = np.array(sct.grab(monitor))
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            img_gray = cv2.resize(img_gray, (200, 300))
            images.append(img_gray)
        return images

def solve_puzzle_round(images):
    diff_scores = [0] * 6
    for i in range(6):
        for j in range(6):
            if i != j:
                diff_scores[i] += mse(images[i], images[j])
                
    indexed_scores = list(enumerate(diff_scores))
    indexed_scores.sort(key=lambda x: x[1], reverse=True)
    
    top1_idx = indexed_scores[0][0]
    top2_idx = indexed_scores[1][0]
    
    return top1_idx, top2_idx

def click_card(index):
    region = cards_regions[index]
    center_x = int(region[0] + (region[2] / 2))
    center_y = int(region[1] + (region[3] / 2))
    pyautogui.click(center_x, center_y)
    print(f" Jane 🖱️ คลิกการ์ด -> ใบที่ {index + 1}")

def check_afk_page_with_opencv():
    with MSS() as sct:
        screenshot = np.array(sct.grab(sct.monitors[1]))
        screen_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
        
        template = cv2.imread('assets/afk_page.png', cv2.IMREAD_GRAYSCALE)
        if template is None:
            return False
            
        res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        if max_val >= 0.8:
            return True
    return False

# ==========================================
# 🕹️ ระบบควบคุมการกด UI ทั่วไป
# ==========================================
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
        time.sleep(0.3)
    return None

# ==========================================
# 🚀 ฟังก์ชันหลักของ Phase 3
# ==========================================
def run_phase_3():
    print("="*50)
    print("🏁 [PHASE 3] เริ่มต้นระบบจัดการหลังจบเกม")
    print("="*50)
    
    # 1. รอจนกว่าจะมีรูป Relay โผล่มา (ตัวละครตาย/หมดแรง)
    if not wait_for_image('assets/relay_btn.png', timeout=600):
        print("❌ รอนานเกินไป ไม่พบปุ่ม Relay")
        return False
        
    # 2. ลำดับการกดออกจากเกม
    click_image('assets/relay_btn.png', timeout=5)
    click_image('assets/stop_btn.png', timeout=5)
    click_image('assets/quit_btn.png', timeout=5)
    time.sleep(1) 
    click_image('assets/quit_confirm_btn.png', timeout=5) 
    
    # 3. ตรวจสอบและแก้ระบบ Anti-AFK
    print("🛡️ กำลังตรวจสอบหน้าจอ Anti-AFK...")
    time.sleep(2.5) # หน่วงเวลารอหน้าจอโหลดสลับสเตจ
    
    if check_afk_page_with_opencv():
        print("\n🚨 [DETECTED] เจอหน้าจอ Anti-AFK แล้ว! เริ่มแก้ด้วย Traditional CV... 🚨")
        print("-" * 40)
        
        previous_cards = None
        for stage in range(1, 4):
            print(f"🧩 กำลังประมวลผลด่านที่ {stage}/3...")
            
            # ระบบ Smart Wait เช็คด่านใหม่
            while True:
                current_cards = capture_cards()
                if previous_cards is not None:
                    total_diff = 0
                    for i in range(6):
                        total_diff += mse(current_cards[i], previous_cards[i])
                    
                    if total_diff < 500: 
                        time.sleep(0.5)
                        continue
                        
                previous_cards = current_cards
                break 
            
            time.sleep(0.5) # รอแอนิเมชันนิ่ง
            current_cards = capture_cards() 
            
            # วิเคราะห์และสั่งจิ้มไพ่ใบที่ต่าง
            target1, target2 = solve_puzzle_round(current_cards)
            print(f"🎯 วิเคราะห์พบการ์ดที่แปลกแยก 2 ใบคือ: ใบที่ {target1 + 1} และ ใบที่ {target2 + 1}")

            time.sleep(1.5) 
            click_card(target1)
            time.sleep(1.5) 
            click_card(target2)
            print("-" * 40)
            time.sleep(1.5) 
            
        print("✅ แก้เสร็จสมบูรณ์ครบทั้ง 3 ด่านแล้ว!")
    else:
        print("⏩ ไม่พบหน้าต่าง Anti-AFK ข้ามไปหน้า Result ทันที")

    # 4. จัดการหน้า Result และเปิดกล่องของขวัญ
    click_image('assets/ok_btn.png', timeout=15) 
    click_image('assets/ok_btn.png', timeout=5)
    click_image('assets/open_all_btn.png', timeout=5)
    
    # 5. วนลูปกด Confirm เพื่อกลับไปหน้าหลัก
    print("🔄 กำลังกด Confirm เพื่อกลับไปหน้าหลัก...")
    start_confirm_time = time.time()
    
    while time.time() - start_confirm_time < 60: 
        try:
            pyautogui.locateOnScreen('assets/main_menu_sign.png', confidence=CONFIDENCE)
            print("🎉 กลับถึงหน้า Main Menu เรียบร้อยแล้ว!")
            print("="*50)
            print("🏁 จบการทำงาน Phase 3 ส่งไม้ต่อให้ Phase 1")
            print("="*50)
            return True
        except pyautogui.ImageNotFoundException:
            pass
            
        click_image('assets/confirm_btn.png', timeout=2, delay_after=1)
        
    print("❌ วนลูปกด Confirm นานเกินไป หาหน้า Main ไม่เจอ")
    return False

if __name__ == "__main__":
    print("🕒 กรุณาสลับไปยังหน้าต่างเกม... ระบบจะเริ่มทดสอบใน 3 วินาที")
    time.sleep(3)
    run_phase_3()