from textual.app import App, ComposeResult
from textual.widgets import Tree, Footer, Header, Label
from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container

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
