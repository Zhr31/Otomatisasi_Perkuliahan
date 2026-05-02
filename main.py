"""
main.py — Entry point utama untuk Otomatisasi Perkuliahan

Menjalankan pipeline lengkap:
1. Scrape Edlink → ambil data mata kuliah, sesi, dan konten
2. Buat task di TickTick dengan prioritas otomatis
3. Download materi & upload ke Google Drive
4. Generate mini resume & upload ke Google Drive

CARA JALANKAN:
    python main.py              → Jalankan semua
    python main.py --explore    → Eksplorasi Edlink saja
    python main.py --test       → Test koneksi semua API
"""
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Setup path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config import (
    TICKTICK_CLIENT_ID, TICKTICK_CLIENT_SECRET, TICKTICK_ACCESS_TOKEN,
    GEMINI_API_KEY, GDRIVE_ROOT_FOLDER_ID, GDRIVE_CREDENTIALS_FILE,
    GDRIVE_TOKEN_FILE, PRIORITY_MAP, STATE_FILE, DOWNLOADS_DIR
)


def load_state() -> dict:
    """Load state dari file (track item yang sudah diproses)"""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"processed_items": [], "last_run": ""}


def save_state(state: dict):
    """Simpan state ke file"""
    state["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def test_connections():
    """Test koneksi ke semua API"""
    print("\n" + "=" * 60)
    print("🧪 TEST KONEKSI API")
    print("=" * 60)
    
    results = {}
    
    # Test Gemini
    print("\n1️⃣ GEMINI AI...")
    if GEMINI_API_KEY:
        try:
            from integrations.gemini_client import GeminiClient
            gemini = GeminiClient(GEMINI_API_KEY)
            result = gemini.generate_mini_resume(
                "Ini adalah teks percobaan untuk testing koneksi Gemini AI.",
                "Test", "Test"
            )
            if result:
                results["gemini"] = "✅ Terhubung"
                print(f"  ✅ Gemini AI terhubung! Preview: {result[:100]}...")
            else:
                results["gemini"] = "❌ Gagal generate"
        except Exception as e:
            results["gemini"] = f"❌ Error: {e}"
            print(f"  ❌ Gemini Error: {e}")
    else:
        results["gemini"] = "⚠️ API Key belum diisi"
        print("  ⚠️ GEMINI_API_KEY belum diisi di .env")
    
    # Test TickTick
    print("\n2️⃣ TICKTICK...")
    if TICKTICK_CLIENT_ID:
        try:
            from integrations.ticktick_client import TickTickClient
            ticktick = TickTickClient(TICKTICK_CLIENT_ID, TICKTICK_CLIENT_SECRET)
            if TICKTICK_ACCESS_TOKEN:
                ticktick.access_token = TICKTICK_ACCESS_TOKEN
                ticktick.save_token()
            if ticktick.load_token():
                projects = ticktick.get_projects()
                results["ticktick"] = f"✅ Terhubung ({len(projects)} projects)"
                print(f"  ✅ TickTick terhubung! {len(projects)} projects ditemukan")
            else:
                print("  🌐 Perlu login TickTick di browser...")
                if ticktick.authorize():
                    results["ticktick"] = "✅ Login berhasil"
                else:
                    results["ticktick"] = "❌ Login gagal"
        except Exception as e:
            results["ticktick"] = f"❌ Error: {e}"
            print(f"  ❌ TickTick Error: {e}")
    else:
        results["ticktick"] = "⚠️ Client ID belum diisi"
        print("  ⚠️ TICKTICK_CLIENT_ID belum diisi di .env")
    
    # Test Google Drive
    print("\n3️⃣ GOOGLE DRIVE...")
    if GDRIVE_CREDENTIALS_FILE.exists():
        try:
            from integrations.gdrive_client import GDriveClient
            gdrive = GDriveClient(str(GDRIVE_CREDENTIALS_FILE), str(GDRIVE_TOKEN_FILE))
            if gdrive.authenticate():
                results["gdrive"] = "✅ Terhubung"
                print("  ✅ Google Drive terhubung!")
            else:
                results["gdrive"] = "❌ Login gagal"
        except Exception as e:
            results["gdrive"] = f"❌ Error: {e}"
            print(f"  ❌ Google Drive Error: {e}")
    else:
        results["gdrive"] = "⚠️ credentials.json belum ada"
        print("  ⚠️ credentials.json belum ada. Download dari Google Cloud Console.")
    
    # Ringkasan
    print("\n" + "=" * 60)
    print("📊 RINGKASAN:")
    print("=" * 60)
    for service, status in results.items():
        print(f"  {service.upper()}: {status}")
    
    return results


def run_full_pipeline():
    """Jalankan pipeline lengkap"""
    print("\n" + "=" * 60)
    print("🚀 OTOMATISASI PERKULIAHAN — MULAI")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    state = load_state()
    
    # ============================================
    # STEP 1: Scrape Edlink
    # ============================================
    print("\n" + "=" * 40)
    print("📱 STEP 1: SCRAPING EDLINK")
    print("=" * 40)
    
    from scraper.edlink_scraper import EdlinkScraper
    # Gunakan headless=True jika di GitHub Actions (CI), atau False jika lokal (untuk debug)
    import os
    is_ci = os.getenv("GITHUB_ACTIONS") == "true"
    scraper = EdlinkScraper(headless=is_ci or True) 
    scraper.start()
    
    if not scraper.login():
        print("\n❌ Gagal login Edlink. Proses dihentikan.")
        scraper.stop()
        sys.exit(1) # Lapor ke GitHub kalau ini error agar screenshot di-upload
        return
        
    courses = scraper.get_courses()
    if courses:
        for c in courses:
            scraper.get_sessions_and_items(c)
    
    if not courses:
        print("\n❌ Tidak ada data dari Edlink. Proses dihentikan.")
        print("💡 Jalankan 'python explore_edlink.py' untuk debug")
        return
    
    print(f"\n✅ Ditemukan {len(courses)} mata kuliah")
    
    # ============================================
    # STEP 2: Setup API Clients
    # ============================================
    print("\n" + "=" * 40)
    print("🔧 STEP 2: SETUP API CLIENTS")
    print("=" * 40)
    
    # Gemini
    gemini = None
    if GEMINI_API_KEY:
        from integrations.gemini_client import GeminiClient
        gemini = GeminiClient(GEMINI_API_KEY)
    else:
        print("  ⚠️ Gemini belum dikonfigurasi, skip mini resume")
    
    # TickTick
    ticktick = None
    if TICKTICK_CLIENT_ID:
        from integrations.ticktick_client import TickTickClient
        ticktick = TickTickClient(TICKTICK_CLIENT_ID, TICKTICK_CLIENT_SECRET)
        if TICKTICK_ACCESS_TOKEN:
            ticktick.access_token = TICKTICK_ACCESS_TOKEN
            ticktick.save_token()
        if not ticktick.load_token():
            ticktick.authorize()
    else:
        print("  ⚠️ TickTick belum dikonfigurasi, skip task creation")
    
    # Google Drive
    gdrive = None
    if GDRIVE_CREDENTIALS_FILE.exists():
        from integrations.gdrive_client import GDriveClient
        gdrive = GDriveClient(str(GDRIVE_CREDENTIALS_FILE), str(GDRIVE_TOKEN_FILE))
        gdrive.authenticate()
    else:
        print("  ⚠️ Google Drive belum dikonfigurasi, skip upload")
    
    # ============================================
    # STEP 3: Process setiap mata kuliah
    # ============================================
    print("\n" + "=" * 40)
    print("⚙️ STEP 3: PROSES DATA")
    print("=" * 40)
    
    from utils.file_reader import read_file
    
    for course in courses:
        print(f"\n{'─' * 50}")
        print(f"📖 MATA KULIAH: {course.name}")
        print(f"{'─' * 50}")
        
        # Gunakan satu project khusus 'Kuliah UNSIA' untuk menghindari limit list di akun free
        tt_project_id = ""
        if ticktick:
            tt_project_id = ticktick.find_or_create_project("📚 Kuliah UNSIA")
            course.ticktick_project_id = tt_project_id
        
        for session in course.sessions:
            print(f"\n  📅 Sesi {session.number}: {session.title}")
            
            # Nama folder GDrive
            date_str = session.upload_date or datetime.now().strftime("%Y-%m-%d")
            session_folder_name = f"Sesi {session.number}_{session.title}_{date_str}"
            
            # Buat folder di GDrive
            gdrive_session_folder = ""
            if gdrive and GDRIVE_ROOT_FOLDER_ID:
                _, gdrive_session_folder = gdrive.create_course_structure(
                    course.name, session_folder_name, GDRIVE_ROOT_FOLDER_ID
                )
            
            for item in session.items:
                # Skip jika sudah diproses
                item_key = f"{course.name}|{session.number}|{item.title}"
                if item_key in state["processed_items"]:
                    print(f"    ⏭️ Skip (sudah diproses): {item.title}")
                    continue
                
                print(f"\n    📄 [{item.priority}] {item.title} ({item.content_type})")
                
                # Buat task di TickTick
                if ticktick:
                    priority_value = PRIORITY_MAP.get(item.priority, 0)
                    description = f"Mata Kuliah: {course.name}\nSesi: {session.number}\nTipe: {item.content_type}"
                    if item.deadline:
                        due = item.deadline.isoformat()
                    else:
                        due = ""
                    
                    ticktick.create_task(
                        title=f"[{item.priority}] [{course.name}] {item.title}",
                        project_id=tt_project_id,
                        priority=priority_value,
                        content=description,
                        due_date=due
                    )
                
                # Ekstrak detail item dan download file
                downloaded_path = ""
                if item.url:
                    files = scraper.get_item_detail(item.url)
                    for file_info in files:
                        if "download" in file_info["url"] or "storage" in file_info["url"]:
                            downloaded_path = scraper.download_file(file_info["url"], file_info["name"])
                            break
                
                # Generate mini resume (jika file materi berhasil didownload)
                if downloaded_path and gemini and item.priority == "P3":
                    content = read_file(downloaded_path)
                    if content:
                        resume = gemini.generate_mini_resume(
                            content, course.name, item.title
                        )
                        if resume:
                            resume_filename = f"MINI RESUME_{item.title}.txt"
                            resume_path = DOWNLOADS_DIR / resume_filename
                            gemini.save_resume_as_text(resume, str(resume_path))
                            
                            # Upload resume ke GDrive
                            if gdrive and gdrive_session_folder:
                                gdrive.upload_file(str(resume_path), gdrive_session_folder, resume_filename)
                
                # Upload file asli ke GDrive
                if downloaded_path and gdrive and gdrive_session_folder:
                    gdrive.upload_file(downloaded_path, gdrive_session_folder)
                
                # Mark sebagai processed
                state["processed_items"].append(item_key)
                
    # Tutup browser Playwright setelah semua selesai
    scraper.stop()
    
    # Simpan state
    save_state(state)
    
    print("\n" + "=" * 60)
    print("✅ OTOMATISASI SELESAI!")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 {len(state['processed_items'])} item telah diproses")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Otomatisasi Perkuliahan Edlink")
    parser.add_argument("--explore", action="store_true", help="Eksplorasi Edlink saja")
    parser.add_argument("--test", action="store_true", help="Test koneksi API")
    parser.add_argument("--run", action="store_true", help="Jalankan pipeline lengkap")
    
    args = parser.parse_args()
    
    if args.explore:
        from explore_edlink import explore
        explore()
    elif args.test:
        test_connections()
    elif args.run:
        run_full_pipeline()
    else:
        # Default: tampilkan menu
        print("\n" + "=" * 60)
        print("🎓 OTOMATISASI PERKULIAHAN")
        print("   Edlink → TickTick + GDrive + Mini Resume")
        print("=" * 60)
        print("\nPilih aksi:")
        print("  1. 🔍 Eksplorasi Edlink (JALANKAN INI PERTAMA)")
        print("  2. 🧪 Test koneksi API")
        print("  3. 🚀 Jalankan otomatisasi penuh")
        print("  4. ❌ Keluar")
        
        choice = input("\nPilihan (1-4): ").strip()
        
        if choice == "1":
            from explore_edlink import explore
            explore()
        elif choice == "2":
            test_connections()
        elif choice == "3":
            run_full_pipeline()
        elif choice == "4":
            print("Bye! 👋")
        else:
            print("Pilihan tidak valid")


if __name__ == "__main__":
    main()
