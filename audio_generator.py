import os
import re
import asyncio
import edge_tts
from gtts import gTTS


# -------- Output folder --------
OUTPUT_FOLDER = os.path.join("static", "output")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def final_text_sanitization(text: str) -> str:
    """
    Universal text sanitization for ANY comic book.
    Improved with context-aware grammar fixes.
    """
    if not text:
        return ""
    
    # ========== REMOVE SPEAKER TAGS FIRST ==========
    # Remove tags like [NARRATOR], [MALE], [CHILD], etc.
    text = re.sub(r'\[(NARRATOR|MALE|MALE2|FEMALE|CHILD|OLD_MALE)\]\s*', '', text, flags=re.IGNORECASE)
    
    # ========== REMOVE VISUAL ARTIFACTS ==========
    
    # Remove underscores
    text = re.sub(r'_+', ' ', text)
    
    # Remove brackets and parentheses
    text = re.sub(r'[\[\]{}()<>]', '', text)
    
    # Remove special symbols
    text = re.sub(r'[#@$%^&*+=|\\~`]', '', text)
    
    # Remove standalone numbers (page numbers)
    text = re.sub(r'\b\d+\.\d+\b', '', text)
    
    # ========== REMOVE WATERMARKS ==========
    
    # Remove website patterns
    text = re.sub(r'https?://[^\s]+', '', text)
    text = re.sub(r'www\.[^\s]+', '', text)
    text = re.sub(r'\bwww\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\bcom\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\blcom\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\.com\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'iskcondesiretree', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\bunderscore\b', '', text, flags=re.IGNORECASE)
    
    # ========== FIX SENTENCE STRUCTURE ISSUES ==========
    
    # Fix "They The" pattern (OCR error)
    text = re.sub(r'\bThey\s+The\b', 'They got down from their horses. The', text)
    
    # Fix "www get down" → "They got down"
    text = re.sub(r'www\s+get\s+down', 'They got down', text, flags=re.IGNORECASE)
    text = re.sub(r'\bget\s+down\s+from', 'got down from', text)
    
    # ========== FIX "I" PLACEMENT (CONTEXT-AWARE) ==========
    
    # Fix missing "I" ONLY at sentence start or after punctuation
    # Pattern: ". am hungry" → ". I am hungry"
    text = re.sub(r'(\.\s+|\!\s+|\?\s+|^)(am|have|will|shall|can|must|should|would|could)\s+', 
                  r'\1I \2 ', text)
    
    # Fix "thought you" → "I thought you" (after period/start)
    text = re.sub(r'(\.\s+|\!\s+|\?\s+|^)(thought|realize|hope)\s+', r'\1I \2 ', text)
    
    # Fix WRONG "I have" placements (overcorrection from previous rules)
    # "You I have come" → "You have come"
    text = re.sub(r'(\w+)\s+I\s+have\s+(?=come|learned|some)', r'\1 have ', text)
    
    # "may I have some" → "may have some"
    text = re.sub(r'may\s+I\s+have\s+some', 'may have some', text)
    
    # "let I have water" → "let me have water"  
    text = re.sub(r'let\s+I\s+have', 'let me have', text)
    
    # Fix word order: "Can please I have" → "Can I please have"
    text = re.sub(r'\bCan\s+please\s+I\s+have\b', 'Can I please have', text, flags=re.IGNORECASE)
    text = re.sub(r'\bCan\s+I\s+have\s+please\b', 'Can I please have', text, flags=re.IGNORECASE)
    
    # ========== FIX COMMON OCR ERRORS ==========
    
    # Fix exclamation marks read as 'l'
    text = re.sub(r'\b(\w+)l\b(?=\s*[\.\!?\s])', r'\1!', text)
    
    # Fix "respectfu!" → "respectful"
    text = re.sub(r'(\w+)fu!', r'\1ful', text)
    
    # Fix spacing in compound words: "Aperson" → "A person"
    text = re.sub(r'\b([A-Z][a-z]+)([a-z]+)\b(?=[a-z])', r'\1 \2', text)
    text = text.replace('Aperson', 'A person')
    text = text.replace('Ajivatama', 'A jivatama')
    
    # Common word fixes (case-insensitive whole word matches)
    ocr_fixes = {
        'mussel': 'mouse',
        'mousel': 'mouse',
        'clothl': 'cloth',
        'youl': 'you',
        'hatl': 'hat',
        'timel': 'time',
        'shopl': 'shop',
        'kingl': 'king',
        'Heyl': 'Hey',
        'taking said': 'the king said',
        'taking was': 'the king was',
        'stated': 'started',
    }
    
    for wrong, correct in ocr_fixes.items():
        text = re.sub(r'\b' + re.escape(wrong) + r'\b', correct, text, flags=re.IGNORECASE)
    
    # ========== REMOVE OCR NOISE ==========
    
    # Remove spaced single letters (keep I, A, a)
    text = re.sub(r'\b(?![IiAa]\b)[a-zA-Z]\s+(?=[A-Z])', '', text)
    
    # Remove sequences of capital letters with spaces: "P M G Z"
    text = re.sub(r'\b[A-Z](?:\s+[A-Z]){2,}\b', '', text)
    
    # Remove number+letter mixtures
    text = re.sub(r'\b\d+\s+[A-Z](?:\s+[A-Z])*\b', '', text)
    text = re.sub(r'\b[A-Z](?:\s+\d+)+\b', '', text)
    
    # Remove lowercase sequences: "w w w"
    text = re.sub(r'\b[a-z](?:\s+[a-z]){2,}\b', '', text)
    
    # ========== FIX PUNCTUATION ==========
    
    # Replace multiple punctuation
    text = re.sub(r'\.\.+', '.', text)
    text = re.sub(r'!!+', '!', text)
    text = re.sub(r'\?\?+', '?', text)
    text = re.sub(r';;+', ';', text)
    text = re.sub(r'::+', ':', text)
    text = re.sub(r',,+', ',', text)
    
    # Fix punctuation spacing
    text = re.sub(r'\s+([,.!?;:])', r'\1', text)
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([,:;])([A-Za-z])', r'\1 \2', text)
    text = re.sub(r"\s+'", "'", text)
    
    # ========== CLEAN UP WHITESPACE ==========
    
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Final punctuation cleanup
    text = re.sub(r'\s+\.', '.', text)
    text = re.sub(r'\s+!', '!', text)
    text = re.sub(r'\s+\?', '?', text)
    
    return text


