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
    "confirm_green_btn": "assets/confirm_green_btn.png", 
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
# ==========================================
# 🛡️ ระบบตรวจจับหน้า Anti-AFK (อัปเดตใหม่)
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
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                if max_val >= threshold:
                    print(f"🚨 เจอหน้า Anti-AFK! max_val={max_val:.3f}")
                    return True
            except Exception as e:
                pass
            time.sleep(0.5)
            
    print("⏩ ไม่พบหน้าต่าง Anti-AFK ข้ามไปขั้นตอนต่อไป")
    return False

def is_afk_screen_present(threshold=AFK_THRESHOLD, monitor_index=1):
    """ฟังก์ชันเช็คแบบเรียลไทม์ว่าป้าย Anti-AFK ยังอยู่บนจอหรือไม่"""
    if AFK_TEMPLATE_GRAY is None:
        return False
    with MSS() as sct:
        screenshot = np.array(sct.grab(sct.monitors[monitor_index]))
        screen_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
        res = cv2.matchTemplate(screen_gray, AFK_TEMPLATE_GRAY, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        return max_val >= threshold

def solve_afk_puzzle():
    """
    แก้ Anti-AFK แบบ Dynamic Loop ทำจนกว่าป้าย AFK จะหายไป (ใช้ Smart Delay)
    """
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
        time.sleep(2.5) # ใช้การหน่วงเวลาตายตัวรอไพ่วางเสร็จ
        
        # แคปภาพทันทีโดยไม่ต้องสนว่าภาพขยับอยู่หรือไม่
        current_cards = capture_cards(debug=True)
            
        target1, target2, conf = detect_odd_two_cards(current_cards, method="ncc", debug=True)
        
        # ถ้าระบบคำนวณแล้วงง แปลว่าอาจจะแคปจังหวะไพ่กระพริบพอดี ให้ลองแคปใหม่
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
# 🚀 ฟังก์ชันหลัก Phase 3 (อัปเดตเคลียร์ Pop-up)
# ==========================================
# ==========================================
# 🚀 ฟังก์ชันหลัก Phase 3 (ลอจิกสแกนเคลียร์ Pop-up อัตโนมัติ)
# ==========================================
def run_phase_3():
    print("=" * 55)
    print("🏁 [PHASE 3] เริ่มต้นระบบจัดการหลังจบเกม")
    print("=" * 55)
    
    check_display_scale()
    
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
    if wait_for_afk_page(timeout=15): 
        solve_afk_puzzle()
    else:
        print("⏩ ไม่พบหน้าต่าง Anti-AFK ข้ามไปหน้า Result ทันที")
    
    # 4. วนลูปสแกนปุ่มและเคลียร์ Pop-up จนกว่าจะเห็นหน้า Main Menu
    print("\n🔄 กำลังเคลียร์หน้าต่าง Pop-up ทั้งหมดจนกว่าจะถึงหน้า Main Menu...")
    start_clear_time = time.time()
    
    # รายชื่อปุ่มทั้งหมดที่โผล่มาขวางได้ (เรียงตามความสำคัญ)
    popup_buttons = ["ok_btn", "open_all_btn", "confirm_btn", "green_confirm_btn"]
    
    while time.time() - start_clear_time < 60: # ให้เวลาเคลียร์สูงสุด 60 วินาที
        
        # เป้าหมายสูงสุด: เช็คก่อนเลยว่าถึงหน้า Main Menu หรือยัง?
        try:
            pyautogui.locateOnScreen(ASSETS["main_menu_sign"], confidence=CONFIDENCE)
            print("\n" + "=" * 55)
            print("🎉 กลับถึงหน้า Main Menu เรียบร้อย!")
            print("=" * 55)
            return True
        except pyautogui.ImageNotFoundException:
            pass # ถ้ายังไม่เจอ แปลว่ายังมีอะไรบังอยู่ ลุยสแกนปุ่มต่อ
            
        # กวาดสายตาหาปุ่มปิด Pop-up 
        clicked_any = False
        for btn in popup_buttons:
            # ใช้ timeout สั้นๆ แค่ 0.5 วินาที เพื่อให้มันกวาดตาเช็คทุกปุ่มอย่างรวดเร็ว
            if click_image(btn, timeout=0.5, delay_after=1.5, confidence=0.75):
                clicked_any = True
                break # พอกดปุ่มใดปุ่มหนึ่งสำเร็จ ให้ออกจากลูป for กลับไปตั้งต้นเช็ค Main Menu ใหม่
                
        # ถ้ากวาดตาดูแล้วไม่เจอปุ่มอะไรให้กดเลย อาจจะติดแอนิเมชันแจกของ ให้รอแป๊บนึงแล้ววนลูปใหม่
        if not clicked_any:
            time.sleep(0.5)
            
    print("❌ วนลูปเคลียร์ Pop-up นานเกินไป (60 วินาที) หาหน้า Main ไม่เจอ")
    return False


def is_afk_screen_present(threshold=AFK_THRESHOLD, monitor_index=1):
    """
    ฟังก์ชันช่วยเช็คแบบเรียลไทม์ว่าป้าย Anti-AFK ยังอยู่บนจอหรือไม่
    """
    if AFK_TEMPLATE_GRAY is None:
        return False
        
    with MSS() as sct:
        screenshot = np.array(sct.grab(sct.monitors[monitor_index]))
        screen_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2GRAY)
        res = cv2.matchTemplate(screen_gray, AFK_TEMPLATE_GRAY, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        return max_val >= threshold

def solve_afk_puzzle():
    """
    แก้ Anti-AFK แบบ Dynamic Loop ทำจนกว่าป้าย AFK จะหายไป
    """
    print("\n🚨 [DETECTED] เจอหน้าจอ Anti-AFK! เริ่มแก้วนลูปแบบไดนามิก...")
    print("-" * 50)
    
    stage = 1
    max_retries = 10 # 🛡️ ระบบเซฟตี้ ป้องกันลูปนรก (ถ้าแก้เกิน 10 รอบแปลว่าเกมค้างหรือบอทเอ๋อ ให้บังคับออก)
    
    # 🔄 ลูปจะทำงานก็ต่อเมื่อ "หน้า AFK ยังแสดงอยู่บนจอ" เท่านั้น
    while is_afk_screen_present():
        if stage > max_retries:
            print("❌ [ERROR] วนลูปแก้ AFK เกิน 10 รอบ! ระบบอาจขัดข้อง บังคับออกเพื่อป้องกันจอค้าง")
            break
            
        print(f"\n🧩 กำลังแก้ด่านที่ {stage}")
        print("⏳ รอการ์ดเซ็ตใหม่ปรากฏและหยุดนิ่ง...")
        
        # 1. รอภาพนิ่ง
        current_cards = wait_for_stable_cards(timeout=10, stable_time=0.5)
        if current_cards is None:
            print("⚠️ แคปการ์ดไม่สำเร็จ หรือภาพไม่นิ่ง ลองเช็คใหม่ในรอบถัดไป...")
            time.sleep(1)
            continue
            
        # 2. วิเคราะห์หาใบที่แปลก (เปิด Debug ไว้ เพื่อให้พิมพ์ Matrix ลง Terminal)
        target1, target2, conf = detect_odd_two_cards(current_cards, method="ncc", debug=True)
        
        if conf < 0.05:
            print(f"⚠️ Confidence ต่ำ ({conf:.2%}) ลองแคปภาพใหม่เพื่อความชัวร์...")
            time.sleep(1.0)
            # โหมดเซฟภาพ Debug: ไพ่ที่แคปใหม่จะถูกเซฟลงโฟลเดอร์ debug เสมอ
            current_cards = capture_cards(debug=True)
            target1, target2, conf = detect_odd_two_cards(current_cards, method="ncc", debug=True)
        else:
            # ถ้ามั่นใจ ก็สั่งเซฟภาพไพ่ชุดนี้ไว้ดูเล่นในโฟลเดอร์ debug ด้วย
            capture_cards(debug=True)
        
        print(f"🎯 แปลก 2 ใบ: ใบที่ {target1+1} และ ใบที่ {target2+1}")
        
        # 3. กดการ์ด
        time.sleep(0.5)
        click_card(target1)
        time.sleep(0.3)
        click_card(target2)
        
        # 4. รอให้เกมประมวลผลและเช็คผลลัพธ์
        print("⏳ รอดูผลลัพธ์และแอนิเมชันของเกม...")
        time.sleep(3.5) 
        
        stage += 1
        
    print("\n✅ หน้าต่าง Anti-AFK หายไปแล้ว! กลับสู่กระบวนการปกติ")
    print("-" * 50)


def wait_for_stable_cards(timeout=20, stable_time=1.0):
    """
    รอภาพนิ่ง ปรับ timeout เพิ่มเป็น 20 วิ และลดเวลารอนิ่งเหลือ 1.0 วิ 
    เพื่อให้จับภาพด่าน 1 และ 2 ได้ทันก่อนหมดเวลา
    """
    start = time.time()
    prev_cards = None
    stable_start = None
    
    with MSS() as sct:
        while time.time() - start < timeout:
            curr_cards = capture_cards()
            
            if curr_cards is not None and len(curr_cards) == 6:
                if prev_cards is not None:
                    # เทียบความต่างภาพ
                    diff = sum(cv2.norm(c, p, cv2.NORM_L2) for c, p in zip(curr_cards, prev_cards))
                    
                    if diff < 600:  # ขยายเกณฑ์ความนิ่งนิดหน่อย เผื่อมีเอฟเฟกต์แสงวิ้งๆ
                        if stable_start is None:
                            stable_start = time.time()
                        elif time.time() - stable_start >= stable_time:
                            print("  📸 ภาพหยุดนิ่งแล้ว! พร้อมวิเคราะห์")
                            return curr_cards
                    else:
                        stable_start = None
                
                prev_cards = curr_cards
            
            time.sleep(0.25)
            
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