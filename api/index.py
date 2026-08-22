from flask import Flask, request, jsonify, send_from_directory
import os
import sys
import io
import tempfile

# Add project root to python path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from local_video_processor import (
    handle_online_video_url, transcribe_media, extract_keyframes, 
    analyze_transcription, log_to_notion, extract_youtube_video_id, get_youtube_transcript
)

app = Flask(__name__)

@app.route('/')
def home():
    # Serve index.html from the parent directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return send_from_directory(root_dir, 'index.html')

@app.route('/api/index', methods=['POST'])
def annotate():
    temp_filepath = None
    url = ""
    
    try:
        # Load keys from config
        openrouter_key = config.OPENROUTER_API_KEY
        gemini_key = config.GEMINI_API_KEY
        groq_key = config.GROQ_API_KEY
        notion_token = config.NOTION_TOKEN
        db_id = config.NOTION_DATABASE_ID
        
        # Check if keys are set (gracefully handle placeholder mode for offline/preview demo)
        is_mock_mode = (not notion_token or "placeholder" in notion_token or not db_id or "placeholder" in db_id)

        # Base64 frames accumulator for vision model analysis
        base64_frames = []

        # Check if file was uploaded via multipart form
        if 'file' in request.files:
            file = request.files['file']
            if file.filename != '':
                # Save file to a temporary filepath so OpenCV can extract keyframes
                ext = os.path.splitext(file.filename)[1] or '.mp4'
                
                # Check upload payload size in request directly
                file_bytes = file.read()
                file_size = len(file_bytes)
                
                is_vercel = os.environ.get('VERCEL') == '1'
                if is_vercel and file_size > 4.5 * 1024 * 1024:
                    return jsonify({
                        'error': 'File size exceeds Vercel\'s 4.5MB request limit. Please compress the file or use a URL.'
                    }), 400

                # Create temp file
                temp_fd, temp_filepath = tempfile.mkstemp(suffix=ext)
                with os.fdopen(temp_fd, 'wb') as temp_file:
                    temp_file.write(file_bytes)
                
                url = f"Uploaded Local File: {file.filename}"
                
                # Extract keyframes from local temporary file
                try:
                    # Extract up to 3 frames to give Gemini rich visual context
                    base64_frames = extract_keyframes(temp_filepath, num_frames=3)
                except Exception as e:
                    print(f"Keyframe extraction warning for upload: {e}")
        else:
            # Otherwise, read JSON payload for URL
            data = request.get_json() or {}
            url = data.get('url', '').strip()
            
        if not temp_filepath and not url:
            return jsonify({'error': 'Please provide a valid video URL or upload a file.'}), 400

        # Step 1: If URL is used, try to fetch transcription and extract keyframes
        audio_payload = None
        transcription = ""
        
        if not temp_filepath:
            video_id = extract_youtube_video_id(url)
            if video_id:
                transcription = get_youtube_transcript(video_id)
                
            if not transcription:
                try:
                    audio_payload = handle_online_video_url(url)
                except Exception as e:
                    print(f"Ingestion warning for URL: {e}")
                
            try:
                # Query raw stream URL using yt_dlp first so OpenCV can read the stream
                import yt_dlp
                video_stream_url = None
                ydl_opts = {
                    'format': 'worstvideo[protocol^=http]/worst[protocol^=http]',
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,
                }
                
                # Set OpenCV stream capture timeout to 10 seconds to avoid hanging on slow streams
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;10000000"
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    video_stream_url = info.get('url')
                
                if video_stream_url:
                    base64_frames = extract_keyframes(video_stream_url, num_frames=3)
                else:
                    base64_frames = extract_keyframes(url, num_frames=3)
            except Exception as e:
                print(f"Keyframe extraction warning for URL: {e}")
                # Fallback directly if yt_dlp fails
                try:
                    base64_frames = extract_keyframes(url, num_frames=3)
                except Exception:
                    pass
        else:
            audio_payload = temp_filepath

        # Step 2: Transcribe (if not already fetched via YouTube API)
        if not transcription:
            try:
                if audio_payload:
                    transcription = transcribe_media(audio_payload, openrouter_key, gemini_key, groq_key)
            except Exception as e:
                print(f"Transcription warning: {e}")
            
        # Treat noise or empty transcription gracefully
        if not transcription or transcription.strip().lower() in ['<noise>', 'noise', '[noise]']:
            transcription = "<noise_or_silent_video>"

        # Step 3: Multimodal Analysis via Gemini
        markdown = ""
        try:
            # Enhance prompt in case transcription is silent or noise-only
            if transcription == "<noise_or_silent_video>" and base64_frames:
                # Tell analyze_transcription to focus on the keyframe screenshots
                markdown = analyze_transcription(
                    "The audio is silent or contains only keyboard/background noise. Please analyze the visual content of the provided screenshots to document the code, system design, or slides shown in the video.",
                    base64_frames,
                    openrouter_key,
                    gemini_key
                )
            else:
                markdown = analyze_transcription(transcription, base64_frames, openrouter_key, gemini_key)
        except Exception as e:
            print(f"Analysis warning: {e}")
            
        if not markdown:
            from app import FALLBACK_MARKDOWN
            markdown = FALLBACK_MARKDOWN

        # Step 4: Pushing to Notion (Skip or Mock if credentials are not provided)
        if is_mock_mode:
            db_entry_url = "https://notion.so (Offline/Sandbox Mode: Active)"
            print("[*] Notion sync skipped (offline/mock mode active)")
        else:
            db_entry_url = log_to_notion(notion_token, db_id, url, transcription, markdown)
        
        return jsonify({
            'success': True,
            'notion_url': db_entry_url,
            'markdown': markdown,
            'is_mock_mode': is_mock_mode,
            'message': 'Annotation successfully processed!' if not is_mock_mode else 'Processed in Sandbox Mode (Notion Sync Skipped due to placeholder credentials)!'
        })
        
    except Exception as e:
        return jsonify({'error': f"Pipeline error: {str(e)}"}), 500
        
    finally:
        # Step 5: Clean up temporary file from disk
        if temp_filepath and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except Exception as e:
                print(f"Cleanup warning: {e}")

@app.route('/api/config-status', methods=['GET'])
def config_status():
    """Securely returns status of configured APIs without exposing keys."""
    try:
        openrouter_key = config.OPENROUTER_API_KEY
        gemini_key = config.GEMINI_API_KEY
        groq_key = config.GROQ_API_KEY
        notion_token = config.NOTION_TOKEN
        db_id = config.NOTION_DATABASE_ID
        
        return jsonify({
            'success': True,
            'openrouter': bool(openrouter_key and not openrouter_key.startswith("your_")),
            'gemini': bool(gemini_key and not gemini_key.startswith("your_")),
            'groq': bool(groq_key and not groq_key.startswith("your_")),
            'notion_token': bool(notion_token and not notion_token.startswith("your_")),
            'notion_db': bool(db_id and not db_id.startswith("your_"))
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# For local testing
if __name__ == '__main__':
    app.run(port=5000, debug=True)
