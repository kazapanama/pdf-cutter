"""
Неінтерактивний режим PDF Cutter — для скриптів і курсів за книгою (скіл book-course).

    python main.py --toc book.pdf [--depth N]
        Зміст у JSON: номер розділу, назва, сторінки PDF і друковані номери сторінок.

    python main.py --extract SPEC book.pdf [--out DIR] [--text]
        Вирізає частину книги в окремий PDF.
        SPEC — номер розділу з назви («2», «2.5»), діапазон розділів одного рівня
        («2.1-2.4») або сторінки PDF («pdf:60-78»).
        --text — поруч зберегти текст із позначками друкованих сторінок (=== стор. 21 ===).
"""

import json
import os
import re
import sys

from pypdf import PdfReader, PdfWriter

from pdf_processor import calculate_end_pages, get_nested_outline

NUM = re.compile(r"^\s*(\d+(?:\.\d+)*)\b")


def _label(reader, idx):
    """Друкований номер сторінки (page label) для 0-базового індексу; якщо міток немає — номер PDF."""
    try:
        return reader.page_labels[idx]
    except Exception:
        return str(idx + 1)


def build_toc(reader, depth=None):
    total = len(reader.pages)
    if not reader.outline:
        return []
    tree = get_nested_outline(reader.outline, reader)
    calculate_end_pages(tree, total)

    def walk(nodes, level):
        out = []
        for n in nodes:
            m = NUM.match(n["title"])
            item = {
                "num": m.group(1) if m else None,
                "title": n["title"].strip(),
                "pdf_start": n["start_page"],
                "pdf_end": n["end_page"],
                "page_start": _label(reader, n["start_page"] - 1),
                "page_end": _label(reader, n["end_page"] - 1),
                "pages": n["end_page"] - n["start_page"] + 1,
            }
            if n["children"] and (depth is None or level < depth):
                item["children"] = walk(n["children"], level + 1)
            out.append(item)
        return out

    return walk(tree, 1)


def _flat(toc):
    for n in toc:
        yield n
        yield from _flat(n.get("children", []))


def resolve(toc, spec):
    """SPEC → (pdf_start, pdf_end, назва для файлу)."""
    m = re.match(r"^pdf:(\d+)-(\d+)$", spec)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return a, b, f"pages-{a}-{b}"
    by_num = {n["num"]: n for n in _flat(toc) if n["num"]}
    if "-" in spec:
        a, b = spec.split("-", 1)
        if a not in by_num or b not in by_num:
            raise SystemExit(f"Розділ не знайдено у змісті: {a if a not in by_num else b}")
        if a.count(".") != b.count("."):
            raise SystemExit("Діапазон має бути з розділів одного рівня, напр. 2.1-2.4")
        return by_num[a]["pdf_start"], by_num[b]["pdf_end"], f"{a}-{b}"
    if spec not in by_num:
        raise SystemExit(f"Розділ «{spec}» не знайдено у змісті. Подивись номери: --toc")
    n = by_num[spec]
    slug = re.sub(r"[^\w\s-]", "", n["title"]).strip().replace(" ", "-")
    return n["pdf_start"], n["pdf_end"], slug or spec


def extract(reader, start, end, out_pdf, text_path=None):
    writer = PdfWriter()
    for p in range(start - 1, end):
        writer.add_page(reader.pages[p])
    with open(out_pdf, "wb") as f:
        writer.write(f)
    if text_path:
        with open(text_path, "w", encoding="utf-8") as f:
            for p in range(start - 1, end):
                f.write(f"\n=== стор. {_label(reader, p)} (PDF {p + 1}) ===\n")
                f.write(reader.pages[p].extract_text() or "")
                f.write("\n")


def run(argv):
    args = list(argv)

    def opt(name, has_value=True):
        if name not in args:
            return None
        i = args.index(name)
        val = args[i + 1] if has_value and i + 1 < len(args) else True
        del args[i:i + (2 if has_value else 1)]
        return val

    toc_mode = opt("--toc", has_value=False)
    spec = opt("--extract")
    depth = opt("--depth")
    out_dir = opt("--out")
    want_text = opt("--text", has_value=False)
    if not args:
        raise SystemExit("Вкажи шлях до PDF.")
    pdf_path = args[0]
    reader = PdfReader(pdf_path)
    toc = build_toc(reader, int(depth) if depth else None)

    if toc_mode:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps({"file": os.path.basename(pdf_path), "pdf_pages": len(reader.pages), "toc": toc},
                         ensure_ascii=False, indent=1))
        return

    start, end, name = resolve(build_toc(reader), spec)
    if not out_dir:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(pdf_path)), os.path.splitext(os.path.basename(pdf_path))[0])
    os.makedirs(out_dir, exist_ok=True)
    out_pdf = os.path.join(out_dir, name + ".pdf")
    text_path = os.path.join(out_dir, name + ".txt") if want_text else None
    extract(reader, start, end, out_pdf, text_path)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"pdf": out_pdf, "text": text_path, "pdf_start": start, "pdf_end": end,
                      "page_start": _label(reader, start - 1), "page_end": _label(reader, end - 1)},
                     ensure_ascii=False))


def wanted(argv):
    return "--toc" in argv or "--extract" in argv
