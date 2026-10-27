"""Bangun Laporan_Kelompok_4.docx dari Laporan_Kelompok_4.md.

Skrip ini hanya memakai Python standard library (re, zipfile, struct, pathlib,
xml.sax.saxutils). Tidak ada pustaka dokumen pihak ketiga. Format DOCX dibuat
langsung sebagai paket OOXML minimal yang valid.
"""

from __future__ import annotations

import re
import struct
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "Laporan_Kelompok_4.md"
OUT_PATH = ROOT / "Laporan_Kelompok_4.docx"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"

ORANGE = "FF5E24"
INK = "232629"
SLATE = "5C6066"
EMBER = "6C3200"
BLUE = "1D5D8C"
HEADER_FILL = "E3F1FE"
CODE_FILL = "F5F8FB"
BORDER = "D3E6F9"
MAX_IMAGE_WIDTH_EMU = int(6.15 * 914400)
MAX_IMAGE_HEIGHT_EMU = int(7.55 * 914400)


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------


def esc(text: str) -> str:
    return escape(text, {"\"": "&quot;"})


def run_xml(
    text: str,
    *,
    bold: bool = False,
    italic: bool = False,
    code: bool = False,
    size: int | None = None,
    color: str | None = None,
    font: str | None = None,
) -> str:
    props = []
    if font:
        props.append(
            f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:eastAsia="{font}"/>'
        )
    if bold:
        props.append("<w:b/>")
    if italic:
        props.append("<w:i/>")
    if color:
        props.append(f'<w:color w:val="{color}"/>')
    if size:
        props.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    if code:
        props.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{CODE_FILL}"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return (
        f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'
    )


INLINE_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")


def inline_runs(
    text: str,
    *,
    base_bold: bool = False,
    size: int | None = None,
    color: str | None = None,
) -> str:
    """Ubah **bold** dan `kode` menjadi run Word."""
    out = []
    position = 0
    for match in INLINE_RE.finditer(text):
        if match.start() > position:
            out.append(
                run_xml(text[position:match.start()], bold=base_bold, size=size, color=color)
            )
        token = match.group(0)
        if token.startswith("**"):
            out.append(
                run_xml(
                    token[2:-2],
                    bold=True,
                    size=size,
                    color=color,
                )
            )
        else:
            out.append(
                run_xml(
                    token[1:-1],
                    bold=base_bold,
                    code=True,
                    font="Consolas",
                    size=(size or 21) - 2,
                    color=EMBER if not color else color,
                )
            )
        position = match.end()
    if position < len(text):
        out.append(run_xml(text[position:], bold=base_bold, size=size, color=color))
    return "".join(out)


def paragraph_xml(
    text: str = "",
    *,
    style: str = "Normal",
    align: str | None = None,
    keep_next: bool = False,
    page_break_before: bool = False,
    indent_left: int | None = None,
    hanging: int | None = None,
    space_before: int | None = None,
    space_after: int | None = None,
    runs: str | None = None,
) -> str:
    props = [f'<w:pStyle w:val="{style}"/>']
    if align:
        props.append(f'<w:jc w:val="{align}"/>')
    if keep_next:
        props.append("<w:keepNext/>")
    if page_break_before:
        props.append("<w:pageBreakBefore/>")
    if indent_left is not None:
        hanging_attr = f' w:hanging="{hanging}"' if hanging is not None else ""
        props.append(f'<w:ind w:left="{indent_left}"{hanging_attr}/>')
    if space_before is not None or space_after is not None:
        before = space_before if space_before is not None else 0
        after = space_after if space_after is not None else 0
        props.append(f'<w:spacing w:before="{before}" w:after="{after}"/>')
    body = runs if runs is not None else inline_runs(text)
    return f"<w:p><w:pPr>{''.join(props)}</w:pPr>{body}</w:p>"


def heading_xml(level: int, text: str) -> str:
    style = f"Heading{level}"
    return paragraph_xml(text, style=style, keep_next=True)


