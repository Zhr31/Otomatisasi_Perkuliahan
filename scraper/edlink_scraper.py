"""
scraper/edlink_scraper.py - Scraper untuk Edlink UNSIA menggunakan Playwright
Disesuaikan dengan struktur HTML Edlink Universitas Siber Asia.
"""
import re
import time
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import EDLINK_EMAIL, EDLINK_PASSWORD, EDLINK_BASE_URL, DOWNLOADS_DIR
from models.course_data import Course, Session, CourseItem, classify_content


class EdlinkScraper:
    """Scraper untuk Edlink UNSIA"""

    def __init__(self, headless=False):
        self.headless = headless
        self.browser = None
        self.page = None
        self.playwright = None
        self.courses = []

    def start(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless, slow_mo=300
        )
        context = self.browser.new_context(
            viewport={"width": 1280, "height": 800}, accept_downloads=True
        )
        self.page = context.new_page()
        print("  Browser dimulai")

    def stop(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("  Browser ditutup")

    def login(self):
        try:
            print("\n[LOGIN] Membuka Edlink...")
            self.page.goto(f"{EDLINK_BASE_URL}/login", wait_until="networkidle")
            time.sleep(2)

            # Isi email
            email_input = self.page.query_selector('input[type="email"], input[name="email"], input[type="text"]')
            if email_input:
                email_input.fill(EDLINK_EMAIL)
            else:
                print("  GAGAL: Field email tidak ditemukan")
                return False

            # Isi password
            pass_input = self.page.query_selector('input[type="password"]')
            if pass_input:
                pass_input.fill(EDLINK_PASSWORD)
            else:
                print("  GAGAL: Field password tidak ditemukan")
                return False

            # Klik login
            btn = self.page.query_selector('button[type="submit"], button:has-text("Masuk"), button:has-text("Login")')
            if btn:
                btn.click()

            time.sleep(5)
            self.page.wait_for_load_state("networkidle")

            # Tutup popup "Berita Kampus" jika muncul
            try:
                close_btn = self.page.query_selector('.modal button:has-text("Tutup"), button:has-text("Tutup")')
                if close_btn and close_btn.is_visible():
                    close_btn.click()
                    time.sleep(1)
            except Exception:
                pass

            if "login" not in self.page.url.lower() or "classes" in self.page.url.lower():
                print("  LOGIN BERHASIL!")
                return True
            else:
                print("  LOGIN GAGAL")
                return False
        except Exception as e:
            print(f"  Error login: {e}")
            return False

    def get_courses(self):
        """Ambil daftar 7 mata kuliah dari halaman utama Edlink"""
        try:
            print("\n[COURSES] Mengambil daftar mata kuliah...")

            # Pastikan di halaman classes
            if "/classes" not in self.page.url:
                self.page.goto(f"{EDLINK_BASE_URL}/classes?tab=1", wait_until="networkidle")
                time.sleep(3)

            # Tutup popup jika ada
            try:
                close_btn = self.page.query_selector('button:has-text("Tutup")')
                if close_btn and close_btn.is_visible():
                    close_btn.click()
                    time.sleep(1)
            except Exception:
                pass

            # Tunggu elemen muncul untuk menghindari execution context destroyed
            try:
                self.page.wait_for_selector('a[href^="/panel/classes/"]', timeout=15000)
            except Exception:
                pass
                
            # Selector: card kelas akademik - sesuai HTML Edlink UNSIA
            cards = []
            for _ in range(3):  # Coba sampai 3 kali
                try:
                    cards = self.page.query_selector_all('a[href^="/panel/classes/"].col-12.col-sm-6')
                    if not cards:
                        cards = self.page.query_selector_all('a[href^="/panel/classes/"]')
                        cards = [c for c in cards if c.get_attribute("href", "").count("/") <= 4]
                    if cards:
                        break
                except Exception as e:
                    print(f"  Retry get cards: {e}")
                    time.sleep(2)

            courses = []
            seen_ids = set()

            for card in cards:
                try:
                    href = card.get_attribute("href") or ""
                    # Extract class ID dari URL: /panel/classes/1899364/
                    match = re.search(r'/panel/classes/(\d+)', href)
                    if not match:
                        continue
                    class_id = match.group(1)
                    if class_id in seen_ids:
                        continue
                    seen_ids.add(class_id)

                    # Nama mata kuliah dari h3.card__title
                    title_elem = card.query_selector('h3.card__title')
                    if title_elem:
                        name = title_elem.inner_text().strip().replace("\n", " ")
                    else:
                        name = card.inner_text().strip().split("\n")[0]

                    # Bersihkan nama (hapus kode duplikat)
                    name = re.sub(r'\s+', ' ', name).strip()

                    url = f"{EDLINK_BASE_URL}{href}"

                    course = Course(name=name, course_id=class_id, url=url)
                    courses.append(course)
                    print(f"  [{class_id}] {name}")
                except Exception:
                    continue

            print(f"\n  Ditemukan {len(courses)} mata kuliah")
            self.courses = courses
            return courses

        except Exception as e:
            print(f"  Error: {e}")
            return []

    def get_sessions_and_items(self, course):
        """Buka halaman mata kuliah (Diskusi) dan ambil semua sesi + konten dari sidebar"""
        try:
            print(f"\n[COURSE] {course.name}")

            # Navigasi ke halaman utama kelas (Diskusi) yang memuat sidebar Sesi
            diskusi_url = f"{EDLINK_BASE_URL}/panel/classes/{course.course_id}"
            self.page.goto(diskusi_url, wait_until="networkidle")
            time.sleep(3)

            # Tutup popup jika ada
            try:
                close_btn = self.page.query_selector('.modal button:has-text("Tutup")')
                if close_btn and close_btn.is_visible():
                    close_btn.click()
                    time.sleep(1)
            except Exception:
                pass

            # Di halaman Diskusi, terdapat sidebar yang mendaftar Sesi dan item-itemnya
            # Biasanya ditandai dengan .session-box atau p.title yang berisi "Sesi"
            # Kita bisa extract langsung dari links Sesi di sidebar
            
            # Kita akan mencari semua <p> yang merupakan judul Sesi, dan <ul> berikutnya
            # Tapi cara termudah adalah extract semua link yang menuju '/sections/...'
            
            all_links = self.page.query_selector_all(f'a[href*="/panel/classes/{course.course_id}/sections/"]')
            sessions_data = {}

            for link in all_links:
                href = link.get_attribute("href") or ""
                text = link.inner_text().strip()
                if not text or len(text) < 2:
                    continue

                # Cek apakah ini tombol/link navigasi biasa (lewatkan)
                if "Sesi Pembelajaran" in text:
                    continue

                # Extract section ID dan item ID
                # Format: /panel/classes/1899364/sections/28315701/7364230/
                match = re.search(r'/sections/(\d+)/(\d+)', href)
                if not match:
                    continue
                    
                section_id = match.group(1)
                item_id = match.group(2)

                if section_id not in sessions_data:
                    sessions_data[section_id] = {
                        "section_id": section_id,
                        "items": []
                    }

                # Tentukan icon_type berdasarkan nama atau container
                icon_type = ""
                clean_text = text.lower()
                if "quiz" in clean_text or "kuis" in clean_text:
                    icon_type = "quiz"
                elif "video konferensi" in clean_text or "vicon" in clean_text:
                    icon_type = "vicon"
                elif "tugas" in clean_text or "assignment" in clean_text:
                    icon_type = "tugas"
                else:
                    icon_type = "material"

                content_type, priority = classify_content(text, icon_type)

                # Cek duplikat
                if not any(item["item_id"] == item_id for item in sessions_data[section_id]["items"]):
                    sessions_data[section_id]["items"].append({
                        "title": text.split("\n")[0].strip(),
                        "content_type": content_type,
                        "priority": priority,
                        "url": f"{EDLINK_BASE_URL}{href}",
                        "item_id": item_id
                    })

            # Convert ke Session objects
            sessions = []
            for i, (sid, sdata) in enumerate(sorted(sessions_data.items()), 1):
                session = Session(number=i, title=f"Sesi {i}", upload_date="")

                for item_data in sdata["items"]:
                    item = CourseItem(
                        title=item_data["title"],
                        content_type=item_data["content_type"],
                        priority=item_data["priority"],
                        url=item_data["url"]
                    )
                    session.items.append(item)

                if session.items:
                    sessions.append(session)
                    print(f"  Sesi {i}: {len(session.items)} item")
                    for item in session.items:
                        print(f"    [{item.priority}] {item.title} ({item.content_type})")

            course.sessions = sessions
            return sessions

        except Exception as e:
            print(f"  Error: {e}")
            return []

    def get_item_detail(self, item_url):
        """Buka halaman detail item dan cari file download"""
        try:
            self.page.goto(item_url, wait_until="networkidle")
            time.sleep(2)

            # Cari link download file
            download_links = self.page.query_selector_all(
                'a[href*="download"], a[href*=".pdf"], a[href*=".doc"], '
                'a[href*=".ppt"], a[href*="storage.googleapis.com"], '
                'a[download], button:has-text("Download"), button:has-text("Unduh")'
            )

            files = []
            for link in download_links:
                href = link.get_attribute("href") or ""
                text = link.inner_text().strip()
                if href:
                    files.append({"url": href, "name": text or href.split("/")[-1]})

            # Cari juga embedded content (YouTube, dll)
            youtube_frames = self.page.query_selector_all('iframe[src*="youtube"], iframe[src*="youtu.be"]')
            for frame in youtube_frames:
                src = frame.get_attribute("src") or ""
                files.append({"url": src, "name": "Video YouTube", "type": "video"})

            return files

        except Exception as e:
            print(f"  Error detail: {e}")
            return []

    def download_file(self, url, filename=""):
        """Download file dari Edlink"""
        try:
            if not filename:
                filename = url.split("/")[-1].split("?")[0]

            download_path = DOWNLOADS_DIR / filename

            # Coba download via Playwright
            with self.page.expect_download(timeout=30000) as download_info:
                self.page.goto(url)
            download = download_info.value
            download.save_as(str(download_path))
            print(f"    Downloaded: {filename}")
            return str(download_path)

        except Exception:
            # Fallback: download via requests dengan cookies browser
            try:
                import requests
                cookies = self.page.context.cookies()
                cookie_dict = {c['name']: c['value'] for c in cookies}
                resp = requests.get(url, cookies=cookie_dict, stream=True, timeout=30)
                if resp.status_code == 200:
                    download_path = DOWNLOADS_DIR / filename
                    with open(download_path, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"    Downloaded (fallback): {filename}")
                    return str(download_path)
            except Exception as e2:
                print(f"    Download gagal: {e2}")
            return ""

    def scrape_all(self):
        """Jalankan full scraping"""
        try:
            self.start()
            if not self.login():
                return []

            courses = self.get_courses()
            if not courses:
                return []

            for course in courses:
                self.get_sessions_and_items(course)

            return courses
        finally:
            self.stop()
