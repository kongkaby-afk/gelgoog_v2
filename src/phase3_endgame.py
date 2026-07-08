# -*- coding: utf-8 -*-
import os
import sys
import cv2
import numpy as np
import pyautogui
import time
import random
from utils import write_log
from mss import MSS

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ==========================================
# ⚙️ การตั้งค่าหลัก
# ==========================================
CONFIDENCE = 0.8
AFK_THRESHOLD = 0.75

cards_regions = [
    [568, 303, 222, 303], [838, 301, 223, 305], [1110, 302, 220, 304],
    [567, 657, 223, 304], [839, 656, 224, 305], [1109, 657, 223, 303]
]
os.makedirs("debug", exist_ok=True)

def check_display_scale():
    try:
        import ctypes
        user32 = ctypes.windll.user32
        dc = user32.GetDC(0)
        scale_x = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  
        user32.ReleaseDC(0, dc)
        if scale_x != 96:
            print(f"⚠️ WARNING: Windows Display Scale อยู่ที่ {int((scale_x/96)*100)}%")
    except:
        pass

# ==========================================
# 📂 โหลด Template (อัปเดต Path ใหม่)
# ==========================================
ASSETS = {
    "afk_page": resource_path("assets/ui/afk_page.png"),
    "relay_btn": resource_path("assets/ui/relay_btn.png"),
    "stop_btn": resource_path("assets/ui/stop_btn.png"),
    "quit_btn": resource_path("assets/ui/quit_btn.png"),
    "quit_confirm_btn": resource_path("assets/ui/quit_confirm_btn.png"),
    "ok_btn": resource_path("assets/ui/ok_btn.png"),
    "open_all_btn": resource_path("assets/ui/open_all_btn.png"),
    "confirm_btn": resource_path("assets/ui/confirm_btn.png"),
    "green_confirm_btn": resource_path("assets/ui/green_confirm_btn.png"), 
    "level_up_confirm_btn": resource_path("assets/ui/level_up_confirm_btn.png"),
    "treasure_confirm_btn": resource_path("assets/ui/treasure_confirm_btn.png"),
    "main_menu_sign": resource_path("assets/ui/main_menu_sign.png"),
}

def load_template(path, flags=cv2.IMREAD_UNCHANGED):
    img = cv2.imread(path, flags)
    return img

templates = {name: load_template(path, cv2.IMREAD_UNCHANGED) for name, path in ASSETS.items()}
AFK_TEMPLATE_GRAY = cv2.imread(ASSETS["afk_page"], cv2.IMREAD_GRAYSCALE) if os.path.exists(ASSETS["afk_page"]) else None

# (ฟังก์ชัน Anti-AFK capture_cards, compute_similarity_matrix, detect_odd_two_cards, click_card คงเดิม)
def capture_cards(debug=False):
    captured = []
    with MSS() as sct:
        for idx, region in enumerate(cards_regions):
            x, y, w, h = int(region[0]), int(region[1]), int(region[2]), int(region[3])
            monitor = {"top": y, "left": x, "width": w, "height": h}
            img = np.array(sct.grab(monitor))[:, :, :3]
            gray = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (200, 300))
            captured.append(gray)
    return captured