def page_break_xml() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def code_block_xml(lines: list[str]) -> str:
    out = []
    for line in lines:
        out.append(
            "<w:p><w:pPr><w:pStyle w:val=\"Code\"/>"
            "<w:shd w:val=\"clear\" w:color=\"auto\" w:fill=\"F5F8FB\"/>"
            "<w:spacing w:before=\"0\" w:after=\"0\" w:line=\"240\" w:lineRule=\"auto\"/>"
            "</w:pPr>"
            + run_xml(line if line else " ", code=True, font="Consolas", size=17, color=INK)
            + "</w:p>"
        )
    return "".join(out)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        raise ValueError(f"Bukan PNG yang valid: {path}")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def image_xml(
    rel_id: str,
    doc_pr_id: int,
    width_emu: int,
    height_emu: int,
    name: str,
) -> str:
    return (
        "<w:p><w:pPr><w:jc w:val=\"center\"/>"
        "<w:spacing w:before=\"120\" w:after=\"60\"/></w:pPr>"
        "<w:r><w:drawing>"
        f"<wp:inline xmlns:wp=\"{WP_NS}\" distT=\"0\" distB=\"0\" distL=\"0\" distR=\"0\">"
        f"<wp:extent cx=\"{width_emu}\" cy=\"{height_emu}\"/>"
        "<wp:effectExtent l=\"0\" t=\"0\" r=\"0\" b=\"0\"/>"
        f"<wp:docPr id=\"{doc_pr_id}\" name=\"Picture {doc_pr_id}\"/>"
        "<wp:cNvGraphicFramePr><a:graphicFrameLocks "
        f"xmlns:a=\"{A_NS}\" noChangeAspect=\"1\"/></wp:cNvGraphicFramePr>"
        f"<a:graphic xmlns:a=\"{A_NS}\">"
        f"<a:graphicData uri=\"http://schemas.openxmlformats.org/drawingml/2006/picture\">"
        f"<pic:pic xmlns:pic=\"{PIC_NS}\">"
        "<pic:nvPicPr>"
        f"<pic:cNvPr id=\"{doc_pr_id}\" name=\"{esc(name)}\"/>"
        "<pic:cNvPicPr/>"
        "</pic:nvPicPr>"
        "<pic:blipFill>"
        f"<a:blip r:embed=\"{rel_id}\"/>"
        "<a:stretch><a:fillRect/></a:stretch>"
        "</pic:blipFill>"
        "<pic:spPr>"
        "<a:xfrm><a:off x=\"0\" y=\"0\"/>"
        f"<a:ext cx=\"{width_emu}\" cy=\"{height_emu}\"/>"
        "</a:xfrm>"
        "<a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom>"
        "</pic:spPr>"
        "</pic:pic></a:graphicData></a:graphic>"
        "</wp:inline></w:drawing></w:r></w:p>"
    )


