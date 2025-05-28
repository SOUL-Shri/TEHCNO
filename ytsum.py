import os
import re
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Initialize the model
model = genai.GenerativeModel('gemini-1.5-flash')

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*?&v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_transcript(video_id):
    """Get transcript from YouTube video with language fallback"""
    try:
        # First try English transcript
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            detected_language = 'en'
        except Exception:
            # If English not available, get the first available language
            transcript = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get manually created transcripts first
            for t in transcript:
                if not t.is_generated:
                    transcript_list = t.fetch()
                    detected_language = t.language_code
                    break
            else:
                # If no manual transcript, get the first generated one
                for t in transcript:
                    if t.is_generated:
                        transcript_list = t.fetch()
                        detected_language = t.language_code
                        break
        
        formatter = TextFormatter()
        text_transcript = formatter.format_transcript(transcript_list)
        
        # If not English, translate using Gemini
        if detected_language != 'en':
            print(f"🌐 Transcript in {detected_language}. Translating to English using Gemini...")
            translation_prompt = f"""
            Please translate the following transcript from {detected_language} to English. 
            Preserve the meaning and maintain natural language flow.
            
            Transcript:
            {text_transcript}
            
            Please provide only the English translation, no additional text.
            """
            
            response = model.generate_content(translation_prompt)
            text_transcript = response.text
            
        return text_transcript, detected_language
    except Exception as e:
        print(f"Error getting transcript: {e}")
        return None, None

def generate_notes_with_gemini(transcript):
    """Generate notes and summary using Gemini"""
    try:
        prompt = f"""
        Based on the following transcript from a YouTube video, please create comprehensive notes and a summary.

        First, create detailed notes that:
        1. Extract key concepts and main ideas
        2. Organize information into logical sections
        3. Include important definitions or explanations
        4. List any significant examples or case studies mentioned
        5. Note any actionable tips or recommendations

        Then, provide a concise summary of the video.

        Here's the transcript:

        {transcript}

        Please format your response as follows:
        NOTES:
        [Detailed notes here]

        SUMMARY:
        [Concise summary here]
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating notes with Gemini: {e}")
        return None

def save_to_file(content, filename="video_notes"):
    """Save content to text files"""
    try:
        # Save the full content (notes + summary)
        with open(f"{filename}_full.txt", "w", encoding="utf-8") as f:
            f.write(content)
        
        # Parse and save notes and summary separately
        parts = content.split("SUMMARY:")
        if len(parts) == 2:
            notes = parts[0].replace("NOTES:", "").strip()
            summary = parts[1].strip()
            
            with open(f"{filename}_notes.txt", "w", encoding="utf-8") as f:
                f.write(notes)
            
            with open(f"{filename}_summary.txt", "w", encoding="utf-8") as f:
                f.write(summary)
            
            print(f"✅ Files saved successfully:")
            print(f"   - {filename}_full.txt (Complete notes and summary)")
            print(f"   - {filename}_notes.txt (Just the notes)")
            print(f"   - {filename}_summary.txt (Just the summary)")
            print(f"✅ Raw transcript saved to: {filename}_transcript.txt")
        else:
            print(f"✅ Full content saved to: {filename}_full.txt")
    except Exception as e:
        print(f"Error saving files: {e}")

def process_youtube_video(url):
    """Main function to process YouTube video"""
    # Extract video ID
    video_id = extract_video_id(url)
    if not video_id:
        print("❌ Invalid YouTube URL")
        return
    
    print(f"🎥 Processing video ID: {video_id}")
    
    # Get transcript
    transcript, language = get_transcript(video_id)
    if not transcript:
        print("❌ Could not retrieve transcript. Make sure the video has subtitles/captions available.")
        return
    
    # Save raw transcript
    with open(f"video_{video_id}_transcript.txt", "w", encoding="utf-8") as f:
        f.write(transcript)
    
    print(f"📝 Generating notes with Gemini... (Original language: {language})")
    
    # Generate notes using Gemini
    notes_content = generate_notes_with_gemini(transcript)
    if not notes_content:
        print("❌ Could not generate notes")
        return
    
    # Save to files
    save_to_file(notes_content, f"video_{video_id}")
    
    print("✅ Processing complete!")

if __name__ == "__main__":
    # Create .env file for API key if it doesn't exist
    if not os.path.exists('.env'):
        print("Creating .env file. Please enter your Gemini API key.")
        api_key = input("Enter your Gemini API key: ")
        with open('.env', 'w') as f:
            f.write(f"GEMINI_API_KEY={api_key}")
        print(".env file created with your API key")
    
    # Get YouTube URL from user
    url = input("Enter YouTube video URL: ")
    process_youtube_video(url)