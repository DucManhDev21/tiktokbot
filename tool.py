import json
import os
import shutil
import sys
import time
from datetime import datetime
from google import genai
from playwright.sync_api import sync_playwright

CONFIG_FILE = "config.json"


# --- 1. TẢI CẤU HÌNH TỪ FILE ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Lỗi: Không tìm thấy file {CONFIG_FILE}!")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    missing_fields = []
    if not config.get("GEMINI_API_KEY"):
        missing_fields.append("GEMINI_API_KEY")
    if not config.get("TARGET_USERS"):
        missing_fields.append("TARGET_USERS")
    if not config.get("COOKIE"):
        missing_fields.append("COOKIE")

    if missing_fields:
        print(f"❌ Lỗi: Thiếu thông tin trong {CONFIG_FILE}: {', '.join(missing_fields)}")
        sys.exit(1)

    return config


def parse_cookie(cookie_raw):
    cookies = []
    if cookie_raw.strip().startswith("["):
        try:
            items = json.loads(cookie_raw)
            for item in items:
                cookies.append({
                    "name": item.get("name"),
                    "value": item.get("value"),
                    "domain": ".tiktok.com",
                    "path": "/",
                })
            return cookies
        except Exception:
            pass

    for item in cookie_raw.split(";"):
        if "=" in item:
            name, value = item.strip().split("=", 1)
            cookies.append({
                "name": name,
                "value": value,
                "domain": ".tiktok.com",
                "path": "/",
            })
    return cookies


# Khởi tạo dữ liệu
config = load_config()
client = genai.Client(api_key=config["GEMINI_API_KEY"])
cookies = parse_cookie(config["COOKIE"])
TARGET_USERS = [
    u.strip().replace("@", "") for u in config["TARGET_USERS"].split(",") if u.strip()
]


# --- 2. HÀM XỬ LÝ GỬI TIN NHẮN CHO 1 USER ---
def process_user_chat(page, target_username, prompt_type, custom_prompt=""):
    try:
        chat_url = f"https://www.tiktok.com/messages?lang=vi&nickname={target_username}"
        print(f"🔄 Đang truy cập khung chat với ID: @{target_username}...")
        
        # Tăng timeout và dùng wait_until domcontentloaded để ổn định hơn
        page.goto(chat_url, timeout=60000, wait_until="domcontentloaded")
        time.sleep(5)

        chat_input = page.locator('div[contenteditable="true"]').first
        if not chat_input.is_visible(timeout=10000):
            print(f"⚠️ Không mở được khung chat hoặc không tìm thấy ô nhập tin nhắn với ID: @{target_username}")
            return

        if prompt_type == "session":
            prompt = f"Viết 1 tin nhắn ngắn (dưới 15 từ) gửi bạn bè/người yêu vào {custom_prompt}, phong cách đáng yêu, thân thiện."
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            msg_to_send = response.text.strip()

            chat_input.click()
            chat_input.fill(msg_to_send)
            page.keyboard.press("Enter")
            print(
                f"[{datetime.now().strftime('%H:%M')}] ✅ Đã gửi tin {custom_prompt} tới [@{target_username}]: {msg_to_send}"
            )

        elif prompt_type == "auto_reply":
            messages = page.locator('div[data-e2e="chat-item"]').all_text_contents()
            if messages:
                last_user_msg = messages[-1]
                print(f"📩 Tin nhắn mới nhất nhận được từ [@{target_username}]: {last_user_msg}")

                prompt = f"Trả lời ngắn gọn, tự nhiên cho tin nhắn này: '{last_user_msg}'"
                response = client.models.generate_content(
                    model="gemini-2.5-flash", contents=prompt
                )
                ai_reply = response.text.strip()

                chat_input.click()
                chat_input.fill(ai_reply)
                page.keyboard.press("Enter")
                print(f"🤖 Đã tự động trả lời [@{target_username}]: {ai_reply}")
            else:
                print(f"ℹ️ Chưa có tin nhắn mới nào từ [@{target_username}]")

    except Exception as e:
        print(f"❌ Lỗi khi xử lý ID [@{target_username}]: {e}")


# --- 3. HÀM TỔNG DUYỆT TẤT CẢ USER ---
def send_tiktok_messages_all(prompt_type, custom_prompt=""):
    with sync_playwright() as p:
        chromium_path = shutil.which("chromium-browser") or shutil.which("chromium")
        
        # Cấu hình cờ Chromium ổn định, loại bỏ cờ ép RAM quá đà
        launch_args = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--mute-audio",
            ],
        }
        if chromium_path:
            launch_args["executable_path"] = chromium_path

        browser = p.chromium.launch(**launch_args)
        
        # Giả lập môi trường trình duyệt Chrome thật trên máy tính
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        context.add_cookies(cookies)

        page = context.new_page()

        try:
            for username in TARGET_USERS:
                process_user_chat(page, username, prompt_type, custom_prompt)
                time.sleep(3)
        except Exception as e:
            print(f"❌ Lỗi kết nối TikTok: {e}")

        page.close()
        context.close()
        browser.close()


# --- 4. THỰC THI CHẠY 1 LẦN DÙNG CHO GITHUB ACTIONS ---
if __name__ == "__main__":
    current_hour = datetime.now().hour

    if current_hour == 8:
        print("🌅 Kích hoạt lịch: Gửi tin nhắn buổi sáng")
        send_tiktok_messages_all("session", "buổi sáng")
    elif current_hour == 12:
        print("☀️ Kích hoạt lịch: Gửi tin nhắn buổi trưa")
        send_tiktok_messages_all("session", "buổi trưa")
    elif current_hour == 19:
        print("🌙 Kích hoạt lịch: Gửi tin nhắn buổi tối")
        send_tiktok_messages_all("session", "buổi tối")
    else:
        print("🤖 Kích hoạt lịch: Kiểm tra & tự động trả lời tin nhắn")
        send_tiktok_messages_all("auto_reply")
