import time
import keyboard
import sys
import os

# ดึงฟังก์ชันการทำงานจากทั้ง 3 เฟสเข้ามา
from src.phase1_prep import run_phase_1
from src.phase2_gameplay import run_phase_2
from src.phase3_endgame import run_phase_3

def emergency_quit():
    """ฟังก์ชันฉุกเฉินสำหรับปิดโปรแกรมทันทีเมื่อกด Q"""
    print("\n🛑 [QUIT] ได้รับคำสั่งยกเลิกจากปุ่ม Q ปิดบอทอย่างเป็นทางการ!")
    # ปล่อยปุ่มเผื่อค้าง
    import pydirectinput
    pydirectinput.keyUp('up')
    pydirectinput.keyUp('down')
    os._exit(0) # สั่งปิดโปรแกรมแบบเด็ดขาดทันที

def start_full_cycle_bot():
    print(r"""
     ██████╗ ██████╗  ██████╗ ██╗  ██╗██╗███████╗
    ██╔════╝██╔═══██╗██╔═══██╗██║ ██╔╝██║██╔════╝
    ██║     ██║   ██║██║   ██║█████╔╝ ██║█████╗  
    ██║     ██║   ██║██║   ██║██╔═██╗ ██║██╔══╝  
    ╚██████╗╚██████╔╝╚██████╔╝██║  ██╗██║███████╗
     ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝
    =============================================
             🤖 FULL CYCLE BOT ACTIVATED
    =============================================
    """)
    print("👉 กดปุ่ม [ S ] เพื่อ เริ่มการทำงาน (Start)")
    print("👉 กดปุ่ม [ Q ] เพื่อ ปิดโปรแกรมฉุกเฉิน (Quit)")
    print("=============================================\n")
    
    # ⚡ ผูกปุ่ม Q เข้ากับฟังก์ชัน emergency_quit แบบ Global
    keyboard.add_hotkey('q', emergency_quit)
    
    print("🕒 รอคำสั่ง... สลับไปหน้าเกมแล้วกด 'S' เมื่อพร้อมลุย!")
    
    # ⚡ ระบบจะหยุดรอตรงนี้จนกว่าคุณจะกดปุ่ม 's'
    keyboard.wait('s') 
    
    print("\n🚀 ได้รับคำสั่ง Start! ลุยกันเลย...")
    time.sleep(1) # หน่วงเวลาเล็กน้อยให้คุณปล่อยนิ้วจากปุ่ม
    
    round_number = 1
    
    # ลูปอนันต์ ทำงานข้ามวันข้ามคืน
    while True:
        print(f"\n🌟🌟🌟 เริ่มต้นรอบการฟาร์มที่: {round_number} 🌟🌟🌟")
        
        # --- เริ่ม Phase 1 (ซื้อของเตรียมตัว) ---
        print("\n▶️ [STEP 1/3] เริ่ม Phase 1...")
        success_p1 = run_phase_1()
        if not success_p1:
            print("⚠️ Phase 1 ทำงานผิดพลาด ระบบจะพยายามเริ่มใหม่...")
            continue
            
        # --- เริ่ม Phase 2 (สมองกลเล่นเกม) ---
        print("\n▶️ [STEP 2/3] เริ่ม Phase 2...")
        run_phase_2() # จะรันไปเรื่อยๆ จนกว่าตัวละครจะตายและเจอปุ่ม Relay
        
        # --- เริ่ม Phase 3 (จัดการ Anti-AFK และจบเกม) ---
        print("\n▶️ [STEP 3/3] เริ่ม Phase 3...")
        success_p3 = run_phase_3()
        if not success_p3:
            print("⚠️ Phase 3 ทำงานผิดพลาด ระบบอาจจะค้างอยู่ที่หน้าไหนสักแห่ง")
            break
            
        print(f"✅ จบรอบที่ {round_number} สำเร็จอย่างงดงาม!\n")
        round_number += 1
        time.sleep(2) # พักเครื่อง 2 วินาทีก่อนเริ่มรอบถัดไป

if __name__ == "__main__":
    start_full_cycle_bot()