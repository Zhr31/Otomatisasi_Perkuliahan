"""
models/course_data.py — Data classes untuk menyimpan informasi dari Edlink
"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class CourseItem:
    """Satu item konten dalam sesi (tugas, materi, video, dll)"""
    title: str                          # Judul item
    content_type: str                   # "ujian", "vicon", "quiz", "video", "pdf", "word", "ppt", "absensi"
    priority: str                       # "P1", "P2", "P3", "P4"
    url: str = ""                       # Link ke item di Edlink
    download_url: str = ""              # Link download file (jika ada)
    file_name: str = ""                 # Nama file yang didownload
    deadline: Optional[datetime] = None # Deadline (jika ada)
    description: str = ""               # Deskripsi tambahan
    is_processed: bool = False          # Sudah diproses atau belum


@dataclass
class Session:
    """Satu sesi dalam mata kuliah"""
    number: int                         # Nomor sesi (1, 2, 3, ...)
    title: str                          # Judul sesi
    upload_date: str = ""               # Tanggal upload
    items: list[CourseItem] = field(default_factory=list)


@dataclass
class Course:
    """Satu mata kuliah"""
    name: str                           # Nama mata kuliah
    course_id: str = ""                 # ID unik dari Edlink
    url: str = ""                       # Link ke mata kuliah di Edlink
    sessions: list[Session] = field(default_factory=list)
    gdrive_folder_id: str = ""          # ID folder di Google Drive
    ticktick_project_id: str = ""       # ID project di TickTick


def classify_content(title: str, description: str = "") -> tuple[str, str]:
    """
    Klasifikasi tipe konten dan prioritas berdasarkan judul dan deskripsi.
    
    Returns:
        (content_type, priority) — contoh: ("quiz", "P1")
    """
    text = (title + " " + description).lower()
    
    # P1 — Ujian, Vicon, Quiz (URGENT)
    p1_keywords = [
        "ujian", "uts", "uas", "exam", "kuis", "quiz",
        "vicon", "video conference", "zoom", "meet", "webinar",
        "tugas", "assignment", "submit", "pengumpulan"
    ]
    for kw in p1_keywords:
        if kw in text:
            if "quiz" in text or "kuis" in text:
                return ("quiz", "P1")
            elif "vicon" in text or "video conference" in text or "zoom" in text or "meet" in text:
                return ("vicon", "P1")
            elif "ujian" in text or "uts" in text or "uas" in text:
                return ("ujian", "P1")
            else:
                return ("tugas", "P1")
    
    # P2 — Video YouTube
    p2_keywords = ["youtube", "youtu.be", "video", "tonton", "watch"]
    for kw in p2_keywords:
        if kw in text:
            return ("video", "P2")
    
    # P3 — Materi (PDF, Word, PPT)
    p3_keywords = [".pdf", ".doc", ".docx", ".ppt", ".pptx", "materi", "modul", "slide", "bahan"]
    for kw in p3_keywords:
        if kw in text:
            if ".pdf" in text or "pdf" in text:
                return ("pdf", "P3")
            elif ".ppt" in text or "slide" in text:
                return ("ppt", "P3")
            elif ".doc" in text:
                return ("word", "P3")
            else:
                return ("materi", "P3")
    
    # P4 — Absensi/Komentar
    p4_keywords = ["absen", "hadir", "kehadiran", "komentar", "diskusi", "forum", "presensi"]
    for kw in p4_keywords:
        if kw in text:
            return ("absensi", "P4")
    
    # Default — P3 (materi umum)
    return ("materi", "P3")
