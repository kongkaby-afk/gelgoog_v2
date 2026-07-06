# -*- coding: utf-8 -*-
import os
import sys
import cv2
import numpy as np
import pyautogui
import time
import keyboard
from mss import MSS
import random
from utils import write_log

def resource_path(relative_path):
    """ฟังก์ชันหาที่อยู่ไฟล์รูปภาพ ไม่ว่าจะรันแบบ .py หรือ .exe"""
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
AFK_WAIT_TIMEOUT = 20

# พิกัดการ์ด 6 ใบ [x, y, width, height]
cards_regions = [
    [568, 303, 222, 303],
    [838, 301, 223, 305],
    [1110, 302, 220, 304],
    [567, 657, 223, 304],
    [839, 656, 224, 305],
    [1109, 657, 223, 303]
]

os.makedirs("debug", exist_ok=True)

# ==========================================
# 🚨 ตรวจสอบ Display Scale ของ Windows
# ==========================================
def check_display_scale():
    try:
        import ctypes
        user32 = ctypes.windll.user32
        dc = user32.GetDC(0)
        scale_x = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  
        user32.ReleaseDC(0, dc)
        if scale_x != 96:
            print(f"⚠️ WARNING: Windows Display Scale อยู่ที่ {int((scale_x/96)*100)}%")
            print("   ควรตั้งเป็น 100% ระหว่างรัน เพื่อให้พิกัดการ์ดและการหารูปตรง")
    except Exception as e:
        print(f"⚠️ ไม่สามารถตรวจ Display Scale ได้: {e}")

# ==========================================
# 📂 โหลด Template ทั้งหมดตอนเริ่มโปรแกรม
# ==========================================
def load_template(path, flags=cv2.IMREAD_UNCHANGED):
    img = cv2.imread(path, flags)
    if img is None:
        print(f"❌ CRITICAL: โหลดไฟล์ '{path}' ไม่ได้ กรุณาตรวจสอบ path")
    else:
        print(f"✅ โหลด Template '{path}' สำเร็จ ({img.shape})")
    return img

ASSETS = {
    "afk_page": resource_path("assets/afk_page.png"),
    "relay_btn": resource_path("assets/relay_btn.png"),
    "stop_btn": resource_path("assets/stop_btn.png"),
    "quit_btn": resource_path("assets/quit_btn.png"),
    "quit_confirm_btn": resource_path("assets/quit_confirm_btn.png"),
    "ok_btn": resource_path("assets/ok_btn.png"),
    "open_all_btn": resource_path("assets/open_all_btn.png"),
    "confirm_btn": resource_path("assets/confirm_btn.png"),
    "green_confirm_btn": resource_path("assets/green_confirm_btn.png"), 
    "level_up_confirm_btn": resource_path("assets/level_up_confirm_btn.png"),
    "treasure_confirm_btn": resource_path("assets/treasure_confirm_btn.png"),
    "main_menu_sign": resource_path("assets/main_menu_sign.png"),
}

templates = {name: load_template(path, cv2.IMREAD_UNCHANGED) for name, path in ASSETS.items()}
AFK_TEMPLATE_GRAY = cv2.imread(ASSETS["afk_page"], cv2.IMREAD_GRAYSCALE)

# ==========================================
# 🖼️ ระบบ Capture การ์ด
# ==========================================
def capture_cards(debug=False):
    captured = []
    with MSS() as sct:
        for idx, region in enumerate(cards_regions):
            x, y, w, h = int(region[0]), int(region[1]), int(region[2]), int(region[3])
            monitor = {"top": y, "left": x, "width": w, "height": h}
            
            img = np.array(sct.grab(monitor))
            img_bgr = img[:, :, :3]
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (200, 300))
            
            captured.append(gray)
            
            if debug:
                cv2.imwrite(f"debug/card_{idx+1}.png", gray)
    return captured

