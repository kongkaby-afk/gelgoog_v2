"""
phase3_endgame.py (ปรับปรุง)
- Dynamic Scan + AFK Solver + All Popups
- รองรับ level_up_confirm, treasure_confirm
- ระบบรอการ์ดนิ่ง + วนแก้ AFK จริง
"""

import os
import sys
import cv2
import numpy as np
import pyautogui
import time
from mss import MSS

# ==========================================
# ⚙️ CONFIG
# ==========================================
CONFIDENCE = 0.8
AFK_CONFIDENCE = 0.75
STAGE_SIM_THRESHOLD = 0.70          # ใช้ตัดสินว่าการ์ดเปลี่ยนด่าน
STABLE_SIM_THRESHOLD = 0.95         # ใช้รอให้การ์ดนิ่ง
MAX_AFK_RETRY_PER_STAGE = 5         # รีไทรสูงสุดต่อด่าน
LOOP_DELAY = 0.05                   # หน่วงระหว่างเปลี่ยนปุ่มใน dynamic scan
POST_CLICK_DELAY = 0.5
MAIN_MENU_STABLE_DURATION = 2

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
pyautogui.FAILSAFE = True

# ==========================================
# 🔍 DISPLAY SCALE CHECK
# ==========================================
def check_display_scale():
    try:
        import ctypes
        user32 = ctypes.windll.user32
        dc = user32.GetDC(0)
        scale_x = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)
        user32.ReleaseDC(0, dc)
        if scale_x != 96:
            print(f"⚠️ WARNING: Display Scale {int((scale_x/96)*100)}% ควรตั้งเป็น 100%")
    except:
        pass

# ==========================================
# 📂 TEMPLATES
# ==========================================
def load_template(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"❌ โหลด '{path}' ไม่ได้")
    else:
        print(f"✅ โหลด '{path}' สำเร็จ")
    return img

ASSET_PATHS = {
    "afk_page": "assets/afk_page.png",
    "relay_btn": "assets/relay_btn.png",
    "stop_btn": "assets/stop_btn.png",
    "quit_btn": "assets/quit_btn.png",
    "quit_confirm_btn": "assets/quit_confirm_btn.png",
    "ok_btn": "assets/ok_btn.png",
    "open_all_btn": "assets/open_all_btn.png",
    "confirm_btn": "assets/confirm_btn.png",
    "level_up_confirm_btn": "assets/level_up_confirm_btn.png",   # ใหม่
    "treasure_confirm_btn": "assets/treasure_confirm_btn.png",   # ใหม่
    "main_menu_sign": "assets/main_menu_sign.png",
}

TEMPLATES = {name: load_template(path) for name, path in ASSET_PATHS.items()}

# ==========================================
# 🖼️ CARD CAPTURE
# ==========================================
def capture_cards():
    captured = []
    with MSS() as sct:
        for region in cards_regions:
            x, y, w, h = map(int, region)
            monitor = {"top": y, "left": x, "width": w, "height": h}
            img = np.array(sct.grab(monitor))
            gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (200, 300))
            captured.append(gray)
    return captured