def compute_similarity_matrix(images):
    n = len(images)
    sim_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i == j: sim_matrix[i][j] = 1.0; continue
            res = cv2.matchTemplate(images[i], images[j], cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            sim_matrix[i][j] = max_val
    return sim_matrix

def detect_odd_two_cards(images):
    sim_matrix = compute_similarity_matrix(images)
    odd_scores = np.sum(1.0 - sim_matrix, axis=1) / (len(images) - 1)
    sorted_indices = np.argsort(odd_scores)[::-1]
    return int(sorted_indices[0]), int(sorted_indices[1]), float(odd_scores[sorted_indices[1]] - odd_scores[sorted_indices[2]])

def click_card(index):
    region = cards_regions[index]
    left, top, width, height = int(region[0]), int(region[1]), int(region[2]), int(region[3])
    pad_x, pad_y = int(width * 0.20), int(height * 0.20)
    target_x = random.randint(left + pad_x, left + width - pad_x)
    target_y = random.randint(top + pad_y, top + height - pad_y)
    pyautogui.moveTo(target_x, target_y, duration=random.uniform(0.15, 0.4), tween=pyautogui.easeOutQuad)
    pyautogui.click()

def click_image(image_key, timeout=10, delay_after=0.5, confidence=None):
    if image_key not in templates or templates[image_key] is None: return False
    conf = confidence if confidence is not None else CONFIDENCE
    print(f"🔍 กำลังหา [{image_key}]...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            box = pyautogui.locateOnScreen(ASSETS[image_key], confidence=conf)
            if box is not None:
                left, top, width, height = box
                pad_x, pad_y = int(width * 0.15), int(height * 0.15)
                target_x = random.randint(left + pad_x, left + width - pad_x)
                target_y = random.randint(top + pad_y, top + height - pad_y)
                pyautogui.moveTo(target_x, target_y, duration=random.uniform(0.15, 0.4))
                pyautogui.click()
                print(f"✅ คลิก [{image_key}] สำเร็จ!")
                time.sleep(delay_after)
                return True
        except: pass
        time.sleep(0.2)
    return False

def wait_for_image(image_key, timeout=60):
    if image_key not in templates or templates[image_key] is None: return None
    print(f"⏳ รอ [{image_key}]...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            box = pyautogui.locateOnScreen(ASSETS[image_key], confidence=CONFIDENCE)
            if box is not None: return box
        except: pass
        time.sleep(0.3)
    return None

def is_afk_screen_present(threshold=AFK_THRESHOLD):
    if AFK_TEMPLATE_GRAY is None: return False
    with MSS() as sct:
        screen_gray = cv2.cvtColor(np.array(sct.grab(sct.monitors[1])), cv2.COLOR_BGRA2GRAY)
        _, max_val, _, _ = cv2.minMaxLoc(cv2.matchTemplate(screen_gray, AFK_TEMPLATE_GRAY, cv2.TM_CCOEFF_NORMED))
        return max_val >= threshold

def solve_afk_puzzle():
    print("\n🚨 [DETECTED] เจอหน้าจอ Anti-AFK! เริ่มแก้วนลูปแบบไดนามิก...")
    write_log("ตรวจพบหน้าจอ Anti-AFK และระบบกำลังเริ่มแก้ปริศนา", level="WARNING")
    stage = 1
    while is_afk_screen_present() and stage <= 10:
        time.sleep(2.5) 
        target1, target2, _ = detect_odd_two_cards(capture_cards())
        time.sleep(0.5)
        click_card(target1)
        time.sleep(0.3)
        click_card(target2)
        time.sleep(3.5) 
        stage += 1
    print("\n✅ หน้าต่าง Anti-AFK หายไปแล้ว!")

# ==========================================
# 🚀 ฟังก์ชันหลัก Phase 3 (รับ config และ status จาก Phase 2)
# ==========================================
def run_phase_3(config, phase2_status):
    print("=" * 55)
    print(f"🏁 [PHASE 3] เริ่มต้นระบบจัดการหลังจบเกม (Status: {phase2_status})")
    print("=" * 55)
    
    check_display_scale()
    
    # 🎯 1. เช็คสถานะการจบเกม
    if phase2_status == "BOX_FOUND":
        print("🎁 [AFK MODE] เจอกล่องเป้าหมายแล้ว ข้ามการรอ Relay พุ่งชนปุ่มออกด่วน!")
        
    elif phase2_status == "DIED":
        # ถ้าตาย เช็คต่อว่าผู้ใช้เปิดให้ใช้ Relay ไหม?
        if config.get('use_relay_death', False):
            print("🔄 [AI MODE] ตัวแตกแล้ว รอชุบชีวิตด้วย Relay ตามการตั้งค่า...")
            relay_box = wait_for_image("relay_btn", timeout=30)
            if relay_box:
                left, top, width, height = relay_box
                pyautogui.moveTo(left + (width/2), top + (height/2), duration=0.2)
                pyautogui.click()
                print("⚡ กดปุ่ม Relay แล้ว! (ระบบจะให้วิ่งต่ออีกนิดจนตายจริงๆ)")
                time.sleep(5) # เผื่อเวลาให้มันตายรอบสอง หรือสลับโค้ดให้กลับไป Phase 2 ถ้ายุ่งยากเกินไปให้ออกเกมเลย
        else:
            print("⏭️ ตัวแตกแล้ว และไม่ได้ตั้งค่าใช้ Relay -> ข้ามไปปุ่มออกเกม")
            
    # 2. ออกเกมรัวๆ (3 สเต็ปคอมโบ)
    print("\n🏃 กำลังออกจากการวิ่ง...")
    click_image("stop_btn", timeout=5)
    click_image("quit_btn", timeout=5)
    time.sleep(1)
    click_image("quit_confirm_btn", timeout=5)
    
    # 3. เคลียร์ Pop-up กลับหน้า Main
    print("\n🔄 เข้าสู่กระบวนการเคลียร์หน้าจอ...")
    start_clear_time = time.time()
    popup_buttons = ["ok_btn", "open_all_btn", "confirm_btn", "green_confirm_btn", "level_up_confirm_btn", "treasure_confirm_btn"]
    
    while time.time() - start_clear_time < 60: 
        try:
            if pyautogui.locateOnScreen(ASSETS["main_menu_sign"], confidence=CONFIDENCE):
                print("\n🎉 กลับถึงหน้า Main Menu เรียบร้อย!")
                return True
        except: pass 
            
        clicked_any = False
        for btn in popup_buttons:
            if click_image(btn, timeout=0.2, delay_after=1.5, confidence=0.75):
                clicked_any = True
                break 
                
        if not clicked_any:
            if is_afk_screen_present():
                solve_afk_puzzle() 
            else:
                time.sleep(0.5)
            
    print("❌ วนลูปเคลียร์ Pop-up นานเกินไป หาหน้า Main ไม่เจอ")
    return False