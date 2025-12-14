import os
from pypdf import PdfReader, PdfWriter

def split_pdf(pdf_path, chapter_starts):
    """
    Splits a PDF into chapters based on start pages.
    
    Args:
        pdf_path (str): Path to the source PDF.
        chapter_starts (list): List of start page numbers (1-based).
    """
    # Ensure chapter starts are sorted
    chapter_starts = sorted(chapter_starts)
    
    # Create output directory
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(os.path.dirname(pdf_path), pdf_name)
    os.makedirs(output_dir, exist_ok=True)
    
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    print(f"Processing {pdf_path} ({total_pages} pages)...")
    
    for i, start_page in enumerate(chapter_starts):
        # Determine end page
        if i < len(chapter_starts) - 1:
            end_page = chapter_starts[i+1] - 1
        else:
            end_page = total_pages
            
        # Convert to 0-based index
        start_idx = start_page - 1
        end_idx = end_page
        
        # Validate range
        if start_idx >= total_pages:
            print(f"Warning: Chapter start {start_page} is beyond total pages {total_pages}. Skipping.")
            continue
            
        writer = PdfWriter()
        
        page_count = 0
        for p in range(start_idx, min(end_idx, total_pages)):
            writer.add_page(reader.pages[p])
            page_count += 1
            
        output_filename = f"chapter{i+1}.pdf"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, "wb") as f:
            writer.write(f)
            
        print(f"Created {output_filename}: Pages {start_page}-{end_page if end_page <= total_pages else total_pages} ({page_count} pages)")

def extract_chapters(pdf_path, chapters):
    """
    Extracts specific chapters from a PDF.
    
    Args:
        pdf_path (str): Path to the source PDF.
        chapters (list): List of dicts with 'title', 'start_page', 'end_page'.
                         Pages are 1-based.
    """
    # Create output directory
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(os.path.dirname(pdf_path), pdf_name)
    os.makedirs(output_dir, exist_ok=True)
    
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    
    print(f"Processing {pdf_path} ({total_pages} pages)...")
    
    for i, chapter in enumerate(chapters):
        title = chapter['title']
        start_page = chapter['start_page']
        end_page = chapter['end_page']
        
        # Sanitize title for filename
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
        if not safe_title:
            safe_title = f"chapter_{i+1}"
            
        # Convert to 0-based index
        start_idx = start_page - 1
        end_idx = end_page 
        
        # Validate range
        if start_idx >= total_pages:
            print(f"Warning: Chapter '{title}' start {start_page} is beyond total pages {total_pages}. Skipping.")
            continue
            
        writer = PdfWriter()
        
        page_count = 0
        # Ensure we don't go past the end of the PDF
        actual_end_idx = min(end_idx, total_pages)
        
        for p in range(start_idx, actual_end_idx):
            writer.add_page(reader.pages[p])
            page_count += 1
            
        output_filename = f"{safe_title}.pdf"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, "wb") as f:
            writer.write(f)
            
        print(f"Created {output_filename}: Pages {start_page}-{end_page} ({page_count} pages)")

def get_nested_outline(outline, reader):
    """
    Recursively traverses the outline and returns a nested list of chapters.
    Returns list of dicts: {'title': str, 'start_page': int, 'children': []}
    """
    chapters = []
    for item in outline:
        if isinstance(item, list):
            # This is a list of sub-chapters for the *previous* item.
            if chapters:
                chapters[-1]['children'] = get_nested_outline(item, reader)
        else:
            try:
                page_num = reader.get_destination_page_number(item)
                chapters.append({
                    'title': item.title,
                    'start_page': page_num + 1,
                    'children': []
                })
            except Exception:
                pass
    return chapters

def calculate_end_pages(chapters, total_pages, next_start=None):
    """
    Recursively calculates end pages for chapters.
    """
    for i, chapter in enumerate(chapters):
        start = chapter['start_page']
        
        # Determine the effective end for this block.
        current_next_start = next_start
        
        if i < len(chapters) - 1:
            current_next_start = chapters[i+1]['start_page']
            
        if current_next_start:
            if current_next_start > start:
                end = current_next_start - 1
            else:
                end = start 
        else:
            end = total_pages
            
        chapter['end_page'] = end
        
        # Recurse for children
        if chapter['children']:
            calculate_end_pages(chapter['children'], end, next_start=current_next_start)