# ==========================================
# 🧩 ระบบหา 2 ใบที่แปลก (NCC)
# ==========================================
def compute_similarity_matrix(images):
    n = len(images)
    sim_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i == j:
                sim_matrix[i][j] = 1.0
                continue
            res = cv2.matchTemplate(images[i], images[j], cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            sim_matrix[i][j] = max_val
    return sim_matrix

def detect_odd_two_cards(images, method="ncc", debug=True):
    n = len(images)
    if method == "ncc":
        sim_matrix = compute_similarity_matrix(images)
        dissim_matrix = 1.0 - sim_matrix
    else:
        raise ValueError("method รองรับแค่ 'ncc'")
    
    odd_scores = np.sum(dissim_matrix, axis=1) / (n - 1)
    sorted_indices = np.argsort(odd_scores)[::-1]
    
    top1 = int(sorted_indices[0])
    top2 = int(sorted_indices[1])
    third = int(sorted_indices[2])
    
    gap = odd_scores[top2] - odd_scores[third]
    max_score = odd_scores[top1]
    confidence = gap / max_score if max_score > 0 else 0.0
    
    if debug:
        print("\n📊 Similarity Matrix (NCC):")
        print(np.round(sim_matrix, 3))
        print("\n🔥 Odd Scores (ยิ่งมากยิ่งแปลก):")
        for i in range(n):
            marker = "⬅️ เลือก" if i in [top1, top2] else ""
            print(f"  ใบที่ {i+1}: {odd_scores[i]:.4f} {marker}")
        print(f"\n✅ Confidence: {confidence:.2%} | gap={gap:.4f} | max={max_score:.4f}")
    
    return top1, top2, float(confidence)

# ==========================================
# 🖱️ ระบบคลิกการ์ดและ UI
# ==========================================
def click_card(index):
    region = cards_regions[index]
    left, top, width, height = int(region[0]), int(region[1]), int(region[2]), int(region[3])
    
    # 🎯 การ์ดใบใหญ่มาก หดขอบเข้ามา 20% ให้จิ้มแถวๆ เนื้อการ์ดด้านใน
    pad_x = int(width * 0.20)
    pad_y = int(height * 0.20)
    
    # 🎲 สุ่มจุดคลิกทั่วบริเวณใบการ์ด
    target_x = random.randint(left + pad_x, left + width - pad_x)
    target_y = random.randint(top + pad_y, top + height - pad_y)
    
    chance = random.randint(1, 100)
    if chance <= 20:
        move_duration = random.uniform(0.15, 0.3)
    elif chance <= 80:
        move_duration = random.uniform(0.4, 0.8)
    else:
        move_duration = random.uniform(0.85, 1.2)
        
    pyautogui.moveTo(target_x, target_y, duration=move_duration, tween=pyautogui.easeOutQuad)
    pyautogui.click()
    print(f"  🖱️ คลิกการ์ดใบที่ {index + 1} ({target_x}, {target_y}) [Speed: {move_duration:.2f}s]")

def click_image(image_key, timeout=10, delay_after=0.5, confidence=None):
    if image_key not in templates:
        print(f"❌ ไม่มี Template ชื่อ {image_key}")
        return False
    
    template = templates[image_key]
    if template is None:
        print(f"❌ Template {image_key} โหลดไม่ติด ข้าม")
        return False
    
    conf = confidence if confidence is not None else CONFIDENCE
    template_path = ASSETS[image_key]
    
    print(f"🔍 กำลังหา [{image_key}]...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # ดึงเอากรอบปุ่มมาคำนวณ
            box = pyautogui.locateOnScreen(template_path, confidence=conf)
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
                print(f"✅ คลิก [{image_key}] สำเร็จ! (ดีเลย์ {reaction_time:.2f}s)")
                time.sleep(delay_after)
                return True
        except pyautogui.ImageNotFoundException:
            pass
        except Exception as e:
            print(f"⚠️ Error คลิก {image_key}: {e}")
        time.sleep(0.2)
    
    print(f"❌ ไม่พบ/คลิก [{image_key}] ไม่สำเร็จภายใน {timeout} วิ")
    return False

def wait_for_image(image_key, timeout=60):
    if image_key not in templates or templates[image_key] is None:
        print(f"❌ Template {image_key} โหลดไม่ติด")
        return None
    
    template_path = ASSETS[image_key]
    print(f"⏳ รอ [{image_key}]...")
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            box = pyautogui.locateOnScreen(template_path, confidence=CONFIDENCE)
            if box is not None:
                print(f"👀 เจอ [{image_key}] แล้ว")
                return box
        except:
            pass
        time.sleep(0.3)
    
    return None

# ==========================================
# 🛡️ ระบบตรวจจับและแก้หน้า Anti-AFK
# ==========================================
def is_afk_screen_present(threshold=AFK_THRESHOLD, monitor_index=1):
    if AFK_TEMPLATE_GRAY is None:
        return False
    with MSS() as sct:
        screenshot = np.array(sct.grab(sct.monitors[monitor_index]))
        screen_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
        res = cv2.matchTemplate(screen_gray, AFK_TEMPLATE_GRAY, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return max_val >= threshold

def solve_afk_puzzle():
    print("\n🚨 [DETECTED] เจอหน้าจอ Anti-AFK! เริ่มแก้วนลูปแบบไดนามิก...")
    
    # 👇 สั่งบันทึก Log ตอนเจอ Anti-AFK ทันที! (บันทึกเป็นระดับ WARNING)
    write_log("ตรวจพบหน้าจอ Anti-AFK และระบบกำลังเริ่มแก้ปริศนา", level="WARNING")
    
    print("-" * 50)
    
    stage = 1
    max_retries = 10
    
    while is_afk_screen_present():
        if stage > max_retries:
            print("❌ [ERROR] วนลูปแก้ AFK เกิน 10 รอบ! บังคับออกเพื่อป้องกันจอค้าง")
            break
            
        print(f"\n🧩 กำลังแก้ด่านที่ {stage}")
        print("⏳ รอแอนิเมชันแจกไพ่ 2.5 วินาที...")
        time.sleep(2.5) 
        
        current_cards = capture_cards(debug=True)
        target1, target2, conf = detect_odd_two_cards(current_cards, method="ncc", debug=True)
        
        if conf < 0.01:
            print(f"⚠️ Confidence ต่ำ ({conf:.2%}) ลองแคปภาพซ้ำอีกรอบ...")
            time.sleep(1.0)
            current_cards = capture_cards(debug=True)
            target1, target2, conf = detect_odd_two_cards(current_cards, method="ncc", debug=True)
        
        print(f"🎯 สรุปผล: เลือกใบที่ {target1+1} และ {target2+1}")
        
        time.sleep(0.5)
        click_card(target1)
        time.sleep(0.3)
        click_card(target2)
        
        print("⏳ รอดูผลลัพธ์และรอแจกไพ่ชุดใหม่...")
        time.sleep(3.5) 
        stage += 1
        
    print("\n✅ หน้าต่าง Anti-AFK หายไปแล้ว! กลับสู่กระบวนการปกติ")
    write_log(f"แก้ปริศนา Anti-AFK สำเร็จ (ใช้ไป {stage-1} ด่าน)", level="INFO")
    print("-" * 50)

# ==========================================
# 🚀 ฟังก์ชันหลัก Phase 3 (สแกนเคลียร์ Pop-up แบบไดนามิก)
# ==========================================
def run_phase_3():
    print("=" * 55)
    print("🏁 [PHASE 3] เริ่มต้นระบบจัดการหลังจบเกม")
    print("=" * 55)
    
    check_display_scale()
    print("ℹ️  หมายเหตุ: หากต้องการหยุดฉุกเฉิน ให้ลาก Mouse ไปมุมจอซ้ายบนสุด")
    print("-" * 55)
    
    # 1. รอจนกว่าจะเจอปุ่ม Relay 
    relay_box = wait_for_image("relay_btn", timeout=600)
    if not relay_box:
        print("❌ รอนานเกินไป ไม่พบปุ่ม Relay")
        return False
    
    # 2. พุ่งกดปุ่ม Relay ทันทีแบบสุ่มและไวจัดๆ
    left, top, width, height = relay_box
    pad_x, pad_y = int(width * 0.15), int(height * 0.15)
    target_x = random.randint(left + pad_x, left + width - pad_x)
    target_y = random.randint(top + pad_y, top + height - pad_y)
    
    fast_reaction = random.uniform(0.08, 0.2)
    print(f"⚡ เจอ Relay แล้ว! พุ่งกดด้วยเวลาตอบสนอง {fast_reaction:.2f} วินาที!")
    pyautogui.moveTo(target_x, target_y, duration=fast_reaction, tween=pyautogui.easeOutQuad)
    pyautogui.click()
    time.sleep(0.5) 
    
    # 3. 🚨 [สำคัญ] คืนโค้ดกดปุ่มออกจากด่าน 3 ปุ่มกลับมาแล้วครับ! 🚨
    click_image("stop_btn", timeout=5)
    click_image("quit_btn", timeout=5)
    time.sleep(1)
    click_image("quit_confirm_btn", timeout=5)
    
    # 4. หลังจากออกจากด่านเสร็จ ค่อยเคลียร์หน้าจอด้วยความเร็วสูง
    print("\n🔄 เข้าสู่กระบวนการเคลียร์หน้าจอ (พุ่งชนปุ่ม OK ก่อน ถ้าไม่เจอค่อยเช็ค AFK)...")
    start_clear_time = time.time()
    
    popup_buttons = [
        "ok_btn", 
        "open_all_btn", 
        "confirm_btn", 
        "green_confirm_btn",
        "level_up_confirm_btn", 
        "treasure_confirm_btn"
    ]
    
    while time.time() - start_clear_time < 60: 
        try:
            pyautogui.locateOnScreen(ASSETS["main_menu_sign"], confidence=CONFIDENCE)
            print("\n" + "=" * 55)
            print("🎉 กลับถึงหน้า Main Menu เรียบร้อย!")
            print("=" * 55)
            return True
        except pyautogui.ImageNotFoundException:
            pass 
            
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
            
    print("❌ วนลูปเคลียร์ Pop-up นานเกินไป (60 วินาที) หาหน้า Main ไม่เจอ")
    return False

if __name__ == "__main__":
    try:
        print("🕒 กรุณาสลับไปยังหน้าต่างเกม...")
        time.sleep(3)
        run_phase_3()
    except pyautogui.FailSafeException:
        print("\n🛑 Emergency stop: Mouse ถูกลากไปมุมจอซ้ายบน")
    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาดร้ายแรง: {e}")
        import traceback
        traceback.print_exc()