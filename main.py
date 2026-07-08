# -*- coding: utf-8 -*-
import time
import keyboard
import sys
import os
import random
import json
import pyautogui

# นำเข้าฟังก์ชันจาก utils และ phases (ปรับให้รับ config เข้าไป)
# หมายเหตุ: เตรียมอัปเดตไฟล์ Phase 1-3 ให้รับ parameter config ด้วยนะครับ
from utils import get_asset_path, click_image, write_log
from src.phase1_prep import run_phase_1
from src.phase2_gameplay import run_phase_2
from src.phase3_endgame import run_phase_3

CONFIG_FILE = "config.json"
is_paused = False
cycle_count = 0

# ==========================================
# ⚙️ ระบบจัดการ Configuration
# ==========================================
def load_config():
    default_config = {
        "mode": "AI",
        "buy_boost": False,
        "buy_relay": False,
        "roll_double_coin": False,
        "use_in_game_boost": False,
        "use_relay_death": False,
        "auto_claim_relic": True
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return default_config

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

# ==========================================
# 🖥️ หน้าต่าง Setup Menu (ตั้งค่าก่อนรัน)
# ==========================================
def print_setup_menu(config):
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=============================================================")
    print("              🤖 GELGOOG AUTO-FARMING SETTINGS")
    print("=============================================================")
    print(f"   [1] 🎮 Mode            : [ {config['mode']} ]")
    print(f"   [2] 🛒 Buy Boost       : [ {'ON' if config['buy_boost'] else 'OFF'} ]")
    print(f"   [3] 🛒 Buy Relay       : [ {'ON' if config['buy_relay'] else 'OFF'} ]")
    print(f"   [4] 🎲 Roll Double Coin: [ {'ON' if config['roll_double_coin'] else 'OFF'} ]")
    print(f"   [5] ⚡ Use In-Game Boost: [ {'ON' if config['use_in_game_boost'] else 'OFF'} ]")
    print(f"   [6] 🔄 Use Relay Death : [ {'ON' if config['use_relay_death'] else 'OFF'} ]")
    print(f"   [7] 🏺 Auto Claim Relic: [ {'ON' if config['auto_claim_relic'] else 'OFF'} ]")
    print("=============================================================")
    print("   👉 พิมพ์เลข [1-7] เพื่อสลับการตั้งค่า")
    print("   👉 พิมพ์ [S] เพื่อเริ่มบอท  |  พิมพ์ [Q] เพื่อออก")
    print("=============================================================")

def setup_bot():
    config = load_config()
    while True:
        print_setup_menu(config)
        choice = input("เลือกคำสั่ง: ").strip().upper()
        
        if choice == '1':
            config['mode'] = "AFK 1 Box" if config['mode'] == "AI" else "AI"
        elif choice == '2':
            config['buy_boost'] = not config['buy_boost']
        elif choice == '3':
            config['buy_relay'] = not config['buy_relay']
        elif choice == '4':
            config['roll_double_coin'] = not config['roll_double_coin']
        elif choice == '5':
            config['use_in_game_boost'] = not config['use_in_game_boost']
        elif choice == '6':
            config['use_relay_death'] = not config['use_relay_death']
        elif choice == '7':
            config['auto_claim_relic'] = not config['auto_claim_relic']
        elif choice == 'S':
            save_config(config)
            print("\n✅ บันทึกการตั้งค่าแล้ว! เตรียมตัวเข้าสู่โหมดฟาร์ม...")
            time.sleep(1)
            return config
        elif choice == 'Q':
            print("\n🛑 ปิดโปรแกรมอย่างเป็นทางการ")
            sys.exit(0)
            
        save_config(config)

# ==========================================
# 🎮 ระบบควบคุมระหว่างรัน
# ==========================================
def emergency_quit():
    print("\n🛑 [SYSTEM] ได้รับคำสั่งยกเลิกจากปุ่ม Q ปิดบอทอย่างเป็นทางการ!")
    try:
        import pydirectinput
        pydirectinput.keyUp('f')
        pydirectinput.keyUp('j')
    except:
        pass
    os._exit(0)

def toggle_pause():
    global is_paused
    is_paused = not is_paused
    if is_paused:
        print("\n\n🟡 [SYSTEM] PAUSED - รับคำสั่งหยุดพัก! (บอทจะหยุดเมื่อจบแอคชั่นปัจจุบัน)")
    else:
        print("\n\n🟢 [SYSTEM] RESUMED - ลุยต่อ!")

def wait_if_paused():
    global is_paused
    if is_paused:
        print("⏳ [SYSTEM] ระบบกำลังหยุดพัก... กด 'P' เพื่อรันบอทต่อ")
        while is_paused:
            time.sleep(0.5)

def print_run_dashboard(config):
    global cycle_count, is_paused
    os.system('cls' if os.name == 'nt' else 'clear')
    status_text = "🟡 PAUSED" if is_paused else "🟢 RUNNING"
    
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
       - Current Mode     : [ {} ]
       - Cycles Completed : [ {} ] รอบ
       - Current Status   : {}
    =============================================================
    🎮 HOTKEYS (กดได้ตลอดเวลาเมื่อสลับหน้าจอมาที่เกม):
       [ P ] - Pause/Resume      (หยุดพักชั่วคราว / ลุยต่อ)
       [ Q ] - Quit              (ปิดโปรแกรมฉุกเฉิน)
    =============================================================
    """.format(config['mode'], cycle_count, status_text))

# ==========================================
# 🚀 ลูปการฟาร์มหลัก
# ==========================================
def start_full_cycle_bot():
    global cycle_count
    
    # 1. เข้าสู่หน้าจอตั้งค่าก่อน
    config = setup_bot()
    
    # 2. ผูกปุ่ม Hotkeys
    keyboard.add_hotkey('q', emergency_quit)
    keyboard.add_hotkey('p', toggle_pause)
    
    # 3. เตรียมตัวรัน
    print_run_dashboard(config)
    print(f"🚀 [SYSTEM] เริ่มกระบวนการฟาร์มด้วยโหมด {config['mode']} ใน 3 วินาที...")
    time.sleep(3)
    
    next_break_cycle = random.randint(12, 18)
    
    while True:
        cycle_count += 1
        print_run_dashboard(config)
        print(f"🌟🌟🌟 BEGIN CYCLE: {cycle_count} (Next Break at: {next_break_cycle}) 🌟🌟🌟")
        write_log(f"----- เริ่มการทำงานรอบที่ {cycle_count} (Mode: {config['mode']}) -----")

        # Phase 1: Preparation
        wait_if_paused()
        print("\n▶️ [STEP 1/3] เริ่ม Phase 1 (Preparation)...")
        success_p1 = run_phase_1(config)  # <--- ส่ง config เข้าไป!
        if not success_p1:
            print("⚠️ Phase 1 ทำงานผิดพลาด สั่งเริ่มรอบใหม่...")
            write_log("Phase 1 ล้มเหลว สั่งยกเลิกรอบนี้", level="ERROR")
            cycle_count -= 1 
            time.sleep(2)
            continue
            
        # Phase 2: Gameplay (AI or AFK 1 Box)
        wait_if_paused()
        print("\n▶️ [STEP 2/3] เริ่ม Phase 2 (Gameplay)...")
        # 👇 รับค่า status กลับมา
        phase2_status = run_phase_2(config)  
        
        # Phase 3: Endgame (รับช่วงต่อหลังเจอกล่อง หรือ ตาย)
        wait_if_paused()
        print("\n▶️ [STEP 3/3] เริ่ม Phase 3 (Endgame)...")
        # 👇 โยน status เข้าไปบอก Phase 3
        success_p3 = run_phase_3(config, phase2_status)
        
        if not success_p3:
            print("⚠️ Phase 3 ทำงานผิดพลาด แต่จะพยายามดันเข้ารอบต่อไป...")
            time.sleep(2)
            
        print(f"\n✅ [SUCCESS] จบ Cycle ที่ {cycle_count} อย่างสมบูรณ์ \n")
        
        # ระบบจำลองความเหนื่อยล้า (Fatigue System)
        if cycle_count >= next_break_cycle:
            break_time = random.randint(180, 420)
            mins, secs = divmod(break_time, 60)
            print("="*55)
            print(f"☕ [FATIGUE] พักสายตา แกล้งไปเข้าห้องน้ำ...")
            print(f"⏳ บอทจะหยุดทำงานเป็นเวลา {mins} นาที {secs} วินาที")
            print("="*55)
            
            pyautogui.moveTo(100, 100, duration=1.5, tween=pyautogui.easeInOutQuad)
            time.sleep(break_time)
            
            next_break_cycle = cycle_count + random.randint(12, 18)
            
        wait_if_paused()
        time.sleep(2)

if __name__ == "__main__":
    start_full_cycle_bot()