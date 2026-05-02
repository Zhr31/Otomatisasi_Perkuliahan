"""
integrations/gemini_client.py — Generate Mini Resume menggunakan Gemini AI
"""
import os
from pathlib import Path
from google import genai


class GeminiClient:
    """Client untuk berinteraksi dengan Gemini AI API"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        print(f"  ✅ Gemini AI terhubung (model: {model})")
    
    def generate_mini_resume(self, content: str, subject_name: str, material_title: str) -> str:
        """
        Generate mini resume dari konten materi kuliah.
        
        Args:
            content: Teks isi materi
            subject_name: Nama mata kuliah
            material_title: Judul materi
            
        Returns:
            Mini resume dalam format teks
        """
        if not content or len(content.strip()) < 50:
            print("  ⚠️ Konten terlalu pendek untuk dibuat resume")
            return ""
        
        # Batasi konten agar tidak melebihi limit token
        max_chars = 30000  # ~7500 tokens
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n[... konten dipotong karena terlalu panjang ...]"
        
        prompt = f"""Kamu adalah asisten akademik yang ahli membuat ringkasan materi kuliah.

Buatkan MINI RESUME dalam Bahasa Indonesia dari materi kuliah berikut.

📚 Mata Kuliah: {subject_name}
📄 Judul Materi: {material_title}

FORMAT MINI RESUME:
1. **Judul**: MINI RESUME - {material_title}
2. **Mata Kuliah**: {subject_name}
3. **Ringkasan Umum** (2-3 kalimat pengantar)
4. **Poin-Poin Kunci** (bullet points, maksimal 10-15 poin utama)
5. **Definisi/Istilah Penting** (jika ada)
6. **Kesimpulan** (2-3 kalimat penutup)

ATURAN:
- Gunakan bahasa yang mudah dipahami mahasiswa
- Fokus pada konsep utama dan definisi penting
- Maksimal 2 halaman jika di-print
- Gunakan emoji untuk membuat lebih menarik dan mudah dibaca
- Jangan menambahkan informasi yang tidak ada di materi asli

MATERI:
{content}
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            resume = response.text
            if resume is None:
                print(f"  ❌ Gagal generate mini resume: response text is None")
                return ""
            print(f"  ✅ Mini resume berhasil dibuat ({len(resume)} karakter)")
            return resume
        except Exception as e:
            print(f"  ❌ Gagal generate mini resume: {e}")
            return ""
    
    def save_resume_as_text(self, resume_text: str, output_path: str) -> bool:
        """Simpan resume sebagai file .txt"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(resume_text)
            print(f"  💾 Resume disimpan: {output_path}")
            return True
        except Exception as e:
            print(f"  ❌ Gagal simpan resume: {e}")
            return False
    
    def save_resume_as_pdf(self, resume_text: str, output_path: str) -> bool:
        """Simpan resume sebagai file PDF"""
        try:
            from fpdf import FPDF
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Gunakan font bawaan yang mendukung latin
            pdf.set_font("Helvetica", size=11)
            
            # Tulis per baris
            for line in resume_text.split("\n"):
                # Skip emoji/unicode yang tidak didukung font default
                clean_line = line.encode('latin-1', errors='replace').decode('latin-1')
                if clean_line.startswith("# ") or clean_line.startswith("**"):
                    pdf.set_font("Helvetica", "B", 13)
                    clean_line = clean_line.replace("# ", "").replace("**", "")
                    pdf.multi_cell(0, 7, clean_line)
                    pdf.set_font("Helvetica", size=11)
                elif clean_line.startswith("## "):
                    pdf.set_font("Helvetica", "B", 12)
                    clean_line = clean_line.replace("## ", "")
                    pdf.multi_cell(0, 7, clean_line)
                    pdf.set_font("Helvetica", size=11)
                else:
                    pdf.multi_cell(0, 6, clean_line)
            
            pdf.output(output_path)
            print(f"  📄 Resume PDF disimpan: {output_path}")
            return True
        except Exception as e:
            print(f"  ❌ Gagal buat PDF: {e}")
            # Fallback: simpan sebagai txt
            txt_path = output_path.replace(".pdf", ".txt")
            return self.save_resume_as_text(resume_text, txt_path)
