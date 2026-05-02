import time
from playwright.sync_api import sync_playwright
from config import EDLINK_EMAIL, EDLINK_PASSWORD, EDLINK_BASE_URL
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(f"{EDLINK_BASE_URL}/login")
    page.fill('input[type="email"]', EDLINK_EMAIL)
    page.fill('input[type="password"]', EDLINK_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    time.sleep(3)
    
    print("Membuka halaman Tugas...")
    page.goto(f"{EDLINK_BASE_URL}/panel/classes/1899364/assignments", wait_until="networkidle")
    time.sleep(3)
    
    html = page.content()
    with open("data/exploration/debug_assignments.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    print("Membuka halaman Berkas...")
    page.goto(f"{EDLINK_BASE_URL}/panel/classes/1899364/medias", wait_until="networkidle")
    time.sleep(3)
    
    html = page.content()
    with open("data/exploration/debug_medias.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    browser.close()