def detect_speaker_from_context(text: str) -> str:
    """
    Intelligently detect speaker type from text content for voice selection
    """
    text_lower = text.lower()
    
    # Check for specific character names/roles
    if any(word in text_lower for word in ["king", "minister", "lord", "sir", "man"]):
        if "old" in text_lower or "sage" in text_lower or "wise" in text_lower:
            return "old_male"
        return "male"
    
    if any(word in text_lower for word in ["queen", "lady", "woman", "she"]):
        return "female"
    
    if any(word in text_lower for word in ["mouse", "chu chu", "little", "small", "child"]):
        return "child"
    
    # Default to narrator for descriptive text
    if any(word in text_lower for word in ["once upon", "then", "after", "meanwhile"]):
        return "narrator"
    
    # Default to narrator
    return "narrator"


def generate_audio(narration_text: str, pdf_filename: str, use_edge_tts: bool = True) -> str:
    """
    Converts clean narration text into MP3 audio with emotion (Edge-TTS) or basic (gTTS).
    Works universally for ANY comic book.

    Args:
        narration_text: Text returned from narration_model.py
        pdf_filename: Base name of the PDF/comic
        use_edge_tts: Use Edge-TTS for emotional voice (True) or gTTS fallback (False)

    Returns:
        Relative path to the saved MP3 file (for HTML playback)
    """

    if not narration_text or not narration_text.strip():
        print("No narration text to convert.")
        return None

    # Remove any remaining labels
    labels_to_remove = [
        "Image Caption:", "OCR Text:", "Image Description:",
        "Scene:", "Text:", "Caption:", "Description:"
    ]
    
    for label in labels_to_remove:
        narration_text = narration_text.replace(label, "")

    # Collapse multiple newlines/spaces
    narration_text = " ".join(narration_text.split())
    
    # Apply universal sanitization
    print("Applying universal text sanitization...")
    narration_text = final_text_sanitization(narration_text)
    
    # Verify we have sufficient text
    if not narration_text or len(narration_text.strip()) < 10:
        print("Warning: Text too short after sanitization")
        return None
    
    # Save cleaned text for verification
    text_filename = f"{pdf_filename}_cleaned.txt"
    text_file_path = os.path.join(OUTPUT_FOLDER, text_filename)
    
    try:
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write(narration_text)
        print(f"Cleaned text saved to {text_file_path}")
    except Exception as e:
        print(f"Warning: Could not save cleaned text: {e}")

    # Generate MP3
    safe_filename = f"{pdf_filename}.mp3"
    audio_file_path = os.path.join(OUTPUT_FOLDER, safe_filename)

    try:
        print(f"Generating audio from {len(narration_text)} characters...")
        
        if use_edge_tts:
            # Use Edge-TTS for natural, emotional voice
            print("Using Edge-TTS (emotional, expressive narration)...")
            
            # Detect appropriate voice based on content
            speaker_type = detect_speaker_from_context(narration_text)
            
            # Voice mapping
            voice_map = {
                "narrator": "en-US-AriaNeural",      # Female, warm storytelling
                "male": "en-US-GuyNeural",           # Male, natural
                "female": "en-US-JennyNeural",       # Female, friendly
                "child": "en-US-AmberNeural",        # Young, cheerful
                "old_male": "en-US-RogerNeural",     # Older, authoritative
            }
            
            selected_voice = voice_map.get(speaker_type, voice_map["narrator"])
            print(f"Selected voice: {selected_voice} (type: {speaker_type})")
            
            # Generate with Edge-TTS
            async def generate_edge_audio():
                communicate = edge_tts.Communicate(
                    text=narration_text,
                    voice=selected_voice,
                    rate="+0%",  # Normal speed
                    pitch="+0Hz"  # Normal pitch
                )
                await communicate.save(audio_file_path)
            
            # Run async function
            asyncio.run(generate_edge_audio())
            
        else:
            # Fallback to gTTS
            print("Using gTTS (basic voice)...")
            tts = gTTS(text=narration_text, lang='en', slow=False)
            tts.save(audio_file_path)
        
        print(f"✓ Audio saved to {audio_file_path}")
        
        # Print statistics
        word_count = len(narration_text.split())
        duration_estimate = word_count / 150  # Average speaking rate
        print(f"Statistics: {word_count} words, ~{duration_estimate:.1f} min duration")
        
    except Exception as e:
        print(f"Failed to generate audio with primary method: {e}")
        print("Falling back to gTTS...")
        
        # Fallback to gTTS if Edge-TTS fails
        try:
            tts = gTTS(text=narration_text, lang='en', slow=False)
            tts.save(audio_file_path)
            print(f"✓ Audio saved with gTTS fallback")
        except Exception as e2:
            print(f"All TTS engines failed: {e2}")
            import traceback
            traceback.print_exc()
            return None

    # Return path relative to static folder
    return f"/static/output/{safe_filename}"


# Test the sanitization function
if __name__ == "__main__":
    # Test with various comic text patterns
    test_cases = [
        "Mouse wants to become_King www.com",
        "am feeling very thirsty:",
        "Heyl am the minister:",
        "Wow l What a nice hatl",
        "P M G Z taking was happy",
        "www iskcondesiretree com 5 am bewildered"
    ]
    
    print("Testing Universal Text Sanitization:")
    print("=" * 60)
    for test in test_cases:
        print(f"\nOriginal: {test}")
        print(f"Cleaned:  {final_text_sanitization(test)}")
