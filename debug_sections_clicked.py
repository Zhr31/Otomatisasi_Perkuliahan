import time
from playwright.sync_api import sync_playwright
from config import EDLINK_EMAIL, EDLINK_PASSWORD, EDLINK_BASE_URL

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(f"{EDLINK_BASE_URL}/login")
    page.fill('input[type="email"]', EDLINK_EMAIL)
    page.fill('input[type="password"]', EDLINK_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")
    
    print("Membuka halaman kelas...")
    page.goto(f"{EDLINK_BASE_URL}/panel/classes/1899364/sections", wait_until="networkidle")
    time.sleep(3)
    
    print("Meng-klik section pertama...")
    sections = page.query_selector_all('.section-box')
    if sections:
        sections[0].click()
        time.sleep(3)
        
        html = page.content()
        with open("data/exploration/debug_sections_clicked.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Disimpan ke debug_sections_clicked.html")
    else:
        print("Tidak ada section-box")
    
    browser.close()
