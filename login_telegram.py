import os
import sys
import asyncio
from telethon import TelegramClient, errors
from config import API_ID, API_HASH, SESSION_NAME

# Ensure UTF-8
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

async def main():
    print("=" * 60)
    print("       DANG NHAP TAI KHOAN TELEGRAM - KINGFOOD SCM")
    print("=" * 60)
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"\n[OK] Tai khoan da dang nhap san: {me.first_name} {getattr(me, 'last_name', '')} (@{getattr(me, 'username', '')}) (ID: {me.id})")
        print("\nKhong can dang nhap lai!")
        await client.disconnect()
        return

    print("\nChon phuong thuc dang nhap:")
    print("1. Dang nhap bang so dien thoai (Nhan ma 5 so gui ve Telegram Desktop)")
    print("2. Dang nhap bang ma QR (Quet bang camera Telegram tren dien thoai)")
    
    choice = input("\nNhap lua chon (1 hoac 2, mac dinh 1): ").strip() or "1"
    
    if choice == "2":
        print("\n[*] Dang khoi tao ma QR...")
        qr = await client.qr_login()
        print("\n" + "=" * 55)
        print("Vui long mo Telegram tren dien thoai:")
        print("Settings (Cai dat) -> Devices (Thiet bi) -> Link Desktop Device")
        print("Va quet ma QR (trinh duyet se tu dong mo anh ma QR):")
        qr_img_url = f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&data={qr.url}"
        print(f"\nLink xem anh QR: {qr_img_url}")
        print("=" * 55)
        try:
            import webbrowser
            webbrowser.open(qr_img_url)
        except Exception:
            pass
        
        print("\n[*] Dang doi ban quet ma QR (het han trong 60s)...")
        try:
            await qr.wait(timeout=60)
            me = await client.get_me()
            print(f"\n[THANH CONG] Da dang nhap: {me.first_name} {getattr(me, 'last_name', '')} (ID: {me.id})")
        except asyncio.TimeoutError:
            print("\n[!] Ma QR da het han, vui long chay lai script de thu lai.")
    else:
        phone = input("\nNhap so dien thoai Telegram (VD: +84912345678 hoac 0912345678): ").strip()
        if not phone.startswith("+"):
            if phone.startswith("0"):
                phone = "+84" + phone[1:]
            else:
                phone = "+" + phone
        
        print(f"[*] Dang gui ma xac nhan den: {phone}...")
        try:
            sent = await client.send_code_request(phone)
            print("[*] Telegram da gui ma OTP 5 chu so vao ung dung Telegram cua ban!")
            code = input("Nhap ma OTP 5 so: ").strip()
            
            try:
                await client.sign_in(phone, code)
            except errors.SessionPasswordNeededError:
                pwd = input("Tai khoan co bat bao mat 2 lop (2FA). Vui long nhap mat khau 2FA: ").strip()
                await client.sign_in(password=pwd)
                
            me = await client.get_me()
            print(f"\n[THANH CONG] Da dang nhap: {me.first_name} {getattr(me, 'last_name', '')} (ID: {me.id})")
        except Exception as e:
            print(f"\n[LOI] Dang nhap that bai: {e}")
            
    await client.disconnect()
    print("\n" + "=" * 60)
    print("Hoan tat! Ban co the chay start_bot.bat de bat dau stream tin nhan.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
