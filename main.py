# -*- coding: utf-8 -*-
import time
import keyboard
import sys
import os
import random
import json
import pyautogui
from utils import get_asset_path, click_image

STATUS_FILE = "status.json"

# ดึงฟังก์ชันการทำงานจากทั้ง 3 เฟสเข้ามา
from src.phase1_prep import run_phase_1
from src.phase2_gameplay import run_phase_2
from src.phase3_endgame import run_phase_3

class BotScheduler:
    # ... (โค้ด __init__ และอัปเดต status.json เหมือนเดิม) ...

    def action_send_hearts(self):
        """ระบบส่งหัวใจ (เรียกใช้เครื่องมือจาก utils.py)"""
        self.current_phase = "ส่งหัวใจ (Human-like)"
        self.update_status_file()
        print("\n❤️ [HUMAN-LIKE] เริ่มกระบวนการส่งหัวใจให้เพื่อน...")
        
        # ตอนนี้เราสามารถเรียกใช้ click_image ได้ง่ายๆ แบบนี้เลย
        mailbox_icon = get_asset_path('mailbox_icon.png')
        
        try:
            if pyautogui.locateOnScreen(mailbox_icon, confidence=0.8) is not None:
                click_image('mailbox_icon.png')
                print("✅ เปิดกล่องจดหมายสำเร็จ")
                time.sleep(2.0) 
                
                if pyautogui.locateOnScreen(get_asset_path('quick_receive_btn.png'), confidence=0.8) is not None:
                    click_image('quick_receive_btn.png')
                    print("✅ กดปุ่ม Quick Receive & Send Lives แล้ว")
                    time.sleep(1.5)
                    
                    max_confirms = 100 
                    confirm_count = 0
                    while confirm_count < max_confirms:
                        # ใช้ timeout สั้นๆ สำหรับป๊อปอัป
                        if click_image('heart_confirm_btn.png', timeout=1.5, delay_after=0.5):
                            confirm_count += 1
                            print(f"   -> กด Confirm ส่งหัวใจคนที่ {confirm_count}")
                        else:
                            print(f"✅ ส่งหัวใจเสร็จสิ้นทั้งหมด {confirm_count} คน")
                            break
                            
                time.sleep(1.0)
                click_image('mailbox_close_btn.png', timeout=3.0)
                print("✅ ปิดกล่องจดหมาย กลับสู่หน้าหลัก")
            else:
                print("❌ หาปุ่มกล่องจดหมายหน้า Main ไม่เจอ")
        except pyautogui.ImageNotFoundException:
            print("❌ หาปุ่มกล่องจดหมายหน้า Main ไม่เจอ")
            
# =============================
# =============
# ⚙️ GLOBAL STATE (ตัวแปรสถานะระบบ)
# ==========================================
is_paused = False
cycle_count = 0


def emergency_quit():
    """ฟังก์ชันฉุกเฉินสำหรับปิดโปรแกรมทันทีเมื่อกด Q"""
    print("\n🛑 [SYSTEM] ได้รับคำสั่งยกเลิกจากปุ่ม Q ปิดบอทอย่างเป็นทางการ!")
    try:
        import pydirectinput
        # ปล่อยปุ่มทั้งหมดเผื่อบอทกดค้างไว้ตอนเราสั่งปิด
        pydirectinput.keyUp('up')
        pydirectinput.keyUp('down')
        pydirectinput.keyUp('f')
        pydirectinput.keyUp('j')
    except:
        pass
    os._exit(0)

def toggle_pause():
    """สลับสถานะ Pause / Resume เมื่อกดปุ่ม P"""
    global is_paused
    is_paused = not is_paused
    if is_paused:
        print("\n\n🟡 [SYSTEM] PAUSED - รับคำสั่งหยุดพัก! (บอทจะหยุดรอเมื่อจบแอคชั่นปัจจุบัน)")
    else:
        print("\n\n🟢 [SYSTEM] RESUMED - ลุยต่อ!")

def wait_if_paused():
    """ฟังก์ชันดักจับสถานะ Pause (เอาไว้คั่นระหว่าง Phase)"""
    global is_paused
    if is_paused:
        print("⏳ [SYSTEM] ระบบกำลังหยุดพัก... กด 'P' เพื่อรันบอทต่อ")
        while is_paused:
            time.sleep(0.5)

