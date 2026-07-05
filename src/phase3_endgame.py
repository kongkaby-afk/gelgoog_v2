import os
import sys
import cv2
import numpy as np
import pyautogui
import time
import keyboard
from mss import MSS

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

# สร้างโฟลเดอร์ debug ถ้ายังไม่มี
os.makedirs("debug", exist_ok=True)


# ==========================================
# 🚨 ตรวจสอบ Display Scale ของ Windows
# ==========================================
def check_display_scale():
    """
    เตือนถ้า Display Scale ไม่ใช่ 100% เพราะ pyautogui/MSS ใช้ pixel ตรงๆ
    """
    try:
        import ctypes
        user32 = ctypes.windll.user32
        dc = user32.GetDC(0)
        scale_x = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
        user32.ReleaseDC(0, dc)
        # 96 DPI = 100%
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
    "afk_page": "assets/afk_page.png",
    "relay_btn": "assets/relay_btn.png",
    "stop_btn": "assets/stop_btn.png",
    "quit_btn": "assets/quit_btn.png",
    "quit_confirm_btn": "assets/quit_confirm_btn.png",
    "ok_btn": "assets/ok_btn.png",
    "open_all_btn": "assets/open_all_btn.png",
    "confirm_btn": "assets/confirm_btn.png",
    "main_menu_sign": "assets/main_menu_sign.png",
}

templates = {name: load_template(path, cv2.IMREAD_UNCHANGED) for name, path in ASSETS.items()}
AFK_TEMPLATE_GRAY = cv2.imread(ASSETS["afk_page"], cv2.IMREAD_GRAYSCALE)


# ==========================================
# 🖼️ ระบบ Capture การ์ด
# ==========================================
def capture_cards(debug=False):
    """
    จับภาพการ์ด 6 ใบ แปลงเป็น Grayscale 200x300
    """
    captured = []
    
    with MSS() as sct:
        for idx, region in enumerate(cards_regions):
            x, y, w, h = int(region[0]), int(region[1]), int(region[2]), int(region[3])
            monitor = {"top": y, "left": x, "width": w, "height": h}
            
            img = np.array(sct.grab(monitor))
            # ตัด alpha ออก เอา BGR
            img_bgr = img[:, :, :3]
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (200, 300))
            
            captured.append(gray)
            
            if debug:
                cv2.imwrite(f"debug/card_{idx+1}.png", gray)
    
    return captured


