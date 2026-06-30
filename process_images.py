"""
Standalone script to process exam paper images from a folder.
Processes images numbered 1, 2, 3, 4 and generates DOCX output.
"""

import os
import sys
from pathlib import Path

# Add the current directory to path to import from app_exam
sys.path.insert(0, os.path.dirname(__file__))

from app_exam import (
    call_llm_json_mode,
    to_input_lines,
    parse_blocks,
    build_docx_from_blocks,
    load_template,
    build_prompt,
    OPENROUTER_API_KEY,
    MODEL_DEFAULT
)
from datetime import datetime

def process_images_from_folder(folder_path: str, output_name: str = None):
    """
    Process images 1.png, 2.png, 3.png, 4.png from the specified folder.
    
    Args:
        folder_path: Path to folder containing the images
        output_name: Optional name for output files (default: exam_paper_YYYYMMDD_HHMMSS)
    """
    folder = Path(folder_path)
    
    if not folder.exists():
        print(f"Error: Folder not found: {folder_path}")
        return
    
    # Find images numbered 1, 2, 3, 4
    image_files = []
    for num in [1, 2, 3, 4]:
        # Try different extensions
        for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
            img_path = folder / f"{num}{ext}"
            if img_path.exists():
                image_files.append(str(img_path))
                print(f"Found: {img_path.name}")
                break
        else:
            print(f"Warning: Image {num} not found (tried .png, .jpg, .jpeg)")
    
    if not image_files:
        print("Error: No images found (1, 2, 3, 4)")
        return
    
    # Sort by number to ensure correct order
    image_files.sort(key=lambda x: int(Path(x).stem))
    
    print(f"\nProcessing {len(image_files)} image(s)...")
    
    if not OPENROUTER_API_KEY:
        print("Error: OPENROUTER_API_KEY not set. Please set it in .env file or environment variable.")
        return
    
    # Load template
    template_path = os.path.join(os.path.dirname(__file__), 'oldinput.txt')
    if os.path.exists(template_path):
        template_text = load_template(template_path)
        print(f"Loaded template from: {template_path}")
    else:
        template_text = "T: Third Terminal Examination 2082\nM: Sub:Science\tFM: 50\nM: Class: 6\tTime: 1.30 hrs\tPM: 20"
        print("Using default template")
    
    # Build prompt
    prompt = build_prompt(template_text)
    
    try:
        print("\nCalling OpenRouter API (mimo-v2.5)...")
        
        # Single model call
        models_to_try = [MODEL_DEFAULT]
        items = None
        last_error = None
        
        for model in models_to_try:
            try:
                print(f"  Trying model: {model}...")
                items = call_llm_json_mode(
                    api_key=OPENROUTER_API_KEY,
                    model=model,
                    prompt=prompt,
                    image_paths=image_files,
                    temperature=0.2,
                )
                print(f"✓ Successfully extracted with {model}")
                break
            except RuntimeError as e:
                error_msg = str(e)
                last_error = e
                if "RECITATION" in error_msg or "blocked" in error_msg.lower():
                    print(f"  ⚠ {model} blocked, trying next model...")
                    if model != models_to_try[-1]:
                        continue
                    else:
                        # Last model failed, try processing images separately
                        print("\n⚠ All models blocked for batch processing. Trying to process images separately...")
                        items = []
                        for i, img_path in enumerate(image_files, 1):
                            try:
                                print(f"  Processing image {i}/{len(image_files)}: {Path(img_path).name}...")
                                img_items = call_llm_json_mode(
                                    api_key=OPENROUTER_API_KEY,
                                    model=MODEL_DEFAULT,
                                    prompt=prompt,
                                    image_paths=[img_path],
                                    temperature=0.2,
                                )
                                items.extend(img_items)
                                print(f"  ✓ Image {i} processed ({len(img_items)} items)")
                            except Exception as img_err:
                                print(f"  ⚠ Image {i} failed: {str(img_err)[:100]}")
                                # Continue with other images
                        if not items:
                            raise RuntimeError("All processing attempts failed. The content may be blocked by safety filters.")
                        print(f"✓ Extracted {len(items)} total items from {len(image_files)} images")
                        break
                else:
                    raise  # Re-raise if it's not a blocking error
        
        if items is None:
            raise last_error or RuntimeError("Failed to process images with any model")
        
        print(f"✓ Extracted {len(items)} items from images")
        
        # Convert to input lines
        print("\nProcessing extracted data...")
        text_content = to_input_lines(items)
        
        # Generate output filename
        if output_name is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_name = f"exam_paper_{timestamp}"
        
        # Save text output
        output_dir = Path(folder_path)
        text_output_path = output_dir / f"{output_name}.txt"
        with open(text_output_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        print(f"✓ Saved text output: {text_output_path}")
        
        # Generate DOCX
        print("\nGenerating DOCX document...")
        blocks = parse_blocks(text_content)
        docx_bytes = build_docx_from_blocks(blocks)
        
        docx_output_path = output_dir / f"{output_name}.docx"
        with open(docx_output_path, 'wb') as f:
            f.write(docx_bytes.getvalue())
        print(f"✓ Saved DOCX output: {docx_output_path}")
        
        print(f"\n✅ Processing complete!")
        print(f"   Text file: {text_output_path}")
        print(f"   DOCX file: {docx_output_path}")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return

if __name__ == '__main__':
    # Default folder path
    default_folder = r"C:\Users\Khage\Downloads\drive-download-20260110T040906Z-3-001"
    
    # Allow command line argument for folder path
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        folder_path = default_folder
    
    # Optional output name as second argument
    output_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("=" * 60)
    print("Exam Paper Image Processor")
    print("=" * 60)
    print(f"Folder: {folder_path}")
    print("=" * 60)
    
    process_images_from_folder(folder_path, output_name)
