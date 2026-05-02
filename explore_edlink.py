"""
explore_edlink.py — Script untuk EKSPLORASI struktur Edlink kampus kamu.

Jalankan ini PERTAMA KALI untuk melihat:
1. Bagaimana halaman login Edlink terlihat
2. Bagaimana daftar mata kuliah ditampilkan
3. Bagaimana sesi/pertemuan ditampilkan
4. Di mana link download materi berada

Hasilnya berupa screenshot + HTML dump yang akan membantu
menyesuaikan scraper dengan Edlink kampus kamu.

CARA JALANKAN:
    python explore_edlink.py
"""
import sys
import os
import time
import json
from pathlib import Path

# Setup path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config import EDLINK_EMAIL, EDLINK_PASSWORD, EDLINK_BASE_URL
from playwright.sync_api import sync_playwright


def explore():
    """Eksplorasi Edlink secara interaktif"""
    
    print("=" * 60)
    print("🔍 EDLINK EXPLORER")
    print("=" * 60)
    print(f"URL: {EDLINK_BASE_URL}")
    print(f"Email: {EDLINK_EMAIL}")
    print()
    
    # Buat folder untuk output
    output_dir = ROOT / "data" / "exploration"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=1000)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            accept_downloads=True
        )
        page = context.new_page()
        
        # ============================================
        # STEP 1: Halaman Login
        # ============================================
        print("\n📌 STEP 1: Membuka halaman login...")
        page.goto(f"{EDLINK_BASE_URL}/login", wait_until="networkidle")
        time.sleep(3)
        
        # Screenshot halaman login
        page.screenshot(path=str(output_dir / "01_login_page.png"), full_page=True)
        print("  📸 Screenshot: 01_login_page.png")
        
        # Simpan HTML
        html = page.content()
        with open(output_dir / "01_login_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("  📄 HTML: 01_login_page.html")
        
        # Cari semua input fields
        inputs = page.query_selector_all("input")
        print(f"\n  🔎 Ditemukan {len(inputs)} input field:")
        for inp in inputs:
            inp_type = inp.get_attribute("type") or "unknown"
            inp_name = inp.get_attribute("name") or ""
            inp_id = inp.get_attribute("id") or ""
            inp_placeholder = inp.get_attribute("placeholder") or ""
            print(f"    - type={inp_type} name={inp_name} id={inp_id} placeholder='{inp_placeholder}'")
        
        # ============================================
        # STEP 2: Login
        # ============================================
        print("\n📌 STEP 2: Mencoba login...")
        
        # Isi email
        email_input = page.query_selector('input[type="email"], input[name="email"], input[placeholder*="email" i], input[type="text"]')
        if email_input:
            email_input.fill(EDLINK_EMAIL)
            print("  ✅ Email diisi")
        else:
            print("  ❌ Field email tidak ditemukan!")
        
        # Isi password
        pass_input = page.query_selector('input[type="password"]')
        if pass_input:
            pass_input.fill(EDLINK_PASSWORD)
            print("  ✅ Password diisi")
        else:
            print("  ❌ Field password tidak ditemukan!")
        
        # Screenshot sebelum submit
        page.screenshot(path=str(output_dir / "02_login_filled.png"), full_page=True)
        
        # Klik login
        submit_btn = page.query_selector('button[type="submit"], button:has-text("Masuk"), button:has-text("Login")')
        if submit_btn:
            submit_btn.click()
            print("  🔐 Tombol login diklik")
        else:
            print("  ❌ Tombol login tidak ditemukan!")
        
        # Tunggu
        time.sleep(5)
        page.wait_for_load_state("networkidle")
        
        # Screenshot setelah login
        page.screenshot(path=str(output_dir / "03_after_login.png"), full_page=True)
        print(f"  📸 Screenshot: 03_after_login.png")
        print(f"  🌐 URL sekarang: {page.url}")
        
        # Simpan HTML dashboard
        html = page.content()
        with open(output_dir / "03_dashboard.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        # ============================================
        # STEP 3: Navigasi ke halaman kelas/courses
        # ============================================
        print("\n📌 STEP 3: Mencari halaman mata kuliah...")
        
        # Cari semua link di halaman
        all_links = page.query_selector_all("a[href]")
        print(f"  🔎 Ditemukan {len(all_links)} link:")
        
        interesting_links = []
        for link in all_links:
            href = link.get_attribute("href") or ""
            text = link.inner_text().strip()
            if text and len(text) > 1 and len(text) < 100:
                interesting_links.append({"text": text, "href": href})
                if any(kw in text.lower() or kw in href.lower() 
                       for kw in ["kelas", "course", "mata kuliah", "jadwal", "materi"]):
                    print(f"    ⭐ '{text}' → {href}")
                else:
                    print(f"    - '{text}' → {href}")
        
        # Simpan data link
        with open(output_dir / "03_links.json", "w", encoding="utf-8") as f:
            json.dump(interesting_links, f, indent=2, ensure_ascii=False)
        
        # Coba navigasi ke courses
        course_link = page.query_selector(
            'a:has-text("Kelas"), a:has-text("Course"), a:has-text("Mata Kuliah"), '
            'a[href*="course"], a[href*="kelas"]'
        )
        
        if course_link:
            course_link.click()
            time.sleep(3)
            page.wait_for_load_state("networkidle")
            print(f"  ✅ Navigasi ke halaman kelas: {page.url}")
        else:
            # Coba akses langsung
            for path in ["/mahasiswa/course", "/student/course", "/course", "/kelas"]:
                try:
                    page.goto(f"{EDLINK_BASE_URL}{path}", wait_until="networkidle", timeout=10000)
                    time.sleep(2)
                    if "login" not in page.url.lower():
                        print(f"  ✅ Navigasi ke: {page.url}")
                        break
                except Exception:
                    continue
        
        # Screenshot halaman kelas
        page.screenshot(path=str(output_dir / "04_courses_page.png"), full_page=True)
        print("  📸 Screenshot: 04_courses_page.png")
        
        # Simpan HTML
        html = page.content()
        with open(output_dir / "04_courses.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        # Analisis struktur
        print("\n📌 STEP 4: Analisis struktur halaman...")
        
        # Cari elemen yang mungkin berisi daftar kelas
        card_selectors = [
            ".card", ".course-card", ".class-card", ".course-item",
            "[class*='course']", "[class*='class']", "[class*='kelas']",
            ".list-group-item", ".item", ".row .col"
        ]
        
        for selector in card_selectors:
            try:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"\n  📦 Selector '{selector}' → {len(elements)} elemen")
                    for i, elem in enumerate(elements[:5]):  # Tampilkan maks 5
                        text = elem.inner_text().strip()[:100]
                        classes = elem.get_attribute("class") or ""
                        print(f"    [{i}] class='{classes[:60]}' text='{text}'")
            except Exception:
                continue
        
        # ============================================
        # STEP 5: Coba buka satu mata kuliah
        # ============================================
        print("\n📌 STEP 5: Mencoba buka mata kuliah pertama...")
        
        # Cari link ke mata kuliah
        course_cards = page.query_selector_all(
            '.card a, .course-item a, [class*="course"] a, .list-group-item a'
        )
        
        if not course_cards:
            # Coba semua link yang mengarah ke course detail
            course_cards = page.query_selector_all('a[href*="course"], a[href*="kelas"]')
        
        if course_cards:
            first_course = course_cards[0]
            first_text = first_course.inner_text().strip()
            first_href = first_course.get_attribute("href") or ""
            print(f"  📖 Membuka: '{first_text}' → {first_href}")
            first_course.click()
            time.sleep(3)
            page.wait_for_load_state("networkidle")
            
            # Screenshot detail course
            page.screenshot(path=str(output_dir / "05_course_detail.png"), full_page=True)
            print("  📸 Screenshot: 05_course_detail.png")
            
            html = page.content()
            with open(output_dir / "05_course_detail.html", "w", encoding="utf-8") as f:
                f.write(html)
            
            # Analisis sesi/pertemuan
            print("\n  🔎 Mencari struktur sesi/pertemuan:")
            session_selectors = [
                ".session", ".meeting", ".pertemuan", ".topic", ".section",
                "[class*='session']", "[class*='pertemuan']", "[class*='topic']",
                ".accordion-item", ".list-group-item", ".tab-pane"
            ]
            
            for selector in session_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        print(f"\n    📋 Selector '{selector}' → {len(elements)} elemen")
                        for i, elem in enumerate(elements[:5]):
                            text = elem.inner_text().strip()[:100]
                            print(f"      [{i}] {text}")
                except Exception:
                    continue
        
        # ============================================
        # Selesai
        # ============================================
        print("\n" + "=" * 60)
        print("✅ EKSPLORASI SELESAI!")
        print("=" * 60)
        print(f"\n📁 Hasil disimpan di: {output_dir}")
        print("\nFile yang dibuat:")
        for f in sorted(output_dir.iterdir()):
            print(f"  - {f.name} ({f.stat().st_size / 1024:.1f} KB)")
        
        print("\n💡 LANGKAH SELANJUTNYA:")
        print("  1. Buka folder 'data/exploration' dan lihat screenshot")
        print("  2. Periksa file HTML untuk memahami selector yang tepat")
        print("  3. Laporkan hasilnya agar saya bisa menyesuaikan scraper")
        
        # Biarkan browser terbuka sebentar
        print("\n⏳ Browser akan tetap terbuka 10 detik untuk inspeksi manual...")
        time.sleep(10)
        
        browser.close()


if __name__ == "__main__":
    explore()
