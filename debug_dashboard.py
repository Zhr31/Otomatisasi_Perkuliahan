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
    time.sleep(3)
    
    print("Membuka dashboard...")
    page.goto(f"{EDLINK_BASE_URL}/panel", wait_until="networkidle")
    time.sleep(5)
    
    # Close popup if any
    try:
        close_btn = page.query_selector('.modal button:has-text("Tutup")')
        if close_btn and close_btn.is_visible():
            close_btn.click()
            time.sleep(1)
    except: pass

    # Get items
    items = page.query_selector_all('.week-schedule-material__item')
    print(f"Found {len(items)} items in dashboard")
    for item in items:
        link = item.query_selector('.week-schedule-material__link')
        print(link.inner_text() if link else "No link", link.get_attribute('href') if link else "")
    
    browser.close()
