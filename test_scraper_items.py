import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from scraper.edlink_scraper import EdlinkScraper

def test():
    scraper = EdlinkScraper(headless=True)
    scraper.start()
    if scraper.login():
        courses = scraper.get_courses()
        if courses:
            # Test on the first course only
            sessions = scraper.get_sessions_and_items(courses[0])
            for session in sessions:
                print(f"Sesi {session.number}: {session.title}")
                for item in session.items:
                    print(f"  - [{item.priority}] {item.title} ({item.url})")
    scraper.stop()

if __name__ == "__main__":
    test()