# ==========================================
# 🧩 ระบบหา 2 ใบที่แปลก (NCC + MSE)
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
    """
    หา 2 ใบที่แปลกจากกลุ่ม โดยเปรียบเทียบทุกคู่
    
    return: (idx1, idx2, confidence)
    """
    n = len(images)
    
    if method == "ncc":
        sim_matrix = compute_similarity_matrix(images)
        dissim_matrix = 1.0 - sim_matrix
    else:
        raise ValueError("method รองรับแค่ 'ncc'")
    
    # คะแนนความแปลก = ค่าความไม่เหมือนเฉลี่ยกับใบอื่น
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
    """
    คลิก UI ตาม Template ที่โหลดไว้
    
    image_key: ชื่อ key ใน ASSETS เช่น 'relay_btn'
    """
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
# 🛡️ ระบบตรวจจับหน้า Anti-AFK
# ==========================================
def wait_for_afk_page(timeout=AFK_WAIT_TIMEOUT, threshold=AFK_THRESHOLD, monitor_index=1):
    """
    รอและตรวจหาหน้า Anti-AFK แบบวนลูป
    """
    if AFK_TEMPLATE_GRAY is None:
        print("❌ ไม่สามารถตรวจ AFK ได้เพราะ Template โหลดไม่ติด")
        return False
    
    print(f"⏳ เริ่มตรวจหาหน้า Anti-AFK (timeout {timeout} วิ, threshold {threshold})...")
    start = time.time()
    
    with MSS() as sct:
        while time.time() - start < timeout:
            try:
                screenshot = np.array(sct.grab(sct.monitors[monitor_index]))
                screen_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
                
                res = cv2.matchTemplate(screen_gray, AFK_TEMPLATE_GRAY, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                print(f"  [AFK Check] max_val={max_val:.3f} at {max_loc}")
                
                if max_val >= threshold:
                    print(f"🚨 เจอหน้า Anti-AFK! max_val={max_val:.3f}")
                    return True
                
                # บันทึกภาพล่าสุดเอาไว้ debug
                cv2.imwrite("debug/last_afk_check.png", screen_gray)
                
            except Exception as e:
                print(f"⚠️ Error ตรวจ AFK: {e}")
            
            time.sleep(0.5)
    
    print(f"❌ หมดเวลาตรวจหา Anti-AFK ({timeout} วิ) - ไม่เจอ")
    print("💾 บันทึกภาพสุดท้ายไว้ที่ debug/last_afk_check.png")
    return False


def solve_afk_puzzle():
    """
    แก้ Anti-AFK 3 ด่าน
    """
    print("\n🚨 [DETECTED] เจอหน้าจอ Anti-AFK แล้ว! เริ่มแก้ด้วย Traditional CV...")
    print("-" * 50)
    
    for stage in range(1, 4):
        print(f"\n🧩 ด่านที่ {stage}/3")
        print("⏳ กำลังรอการ์ดเซ็ตใหม่ปรากฏและหยุดนิ่ง...")
        
        # ใช้ระบบใหม่: รอจนกว่าภาพจะนิ่ง 1.5 วินาที
        current_cards = wait_for_stable_cards(timeout=15, stable_time=1.5)
        if current_cards is None:
            print("⚠️ ไม่สามารถ capture การ์ดที่นิ่งได้ ข้ามด่านนี้")
            continue
        
        # วิเคราะห์หา 2 ใบแปลก
        target1, target2, conf = detect_odd_two_cards(current_cards, debug=True)
        
        # ถ้า confidence ต่ำมาก ให้ capture ใหม่ครั้งหนึ่ง
        if conf < 0.05:
            print(f"⚠️ Confidence ต่ำ ({conf:.2%}) ขอเวลาให้ชัวร์แล้ว capture ใหม่...")
            time.sleep(1.0)
            current_cards = capture_cards()
            target1, target2, conf = detect_odd_two_cards(current_cards, debug=True)
        
        print(f"🎯 แปลก 2 ใบ: ใบที่ {target1+1} และ ใบที่ {target2+1}")
        
        # กดการ์ด 2 ใบ
        time.sleep(0.5)
        click_card(target1)
        time.sleep(0.3)
        click_card(target2)
        
        if stage < 3:
            print("⏳ รอแอนิเมชันเปลี่ยนด่าน...")
            time.sleep(3.5) # ⚠️ เพิ่มเวลาเผื่อแอนิเมชันไพ่หายและแจกใหม่ให้ชัวร์
            
    print("\n✅ แก้ Anti-AFK เสร็จสมบูรณ์!")
    print("-" * 50)


def wait_for_stable_cards(timeout=15, stable_time=1.5):
    
    start = time.time()
    prev_cards = None
    stable_start = None
    
    with MSS() as sct:
        while time.time() - start < timeout:
            curr_cards = capture_cards()
            
            if curr_cards is not None and len(curr_cards) == 6:
                if prev_cards is not None:
                    
                    diff = sum(cv2.norm(c, p, cv2.NORM_L2) for c, p in zip(curr_cards, prev_cards))
                    
                    if diff < 500: 
                        if stable_start is None:
                            stable_start = time.time()
                        elif time.time() - stable_start >= stable_time:
                            print("  📸 ภาพหยุดนิ่งแล้ว! พร้อมวิเคราะห์")
                            return curr_cards 
                    else:
                        stable_start = None 
                
                prev_cards = curr_cards
            
            time.sleep(0.2)
            
    print("⚠️ รอภาพนิ่งนานเกินไป (Timeout)")
    return None


# ==========================================
# 🚀 ฟังก์ชันหลัก Phase 3
# ==========================================
def run_phase_3():
    print("=" * 55)
    print("🏁 [PHASE 3] เริ่มต้นระบบจัดการหลังจบเกม")
    print("=" * 55)
    
    check_display_scale()
    print("ℹ️  หมายเหตุ: หากต้องการหยุดฉุกเฉิน ให้ลาก Mouse ไปมุมจอซ้ายบนสุด")
    print("-" * 55)
    
    # 1. รอปุ่ม Relay
    if not wait_for_image("relay_btn", timeout=600):
        print("❌ รอนานเกินไป ไม่พบปุ่ม Relay")
        return False
    
    # 2. ลำดับออกจากเกม
    click_image("relay_btn", timeout=5)
    click_image("stop_btn", timeout=5)
    click_image("quit_btn", timeout=5)
    time.sleep(1)
    click_image("quit_confirm_btn", timeout=5)
    
    # 3. ตรวจสอบ Anti-AFK
    print("\n🛡️ กำลังตรวจสอบหน้าจอ Anti-AFK...")
    if wait_for_afk_page():
        solve_afk_puzzle()
    else:
        print("⏩ ไม่พบหน้าต่าง Anti-AFK ข้ามไปหน้า Result ทันที")
    
    # 4. จัดการหน้า Result
    click_image("ok_btn", timeout=15)
    click_image("ok_btn", timeout=5)
    click_image("open_all_btn", timeout=5)
    
    # 5. วนกด Confirm เพื่อเคลียร์ Pop-up ให้เกลี้ยงแล้วกลับ Main Menu
    print("\n🔄 กำลังเคลียร์หน้าต่าง Pop-up เพื่อกลับไปหน้าหลัก...")
    start_confirm_time = time.time()
    
    while time.time() - start_confirm_time < 60:
        # 1. ให้ความสำคัญกับการเคลียร์ Pop-up ก่อน ถ้าเจอต้องกด!
        clicked_confirm = click_image("confirm_btn", timeout=1, delay_after=1.5)
        
        if clicked_confirm:
            # ถ้าเพิ่งกดไป ให้วนลูปกลับไปเช็คใหม่เผื่อมี Pop-up ซ้อนกันอีก ห้ามเพิ่งเช็ค Main Menu
            continue
            
        # 2. ถ้าหาปุ่ม Confirm ไม่เจอแล้ว (Pop-up หมดแล้ว) ค่อยมาเช็คว่าถึงหน้า Main Menu จริงๆ หรือยัง
        try:
            pyautogui.locateOnScreen(ASSETS["main_menu_sign"], confidence=CONFIDENCE)
            print("\n" + "=" * 55)
            print("🎉 กลับถึงหน้า Main Menu เรียบร้อย!")
            print("=" * 55)
            return True
        except pyautogui.ImageNotFoundException:
            pass
            
    print("❌ วนลูปกด Confirm นานเกินไป หาหน้า Main ไม่เจอ")
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