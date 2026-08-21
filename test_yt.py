import sys
import os
import io
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from local_video_processor import handle_online_video_url

def main():
    log_file = "yt_test_log.txt"
    print(f"Running yt-dlp diagnostic test. Results will be saved to {log_file}...")
    
    with open(log_file, "w", encoding="utf-8") as f:
        def log_to_file(msg):
            print(msg)
            f.write(msg + "\n")
            f.flush()
            
        log_to_file("=== YT-DLP DIAGNOSTIC RUN ===")
        log_to_file(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        log_to_file(f"Python: {sys.executable}")
        
        try:
            import yt_dlp
            log_to_file("yt_dlp imported successfully.")
        except Exception as e:
            log_to_file(f"ERROR: Failed to import yt_dlp: {e}")
            return
            
        test_url = "https://youtube.com/shorts/-_-_2_H2YSA?si=XPsaaceACIUWSTtG"
        log_to_file(f"Testing URL: {test_url}")
        
        try:
            buffer = handle_online_video_url(test_url, log_func=log_to_file)
            if buffer:
                log_to_file("🟢 SUCCESS: handle_online_video_url returned a buffer!")
                log_to_file(f"Buffer MIME type: {getattr(buffer, 'mime_type', 'N/A')}")
                log_to_file(f"Buffer display name: {getattr(buffer, 'display_name', 'N/A')}")
                buffer.seek(0, 2)
                size = buffer.tell()
                log_to_file(f"Buffer size: {size / (1024 * 1024):.2f} MB")
            else:
                log_to_file("🔴 FAILED: handle_online_video_url returned None.")
        except Exception as e:
            log_to_file(f"🔴 CRITICAL EXCEPTION: {e}")
            import traceback
            log_to_file(traceback.format_exc())

if __name__ == "__main__":
    main()
