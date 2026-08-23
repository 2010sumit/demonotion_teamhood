from flask import Flask, request, jsonify, send_from_directory
import os
import sys
import io
import tempfile

import traceback

# Add project root to python path to import local modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import_error = None
try:
    import config
    from local_video_processor import (
        handle_online_video_url, transcribe_media, extract_keyframes, 
        analyze_transcription, log_to_notion, extract_youtube_video_id, get_youtube_transcript,
        FALLBACK_MARKDOWN
    )
except Exception as e:
    import_error = traceback.format_exc()
    config = None
    FALLBACK_MARKDOWN = "Import failed fallback"

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
    media_is_video = True
    
    try:
        if import_error:
            return jsonify({
                'error': 'Server startup failed while importing the processing modules.',
                'details': import_error.splitlines()[-1] if import_error else ''
            }), 500

        # Load keys from config
        openrouter_key = config.OPENROUTER_API_KEY
        gemini_key = config.GEMINI_API_KEY
        groq_key = config.GROQ_API_KEY
        notion_token = config.NOTION_TOKEN
        db_id = config.NOTION_DATABASE_ID
        
        # Avoid spending the serverless request budget when AI credentials are absent.
        has_ai_key = any([
            openrouter_key and not openrouter_key.startswith("your_"),
            gemini_key and not gemini_key.startswith("your_"),
            groq_key and not groq_key.startswith("your_")
        ])
        is_mock_mode = (
            not notion_token or "placeholder" in notion_token or
            not db_id or "placeholder" in db_id or not has_ai_key
        )

        if is_mock_mode:
            db_entry_url = "https://notion.so (Offline/Sandbox Mode: Active)"
            print("[*] Notion sync skipped (offline/mock mode active)")
            return jsonify({
                'success': True,
                'notion_url': db_entry_url,
                'markdown': FALLBACK_MARKDOWN,
                'is_mock_mode': True,
                'message': 'Processed in Sandbox Mode (configure Vercel environment variables for live processing)!'
            })

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
                media_is_video = file.mimetype.startswith('video/') if file.mimetype else ext.lower() not in {'.mp3', '.wav', '.m4a', '.ogg'}
                
                # Extract keyframes from local temporary file
                try:
                    # Keep the payload small enough for a serverless request while retaining visual context.
                    base64_frames = extract_keyframes(temp_filepath, num_frames=2)
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
                import yt_dlp
                video_stream_url = None
                ydl_opts = {
                    'format': 'worstvideo[protocol^=http]/worst[protocol^=http]',
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,
                }
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;10000000"

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                        video_stream_url = info.get('url')
                except Exception as e_yt:
                    print(f"yt-dlp video extract warning: {e_yt}. Trying Piped API fallback...")
                    
                # NEW PIPED API FALLBACK FOR VIDEO STREAM
                if not video_stream_url and video_id:
                    import requests
                    piped_url = f"https://pipedapi.kavin.rocks/streams/{video_id}"
                    try:
                        res = requests.get(piped_url, timeout=10)
                        if res.status_code == 200:
                            data = res.json()
                            video_streams = data.get('videoStreams', [])
                            if video_streams:
                                # Pick lowest quality video stream for faster keyframe extraction
                                video_streams.sort(key=lambda x: x.get('bitrate', 99999999))
                                video_stream_url = video_streams[0]['url']
                                print("[*] Successfully got video stream from Piped API.")
                    except Exception as e_piped:
                        print(f"Piped video fallback failed: {e_piped}")

                base64_frames = extract_keyframes(
                    video_stream_url or url,
                    num_frames=2
                )
            except Exception as e:
                print(f"Keyframe extraction warning for URL: {e}")
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

        audio_analyzed = transcription != "<noise_or_silent_video>"
        video_analyzed = bool(base64_frames) if media_is_video else False

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
            markdown = FALLBACK_MARKDOWN

        # Step 4: Pushing to Notion (Disabled as requested)
        if is_mock_mode:
            db_entry_url = "https://notion.so (Offline/Sandbox Mode: Active)"
            print("[*] Notion sync skipped (offline/mock mode active)")
        else:
            print("[*] Notion sync disabled by user request.")
            db_entry_url = ""
        
        return jsonify({
            'success': True,
            'notion_url': db_entry_url,
            'markdown': markdown,
            'audio_analyzed': audio_analyzed,
            'video_analyzed': video_analyzed,
            'is_mock_mode': is_mock_mode,
            'message': (
                'Annotation successfully processed and synced to Notion!'
                if not is_mock_mode and db_entry_url
                else 'Annotation processed in fallback mode; Notion sync was skipped.'
                if is_mock_mode
                else 'Annotation processed, but Notion sync failed.'
            )
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
        if import_error:
            return jsonify({
                'success': False,
                'error': 'Server startup failed while importing the processing modules.',
                'details': import_error.splitlines()[-1] if import_error else ''
            }), 500

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
