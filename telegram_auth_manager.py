import os
import sys
import time
import socket
import asyncio
import threading
import subprocess
from telethon import TelegramClient, errors
from config import API_ID, API_HASH, SESSION_NAME
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ACTIVE_QR_LOGIN = None
ACTIVE_PHONE_LOGIN = {}
STATUS_CACHE = {"time": 0, "data": None}

def is_listener_running():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('127.0.0.1', 5001))
        s.close()
        return True
    except Exception:
        return False

def get_telegram_status(force_refresh=False):
    global STATUS_CACHE
    now = time.time()
    if not force_refresh and STATUS_CACHE["data"] and (now - STATUS_CACHE["time"] < 10):
        data = dict(STATUS_CACHE["data"])
        data["is_running"] = is_listener_running()
        return data

    is_running = is_listener_running()
    is_auth = False
    user_info = None

    async def _check():
        nonlocal is_auth, user_info
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        try:
            await client.connect()
            if await client.is_user_authorized():
                is_auth = True
                me = await client.get_me()
                user_info = {
                    "id": me.id,
                    "first_name": me.first_name or "",
                    "last_name": getattr(me, "last_name", "") or "",
                    "username": f"@{me.username}" if getattr(me, "username", None) else "",
                    "phone": getattr(me, "phone", "") or ""
                }
            await client.disconnect()
        except Exception as e:
            try:
                await client.disconnect()
            except Exception:
                pass

    try:
        asyncio.run(_check())
    except Exception:
        pass

    result = {
        "is_authorized": is_auth,
        "is_running": is_running,
        "user": user_info
    }
    STATUS_CACHE = {"time": now, "data": result}
    return result

def launch_desktop_login():
    bat_path = os.path.join(BASE_DIR, "DANG_NHAP_TELEGRAM.bat")
    try:
        subprocess.Popen(["cmd.exe", "/c", "start", bat_path], cwd=BASE_DIR)
        return True
    except Exception as e:
        print(f"[!] Error launching desktop login: {e}")
        return False

# --- QR LOGIN LOGIC ---
QR_STATE = {
    "url": None,
    "qr_img": None,
    "status": "idle", # idle, waiting, success, expired, error
    "user": None,
    "error": None
}

def start_qr_session():
    global QR_STATE
    QR_STATE["status"] = "waiting"
    QR_STATE["error"] = None
    QR_STATE["user"] = None

    def _qr_thread():
        async def _run():
            global QR_STATE
            client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
            try:
                await client.connect()
                if await client.is_user_authorized():
                    me = await client.get_me()
                    QR_STATE["status"] = "success"
                    QR_STATE["user"] = f"{me.first_name} {getattr(me, 'last_name', '')}"
                    await client.disconnect()
                    return

                qr = await client.qr_login()
                QR_STATE["url"] = qr.url
                QR_STATE["qr_img"] = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={qr.url}"
                
                try:
                    await qr.wait(timeout=75)
                    if await client.is_user_authorized():
                        me = await client.get_me()
                        QR_STATE["status"] = "success"
                        QR_STATE["user"] = f"{me.first_name} {getattr(me, 'last_name', '')}"
                    else:
                        QR_STATE["status"] = "expired"
                except asyncio.TimeoutError:
                    QR_STATE["status"] = "expired"
                except Exception as ex:
                    QR_STATE["status"] = "error"
                    QR_STATE["error"] = str(ex)
                finally:
                    await client.disconnect()
            except Exception as e:
                QR_STATE["status"] = "error"
                QR_STATE["error"] = str(e)
                try:
                    await client.disconnect()
                except Exception:
                    pass

        asyncio.run(_run())

    t = threading.Thread(target=_qr_thread, daemon=True)
    t.start()

    # Wait up to 3 seconds for QR url to be generated
    for _ in range(15):
        time.sleep(0.2)
        if QR_STATE["url"] or QR_STATE["status"] in ["success", "error"]:
            break

    return QR_STATE

def get_qr_state():
    return QR_STATE

# --- PHONE LOGIN LOGIC ---
PHONE_STATE = {}

def request_phone_code(phone):
    global PHONE_STATE
    phone = phone.strip()
    if not phone.startswith("+"):
        if phone.startswith("0"):
            phone = "+84" + phone[1:]
        else:
            phone = "+" + phone

    result = {"success": False, "error": None}

    async def _send():
        nonlocal result
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        try:
            await client.connect()
            sent = await client.send_code_request(phone)
            PHONE_STATE[phone] = {
                "phone_code_hash": sent.phone_code_hash,
                "time": time.time()
            }
            result["success"] = True
            result["phone"] = phone
            await client.disconnect()
        except Exception as e:
            result["error"] = str(e)
            try:
                await client.disconnect()
            except Exception:
                pass

    try:
        asyncio.run(_send())
    except Exception as e:
        result["error"] = str(e)

    return result

def verify_phone_code(phone, code, password=None):
    global PHONE_STATE
    phone = phone.strip()
    if not phone.startswith("+"):
        if phone.startswith("0"):
            phone = "+84" + phone[1:]
        else:
            phone = "+" + phone

    code_info = PHONE_STATE.get(phone, {})
    phone_code_hash = code_info.get("phone_code_hash")

    result = {"success": False, "need_password": False, "error": None, "user": None}

    async def _verify():
        nonlocal result
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        try:
            await client.connect()
            try:
                if phone_code_hash:
                    await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                else:
                    await client.sign_in(phone, code)
            except errors.SessionPasswordNeededError:
                if password:
                    await client.sign_in(password=password)
                else:
                    result["need_password"] = True
                    result["error"] = "Tài khoản có bảo mật 2 lớp (2FA). Vui lòng nhập mật khẩu 2FA."
                    await client.disconnect()
                    return

            if await client.is_user_authorized():
                me = await client.get_me()
                result["success"] = True
                result["user"] = f"{me.first_name} {getattr(me, 'last_name', '')}"
                # Start listener immediately
                start_listener_process()
            else:
                result["error"] = "Xác nhận mã không thành công."
            await client.disconnect()
        except Exception as e:
            result["error"] = str(e)
            try:
                await client.disconnect()
            except Exception:
                pass

    try:
        asyncio.run(_verify())
    except Exception as e:
        result["error"] = str(e)

    return result

LISTENER_PROCESS = None

def start_listener_process():
    global LISTENER_PROCESS
    if is_listener_running():
        return True
    try:
        script = os.path.join(BASE_DIR, "telegram_listener.py")
        LISTENER_PROCESS = subprocess.Popen([sys.executable, script], cwd=BASE_DIR)
        print("[*] Đã khởi chạy subprocess telegram_listener.py thành công!", flush=True)
        return True
    except Exception as e:
        print(f"[!] Lỗi khởi chạy telegram_listener: {e}", flush=True)
        return False
