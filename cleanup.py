import os
import time
import glob
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def cleanup_old_files(directory, pattern="*", max_age_hours=24):
    if not os.path.exists(directory) and directory != ".":
        logging.info(f"Directory {directory} does not exist, skipping.")
        return
        
    now = time.time()
    max_age_seconds = max_age_hours * 3600
    cleaned = 0
    
    search_path = os.path.join(directory, pattern) if directory != "." else pattern
    
    for filepath in glob.glob(search_path):
        if os.path.isfile(filepath):
            file_mtime = os.path.getmtime(filepath)
            if (now - file_mtime) > max_age_seconds:
                try:
                    os.remove(filepath)
                    cleaned += 1
                except Exception as e:
                    logging.error(f"Failed to delete {filepath}: {e}")
                    
    logging.info(f"Cleaned up {cleaned} files from {directory} matching '{pattern}' older than {max_age_hours} hours.")

def run_cleanup():
    logging.info("Starting cleanup task...")
    
    # 1. Clean up scheduled_uploads that have been processed and left behind
    # For scheduled_uploads, if they are older than 48 hours, it's safe to assume they were either processed or abandoned
    cleanup_old_files("scheduled_uploads", pattern="*", max_age_hours=48)
    
    # 2. Clean up temp_uploads (older than 24 hours)
    cleanup_old_files("temp_uploads", pattern="*", max_age_hours=24)
    
    # 3. Clean up root directory debug screenshots (older than 24 hours)
    cleanup_old_files(".", pattern="debug_*.png", max_age_hours=24)
    cleanup_old_files(".", pattern="sync_debug_*.png", max_age_hours=24)
    cleanup_old_files(".", pattern="sync_debug_*.html", max_age_hours=24)
    cleanup_old_files(".", pattern="community_debug.png", max_age_hours=24)
    
    logging.info("Cleanup task finished.")

if __name__ == "__main__":
    run_cleanup()
