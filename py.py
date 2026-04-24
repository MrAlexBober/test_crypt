import numpy as np
import mss
import pytesseract
import keyboard
import re

OUTPUT_FILE = "output.txt"

def capture_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)

        # 🔥 ВАЖНО: конвертация в numpy array
        img = np.array(screenshot)

        return img

def extract_text(img):
    return pytesseract.image_to_string(img)

def find_lol(text):
    return [m.strip() for m in re.findall(r"#LOL#(.*)", text)]

def save_to_file(lines):
    if not lines:
        return
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

def run():
    print("Running... press F8 to capture")

    while True:
        keyboard.wait("F8")

        img = capture_screen()
        text = extract_text(img)

        results = find_lol(text)

        if results:
            save_to_file(results)
            print("Saved:", results)
        else:
            print("Nothing found")

run()