# TikTok Streak Bot

This bot designed to solve one specific, annoying problem: **maintaining TikTok streaks.**

Manually sending a message every day to keep a streak alive is a waste of mental energy. You forget, the streak dies, it's a chore. This script automates that chore.

## How It's Built to Not Fail

I built this thing to be solid because I never want to think about streaks again.

*   **No Lazy Timers:** It doesn't use `sleep(86400)` loop. It runs on a schedule.
*   **No Zombie Processes:** This system **guarantees** the browser is terminated and all temporary data is removed after every run, success or fail. No memory leaks, no disk space creep.
*   **No Blindness:** Bot keeps a detailed `log file` of every major action, warning, and critical error.
*   **Smart Configuration:** All needed variables are in `config.json`. The XPaths are hardcoded in the script. TikTok's frontend team is lazy. They haven't changed the core message UI in ages. If they ever do, you'll update a few variables at the top of the script. If I see it, I'll fix it and commit it.

## Installation

You need Python 3.

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/thetrekir/tiktok-streak-bot.git
    cd tiktok-streak-bot
    ```

2.  **Install Dependencies:** 
    ```bash
    pip install -r requirements.txt
    ```

3.  **Get Your Cookies:**
    The bot uses cookies to log in. No password needed.
    *   Log in to TikTok in your browser.
    *   Use an extension like [Cookie-Editor](https://cookie-editor.com/) to export your cookies for the `tiktok.com` domain.
    *   Save the exported JSON data into a file named `cookies.json` in the same directory.

4.  **Configure It:**
    The first time you run the script, it will create a `config.json` file. Open it and set it up.

## Configuration (`config.json`)

This file controls the bot.

```json
{
  "TEST_MODE": false,
  "TARGET_USERS": ["username1", "username2"],
  "MESSAGE_TO_SEND": ".",
  "TARGET_SEND_TIME_HM": [0, 2],
  "COOKIES_FILE": "cookies.json",
  "LOG_FILENAME": "tiktok_bot.txt",
  "HEADLESS_MODE": true
}
```

*   `TEST_MODE`: `true` runs it once, now. `false` uses the daily schedule.
*   `TARGET_USERS`: List of usernames to send the message to.
*   `MESSAGE_TO_SEND`: The message. `.` is enough.
*   `TARGET_SEND_TIME_HM`: `[Hour, Minute]` in 24-hour format. `[0, 2]` means 00:02 AM.
*   `COOKIES_FILE`: Name of your cookies file.
*   `LOG_FILENAME`: Name of the log file.
*   `HEADLESS_MODE`: `true` runs it invisibly. `false` shows the browser window.

## Usage

1.  **Test Run:**
    Set `"TEST_MODE": true` in the config and run `python main.py`. Check the console and the log file to see if it worked.

3.  **Deploy:**
    Set `"TEST_MODE": false` in the config. For a silent background process on Windows, run it with `pythonw.exe`:
    ```bash
    pythonw.exe main.py
    ```
    
    **For to open automatically after the system reboots, set this up as a Scheduled Task or Service in Windows to run at logon.(I use this)**

### 3. Complete Automation Setup (Windows Service via .exe)

If you don't know Python or just want a bulletproof background process that survives reboots and runs silently, use the `.exe` version with NSSM (Non-Sucking Service Manager).

 1. Download the latest `tiktok-bot.exe` from the **Releases** tab.
 2. Put the `.exe`, `config.json`, and `cookies.json` in a dedicated folder (e.g., `C:\TikTokBot`).
 3. Download [NSSM](http://nssm.cc/) and extract `nssm.exe` (use the win64 version) into the same folder.
 4. Open Command Prompt **as Administrator**, navigate to your folder, and type:
   ```bash
   nssm install TikTokStreakBot
   ```
 5. A GUI will pop up. In the **Path** box, select your `tiktok-bot.exe`.
 6. Go to the **Details** tab, set the display name and description if you want.
 7. Click **Install service**. 
 8. After you install the service **type**:
   ```bash
   sc start TikTokStreakBot
   ```

That's it. It's now a Windows system service. It will run automatically every time your PC turns on, completely invisible. You can check your `tiktok_bot.txt` log file to see it working.

## Troubleshooting

#### Mac and Linux Compatibility

The bot is fully cross-platform. It automatically detects your operating system (Windows, macOS, or Linux) and executes the correct background cleanup commands (`taskkill` for Windows, `pkill` for Unix). 

If you are running this on an ARM device (like a Raspberry Pi or an Apple Silicon Mac M1/M2/M3), modern versions of `webdriver-manager` handle the architecture automatically. Just ensure you have the respective browser installed on your system (e.g., Chromium on Linux).

## Is It Reliable? (Real-World Data)

A 100% success rate is a fantasy. Things break. Here's the data from about 90 days of it running live:

*   **Total Operations (Bot's Responsibility):** 80
*   **Successful Operations:** 76
*   **Operational Success Rate: 95%**

The 4 times it failed, it wasn't a bug in my code. It was TikTok being flaky.

* **June 4, 5, 23:** The UI glitched out. Clicks didn't register or it couldn't find the user in the list.

* **June 15:** The connection timed out waiting for the server to respond.

**The takeaway:** The bot's logic is solid. It works consistently, and the rare failures are due to the Tiktok.
