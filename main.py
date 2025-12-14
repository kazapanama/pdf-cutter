import os
import sys
from pypdf import PdfReader
from terminal_ui import run_tui
from pdf_processor import extract_chapters, get_nested_outline, calculate_end_pages

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <book.pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' not found.")
        sys.exit(1)

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        if not reader.outline:
            print("No outline found in this PDF.")
            sys.exit(1)
            
        # Get nested chapters
        nested_chapters = get_nested_outline(reader.outline, reader)
        
        if not nested_chapters:
            print("No valid chapters found in outline.")
            sys.exit(1)
            
        # Calculate end pages
        calculate_end_pages(nested_chapters, total_pages)
        
        # Run TUI
        selected_chapters = run_tui(nested_chapters, os.path.basename(pdf_path))
        
        if not selected_chapters:
            print("No chapters selected.")
            sys.exit(0)
            
        print(f"\nExtracting {len(selected_chapters)} chapters...")
        extract_chapters(pdf_path, selected_chapters)
            
    except Exception as e:
        print(f"Error reading PDF: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
