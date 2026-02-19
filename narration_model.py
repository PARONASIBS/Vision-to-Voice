import os
import numpy as np
from PIL import Image
import fitz  # PyMuPDF
import re
import torch
from transformers import (
    BlipProcessor, BlipForConditionalGeneration,
    TrOCRProcessor, VisionEncoderDecoderModel
)


# Global model instance (initialized once)
_narration_model_instance = None


def get_narration_model():
    """Get or create the global narration model instance"""
    global _narration_model_instance
    if _narration_model_instance is None:
        _narration_model_instance = NarrationModel()
    return _narration_model_instance


class NarrationModel:
    def __init__(self):
        """Initialize BLIP for captioning and TrOCR/EasyOCR for text extraction"""
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
        
        # Initialize BLIP for image captioning
        print("Loading BLIP model for captioning...")
        self.blip_processor = BlipProcessor.from_pretrained(
            "Salesforce/blip-image-captioning-base",
            use_fast=True
        )
        self.blip_model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-base",
            use_safetensors=True
        ).to(self.device)
        self.blip_model.eval()
        
        # Initialize TrOCR for text extraction (primary)
        print("Loading TrOCR model for text extraction...")
        self.trocr_processor = TrOCRProcessor.from_pretrained('microsoft/trocr-base-printed')
        self.trocr_model = VisionEncoderDecoderModel.from_pretrained(
            'microsoft/trocr-base-printed',
            use_safetensors=True
        ).to(self.device)
        self.trocr_model.eval()
        
        # Initialize EasyOCR (fallback)
        print("Loading EasyOCR model...")
        try:
            import easyocr
            self.easy_ocr = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
            print("✓ EasyOCR loaded successfully")
        except Exception as e:
            print(f"✗ EasyOCR initialization failed: {e}")
            self.easy_ocr = None
    
    def generate_blip_caption(self, image):
        """Generate image caption using BLIP"""
        try:
            inputs = self.blip_processor(images=image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                out = self.blip_model.generate(**inputs, max_length=50)
            
            caption = self.blip_processor.decode(out[0], skip_special_tokens=True)
            return caption.strip()
        except Exception as e:
            print(f"BLIP caption generation failed: {e}")
            return ""
    
    def extract_text_trocr(self, image):
        """Extract text using TrOCR"""
        try:
            pixel_values = self.trocr_processor(
                images=image, 
                return_tensors="pt"
            ).pixel_values.to(self.device)
            
            with torch.no_grad():
                generated_ids = self.trocr_model.generate(pixel_values, max_length=512)
            
            text = self.trocr_processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            return text.strip()
        except Exception as e:
            print(f"TrOCR extraction failed: {e}")
            return None
    
    def extract_text_easyocr(self, image):
        """Extract text using EasyOCR"""
        if self.easy_ocr is None:
            print("    ✗ EasyOCR not available")
            return ""
        
        try:
            # Convert PIL image to numpy array
            img_array = np.array(image)
            
            # Resize if too large
            max_dimension = 1500
            height, width = img_array.shape[:2]
            
            if height > max_dimension or width > max_dimension:
                scale = max_dimension / max(height, width)
                new_height = int(height * scale)
                new_width = int(width * scale)
                
                img_pil = Image.fromarray(img_array)
                img_pil = img_pil.resize((new_width, new_height), Image.LANCZOS)
                img_array = np.array(img_pil)
            
            # Run EasyOCR
            result = self.easy_ocr.readtext(img_array, detail=1, paragraph=False)
            
            # Extract text with confidence threshold
            text_lines = []
            for (bbox, text, confidence) in result:
                if confidence > 0.25:  # Low threshold for comic text
                    text_lines.append(text)
            
            if text_lines:
                extracted_text = ' '.join(text_lines)
                print(f"    ✓ EasyOCR: {len(text_lines)} regions, {len(extracted_text)} chars")
                return extracted_text
            
            return ""
            
        except Exception as e:
            print(f"    ✗ EasyOCR error: {str(e)[:50]}")
            return ""
    
    def clean_text(self, text):
        """Clean extracted text"""
        if not text:
            return ""
        
        # Remove timestamps
        text = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text)
        
        # Remove URLs and website watermarks (aggressive)
        text = re.sub(r'http[s]?://\S+', '', text)
        text = re.sub(r'www\.[\w\.]+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\.com\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bcom\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bWWW\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bwww\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bw\s+w\s+w\b', '', text, flags=re.IGNORECASE)
        
        # Fix common OCR errors
        text = re.sub(r'Wowl\b', 'Wow!', text)
        text = re.sub(r'mousel\b', 'mouse!', text)
        text = re.sub(r'mussel\b', 'mouse!', text)
        text = re.sub(r'youl\b', 'you!', text)
        text = re.sub(r'hatl\b', 'hat!', text)
        text = re.sub(r'tall\b', 'hat!', text)  # Common OCR error
        text = re.sub(r'timel\b', 'time!', text)
        text = re.sub(r'shopl\b', 'shop!', text)
        text = re.sub(r'\bdull\b', 'hat', text)
        text = re.sub(r'Mel\b', 'me!', text)
        text = re.sub(r'chui\b', '', text)  # Remove OCR noise
        
        # Remove visual description artifacts
        text = re.sub(r'underscore', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\d+\.\d+', '', text)  # Remove numbers like "6.00"
        
        # Remove unwanted labels
        unwanted_patterns = [
            r'\[Music\]', r'\[Applause\]', r'\[Laughter\]',
            r'WEBVTT', r'Kind:', r'Language:'
        ]
        for pattern in unwanted_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.,!?;:\'\"-]', '', text)
        
        return text.strip()
    
    def process_single_image(self, image):
        """Process a single PIL Image and return combined caption + OCR text"""
        try:
            # Generate BLIP caption (for context, but prioritize OCR text)
            print(f"  → BLIP caption...")
            caption = self.generate_blip_caption(image)
            
            # Try TrOCR first
            print(f"  → TrOCR...")
            ocr_text = self.extract_text_trocr(image)
            
            # If TrOCR insufficient, use EasyOCR
            if not ocr_text or len(ocr_text.strip()) < 5:
                print(f"  → EasyOCR fallback...")
                ocr_text = self.extract_text_easyocr(image)
            else:
                print(f"    ✓ TrOCR: {len(ocr_text)} chars")
            
            # Clean the OCR text
            ocr_text = self.clean_text(ocr_text)
            
            # Prioritize OCR text for audio (captions are visual descriptions)
            if ocr_text:
                combined = ocr_text
            elif caption:
                # Only use caption if no text was extracted
                combined = caption
            else:
                combined = ""
            
            return combined
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return ""


# -------- FUNCTION WRAPPERS -------- #

def extract_images_from_pdf(pdf_path, dpi=400):
    """Extract images from PDF pages"""
    output_folder = "static/output"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    doc = fitz.open(pdf_path)
    images = []
    
    zoom = dpi / 72.0
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    
    doc.close()
    return images


def generate_combined_caption(images, blip_fallback=True):
    """Generate combined caption + OCR text for all images"""
    model = get_narration_model()
    
    all_narrations = []
    for i, img in enumerate(images):
        print(f"\n[Page {i+1}/{len(images)}]")
        narration = model.process_single_image(img)
        
        if narration:
            all_narrations.append(narration)
            print(f"  ✓ Result: {narration[:80]}...")
    
    full_narration = ' '.join(all_narrations)
    return full_narration


if __name__ == "__main__":
    print("NarrationModel module loaded successfully!")