def table_xml(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    columns = max(len(r) for r in rows)
    total_width = 9360
    col_width = total_width // columns
    grid = "".join(f'<w:gridCol w:w="{col_width}"/>' for _ in range(columns))

    body = []
    for row_index, row in enumerate(rows):
        cells = []
        for col_index in range(columns):
            text = row[col_index] if col_index < len(row) else ""
            shaded = (
                f'<w:shd w:val="clear" w:color="auto" w:fill="{HEADER_FILL}"/>'
                if row_index == 0
                else ""
            )
            cell_props = (
                f'<w:tcPr><w:tcW w:w="{col_width}" w:type="dxa"/>{shaded}'
                "<w:vAlign w:val=\"center\"/></w:tcPr>"
            )
            cell_paragraph = (
                "<w:p><w:pPr><w:pStyle w:val=\"TableText\"/>"
                "<w:spacing w:before=\"0\" w:after=\"0\" w:line=\"240\" w:lineRule=\"auto\"/>"
                "</w:pPr>"
                + inline_runs(text, base_bold=(row_index == 0), size=17)
                + "</w:p>"
            )
            cells.append(f"<w:tc>{cell_props}{cell_paragraph}</w:tc>")
        header = "<w:trPr><w:tblHeader/></w:trPr>" if row_index == 0 else ""
        body.append(f"<w:tr>{header}{''.join(cells)}</w:tr>")

    borders = "".join(
        f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="{BORDER}"/>'
        for side in ("top", "left", "bottom", "right", "insideH", "insideV")
    )
    return (
        "<w:tbl><w:tblPr>"
        f'<w:tblW w:w="{total_width}" w:type="dxa"/>'
        "<w:tblBorders>" + borders + "</w:tblBorders>"
        "<w:tblCellMar>"
        "<w:top w:w=\"70\" w:type=\"dxa\"/><w:left w:w=\"90\" w:type=\"dxa\"/>"
        "<w:bottom w:w=\"70\" w:type=\"dxa\"/><w:right w:w=\"90\" w:type=\"dxa\"/>"
        "</w:tblCellMar>"
        "</w:tblPr>"
        f"<w:tblGrid>{grid}</w:tblGrid>"
        + "".join(body)
        + "</w:tbl>"
        + '<w:p><w:pPr><w:spacing w:before="0" w:after="80"/></w:pPr></w:p>'
    )


# ---------------------------------------------------------------------------
# Markdown parser
# ---------------------------------------------------------------------------


def split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def is_table_separator(line: str) -> bool:
    stripped = line.strip().strip("|")
    return bool(stripped) and all(
        re.fullmatch(r":?-{2,}:?", cell.strip()) for cell in stripped.split("|")
    )


class ReportBuilder:
    def __init__(self, markdown: str) -> None:
        self.markdown = markdown
        self.images: list[dict[str, object]] = []
        self.image_counter = 0
        self.docpr_counter = 1

    # -- image registration ------------------------------------------------

    def register_image(self, path_text: str, caption: str) -> str:
        path = (ROOT / path_text).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Gambar tidak ditemukan: {path}")
        self.image_counter += 1
        rel_id = f"rIdImg{self.image_counter}"
        width, height = png_size(path)
        width_emu = width * 9525
        height_emu = height * 9525
        scale = min(
            MAX_IMAGE_WIDTH_EMU / width_emu,
            MAX_IMAGE_HEIGHT_EMU / height_emu,
            1.0,
        )
        width_emu = int(width_emu * scale)
        height_emu = int(height_emu * scale)
        self.docpr_counter += 1
        self.images.append(
            {
                "path": path,
                "rel_id": rel_id,
                "name": path.name,
                "width": width_emu,
                "height": height_emu,
            }
        )
        xml = image_xml(rel_id, self.docpr_counter, width_emu, height_emu, path.name)
        if caption:
            xml += paragraph_xml(caption, style="Caption", align="center")
        return xml

    # -- parsing -----------------------------------------------------------

    def cover_xml(self, lines: list[str]) -> str:
        icon_path = ROOT / "docs" / "cover-icon.png"
        out = []
        if icon_path.is_file():
            out.append(self.register_image("docs/cover-icon.png", ""))
        out.append('<w:p><w:pPr><w:spacing w:before="900" w:after="0"/></w:pPr></w:p>')
        out.append(
            '<w:p><w:pPr><w:pStyle w:val="CoverTitle"/><w:jc w:val="center"/>'
            '<w:spacing w:before="0" w:after="240"/></w:pPr>'
            + run_xml("Laporan Program: ", bold=True, size=46, color=ORANGE, font="Georgia")
            + run_xml("Secure Multiplayer Game Simulator", bold=True, size=46, color=INK, font="Georgia")
            + "</w:p>"
        )
        out.append(
            '<w:p><w:pPr><w:pStyle w:val="CoverRule"/><w:jc w:val="center"/>'
            '<w:spacing w:before="0" w:after="360"/></w:pPr></w:p>'
        )
        out.append(
            '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="120"/></w:pPr>'
            + run_xml("Mata Kuliah: Kriptografi (C)", bold=True, size=30, color=EMBER, font="Calibri")
            + "</w:p>"
        )
        out.append(
            '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="480"/></w:pPr>'
            + run_xml("Kelompok 4", bold=True, size=52, color=ORANGE, font="Georgia")
            + "</w:p>"
        )
        out.append(
            '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="180"/></w:pPr>'
            + run_xml("Nama Anggota Kelompok:", bold=True, size=26, color=INK, font="Calibri")
            + "</w:p>"
        )
        members = [line for line in lines if re.match(r"^\d+\.\s", line.strip())]
        for member in members:
            out.append(
                '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="100"/></w:pPr>'
                + run_xml(member.strip(), size=24, color=INK, font="Calibri")
                + "</w:p>"
            )

        # Identitas institusional pada halaman sampul. Baris fakultas sengaja
        # berupa placeholder agar tidak mengarang informasi yang belum tersedia.
        meta_prefixes = (
            "Dosen Pengampu:",
            "Program Studi:",
            "Departemen:",
            "Fakultas:",
            "Institusi:",
            "Tahun:",
        )
        metadata = [line.strip() for line in lines if line.strip().startswith(meta_prefixes)]
        if metadata:
            out.append(
                '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="300" w:after="60"/></w:pPr>'
                + run_xml(" | ".join(metadata[:3]), size=20, color=EMBER, font="Calibri")
                + "</w:p>"
            )
            remaining = metadata[3:]
            if remaining:
                out.append(
                    '<w:p><w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="0"/></w:pPr>'
                    + run_xml(" | ".join(remaining), size=20, color=SLATE, font="Calibri")
                    + "</w:p>"
                )
        return "".join(out)

    def build(self) -> str:
        text = self.markdown.replace("\r\n", "\n")
        cover_match = re.search(r"<!-- cover:start -->(.*?)<!-- cover:end -->", text, re.S)
        cover_lines: list[str] = []
        if cover_match:
            cover_lines = [line.strip() for line in cover_match.group(1).strip().splitlines()]
            text = text[: cover_match.start()] + text[cover_match.end():]

        blocks: list[str] = []
        if cover_lines:
            blocks.append(self.cover_xml(cover_lines))

        lines = text.split("\n")
        i = 0
        paragraph_buffer: list[str] = []
        first_heading = True

        def flush_paragraph() -> None:
            nonlocal paragraph_buffer
            if paragraph_buffer:
                joined = " ".join(s.strip() for s in paragraph_buffer if s.strip())
                if joined:
                    blocks.append(paragraph_xml(joined))
                paragraph_buffer = []

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if stripped == "<!-- pagebreak -->":
                flush_paragraph()
                blocks.append(page_break_xml())
                i += 1
                continue

            if not stripped:
                flush_paragraph()
                i += 1
                continue

            if stripped.startswith("```"):
                flush_paragraph()
                i += 1
                code_lines: list[str] = []
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                i += 1
                blocks.append(code_block_xml(code_lines))
                continue

            heading_match = re.match(r"^(#{1,3})\s+(.*)$", stripped)
            if heading_match:
                flush_paragraph()
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                blocks.append(heading_xml(level, heading_text))
                i += 1
                continue

            image_match = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", stripped)
            if image_match:
                flush_paragraph()
                blocks.append(self.register_image(image_match.group(2), image_match.group(1)))
                i += 1
                continue

            if stripped.startswith("|") and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
                flush_paragraph()
                rows = [split_table_row(lines[i])]
                i += 2
                while i < len(lines) and lines[i].strip().startswith("|"):
                    rows.append(split_table_row(lines[i]))
                    i += 1
                blocks.append(table_xml(rows))
                continue

            bullet_match = re.match(r"^[-*]\s+(.*)$", stripped)
            if bullet_match:
                flush_paragraph()
                blocks.append(
                    paragraph_xml(
                        "• " + bullet_match.group(1),
                        indent_left=420,
                        hanging=220,
                        space_after=40,
                    )
                )
                i += 1
                continue

            number_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
            if number_match:
                flush_paragraph()
                blocks.append(
                    paragraph_xml(
                        f"{number_match.group(1)}. {number_match.group(2)}",
                        indent_left=420,
                        hanging=220,
                        space_after=40,
                    )
                )
                i += 1
                continue

            if stripped.startswith("> "):
                flush_paragraph()
                blocks.append(
                    paragraph_xml(
                        stripped[2:],
                        style="Quote",
                        indent_left=360,
                        space_after=80,
                    )
                )
                i += 1
                continue

            if re.fullmatch(r"-{3,}", stripped):
                flush_paragraph()
                i += 1
                continue

            paragraph_buffer.append(line)
            i += 1

        flush_paragraph()

        sect = (
            "<w:sectPr>"
            "<w:footerReference w:type=\"default\" r:id=\"rIdFooter\"/>"
            "<w:footerReference w:type=\"first\" r:id=\"rIdFirstFooter\"/>"
            "<w:titlePg/>"
            "<w:pgSz w:w=\"11906\" w:h=\"16838\"/>"
            "<w:pgMar w:top=\"1418\" w:right=\"1418\" w:bottom=\"1418\" "
            "w:left=\"1418\" w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/>"
            "<w:cols w:space=\"708\"/>"
            "<w:docGrid w:linePitch=\"360\"/>"
            "</w:sectPr>"
        )
        return (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}" '
            f'xmlns:wp="{WP_NS}" xmlns:a="{A_NS}" xmlns:pic="{PIC_NS}">'
            "<w:body>"
            + "".join(blocks)
            + sect
            + "</w:body></w:document>"
        )


