from textual.app import App, ComposeResult
from textual.widgets import Tree, Footer, Header, Label, TextArea, Button, Static
from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal
import re

class ChapterTree(Tree):
    BINDINGS = [
        Binding("space", "toggle_check", "Toggle Check"),
        Binding("right", "expand_node", "Expand"),
        Binding("left", "collapse_node", "Collapse"),
        Binding("enter", "confirm_selection", "Confirm"),
    ]

    def __init__(self, label, data=None):
        super().__init__(label, data=data)
        self.guide_depth = 2
        self.auto_expand = False

    def on_mount(self):
        self.root.expand()

    def action_toggle_check(self):
        node = self.cursor_node
        if node and node.data:
            # Toggle state
            new_state = not node.data['checked']
            self.app.set_node_checked(node, new_state)

    def action_expand_node(self):
        if self.cursor_node:
            self.cursor_node.expand()

    def action_collapse_node(self):
        if self.cursor_node:
            self.cursor_node.collapse()

    def action_confirm_selection(self):
        self.app.action_confirm()

class PDFSplitterApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    Header {
        dock: top;
    }
    Footer {
        dock: bottom;
    }
    Tree {
        padding: 1;
        border: solid green;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("enter", "confirm", "Confirm Selection"),
    ]

    def __init__(self, outline_data, pdf_title):
        super().__init__()
        self.outline_data = outline_data
        self.pdf_title = pdf_title
        self.selected_chapters = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(f"Select chapters for: {self.pdf_title}")
        yield ChapterTree("PDF Content")
        yield Footer()

    def on_mount(self):
        tree = self.query_one(ChapterTree)
        tree.focus() # Ensure tree has focus
        tree.root.expand()
        self.populate_tree(tree.root, self.outline_data)

    def populate_tree(self, node, children_data):
        for item in children_data:
            label_text = f"{item['title']} (Pages {item['start_page']}-{item['end_page']})"
            if 'checked' not in item:
                item['checked'] = True
            
            # Apply Rich styling
            if item['checked']:
                prefix = "[bold green][x] "
                styled_label = f"{prefix}{label_text}[/]"
            else:
                prefix = "[dim red][ ] "
                styled_label = f"{prefix}{label_text}[/]"
            
            child_node = node.add(styled_label, data=item)
            if item.get('children'):
                self.populate_tree(child_node, item['children'])
            else:
                child_node.allow_expand = False

    def set_node_checked(self, node, checked):
        if node.data:
            node.data['checked'] = checked
            
            label_text = f"{node.data['title']} (Pages {node.data['start_page']}-{node.data['end_page']})"
            
            if checked:
                prefix = "[bold green][x] "
                styled_label = f"{prefix}{label_text}[/]"
            else:
                prefix = "[dim red][ ] "
                styled_label = f"{prefix}{label_text}[/]"
                
            node.label = styled_label
            
        # Propagate to children
        for child in node.children:
            self.set_node_checked(child, checked)

    def action_confirm(self):
        tree = self.query_one(ChapterTree)
        self.selected_chapters = self.collect_chapters(tree.root)
        self.exit(self.selected_chapters)

    def collect_chapters(self, node):
        chapters = []
        for child in node.children:
            data = child.data
            if not data or not data['checked']:
                continue

            if not child.is_expanded:
                chapters.append({
                    'title': data['title'],
                    'start_page': data['start_page'],
                    'end_page': data['end_page']
                })
            else:
                child_chapters = self.collect_chapters(child)
                if child_chapters:
                    chapters.extend(child_chapters)
        return chapters

def run_tui(outline_data, pdf_title):
    app = PDFSplitterApp(outline_data, pdf_title)
    return app.run()


class ManualRangeApp(App):
    """TUI for manually entering page ranges to split a PDF."""

    CSS = """
    Screen {
        layout: vertical;
    }
    Header {
        dock: top;
    }
    Footer {
        dock: bottom;
    }
    #info {
        padding: 1;
        margin: 1;
        background: $surface;
    }
    #help-text {
        padding: 1;
        margin: 0 1;
        color: $text-muted;
    }
    TextArea {
        height: 15;
        margin: 1;
        border: solid green;
    }
    #buttons {
        height: 3;
        margin: 1;
        align: center middle;
    }
    Button {
        margin: 0 1;
    }
    #error {
        padding: 1;
        margin: 0 1;
        color: red;
    }
    """

    BINDINGS = [
        Binding("ctrl+s", "confirm", "Confirm"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, pdf_title: str, total_pages: int):
        super().__init__()
        self.pdf_title = pdf_title
        self.total_pages = total_pages
        self.chapters = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Manual split for: [bold]{self.pdf_title}[/] ({self.total_pages} pages)", id="info")
        yield Static(
            "Enter page ranges, one per line. Format: [bold]start-end[/] or [bold]start-end:Title[/]\n"
            "Examples:\n"
            "  1-50\n"
            "  51-100:Chapter 2\n"
            "  101-150:Results and Discussion",
            id="help-text"
        )
        yield TextArea(id="ranges-input")
        yield Static("", id="error")
        yield Horizontal(
            Button("Confirm (Ctrl+S)", id="confirm", variant="primary"),
            Button("Quit (Q)", id="quit", variant="error"),
            id="buttons"
        )
        yield Footer()

    def on_mount(self):
        self.query_one("#ranges-input", TextArea).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.action_confirm()
        elif event.button.id == "quit":
            self.exit([])

    def action_confirm(self):
        text_area = self.query_one("#ranges-input", TextArea)
        error_label = self.query_one("#error", Static)

        text = text_area.text.strip()
        if not text:
            error_label.update("[bold red]Error: Please enter at least one range[/]")
            return

        chapters, error = self.parse_ranges(text)
        if error:
            error_label.update(f"[bold red]Error: {error}[/]")
            return

        self.chapters = chapters
        self.exit(chapters)

    def parse_ranges(self, text: str):
        """Parse range input text into chapter list.

        Returns: (chapters, error_message)
        """
        chapters = []
        lines = [line.strip() for line in text.strip().split('\n') if line.strip()]

        for i, line in enumerate(lines, 1):
            # Match pattern: start-end or start-end:title
            match = re.match(r'^(\d+)\s*-\s*(\d+)(?:\s*:\s*(.+))?$', line)
            if not match:
                return None, f"Line {i}: Invalid format '{line}'. Use 'start-end' or 'start-end:title'"

            start = int(match.group(1))
            end = int(match.group(2))
            title = match.group(3) if match.group(3) else f"Part {i}"

            # Validate range
            if start < 1:
                return None, f"Line {i}: Start page must be at least 1"
            if end > self.total_pages:
                return None, f"Line {i}: End page {end} exceeds total pages ({self.total_pages})"
            if start > end:
                return None, f"Line {i}: Start page {start} cannot be greater than end page {end}"

            chapters.append({
                'title': title.strip(),
                'start_page': start,
                'end_page': end
            })

        return chapters, None


def run_manual_range_tui(pdf_title: str, total_pages: int):
    """Run the manual range input TUI."""
    app = ManualRangeApp(pdf_title, total_pages)
    return app.run()
