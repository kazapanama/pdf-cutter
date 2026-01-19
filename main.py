import os
import sys
from pypdf import PdfReader
from terminal_ui import run_tui, run_manual_range_tui
from pdf_processor import extract_chapters, get_nested_outline, calculate_end_pages


def main():
    # Parse arguments
    manual_mode = '--manual' in sys.argv or '-m' in sys.argv
    args = [arg for arg in sys.argv[1:] if arg not in ('--manual', '-m')]

    if len(args) < 1:
        print("Usage: python main.py [--manual] <book.pdf>")
        print("  --manual, -m  Force manual range input mode")
        sys.exit(1)

    pdf_path = args[0]

    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' not found.")
        sys.exit(1)

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        pdf_name = os.path.basename(pdf_path)

        # Use manual mode if forced or if no outline exists
        use_manual = manual_mode

        if not manual_mode:
            if not reader.outline:
                print("No outline found in this PDF. Switching to manual mode.")
                use_manual = True
            else:
                nested_chapters = get_nested_outline(reader.outline, reader)
                if not nested_chapters:
                    print("No valid chapters found in outline. Switching to manual mode.")
                    use_manual = True

        if use_manual:
            # Run manual range TUI
            selected_chapters = run_manual_range_tui(pdf_name, total_pages)
        else:
            # Calculate end pages and run outline-based TUI
            calculate_end_pages(nested_chapters, total_pages)
            selected_chapters = run_tui(nested_chapters, pdf_name)

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