# ---------------------------------------------------------------------------
# Package parts
# ---------------------------------------------------------------------------


def styles_xml() -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W_NS}">
  <w:docDefaults>
    <w:rPrDefault><w:rPr>
      <w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Calibri" w:cs="Calibri"/>
      <w:sz w:val="22"/><w:szCs w:val="22"/><w:color w:val="{INK}"/>
    </w:rPr></w:rPrDefault>
    <w:pPrDefault><w:pPr>
      <w:spacing w:after="120" w:line="276" w:lineRule="auto"/>
    </w:pPr></w:pPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/><w:qFormat/>
    <w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
    <w:pPr><w:keepNext/><w:spacing w:before="360" w:after="160"/><w:outlineLvl w:val="0"/>
      <w:pBdr><w:bottom w:val="single" w:sz="12" w:space="4" w:color="{ORANGE}"/></w:pBdr>
    </w:pPr>
    <w:rPr><w:rFonts w:ascii="Georgia" w:hAnsi="Georgia"/><w:b/><w:sz w:val="34"/><w:color w:val="{INK}"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
    <w:pPr><w:keepNext/><w:spacing w:before="260" w:after="90"/><w:outlineLvl w:val="1"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Georgia" w:hAnsi="Georgia"/><w:b/><w:sz w:val="27"/><w:color w:val="{EMBER}"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>
    <w:pPr><w:keepNext/><w:spacing w:before="180" w:after="70"/><w:outlineLvl w:val="2"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="23"/><w:color w:val="{BLUE}"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Caption">
    <w:name w:val="Caption"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="160"/></w:pPr>
    <w:rPr><w:i/><w:sz w:val="18"/><w:color w:val="{SLATE}"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Code">
    <w:name w:val="Code"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>
      <w:ind w:left="120"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="17"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Quote">
    <w:name w:val="Quote"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:ind w:left="360"/><w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="{ORANGE}"/></w:pBdr></w:pPr>
    <w:rPr><w:i/><w:color w:val="{SLATE}"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="TableText">
    <w:name w:val="Table Text"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:sz w:val="17"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="CoverTitle">
    <w:name w:val="Cover Title"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="240"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Georgia" w:hAnsi="Georgia"/><w:b/><w:sz w:val="46"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="CoverRule">
    <w:name w:val="Cover Rule"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:jc w:val="center"/><w:pBdr><w:bottom w:val="single" w:sz="24" w:space="1" w:color="{ORANGE}"/></w:pBdr></w:pPr>
    <w:rPr><w:sz w:val="4"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Footer">
    <w:name w:val="Footer"/><w:basedOn w:val="Normal"/>
    <w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="0"/></w:pPr>
    <w:rPr><w:sz w:val="16"/><w:color w:val="{SLATE}"/></w:rPr>
  </w:style>