def print_dashboard():
    """ฟังก์ชันวาด UI บน Terminal แบบ Dynamic"""
    global cycle_count, is_paused
    
    # เคลียร์หน้าจอ Terminal ให้ดูสะอาดเหมือน Dashboard มืออาชีพ
    os.system('cls' if os.name == 'nt' else 'clear')
    
    status_text = "🟡 PAUSED (หยุดพัก)" if is_paused else "🟢 RUNNING (กำลังทำงาน)"
    
    print(r"""
     ██████╗ ███████╗██╗      ██████╗  ██████╗  ██████╗  ██████╗ 
    ██╔════╝ ██╔════╝██║     ██╔════╝ ██╔═══██╗██╔═══██╗██╔════╝ 
    ██║  ███╗█████╗  ██║     ██║  ███╗██║   ██║██║   ██║██║  ███╗
    ██║   ██║██╔══╝  ██║     ██║   ██║██║   ██║██║   ██║██║   ██║
    ╚██████╔╝███████╗███████╗╚██████╔╝╚██████╔╝╚██████╔╝╚██████╔╝
     ╚═════╝ ╚══════╝╚══════╝ ╚═════╝  ╚═════╝  ╚═════╝  ╚═════╝ 
    =============================================================
                  🤖 GELGOOG AUTO-FARMING SYSTEM v2.0
    =============================================================
    📊 SYSTEM STATS:
       - Cycles Completed : [ {} ] รอบ
       - Current Status   : {}
    =============================================================
    🎮 CONTROLS (สามารถกดได้ตลอดเวลา):
       [ S ] - Start      (เริ่มการทำงานรอบแรก)
       [ P ] - Pause      (หยุดพักชั่วคราว / ทำงานต่อ)
       [ Q ] - Quit       (ปิดโปรแกรมฉุกเฉิน)
    =============================================================
    """.format(cycle_count, status_text))

def start_full_cycle_bot():
    global cycle_count
    
    # ⚡ ผูกปุ่มลัดเข้ากับฟังก์ชันแบบ Global
    keyboard.add_hotkey('q', emergency_quit)
    keyboard.add_hotkey('p', toggle_pause)
    
    # แสดงหน้า Dashboard เริ่มต้น
    print_dashboard()
    print("🕒 [STANDBY] รอคำสั่ง... สลับไปหน้าเกมแล้วกด 'S' ")
    
    # หยุดรอตรงนี้จนกว่าคุณจะกดปุ่ม 's'
    keyboard.wait('s') 
    
    print("\n🚀 [SYSTEM] ได้รับคำสั่ง Start! เริ่มกระบวนการฟาร์ม...")
    time.sleep(1)
    
    # ลูปอนันต์ ทำงานข้ามวันข้ามคืน
    while True:
        cycle_count += 1
        
        # อัปเดตหน้า Dashboard ใหม่ทุกครั้งที่ขึ้นรอบใหม่
        print_dashboard()
        print(f"🌟🌟🌟 BEGIN CYCLE: {cycle_count} 🌟🌟🌟")
        
        # --- เริ่ม Phase 1 ---
        wait_if_paused()
        print("\n▶️ [STEP 1/3] เริ่ม Phase 1 (Preparation)...")
        success_p1 = run_phase_1()
        if not success_p1:
            print("⚠️ Phase 1 ทำงานผิดพลาด ระบบจะพยายามเริ่มใหม่...")
            cycle_count -= 1 # หักรอบออกเพราะทำงานไม่สำเร็จ
            time.sleep(2)
            continue
            
        # --- เริ่ม Phase 2 ---
        wait_if_paused()
        print("\n▶️ [STEP 2/3] เริ่ม Phase 2 (Gameplay)...")
        run_phase_2() 
        
        # --- เริ่ม Phase 3 ---
        wait_if_paused()
        print("\n▶️ [STEP 3/3] เริ่ม Phase 3 (Endgame & Anti-AFK)...")
        success_p3 = run_phase_3()
        if not success_p3:
            print("⚠️ Phase 3 ทำงานผิดพลาด ระบบอาจจะค้างอยู่ที่หน้าไหนสักแห่ง")
            break
            
        print(f"\n✅ [SUCCESS] จบ Cycle ที่ {cycle_count} อย่างสมบูรณ์ \n")
        
        # พักเครื่อง 2 วินาทีก่อนเริ่มรอบถัดไป (ดัก Pause ไว้ด้วยเผื่อกดตอนจบด่านพอดี)
        wait_if_paused()
        time.sleep(2) 

if __name__ == "__main__":
    start_full_cycle_bot()