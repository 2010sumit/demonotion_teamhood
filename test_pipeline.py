import sys
import os
import io
import time
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from local_video_processor import load_dotenv, handle_online_video_url, transcribe_media, extract_keyframes, analyze_transcription

def main():
    log_file = "pipeline_test_log.txt"
    print(f"Running full pipeline test. Results will be saved to {log_file}...")
    
    with open(log_file, "w", encoding="utf-8") as f:
        def log_to_file(msg):
            print(msg)
            f.write(msg + "\n")
            f.flush()
            
        log_to_file("=== FULL PIPELINE DIAGNOSTIC RUN ===")
        log_to_file(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        import config
        openrouter_key = config.OPENROUTER_API_KEY
        gemini_key = config.GEMINI_API_KEY
        groq_key = config.GROQ_API_KEY
        
        url = "https://youtube.com/shorts/-_-_2_H2YSA?si=XPsaaceACIUWSTtG"
        
        # 1. Download audio stream
        log_to_file("\n--- Step 1: Downloading Audio Stream ---")
        try:
            audio_buffer = handle_online_video_url(url, log_func=log_to_file)
            if audio_buffer:
                log_to_file(f"Audio buffer verified. Size: {len(audio_buffer.getvalue()) / (1024*1024):.2f} MB")
            else:
                log_to_file("Audio buffer is None.")
        except Exception as e:
            log_to_file(f"Audio download exception: {e}\n{traceback.format_exc()}")
            return
            
        # 2. Extract keyframes from URL
        log_to_file("\n--- Step 2: Extracting Video Keyframes ---")
        video_stream_url = None
        try:
            import yt_dlp
            log_to_file("Querying worstvideo stream from URL...")
            ydl_opts = {
                'format': 'worstvideo[protocol^=http]/worst[protocol^=http]',
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_stream_url = info.get('url')
                log_to_file(f"Extracted video stream URL: {video_stream_url[:100]}...")
        except Exception as e:
            log_to_file(f"Failed to query worstvideo: {e}\n{traceback.format_exc()}")
            
        base64_frames = []
        if video_stream_url:
            try:
                base64_frames = extract_keyframes(video_stream_url, num_frames=3, log_func=log_to_file)
                log_to_file(f"Successfully extracted {len(base64_frames)} real keyframes.")
            except Exception as e:
                log_to_file(f"Failed to extract keyframes from stream: {e}\n{traceback.format_exc()}")
        else:
            log_to_file("No video stream URL found. Falling back to dummy scan.")
            
        # 3. Transcribe media
        log_to_file("\n--- Step 3: Transcribing Audio ---")
        transcription = ""
        try:
            transcription = transcribe_media(audio_buffer, openrouter_key, gemini_key, groq_key, log_func=log_to_file)
            log_to_file(f"Transcription successful: '{transcription}'")
        except Exception as e:
            log_to_file(f"Transcription failed: {e}\n{traceback.format_exc()}")
            
        # 4. Multimodal analysis
        log_to_file("\n--- Step 4: Generating Multimodal Analysis ---")
        try:
            markdown = analyze_transcription(transcription, base64_frames, openrouter_key, gemini_key, log_func=log_to_file)
            log_to_file(f"Multimodal Analysis Output:\n{markdown[:500]}...")
        except Exception as e:
            log_to_file(f"Multimodal analysis failed: {e}\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
