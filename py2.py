import mss
import numpy as np
import pytesseract
import keyboard
import win32gui
import win32process
import pyautogui
import re
import time

# путь к tesseract (если не в PATH)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

OUTPUT_FILE = "output.txt"

selected_hwnd = None


# -----------------------------
# получить окно под мышкой
# -----------------------------
def get_window_under_mouse():
    x, y = pyautogui.position()
    hwnd = win32gui.WindowFromPoint((x, y))
    return hwnd


# -----------------------------
# скрин окна
# -----------------------------
def capture_window(hwnd):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)

    region = {
        "top": top,
        "left": left,
        "width": right - left,
        "height": bottom - top
    }

    with mss.MSS() as sct:
        img = sct.grab(region)
        return np.array(img)


# -----------------------------
# OCR
# -----------------------------
def extract_text(img):
    return pytesseract.image_to_string(img)


# -----------------------------
# поиск #LOL#
# -----------------------------
def find_lol(text):
    return re.findall(r"#LOL#(.*)", text)


# -----------------------------
# сохранить
# -----------------------------
def save(lines):
    if not lines:
        return

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line.strip() + "\n")


# -----------------------------
# MAIN
# -----------------------------
def main():
    global selected_hwnd

    print("🖱️ Наведи мышку на окно и нажми F1 чтобы выбрать его")

    # выбор окна
    keyboard.wait("F1")

    selected_hwnd = get_window_under_mouse()

    title = win32gui.GetWindowText(selected_hwnd)
    print("✅ Выбрано окно:", title)

    print("📸 Нажимай F8 для захвата")

    while True:
        keyboard.wait("F8")

        try:
            img = capture_window(selected_hwnd)
            text = extract_text(img)

            results = find_lol(text)

            if results:
                save(results)
                print("💾 Saved:", results)
            else:
                print("Nothing found")

        except Exception as e:
            print("Error:", e)

        time.sleep(0.2)


if __name__ == "__main__":
    main()