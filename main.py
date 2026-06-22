import time
import json
import logging
import random
import sys
import os
import shutil
import platform
from datetime import datetime, time as dt_time, date, timedelta
from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException,
    StaleElementReferenceException, ElementNotInteractableException
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

os.environ['WDM_LOG'] = '0'
os.environ['WDM_PROGRESS_BAR'] = '0'
from webdriver_manager.chrome import ChromeDriverManager

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "TEST_MODE": False,
    "TARGET_USERS": ["kullanici1", "kullanici2"],
    "MESSAGE_TO_SEND": ".",
    "TARGET_SEND_TIME_HM": [0, 2],
    "COOKIES_FILE": "cookies.json",
    "LOG_FILENAME": "tiktok_bot.txt",
    "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "TIKTOK_MESSAGES_URL": "https://www.tiktok.com/messages?lang=en",
}

IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"

# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def load_or_create_config(filename):
    if not os.path.exists(filename):
        logging.warning(f"Config '{filename}' not found. Creating with defaults.")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
            return DEFAULT_CONFIG
        except Exception as e:
            logging.error(f"Could not create config: {e}")
            return None
    else:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            logging.error(f"Error loading config: {e}")
            return None

def terminate_lingering_processes():
    logging.info("Terminating any lingering chrome/chromedriver processes...")
    try:
        if IS_WINDOWS:
            os.system("taskkill /F /IM chromedriver.exe /T > NUL 2>&1")
            os.system("taskkill /F /IM chrome.exe /T > NUL 2>&1")
        else:
            os.system("pkill -f chromedriver > /dev/null 2>&1")
            os.system("pkill -f chromium > /dev/null 2>&1")
            os.system("pkill -f chrome > /dev/null 2>&1")
        logging.info("Process cleanup done.")
    except Exception as e:
        logging.error(f"Error during process cleanup: {e}")

# Load Config
config = load_or_create_config(CONFIG_FILE)
if config is None:
    sys.exit(1)

TEST_MODE        = config.get('TEST_MODE',            DEFAULT_CONFIG['TEST_MODE'])
TARGET_USERS     = config.get('TARGET_USERS',         DEFAULT_CONFIG['TARGET_USERS'])
MESSAGE_TO_SEND  = config.get('MESSAGE_TO_SEND',      DEFAULT_CONFIG['MESSAGE_TO_SEND'])
time_hm          = config.get('TARGET_SEND_TIME_HM',  DEFAULT_CONFIG['TARGET_SEND_TIME_HM'])
COOKIES_FILE     = config.get('COOKIES_FILE',         DEFAULT_CONFIG['COOKIES_FILE'])
LOG_FILENAME     = config.get('LOG_FILENAME',         DEFAULT_CONFIG['LOG_FILENAME'])
USER_AGENT       = config.get('USER_AGENT',           DEFAULT_CONFIG['USER_AGENT'])
TIKTOK_MESSAGES_URL = config.get('TIKTOK_MESSAGES_URL', DEFAULT_CONFIG['TIKTOK_MESSAGES_URL'])
HEADLESS_MODE = config.get('HEADLESS_MODE', False)  # Всегда держим FALSE, чтобы видеть окно

if not os.path.exists(COOKIES_FILE):
    with open(COOKIES_FILE, 'w', encoding='utf-8') as f: json.dump([], f)

try:
    if isinstance(time_hm, list) and len(time_hm) == 2:
        TARGET_SEND_TIME = dt_time(int(time_hm[0]), int(time_hm[1]))
    else:
        TARGET_SEND_TIME = dt_time(0, 2)
except Exception:
    TARGET_SEND_TIME = dt_time(0, 2)

for h in logging.root.handlers[:]: logging.root.removeHandler(h)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILENAME, encoding='utf-8'), logging.StreamHandler()]
)

logging.info("--- Bot Started ---")

# XPATHS
MESSAGE_LIST_CONTAINER_XPATH = "//*[@data-e2e='dm-new-conversation-list']"
CONVERSATION_ITEM_XPATH      = "//*[@data-e2e='dm-new-conversation-item']"
NICKNAME_CLASS_PARTIAL       = "PInfoNickname"
NICKNAME_XPATH_INSIDE_ITEM   = f".//p[contains(@class, '{NICKNAME_CLASS_PARTIAL}')]"

# Железный XPATH: ищет любой элемент, где можно писать (contenteditable)
CLICK_TARGET_XPATH           = "//div[@contenteditable='true']"
WRITE_TARGET_XPATH           = "//div[@contenteditable='true']"

TOAST_XPATH                  = "//li[@data-sonner-toast]"
MAX_RETRIES                  = 3
RETRY_DELAY_SECONDS          = 12