def is_same_stage(cards_a, cards_b, threshold=STAGE_SIM_THRESHOLD):
    if cards_a is None or cards_b is None or len(cards_a) != len(cards_b):
        return False
    sims = []
    for a, b in zip(cards_a, cards_b):
        res = cv2.matchTemplate(a, b, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        sims.append(max_val)
    avg = sum(sims) / len(sims)
    print(f"  [Stage Compare] avg={avg:.3f}")
    return avg >= threshold

def wait_for_stable_cards(timeout=10):
    """รอจนกว่าการ์ดจะนิ่ง โดยเปรียบเทียบสองเฟรมติดกัน"""
    print("  📸 รอให้การ์ดนิ่ง...")
    start = time.time()
    last = None
    while time.time() - start < timeout:
        current = capture_cards()
        if current is None or len(current) != 6:
            time.sleep(0.3)
            continue
        if last is not None and is_same_stage(last, current, threshold=STABLE_SIM_THRESHOLD):
            print("  ✅ การ์ดนิ่งแล้ว")
            return current
        last = current
        time.sleep(0.3)
    print("  ⚠️ หมดเวลารอการ์ดนิ่ง")
    return last

# ==========================================
# 🧩 PUZZLE SOLVER
# ==========================================
def compute_similarity_matrix(images):
    n = len(images)
    sim = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i == j:
                sim[i][j] = 1.0
                continue
            res = cv2.matchTemplate(images[i], images[j], cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            sim[i][j] = max_val
    return sim

def detect_odd_two_cards(images):
    n = len(images)
    sim = compute_similarity_matrix(images)
    dissim = 1.0 - sim
    odd_scores = np.sum(dissim, axis=1) / (n - 1)
    sorted_idx = np.argsort(odd_scores)[::-1]
    top1, top2, third = int(sorted_idx[0]), int(sorted_idx[1]), int(sorted_idx[2])
    gap = odd_scores[top2] - odd_scores[third]
    confidence = gap / odd_scores[top1] if odd_scores[top1] > 0 else 0.0
    print(f"\n📊 Similarity:\n{np.round(sim, 3)}")
    print("🔥 Odd Scores:")
    for i in range(n):
        marker = "⬅️ เลือก" if i in [top1, top2] else ""
        print(f"  ใบที่ {i+1}: {odd_scores[i]:.4f} {marker}")
    print(f"✅ Confidence: {confidence:.2%}")
    return top1, top2, confidence

def click_card(index):
    region = cards_regions[index]
    x = int(region[0] + region[2] / 2)
    y = int(region[1] + region[3] / 2)
    pyautogui.click(x, y)
    print(f"🖱️ คลิกการ์ดใบที่ {index+1}")

# ==========================================
# 🖱️ UI CLICK UTILS
# ==========================================
def locate_image(name, confidence=None):
    if name not in TEMPLATES or TEMPLATES[name] is None:
        return None
    conf = confidence or CONFIDENCE
    path = ASSET_PATHS[name]
    try:
        return pyautogui.locateCenterOnScreen(path, confidence=conf)
    except:
        return None

def is_image_present(name, confidence=None):
    return locate_image(name, confidence) is not None

def click_image(name, delay=POST_CLICK_DELAY, confidence=None):
    loc = locate_image(name, confidence)
    if loc:
        pyautogui.click(loc.x, loc.y)
        print(f"✅ คลิก [{name}]")
        time.sleep(delay)
        return True
    return False

def click_image_with_validation(name, max_attempts=3, delay=POST_CLICK_DELAY):
    """กดปุ่มแล้วรอจนกว่ามันจะหายไป"""
    for _ in range(max_attempts):
        loc = locate_image(name)
        if loc is None:
            return True  # หายไปแล้ว
        pyautogui.click(loc.x, loc.y)
        time.sleep(delay)
        # รอสักครู่ให้ UI อัปเดต
        time.sleep(0.5)
    return not is_image_present(name)

def is_afk_screen():
    return is_image_present("afk_page", confidence=AFK_CONFIDENCE)

# ==========================================
# 🛡️ AFK SOLVER (วนแก้จนกว่า AFK จะหาย)
# ==========================================
def solve_afk_puzzle():
    print("\n🚨 [AFK] เริ่มแก้ปริศนา...")
    stage = 0
    while is_afk_screen():
        stage += 1
        print(f"\n🧩 AFK Stage #{stage}")
        solved = False
        for retry in range(MAX_AFK_RETRY_PER_STAGE):
            print(f"  🔄 ลองครั้งที่ {retry+1}")
            before = wait_for_stable_cards(timeout=10)
            if before is None:
                break

            for i, card in enumerate(before):
                cv2.imwrite(f"debug/afk_s{stage}_r{retry+1}_card{i+1}.png", card)

            t1, t2, conf = detect_odd_two_cards(before)
            if conf < 0.05:
                print("  ⚠️ Confidence ต่ำ ลองใหม่")
                time.sleep(0.5)
                before = capture_cards()
                t1, t2, conf = detect_odd_two_cards(before)

            click_card(t1)
            time.sleep(0.3)
            click_card(t2)

            print("  ⏳ รอหน้าจอตอบสนอง...")
            time.sleep(2.0)

            if not is_afk_screen():
                print("  ✅ AFK หายไปแล้ว")
                return

            after = capture_cards()
            if after and is_same_stage(after, before, threshold=STAGE_SIM_THRESHOLD):
                print("  🔄 การ์ดยังเหมือนเดิม (กดผิด) ลองใหม่")
                continue
            else:
                print("  ✅ ด่านเปลี่ยน")
                solved = True
                break

        if not solved:
            print(f"  ❌ ด่าน #{stage} ทำไม่สำเร็จหลังจาก {MAX_AFK_RETRY_PER_STAGE} ครั้ง")
            # หลุดจาก while เพราะ AFK อาจยังอยู่ แต่กัน infinite loop
            break
        time.sleep(1.0)
    print("✅ ออกจากหน้า Anti-AFK แล้ว")

# ==========================================
# 🤖 DYNAMIC SCAN LOOP
# ==========================================
def run_phase_3():
    print("=" * 55)
    print("🏁 [PHASE 3] Dynamic Scan Mode (ทุกปุ่ม + AFK)")
    print("=" * 55)
    check_display_scale()
    print("ℹ️  หยุดฉุกเฉิน: ลากเมาส์ไปมุมซ้ายบน")
    print("-" * 55)

    # ลำดับการสแกน (Round‑Robin)
    SCAN_ORDER = [
        "relay_btn",                # รีบกด
        "stop_btn",
        "quit_btn",
        "quit_confirm_btn",
        "afk_page",                 # แก้ปริศนา
        "ok_btn",
        "open_all_btn",
        "confirm_btn",
        "level_up_confirm_btn",
        "treasure_confirm_btn",
        "main_menu_sign"            # จบบอท
    ]

    start_time = time.time()
    while True:
        if time.time() - start_time > 600:  # timeout 10 นาที
            print("❌ Timeout")
            return False

        # เดินหน้าตรวจทีละชื่อ
        for name in SCAN_ORDER:
            loc = locate_image(name)
            if loc is None:
                time.sleep(LOOP_DELAY)
                continue

            print(f"\n🎯 พบ: [{name}]")
            if name == "relay_btn":
                # กดทันที ไม่ต้อง validation
                pyautogui.click(loc.x, loc.y)
                print("⚡ กด Relay")
                time.sleep(0.1)
                break   # กลับไปเริ่มสแกนใหม่

            elif name == "afk_page":
                solve_afk_puzzle()
                break

            elif name == "main_menu_sign":
                # ต้องเสถียร
                print("⏳ ตรวจสอบ Main Menu...")
                stable = False
                for _ in range(5):
                    if not is_image_present("main_menu_sign"):
                        stable = False
                        break
                    time.sleep(0.5)
                if is_image_present("main_menu_sign"):
                    print("\n🎉 กลับถึง Main Menu แล้ว!")
                    return True
                else:
                    print("⚠️ Main Menu หลอกตา ทำต่อ")
                    break

            else:
                # ปุ่มทั่วไป กดด้วย validation
                click_image_with_validation(name)
                break

        # จบลูป for แล้วกลับไปเริ่มต้นใหม่
        time.sleep(0.2)

# ==========================================
# 🚀 ENTRY POINT
# ==========================================
if __name__ == "__main__":
    try:
        print("🕒 สลับไปหน้าต่างเกม...")
        time.sleep(3)
        run_phase_3()
    except pyautogui.FailSafeException:
        print("\n🛑 หยุดฉุกเฉิน")
    except Exception as e:
        print(f"\n❌ ผิดพลาด: {e}")
        import traceback
        traceback.print_exc()