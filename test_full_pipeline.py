import os
from narration_model import extract_images_from_pdf, generate_combined_caption
from audio_generator import generate_audio


def find_test_pdf():
    """Find a test PDF file."""
    possible_paths = [
        "king.pdf",                           
        "../king.pdf",                        
        "static/uploads/test.pdf",            
        "static/uploads/king.pdf",
        r"D:\my\Vision to voice UX\king.pdf",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    uploads_dir = "static/uploads"
    if os.path.exists(uploads_dir):
        pdf_files = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf')]
        if pdf_files:
            return os.path.join(uploads_dir, pdf_files[0])
    
    return None


def test_full_pipeline(pdf_path):
    """Test complete PDF to Audio pipeline."""
    
    print("\n" + "="*80)
    print("TESTING COMPLETE PDF TO AUDIO PIPELINE")
    print("="*80 + "\n")
    
    if not os.path.exists(pdf_path):
        print(f"✗ ERROR: PDF not found at {pdf_path}")
        return False
    
    print(f"✓ PDF found: {pdf_path}")
    print(f"  Size: {os.path.getsize(pdf_path)/1024:.1f} KB\n")
    
    # Step 1: Extract images
    print("STEP 1: Extracting images...")
    print("-" * 80)
    images = extract_images_from_pdf(pdf_path, dpi=400)
    
    if len(images) == 0:
        print("✗ FAILED: No images extracted")
        return False
    
    print(f"✓ Extracted {len(images)} page(s)\n")
    
    # Step 2: Generate narration
    print("STEP 2: Generating narration...")
    print("-" * 80)
    narration_text = generate_combined_caption(
        images, 
        blip_fallback=False, 
        debug=True,
        aggressive_cleaning=False  # IMPORTANT: Set to False
    )
    
    print(f"\n✓ Narration statistics:")
    print(f"   Characters: {len(narration_text)}")
    print(f"   Words: {len(narration_text.split())}")
    
    if len(narration_text) > 500:
        print(f"   Preview: {narration_text[:500]}...")
    else:
        print(f"   Full text: {narration_text}")
    
    if len(narration_text) < 10:
        print("\n✗ FAILED: Text too short")
        return False
    
    # Save narration
    os.makedirs("test_output", exist_ok=True)
    text_path = "test_output/narration.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(narration_text)
    print(f"\n✓ Text saved to {text_path}\n")
    
    # Step 3: Generate audio
    print("STEP 3: Generating audio...")
    print("-" * 80)
    
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
    audio_path = generate_audio(narration_text, f"test_{pdf_basename}")
    
    if audio_path and os.path.exists(audio_path):
        file_size = os.path.getsize(audio_path)
        print(f"\n✓ Audio created successfully!")
        print(f"   Path: {audio_path}")
        print(f"   Size: {file_size/1024:.1f} KB")
        
        print("\n" + "="*80)
        print("✓✓✓ PIPELINE TEST SUCCESSFUL ✓✓✓")
        print("="*80 + "\n")
        
        print("Generated files:")
        print(f"  1. Text: {text_path}")
        print(f"  2. Audio: {audio_path}")
        print()
        
        return True
    else:
        print("\n✗ FAILED: Audio not created")
        return False


if __name__ == "__main__":
    print("\nSearching for PDF...")
    pdf_file = find_test_pdf()
    
    if not pdf_file:
        print("\n✗ ERROR: No PDF found!")
        print("\nPlace a PDF in one of these locations:")
        print("  - Code/king.pdf")
        print("  - Code/static/uploads/test.pdf")
        exit(1)
    
    print(f"✓ Using: {pdf_file}\n")
    
    success = test_full_pipeline(pdf_file)
    
    if success:
        print("="*80)
        print("✓ You can now integrate with Flask!")
        print("="*80)
    else:
        print("="*80)
        print("✗ Test failed - check errors above")
        print("="*80)