def load_cookies(driver, cookie_file):
    logging.info(f"Loading cookies from '{cookie_file}'...")
    added = 0
    try:
        with open(cookie_file, 'r') as f: cookies = json.load(f)
        driver.get("https://www.tiktok.com/explore")
        time.sleep(random.uniform(3, 5))
        for cookie in cookies:
            c = {'name': cookie['name'], 'value': cookie['value']}
            for field in ('path', 'domain', 'secure', 'httpOnly'):
                if field in cookie: c[field] = cookie[field]
            if cookie.get('expirationDate'):
                try: c['expiry'] = int(float(cookie['expirationDate']))
                except Exception: pass
            ss = cookie.get('sameSite')
            if ss is None or (isinstance(ss, str) and ss.lower() == 'no_restriction'):
                if c.get('secure'): c['sameSite'] = 'None'
            elif isinstance(ss, str) and ss.lower() in ('lax', 'strict', 'none'):
                c['sameSite'] = ss.capitalize()
            if not c.get('domain'): c['domain'] = ".tiktok.com"
            try:
                driver.add_cookie(c)
                added += 1
            except Exception: pass
        logging.info(f"Successfully added {added} cookies.")
        return True
    except Exception as e:
        logging.error(f"Error loading cookies: {e}")
        return False

def switch_to_iframe_with_element(driver, element_xpath):
    driver.switch_to.default_content()
    try: WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.TAG_NAME, "iframe")))
    except Exception: return False
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for index, iframe in enumerate(iframes):
        try:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            if driver.find_elements(By.XPATH, element_xpath): return True
        except Exception: continue
    driver.switch_to.default_content()
    return False

def wait_for_element(driver, by, value, timeout=20):
    try:
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((by, value)))
        return True
    except TimeoutException:
        if by == By.XPATH and switch_to_iframe_with_element(driver, value):
            try:
                WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
                return True
            except Exception: pass
        return False

def find_and_click_conversation(driver, username):
    logging.info(f"Searching for conversation: '{username}'...")
    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, CONVERSATION_ITEM_XPATH)))
        time.sleep(random.uniform(2, 4))
        items = driver.find_elements(By.XPATH, CONVERSATION_ITEM_XPATH)
        for i, item in enumerate(items):
            try:
                nick = item.find_element(By.XPATH, NICKNAME_XPATH_INSIDE_ITEM).text.strip()
                if nick.lower() == username.lower():
                    driver.execute_script("arguments[0].scrollIntoView(true);", item)
                    time.sleep(0.5)
                    item.click()
                    time.sleep(random.uniform(3, 5))
                    return True
            except Exception: continue
        return False
    except Exception as e:
        logging.error(f"Error in find_and_click_conversation: {e}")
        return False

def send_message_in_open_chat(driver):
    logging.info("Sending message...")
    try:
        import pyperclip
        from selenium.webdriver.common.action_chains import ActionChains
        
        try: WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.XPATH, TOAST_XPATH)))
        except Exception: pass

        try:
            write_target = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.XPATH, WRITE_TARGET_XPATH))
            )
        except TimeoutException:
            logging.error("Input field not found.")
            return False

        # 1. Помещаем огонёк в буфер обмена Макбука
        pyperclip.copy(MESSAGE_TO_SEND)
        logging.info(f"Copied to clipboard: {MESSAGE_TO_SEND}")
        time.sleep(0.5)

        # 2. Имитируем реальное поведение: подводим мышь, кликаем, вставляем через Cmd+V и жмем Enter
        try:
            actions = ActionChains(driver)
            # Кликаем по полю ввода
            actions.move_to_element(write_target).click()
            time.sleep(0.5)
            
            # Нажимаем Command + V (вставить)
            logging.info("Sending Command+V hotkey...")
            actions.key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND)
            time.sleep(0.8)
            
            # Нажимаем Enter
            actions.send_keys(Keys.ENTER)
            actions.perform()
            
            logging.info("Hotkeys executed successfully.")
            time.sleep(random.uniform(2, 4))
            return verify_message_sent(driver)
            
        except Exception as e:
            logging.error(f"Error executing hotkeys: {e}")
            return False

    except Exception as e:
        logging.error(f"General error in send_message: {e}")
        return False

def verify_message_sent(driver):
    try:
        write_target = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.XPATH, WRITE_TARGET_XPATH)))
        content = (write_target.text or write_target.get_attribute("textContent") or "").strip()
        return content == ""
    except Exception: return False

def verify_message_sent(driver):
    try:
        write_target = WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.XPATH, WRITE_TARGET_XPATH)))
        content = (write_target.text or write_target.get_attribute("textContent") or "").strip()
        return content == ""
    except Exception: return False

def handle_passkey_popup(driver):
    xpath = "//div[starts-with(@id, 'floating-ui-')]/div/div[2]/button[1]"
    try:
        btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, xpath)))
        btn.click()
    except Exception: pass

