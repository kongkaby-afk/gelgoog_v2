# -*- coding: utf-8 -*-
import time
import keyboard
import sys
import os
import random
import json
import pyautogui

from utils import get_asset_path, click_image, write_log

STATUS_FILE = "status.json"

from src.phase1_prep import run_phase_1
from src.phase2_gameplay import run_phase_2
from src.phase3_endgame import run_phase_3

class BotScheduler:
    def action_send_hearts(self):
        print("\n❤️ [HUMAN-LIKE] เริ่มกระบวนการส่งหัวใจให้เพื่อน...")
        mailbox_icon = get_asset_path('mailbox_icon.png')
        try:
            if pyautogui.locateOnScreen(mailbox_icon, confidence=0.8) is not None:
                click_image('mailbox_icon.png')
                time.sleep(2.0) 
                if pyautogui.locateOnScreen(get_asset_path('quick_receive_btn.png'), confidence=0.8) is not None:
                    click_image('quick_receive_btn.png')
                    time.sleep(1.5)
                    max_confirms = 100 
                    confirm_count = 0
                    while confirm_count < max_confirms:
                        if click_image('heart_confirm_btn.png', timeout=1.5, delay_after=0.5):
                            confirm_count += 1
                        else:
                            break
                time.sleep(1.0)
                click_image('mailbox_close_btn.png', timeout=3.0)
        except pyautogui.ImageNotFoundException:
            pass
            
is_paused = False
cycle_count = 0

def emergency_quit():
    print("\n🛑 [SYSTEM] ได้รับคำสั่งยกเลิกจากปุ่ม Q ปิดบอทอย่างเป็นทางการ!")
    try:
        import pydirectinput
        pydirectinput.keyUp('up')
        pydirectinput.keyUp('down')
        pydirectinput.keyUp('f')
        pydirectinput.keyUp('j')
    except:
        pass
    os._exit(0)

def toggle_pause():
    global is_paused
    is_paused = not is_paused
    if is_paused:
        print("\n\n🟡 [SYSTEM] PAUSED - รับคำสั่งหยุดพัก! (บอทจะหยุดรอเมื่อจบแอคชั่นปัจจุบัน)")
    else:
        print("\n\n🟢 [SYSTEM] RESUMED - ลุยต่อ!")

def wait_if_paused():
    global is_paused
    if is_paused:
        print("⏳ [SYSTEM] ระบบกำลังหยุดพัก... กด 'P' เพื่อรันบอทต่อ")
        while is_paused:
            time.sleep(0.5)

def print_dashboard():
    global cycle_count, is_paused
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
    
    keyboard.add_hotkey('q', emergency_quit)
    keyboard.add_hotkey('p', toggle_pause)
    
    print_dashboard()
    print("🕒 [STANDBY] รอคำสั่ง... สลับไปหน้าเกมแล้วกด 'S' ")
    keyboard.wait('s') 
    
    print("\n🚀 [SYSTEM] ได้รับคำสั่ง Start! เริ่มกระบวนการฟาร์ม...")
    time.sleep(1)
    
    # 🎯 [แก้ไขบั๊กแล้ว] กำหนดเป้าหมายการพักเบรกล่วงหน้า
    next_break_cycle = random.randint(12, 18)
    
    while True:
        cycle_count += 1
        print_dashboard()
        print(f"🌟🌟🌟 BEGIN CYCLE: {cycle_count} (Next Break at: {next_break_cycle}) 🌟🌟🌟")
        
        write_log(f"----- เริ่มการทำงานรอบที่ {cycle_count} -----")

        wait_if_paused()
        print("\n▶️ [STEP 1/3] เริ่ม Phase 1 (Preparation)...")
        success_p1 = run_phase_1()
        if not success_p1:
            print("⚠️ Phase 1 ทำงานผิดพลาด ระบบจะพยายามเริ่มใหม่...")
            write_log("Phase 1 ล้มเหลว สั่งยกเลิกรอบนี้เพื่อเริ่มใหม่", level="ERROR") # <--- จด Log
            cycle_count -= 1 
            time.sleep(2)
            continue
            
        wait_if_paused()
        run_phase_2() 
        
        wait_if_paused()
        success_p3 = run_phase_3()
        if not success_p3:
            break
            
        print(f"\n✅ [SUCCESS] จบ Cycle ที่ {cycle_count} อย่างสมบูรณ์ \n")
        
        # ☕ เช็คว่าถึงรอบที่กำหนดให้พักหรือยัง
        if cycle_count >= next_break_cycle:
            break_time = random.randint(180, 420)
            mins = break_time // 60
            secs = break_time % 60
            print("="*55)
            print(f"☕ [FATIGUE] คนเล่นรู้สึกเมื่อยตา ขอพักเบรกหยิบน้ำ ลุกเดินไปเข้าห้องน้ำ...")
            print(f"⏳ บอทจะหยุดทำงานเป็นเวลา {mins} นาที {secs} วินาที")
            print("="*55)
            
            pyautogui.moveTo(100, 100, duration=1.5, tween=pyautogui.easeInOutQuad)
            time.sleep(break_time)
            
            print("🔋 กลับมานั่งหน้าคอมแล้ว! พร้อมลุยรอบต่อไป!")
            # สุ่มเป้าหมายพักเบรกรอบถัดไป
            next_break_cycle = cycle_count + random.randint(12, 18)
            
        wait_if_paused()
        time.sleep(2) 

if __name__ == "__main__":
    start_full_cycle_bot()