</w:styles>'''


def footer_xml(first: bool = False) -> str:
    if first:
        return (
            f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:ftr xmlns:w="{W_NS}" xmlns:r="{R_NS}">'
            '<w:p><w:pPr><w:pStyle w:val="Footer"/></w:pPr></w:p>'
            "</w:ftr>"
        )
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:ftr xmlns:w="{W_NS}" xmlns:r="{R_NS}">'
        '<w:p><w:pPr><w:pStyle w:val="Footer"/><w:jc w:val="center"/></w:pPr>'
        + run_xml("Secure Multiplayer Game Simulator  ·  Kriptografi (C) - Kelompok 4  ·  Halaman ", size=16, color=SLATE)
        + '<w:fldSimple w:instr=" PAGE "><w:r><w:t>1</w:t></w:r></w:fldSimple>'
        + "</w:p></w:ftr>"
    )


def content_types_xml(image_exts: set[str]) -> str:
    defaults = [
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
    ]
    for ext in sorted(image_exts):
        defaults.append(
            f'<Default Extension="{ext}" ContentType="image/{ext}"/>'
        )
    overrides = [
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>',
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>',
        '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>',
        '<Override PartName="/word/footer2.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>',
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>',
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>',
    ]
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        + "".join(defaults)
        + "".join(overrides)
        + "</Types>"
    )


def root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def document_rels_xml(builder: ReportBuilder) -> str:
    rels = [
        '<Relationship Id="rIdStyles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>',
        '<Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>',
        '<Relationship Id="rIdFirstFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer2.xml"/>',
    ]
    for image in builder.images:
        target = "media/" + str(image["name"])
        rels.append(
            f'<Relationship Id="{image["rel_id"]}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{esc(target)}"/>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(rels)
        + "</Relationships>"
    )


def core_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:title>Laporan Program: Secure Multiplayer Game Simulator</dc:title>"
        "<dc:creator>Kelompok 4 - Kriptografi (C)</dc:creator>"
        "<cp:lastModifiedBy>Kelompok 4</cp:lastModifiedBy>"
        "<dc:description>Laporan program Diffie-Hellman dan ElGamal</dc:description>"
        "</cp:coreProperties>"
    )


def app_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>Python stdlib DOCX builder</Application>"
        "<Company>Kelompok 4</Company>"
        "</Properties>"
    )


def build_docx(markdown: str) -> None:
    builder = ReportBuilder(markdown)
    document = builder.build()

    image_exts = {str(image["path"].suffix.lower().lstrip(".")) for image in builder.images}
    if not image_exts:
        image_exts = {"png"}

    with zipfile.ZipFile(OUT_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml(image_exts))
        zf.writestr("_rels/.rels", root_rels_xml())
        zf.writestr("docProps/core.xml", core_xml())
        zf.writestr("docProps/app.xml", app_xml())
        zf.writestr("word/document.xml", document)
        zf.writestr("word/styles.xml", styles_xml())
        zf.writestr("word/footer1.xml", footer_xml(first=False))
        zf.writestr("word/footer2.xml", footer_xml(first=True))
        zf.writestr("word/_rels/document.xml.rels", document_rels_xml(builder))
        for image in builder.images:
            zf.write(image["path"], "word/media/" + str(image["name"]))

    print(f"DOCX ditulis: {OUT_PATH}")
    print(f"Gambar tertanam: {len(builder.images)}")


def main() -> None:
    markdown = MD_PATH.read_text(encoding="utf-8")
    build_docx(markdown)


if __name__ == "__main__":
    main()