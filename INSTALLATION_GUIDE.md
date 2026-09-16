# Bot Setup, Installation, and User Guide

This guide provides step-by-step instructions on how to download, install, and run the bot on your local system (laptop). The bot is built using Python, Streamlit (for the user interface), and Playwright (for browser automation). 

Instructions are provided for both **Linux (Ubuntu/Debian)** and **Windows**.

---

## 1. Downloading and Installing Git

Git is required to download the bot's code and receive future updates.

### For Linux:
Open your terminal and run:
```bash
sudo apt-get update
sudo apt-get install -y git
```

### For Windows:
You can install Git directly from the Windows terminal using the Windows Package Manager (`winget`):
```cmd
winget install -e --id Git.Git
```
*(Alternatively, you can download the installer from the [official Git website](https://git-scm.com/download/win) and click through the default installation steps).*

---

## 2. Getting the Code (Git Clone)

Once Git is installed, you need to download the bot's code to your laptop.

Open your terminal or Command Prompt, navigate to where you want the folder to be (e.g., your Desktop), and run:
```bash
git clone https://github.com/david253574/playwright-v.2.1.01-.git
```

Then, enter the newly created folder:
```bash
cd playwright-v.2.1.01-
```

---

## 3. How to Update the Code (Git Pull)

If changes (like bug fixes or new features) have been made to the code online, you can easily pull them down to your laptop without having to re-download the whole folder.

Simply open your terminal, navigate inside the bot's folder, and run:
```bash
git pull
```
This will automatically fetch and apply the latest changes.

---

## 4. Prerequisites (Python & Tools)

### For Linux:
Before installing the Python packages, ensure your system has the following requirements:
- **Python 3.12** (or a compatible Python 3 version)
- **Xvfb**: A virtual display server, which is required to run the bot in the background without opening visible windows on your main screen.

**Terminal Command (Linux):**
```bash
sudo apt-get update
sudo apt-get install -y xvfb python3.12 python3.12-venv
```

### For Windows:
You can easily install Python 3.12 using the terminal.

**Terminal Command (Windows):**
```cmd
winget install -e --id Python.Python.3.12
```
*(Alternatively, download and install Python 3.12 from the [official Python website](https://www.python.org/downloads/). **CRITICAL: When installing manually, make sure to check the box that says "Add Python to PATH" before clicking Install**).*

---

## 5. Setting Up the Virtual Environment

It is highly recommended to isolate the bot's dependencies inside a virtual environment (`venv`). Ensure you are inside the bot's folder in your terminal.

### For Linux:
```bash
# Create the virtual environment
python3.12 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

### For Windows:
Open **Command Prompt** (cmd) or **PowerShell**, then type:
```cmd
# Create the virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate
```
*(Note: You must activate the virtual environment every time you open a new terminal to run the bot).*

---

## 6. Installing Dependencies

With the virtual environment activated, install the required Python packages and their specific versions. (These commands are the exact same for both Linux and Windows).

### Terminal Commands:
```bash
# Install the python packages
pip install streamlit==1.58.0 playwright==1.60.0 playwright-stealth==2.0.3 pandas==3.0.4 urllib3

# Install the necessary Playwright browsers (Chromium is required)
playwright install chromium
```

---

## 7. How to Run the Bot

The bot is composed of two main parts:
1. **The Web Interface**: Used to configure tasks, manage profiles, and monitor the bot.
2. **The Background Worker**: The engine that executes the automated tasks in the background.

### For Linux:
Linux runs both parts using provided shell scripts that utilize `xvfb-run`. This ensures the automated browser runs seamlessly in a virtual display in the background.

**Step 7A: Start the Web Interface**
```bash
./start_background.sh
```
*You can access the interface by opening a web browser and navigating to `http://localhost:8501`. Logs are saved to `streamlit.log`.*

**Step 7B: Start the Background Worker**
```bash
./start_worker.sh
```
*Logs are saved to `worker.log`.*

### For Windows:
On Windows, you should open **two separate Command Prompt windows**. Navigate to the bot's folder and activate the virtual environment in **both** windows (`venv\Scripts\activate`).

**Step 7A: Start the Web Interface (Window 1)**
```cmd
python -m streamlit run app.py
```
*Leave this window open. A browser will automatically open to `http://localhost:8501` displaying the Streamlit interface.*

**Step 7B: Start the Background Worker (Window 2)**
```cmd
python background_worker.py
```
*Leave this window open to keep the worker running. You will see its activity directly in the console.*

---

## 8. Troubleshooting & Maintenance

- **Stopping the Bot (Linux)**: Because they run in the background via `nohup`, you can stop them by killing their process IDs (PIDs):
  ```bash
  pkill -f streamlit
  pkill -f background_worker.py
  ```
- **Stopping the Bot (Windows)**: Simply click into the Command Prompt windows where the bot is running and press `Ctrl + C` to stop them, or close the terminal windows.
- **Session Locked**: If you encounter a "Browser in use" warning, make sure all manual Chrome windows opened by the bot are closed. The bot checks for a `SingletonLock` file and will refuse to start if another instance is actively using the same profile.
