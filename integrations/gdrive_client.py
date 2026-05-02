"""
integrations/gdrive_client.py — Integrasi dengan Google Drive API
"""
import os
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


# Scope yang dibutuhkan
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GDriveClient:
    """Client untuk berinteraksi dengan Google Drive API"""
    
    def __init__(self, credentials_file: str, token_file: str):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self._folder_cache = {}
    
    def authenticate(self) -> bool:
        """
        Autentikasi dengan Google Drive.
        Pertama kali akan membuka browser untuk login.
        Selanjutnya pakai token yang sudah disimpan.
        """
        creds = None
        
        # Cek token yang sudah ada
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            except Exception:
                pass
        
        # Jika token expired atau belum ada
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("  🔄 Token Google Drive di-refresh")
                except Exception:
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    print("  ❌ File credentials.json tidak ditemukan!")
                    print("  📝 Download dari Google Cloud Console:")
                    print("     https://console.cloud.google.com/apis/credentials")
                    return False
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=8081)
                print("  ✅ Login Google Drive berhasil!")
            
            # Simpan token
            with open(self.token_file, "w") as f:
                f.write(creds.to_json())
        
        self.service = build("drive", "v3", credentials=creds)
        print("  ✅ Google Drive terhubung")
        return True
    
    def find_folder(self, name: str, parent_id: str = None) -> str:
        """Cari folder berdasarkan nama. Return folder ID atau empty string."""
        cache_key = f"{parent_id}:{name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]
        
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        try:
            results = self.service.files().list(
                q=query, spaces="drive", fields="files(id, name)"
            ).execute()
            
            files = results.get("files", [])
            if files:
                folder_id = files[0]["id"]
                self._folder_cache[cache_key] = folder_id
                return folder_id
        except Exception as e:
            print(f"  ❌ Error cari folder: {e}")
        
        return ""
    
    def create_folder(self, name: str, parent_id: str = None) -> str:
        """Buat folder baru. Return folder ID."""
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_id:
            metadata["parents"] = [parent_id]
        
        try:
            folder = self.service.files().create(
                body=metadata, fields="id"
            ).execute()
            folder_id = folder.get("id", "")
            
            cache_key = f"{parent_id}:{name}"
            self._folder_cache[cache_key] = folder_id
            print(f"  📁 Folder dibuat: {name}")
            return folder_id
        except Exception as e:
            print(f"  ❌ Error buat folder: {e}")
            return ""
    
    def find_or_create_folder(self, name: str, parent_id: str = None) -> str:
        """Cari folder, buat jika belum ada"""
        folder_id = self.find_folder(name, parent_id)
        if folder_id:
            return folder_id
        return self.create_folder(name, parent_id)
    
    def create_course_structure(self, course_name: str, session_name: str, 
                                 root_folder_id: str = None) -> tuple[str, str]:
        """
        Buat struktur folder:
        KELAS [MATA KULIAH] > SESI_NAMA_TANGGAL
        
        Returns:
            (course_folder_id, session_folder_id)
        """
        # Folder mata kuliah
        course_folder_name = f"KELAS {course_name.upper()}"
        course_folder_id = self.find_or_create_folder(course_folder_name, root_folder_id)
        
        # Subfolder sesi
        session_folder_id = self.find_or_create_folder(session_name, course_folder_id)
        
        return course_folder_id, session_folder_id
    
    def upload_file(self, file_path: str, folder_id: str, file_name: str = None) -> str:
        """
        Upload file ke Google Drive.
        
        Returns:
            File ID atau empty string jika gagal
        """
        if not os.path.exists(file_path):
            print(f"  ❌ File tidak ditemukan: {file_path}")
            return ""
        
        if not file_name:
            file_name = os.path.basename(file_path)
        
        # Tentukan MIME type
        ext = Path(file_path).suffix.lower()
        mime_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".ppt": "application/vnd.ms-powerpoint",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".txt": "text/plain",
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".mp4": "video/mp4",
        }
        mime_type = mime_types.get(ext, "application/octet-stream")
        
        metadata = {
            "name": file_name,
            "parents": [folder_id]
        }
        
        try:
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            file = self.service.files().create(
                body=metadata, media_body=media, fields="id"
            ).execute()
            file_id = file.get("id", "")
            print(f"  ☁️ Upload ke GDrive: {file_name}")
            return file_id
        except Exception as e:
            print(f"  ❌ Gagal upload: {e}")
            return ""
    
    def file_exists(self, name: str, folder_id: str) -> bool:
        """Cek apakah file sudah ada di folder"""
        try:
            query = f"name='{name}' and '{folder_id}' in parents and trashed=false"
            results = self.service.files().list(
                q=query, spaces="drive", fields="files(id)"
            ).execute()
            return len(results.get("files", [])) > 0
        except Exception:
            return False
