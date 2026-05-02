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
    
    print("Membuka halaman sections...")
    page.goto(f"{EDLINK_BASE_URL}/panel/classes/1899364/sections", wait_until="networkidle")
    time.sleep(3)
    
    print("Meng-klik semua section-box...")
    sections = page.query_selector_all('.section-box')
    for i, s in enumerate(sections):
        try:
            s.click(force=True)
            time.sleep(0.5)
        except Exception as e:
            print(f"Error click {i}: {e}")
            
    time.sleep(2)
    html = page.content()
    
    # regex extract
    links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html)
    found = 0
    for href, text in links:
        if 'sections' in href or 'panel' in href:
            clean_text = re.sub(r'<[^>]+>', '', text).strip()
            if clean_text:
                print(f"Link: {clean_text} -> {href}")
                found += 1
                
    print(f"Found {found} content links!")
    
    browser.close()
