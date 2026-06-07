"""Lightweight markdown → HTML/DOCX for LLM-generated report narratives."""
from __future__ import annotations

import html
import re
from typing import Any

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")
_NUMBERED_LINE_RE = re.compile(r"^\d+\.\s*(?:→|->)\s*(.*)$")
_NUMBERED_PLAIN_RE = re.compile(r"^\d+\.\s*(.*)$")
_ARROW_LINE_RE = re.compile(r"^(?:→|->)\s*(.*)$")


def _inline_markdown_html(escaped: str) -> str:
    text = _BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    return _ITALIC_RE.sub(r"<em>\1</em>", text)


def _split_blocks(text: str) -> list[str]:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    return [block.strip() for block in re.split(r"\n\n+", normalized) if block.strip()]


def _numbered_match(line: str) -> re.Match[str] | None:
    stripped = line.strip()
    return _NUMBERED_LINE_RE.match(stripped) or _NUMBERED_PLAIN_RE.match(stripped)


def _format_block_html(block: str) -> str:
    lines = block.split("\n")
    parts: list[str] = []
    prose_buffer: list[str] = []
    i = 0

    def flush_prose() -> None:
        nonlocal prose_buffer
        if not prose_buffer:
            return
        inner = "<br/>".join(_inline_markdown_html(html.escape(ln)) for ln in prose_buffer)
        parts.append(f'<p class="report-prose">{inner}</p>')
        prose_buffer = []

    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue

        numbered = _numbered_match(stripped)
        if numbered:
            flush_prose()
            items: list[str] = []
            while i < len(lines):
                cur = lines[i].strip()
                if not cur:
                    i += 1
                    continue
                match = _numbered_match(cur)
                if not match:
                    break
                items.append(f"<li>{_inline_markdown_html(html.escape(match.group(1)))}</li>")
                i += 1
            parts.append(f'<ol class="report-list report-list--numbered">{"".join(items)}</ol>')
            continue

        if _ARROW_LINE_RE.match(stripped):
            flush_prose()
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                if not cur:
                    i += 1
                    continue
                match = _ARROW_LINE_RE.match(cur)
                if not match:
                    break
                items.append(f"<li>{_inline_markdown_html(html.escape(match.group(1)))}</li>")
                i += 1
            parts.append(f'<ul class="report-list">{"".join(items)}</ul>')
            continue

        prose_buffer.append(stripped)
        i += 1

    flush_prose()
    return "\n".join(parts)


def format_report_text_html(text: str) -> str:
    """Convert LLM markdown-ish prose to styled HTML (safe: escaped before inline markup)."""
    blocks = _split_blocks(text)
    if not blocks:
        return ""
    return "\n".join(_format_block_html(block) for block in blocks)


def _strip_markdown(text: str) -> str:
    text = _BOLD_RE.sub(r"\1", text)
    return _ITALIC_RE.sub(r"\1", text)


def _add_markdown_runs(paragraph: Any, text: str, *, bold_all: bool = False) -> None:
    if bold_all:
        run = paragraph.add_run(_strip_markdown(text))
        run.bold = True
        return

    pos = 0
    for match in _BOLD_RE.finditer(text):
        if match.start() > pos:
            paragraph.add_run(text[pos:match.start()])
        run = paragraph.add_run(match.group(1))
        run.bold = True
        pos = match.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def _format_block_docx(doc: Any, block: str) -> None:
    lines = block.split("\n")
    prose_buffer: list[str] = []
    i = 0

    def flush_prose() -> None:
        nonlocal prose_buffer
        if not prose_buffer:
            return
        paragraph = doc.add_paragraph()
        for idx, ln in enumerate(prose_buffer):
            if idx > 0:
                paragraph.add_run("\n")
            _add_markdown_runs(paragraph, ln)
        prose_buffer = []

    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue

        numbered = _numbered_match(stripped)
        if numbered:
            flush_prose()
            while i < len(lines):
                cur = lines[i].strip()
                if not cur:
                    i += 1
                    continue
                match = _numbered_match(cur)
                if not match:
                    break
                paragraph = doc.add_paragraph(style="List Number")
                _add_markdown_runs(paragraph, match.group(1))
                i += 1
            continue

        if _ARROW_LINE_RE.match(stripped):
            flush_prose()
            while i < len(lines):
                cur = lines[i].strip()
                if not cur:
                    i += 1
                    continue
                match = _ARROW_LINE_RE.match(cur)
                if not match:
                    break
                paragraph = doc.add_paragraph(style="List Bullet")
                _add_markdown_runs(paragraph, match.group(1))
                i += 1
            continue

        prose_buffer.append(stripped)
        i += 1

    flush_prose()


def append_report_text_docx(doc: Any, text: str) -> None:
    """Append formatted narrative blocks to a python-docx Document."""
    for block in _split_blocks(text):
        _format_block_docx(doc, block)


def format_report_line_html(text: str) -> str:
    if not (text or "").strip():
        return ""
    return _inline_markdown_html(html.escape(str(text)))