@contextmanager
def managed_webdriver():
    global HEADLESS_MODE  # Заставляем функцию видеть переменную из конфига
    
    terminate_lingering_processes()
    time.sleep(1)
    SESSION_DIR = os.path.join(os.getcwd(), "session_data")
    if os.path.exists(SESSION_DIR):
        shutil.rmtree(SESSION_DIR, ignore_errors=True)
    
    driver = None
    try:
        opts = Options()
        opts.add_argument(f"user-agent={USER_AGENT}")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("--no-sandbox")           
        opts.add_argument("--disable-dev-shm-usage") 
        opts.add_argument("--window-size=1280,800")
        opts.add_argument(f"--user-data-dir={SESSION_DIR}")

        # ДОБАВЛЯЕМ СЮДА:
        if HEADLESS_MODE:
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-gpu")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        yield driver
    finally:
        if driver:
            try: driver.quit()
            except Exception: pass
        terminate_lingering_processes()
        shutil.rmtree(SESSION_DIR, ignore_errors=True)

# ──────────────────────────────────────────────
# MAIN BOT LOGIC
# ──────────────────────────────────────────────
def run_bot():
    try:
        with managed_webdriver() as driver:
            logging.info("Browser ready.")
            if not load_cookies(driver, COOKIES_FILE): return

            logging.info(f"Navigating to {TIKTOK_MESSAGES_URL}...")
            driver.get(TIKTOK_MESSAGES_URL)
            handle_passkey_popup(driver)

            logging.info("Waiting for message list...")
            wait_for_element(driver, By.XPATH, MESSAGE_LIST_CONTAINER_XPATH, timeout=35)

            # ─── РУЧНОЙ ОБХОД БЛОКИРОВКИ (ВСТАВЛЕНО СЮДА) ───
            # logging.info("⏸ БОТ НА ПАУЗЕ 30 СЕКУНД! Быстро перейди в окно Хрома руками:")
            # logging.info("1. Если висит робот 'Something went wrong' — руками обнови страницу в Хроме (круглым значком или F5).")
            # logging.info("2. Если вылезли баннеры/плашки — закрой их мышкой.")
            # logging.info("3. Убедись, что список чатов прогрузился. Через 30 сек бот начнет рассылку.")
            # time.sleep(30)
            # ───────────────────────────────────────────────

            if not TARGET_USERS: return
            success = 0
            for user in TARGET_USERS:
                safe_user = ''.join(c for c in user if c.isprintable())
                sent = False
                for attempt in range(1, MAX_RETRIES + 1):
                    logging.info(f"--- Processing: '{safe_user}' (attempt {attempt}/{MAX_RETRIES}) ---")
                    if attempt > 1:
                        try:
                            driver.get(TIKTOK_MESSAGES_URL)
                            wait_for_element(driver, By.XPATH, MESSAGE_LIST_CONTAINER_XPATH, timeout=20)
                            time.sleep(3)
                        except Exception: pass

                    if not find_and_click_conversation(driver, user):
                        if attempt < MAX_RETRIES: time.sleep(RETRY_DELAY_SECONDS)
                        continue

                    if send_message_in_open_chat(driver):
                        sent = True
                        break
                    if attempt < MAX_RETRIES: time.sleep(RETRY_DELAY_SECONDS)

                if sent:
                    success += 1
                    logging.info(f"✓ Message confirmed sent to '{safe_user}'.")
                else:
                    logging.error(f"✗ All attempts failed for '{safe_user}'.")

                if len(TARGET_USERS) > 1 and user != TARGET_USERS[-1]:
                    time.sleep(random.uniform(5, 10))

            logging.info(f"Done. {success}/{len(TARGET_USERS)} messages sent.")
    except Exception as e:
        logging.error(f"Critical error: {e}")


if __name__ == "__main__":
    
    if TEST_MODE:
        logging.info("Работаем в TEST_MODE. Запуск скрипта прямо сейчас...")
        run_bot()
    else:
        base_time = TARGET_SEND_TIME
        random_minutes = random.randint(-40, 40)
        
        current_target_datetime = datetime.combine(date.today(), base_time) + timedelta(minutes=random_minutes)
        
        if datetime.now() >= current_target_datetime:
            current_target_datetime += timedelta(days=1)
            
        logging.info(f"Следующий запуск запланирован на: {current_target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        while True:
            now = datetime.now()
            if now >= current_target_datetime:
                logging.info("Время пришло! Запускаю рассылку...")
                run_bot()
                
                random_minutes = random.randint(-40, 40)
                current_target_datetime = datetime.combine(now.date() + timedelta(days=1), base_time) + timedelta(minutes=random_minutes)
                logging.info(f"Рассылка завершена. Новый запуск запланирован на: {current_target_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            
            time.sleep(60)
