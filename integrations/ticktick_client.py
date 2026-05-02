"""
integrations/ticktick_client.py — Integrasi dengan TickTick API
"""
import json
import webbrowser
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path


class TickTickClient:
    """Client untuk berinteraksi dengan TickTick Open API"""
    
    API_BASE = "https://api.ticktick.com/open/v1"
    AUTH_URL = "https://ticktick.com/oauth/authorize"
    TOKEN_URL = "https://ticktick.com/oauth/token"
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://localhost:8080/callback"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = ""
        self.token_file = Path(__file__).parent.parent / "ticktick_token.json"
        self._projects_cache = {}
    
    def load_token(self) -> bool:
        """Load token dari file jika ada"""
        if self.token_file.exists():
            try:
                with open(self.token_file, "r") as f:
                    data = json.load(f)
                    self.access_token = data.get("access_token", "")
                    if self.access_token:
                        # Verifikasi token masih valid
                        resp = requests.get(
                            f"{self.API_BASE}/project",
                            headers=self._headers()
                        )
                        if resp.status_code == 200:
                            print("  ✅ TickTick token valid (dari file)")
                            return True
                        else:
                            print("  ⚠️ TickTick token expired, perlu login ulang")
            except Exception:
                pass
        return False
    
    def save_token(self):
        """Simpan token ke file"""
        with open(self.token_file, "w") as f:
            json.dump({"access_token": self.access_token}, f)
    
    def authorize(self):
        """
        Mulai OAuth2 flow untuk mendapatkan access token.
        Akan membuka browser dan menunggu callback.
        """
        if self.load_token():
            return True
        
        if not self.client_id or not self.client_secret:
            print("  ❌ TickTick Client ID / Secret belum diisi di .env!")
            print("  📝 Daftar di: https://developer.ticktick.com/manage")
            return False
        
        # Step 1: Buka browser untuk login
        auth_url = (
            f"{self.AUTH_URL}"
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&response_type=code"
            f"&scope=tasks:write tasks:read"
        )
        
        print(f"\n  🌐 Membuka browser untuk login TickTick...")
        print(f"  📎 URL: {auth_url}")
        webbrowser.open(auth_url)
        
        # Step 2: Tunggu callback dengan authorization code
        auth_code = self._wait_for_callback()
        if not auth_code:
            print("  ❌ Gagal mendapatkan authorization code")
            return False
        
        # Step 3: Exchange code for token
        try:
            resp = requests.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": auth_code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if resp.status_code == 200:
                token_data = resp.json()
                self.access_token = token_data.get("access_token", "")
                self.save_token()
                print("  ✅ TickTick berhasil terautentikasi!")
                return True
            else:
                print(f"  ❌ Gagal mendapat token: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"  ❌ Error saat exchange token: {e}")
            return False
    
    def _wait_for_callback(self) -> str:
        """Jalankan mini HTTP server untuk menangkap callback OAuth"""
        auth_code = None
        
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                nonlocal auth_code
                query = parse_qs(urlparse(self.path).query)
                auth_code = query.get("code", [None])[0]
                
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                <html><body style="font-family:Arial;text-align:center;padding:50px">
                <h1>Berhasil! Login TickTick sukses</h1>
                <p>Kamu bisa menutup tab ini dan kembali ke program.</p>
                </body></html>
                """)
            
            def log_message(self, format, *args):
                pass  # Suppress log output
        
        server = HTTPServer(("localhost", 8080), CallbackHandler)
        print("  ⏳ Menunggu login di browser... (selesaikan login lalu kembali)")
        server.handle_request()  # Handle satu request saja
        server.server_close()
        
        return auth_code
    
    def _headers(self) -> dict:
        """Headers untuk API request"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def get_projects(self) -> list:
        """Ambil semua project/list"""
        try:
            resp = requests.get(f"{self.API_BASE}/project", headers=self._headers())
            if resp.status_code == 200:
                projects = resp.json()
                self._projects_cache = {p["name"]: p["id"] for p in projects}
                return projects
            else:
                print(f"  ❌ Gagal ambil projects: {resp.status_code}")
                return []
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return []
    
    def find_or_create_project(self, name: str) -> str:
        """Cari project berdasarkan nama, buat jika belum ada"""
        # Cek cache dulu
        if not self._projects_cache:
            self.get_projects()
        
        if name in self._projects_cache:
            return self._projects_cache[name]
        
        # Buat project baru
        try:
            resp = requests.post(
                f"{self.API_BASE}/project",
                headers=self._headers(),
                json={"name": name}
            )
            if resp.status_code == 200:
                project = resp.json()
                project_id = project.get("id", "")
                self._projects_cache[name] = project_id
                print(f"  📁 Project TickTick dibuat: {name}")
                return project_id
            else:
                print(f"  ❌ Gagal buat project: {resp.status_code} - {resp.text}")
                return ""
        except Exception as e:
            print(f"  ❌ Error buat project: {e}")
            return ""
    
    def create_task(self, title: str, project_id: str = "", priority: int = 0,
                    content: str = "", due_date: str = "") -> dict:
        """
        Buat task baru di TickTick.
        
        Args:
            title: Judul task
            project_id: ID project (opsional)
            priority: 0=None, 1=Low, 3=Medium, 5=High
            content: Deskripsi task
            due_date: Due date dalam format ISO (2026-05-02T23:59:00+0700)
        """
        payload = {
            "title": title,
            "priority": priority,
        }
        
        if project_id:
            payload["projectId"] = project_id
        if content:
            payload["content"] = content
        if due_date:
            payload["dueDate"] = due_date
        
        try:
            resp = requests.post(
                f"{self.API_BASE}/task",
                headers=self._headers(),
                json=payload
            )
            if resp.status_code == 200:
                task = resp.json()
                priority_label = {0: "P4", 1: "P3", 3: "P2", 5: "P1"}.get(priority, "?")
                print(f"  ✅ Task dibuat [{priority_label}]: {title}")
                return task
            else:
                print(f"  ❌ Gagal buat task: {resp.status_code} - {resp.text}")
                return {}
        except Exception as e:
            print(f"  ❌ Error buat task: {e}")
            return {}
    
    def get_tasks(self, project_id: str) -> list:
        """Ambil semua task dari project tertentu"""
        try:
            resp = requests.get(
                f"{self.API_BASE}/project/{project_id}/data",
                headers=self._headers()
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("tasks", [])
            return []
        except Exception as e:
            print(f"  ❌ Error ambil tasks: {e}")
            return []
