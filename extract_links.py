import re
with open("data/exploration/debug_diskusi.html", "r", encoding="utf-8") as f:
    html = f.read()

links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html)
for href, text in links:
    clean_text = re.sub(r'<[^>]+>', '', text).strip()
    if 'Materi - Sesi #' in clean_text or 'Quiz #' in clean_text or 'Video Konferensi' in clean_text:
        print(f'{clean_text} -> {href}')
