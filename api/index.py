from flask import Flask, request, jsonify, send_from_directory
import os
import sys
import io
import tempfile

# Add project root to python path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from local_video_processor import handle_online_video_url, transcribe_media, extract_keyframes, analyze_transcription, log_to_notion

app = Flask(__name__)

@app.route('/')
def home():
    # Serve index.html from the parent directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return send_from_directory(root_dir, 'index.html')

@app.route('/api/annotate', methods=['POST'])
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
        
        # Check if keys are set
        if not notion_token or "placeholder" in notion_token:
            return jsonify({'error': 'Notion API credentials are not set on the server.'}), 400

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

        # Step 1: If URL is used, download audio buffer and extract keyframes
        audio_payload = None
        if not temp_filepath:
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

        # Step 2: Transcribe
        transcription = ""
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
            markdown = (
                "# 📝 Live Event Annotation\n\n"
                "### Summary\n"
                f"Successfully captured event: {url}\n\n"
                "### Learning Roadmap\n"
                "- [ ] Review session notes and video highlights.\n"
                "- [ ] Check out linked resources.\n"
            )

        # Step 4: Pushing to Notion
        db_entry_url = log_to_notion(notion_token, db_id, url, transcription, markdown)
        
        return jsonify({
            'success': True,
            'notion_url': db_entry_url,
            'markdown': markdown,
            'message': 'Annotation successfully processed!'
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

# For local testing
if __name__ == '__main__':
    app.run(port=5000, debug=True)
