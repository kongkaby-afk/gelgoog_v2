# -*- coding: utf-8 -*-
import os
import sys
import cv2
import numpy as np
import pyautogui
import time
import keyboard
from mss import MSS

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

# 🎯 จุดสำคัญ: ครอบที่อยู่ไฟล์ทั้งหมดด้วย resource_path()
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

# ... (โค้ดฟังก์ชัน capture_cards และอื่นๆ ด้านล่างคงเดิมได้เลยครับ) ...

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
def click_card(index, duration=0.05):
    region = cards_regions[index]
    center_x = int(region[0] + region[2] / 2)
    center_y = int(region[1] + region[3] / 2)
    pyautogui.moveTo(center_x, center_y, duration=duration)
    pyautogui.click()
    print(f"  🖱️ คลิกการ์ดใบที่ {index + 1} ({center_x}, {center_y})")

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
            location = pyautogui.locateCenterOnScreen(template_path, confidence=conf)
            if location is not None:
                pyautogui.moveTo(location.x, location.y, duration=0.1)
                pyautogui.click()
                print(f"✅ คลิก [{image_key}] สำเร็จ!")
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
            loc = pyautogui.locateCenterOnScreen(template_path, confidence=CONFIDENCE)
            if loc is not None:
                print(f"👀 เจอ [{image_key}] แล้ว")
                return loc
        except:
            pass
        time.sleep(0.3)
    
    return None

# ==========================================
# 🛡️ ระบบตรวจจับและแก้หน้า Anti-AFK
# ==========================================
def wait_for_afk_page(timeout=AFK_WAIT_TIMEOUT, threshold=AFK_THRESHOLD, monitor_index=1):
    if AFK_TEMPLATE_GRAY is None:
        return False
    
    print(f"⏳ เริ่มตรวจหาหน้า Anti-AFK (timeout {timeout} วิ)...")
    start = time.time()
    
    with MSS() as sct:
        while time.time() - start < timeout:
            try:
                screenshot = np.array(sct.grab(sct.monitors[monitor_index]))
                screen_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
                res = cv2.matchTemplate(screen_gray, AFK_TEMPLATE_GRAY, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                
                if max_val >= threshold:
                    print(f"🚨 เจอหน้า Anti-AFK! max_val={max_val:.3f}")
                    return True
            except Exception:
                pass
            time.sleep(0.5)
            
    print("⏩ ไม่พบหน้าต่าง Anti-AFK ข้ามไปขั้นตอนต่อไป")
    return False

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
    print("-" * 50)

# ==========================================
# 🚀 ฟังก์ชันหลัก Phase 3 (สแกนเคลียร์ Pop-up)
# ==========================================
def run_phase_3():
    print("=" * 55)
    print("🏁 [PHASE 3] เริ่มต้นระบบจัดการหลังจบเกม")
    print("=" * 55)
    
    check_display_scale()
    print("ℹ️  หมายเหตุ: หากต้องการหยุดฉุกเฉิน ให้ลาก Mouse ไปมุมจอซ้ายบนสุด")
    print("-" * 55)
    
    if not wait_for_image("relay_btn", timeout=600):
        print("❌ รอนานเกินไป ไม่พบปุ่ม Relay")
        return False
    
    click_image("relay_btn", timeout=5)
    click_image("stop_btn", timeout=5)
    click_image("quit_btn", timeout=5)
    time.sleep(1)
    click_image("quit_confirm_btn", timeout=5)
    
    print("\n🛡️ กำลังตรวจสอบหน้าจอ Anti-AFK...")
    if wait_for_afk_page(timeout=15): 
        solve_afk_puzzle()
    else:
        print("⏩ ไม่พบหน้าต่าง Anti-AFK ข้ามไปหน้า Result ทันที")
    
    print("\n🔄 กำลังเคลียร์หน้าต่าง Pop-up ทั้งหมดจนกว่าจะถึงหน้า Main Menu...")
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
            if click_image(btn, timeout=0.5, delay_after=1.5, confidence=0.75):
                clicked_any = True
                break 
                
        if not clicked_any:
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