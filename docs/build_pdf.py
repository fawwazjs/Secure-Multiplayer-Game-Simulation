"""Bangun PDF laporan dari Markdown (opsional, untuk pengembangan).

Prasyarat pengembangan:
    pip install Markdown playwright

Jalankan dari root proyek:
    python docs/build_pdf.py

Aplikasi utama tidak memerlukan pustaka ini; PDF final sudah disertakan.
"""

from __future__ import annotations

from pathlib import Path
import re

import markdown
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "Laporan_Kelompok_4.md"
OUT_PATH = ROOT / "Laporan_Kelompok_4.pdf"
HTML_PATH = ROOT / "docs" / "_report_print.html"


def cover_html(lines: list[str]) -> str:
    members: list[str] = []
    metadata: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d+\.\s", stripped):
            members.append(stripped)
        elif ":" in stripped:
            key, value = stripped.split(":", 1)
            metadata[key.strip()] = value.strip()

    member_html = "".join(f"<li>{item}</li>" for item in members)
    return f"""
    <section class="cover">
      <div class="cover-mark" aria-hidden="true"></div>
      <p class="cover-kicker">LAPORAN PROGRAM</p>
      <h1 class="cover-title">Secure Multiplayer<br><span>Game Simulator</span></h1>
      <p class="cover-subtitle">Implementasi Diffie-Hellman dan ElGamal dari nol
      untuk simulasi komunikasi client-server pada game.</p>

      <div class="cover-meta">
        <div><span>Mata Kuliah</span><b>{metadata.get('Mata Kuliah', 'Kriptografi (C)')}</b></div>
        <div><span>Dosen Pengampu</span><b>{metadata.get('Dosen Pengampu', '[Nama Dosen]')}</b></div>
        <div><span>Kelompok</span><b>{metadata.get('Kelompok', 'Kelompok 4')}</b></div>
      </div>

      <div class="cover-members">
        <p class="cover-label">Anggota Kelompok</p>
        <ol>{member_html}</ol>
      </div>

      <div class="cover-inst">
        <p>Program Studi: {metadata.get('Program Studi', 'Teknologi Informasi')}</p>
        <p>Departemen: {metadata.get('Departemen', 'Teknologi Informasi')}</p>
        <p>Fakultas: {metadata.get('Fakultas', '[Nama Fakultas - sesuaikan]')}</p>
        <p><b>{metadata.get('Institusi', 'Institut Teknologi Sepuluh Nopember')}</b></p>
        <p class="cover-year">Tahun {metadata.get('Tahun', '2026')}</p>
      </div>
    </section>
    """


def build_html() -> str:
    text = MD_PATH.read_text(encoding="utf-8")
    cover_match = re.search(r"<!-- cover:start -->(.*?)<!-- cover:end -->", text, re.S)
    cover_lines = cover_match.group(1).strip().splitlines() if cover_match else []
    if cover_match:
        text = text[: cover_match.start()] + text[cover_match.end():]

    text = text.replace("<!-- pagebreak -->", "")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)

    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )

    font_dir = (ROOT / "source_code" / "static" / "fonts").as_uri()
    css = f"""
    @font-face {{
      font-family: 'Manrope'; font-style: normal; font-weight: 400;
      src: url('{font_dir}/manrope-400.ttf') format('truetype');
    }}
    @font-face {{
      font-family: 'Manrope'; font-style: normal; font-weight: 600;
      src: url('{font_dir}/manrope-600.ttf') format('truetype');
    }}
    @font-face {{
      font-family: 'Manrope'; font-style: normal; font-weight: 700;
      src: url('{font_dir}/manrope-700.ttf') format('truetype');
    }}
    @font-face {{
      font-family: 'Jersey 10'; font-style: normal; font-weight: 400;
      src: url('{font_dir}/jersey10.ttf') format('truetype');
    }}

    * {{ box-sizing: border-box; }}
    html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    body {{
      margin: 0;
      font-family: 'Manrope', 'Segoe UI', sans-serif;
      font-size: 10.4pt;
      line-height: 1.62;
      color: #232629;
      background: #ffffff;
    }}
    .cover {{
      min-height: 250mm;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: 20mm 18mm 8mm;
      page-break-after: always;
      background: #e3f1fe;
      border-top: 10mm solid #ff5e24;
    }}
    .cover-mark {{
      width: 18mm; height: 18mm; margin-top: 5mm;
      background: #ff5e24; border-radius: 4mm;
      box-shadow: inset 0 0 0 5mm #ff5e24, inset 0 0 0 8mm #fff;
    }}
    .cover-kicker {{
      margin: 9mm 0 3mm; color: #5c6066; font-size: 9pt;
      font-weight: 700; letter-spacing: .22em;
    }}
    .cover-title {{
      margin: 0; font-family: Georgia, 'Times New Roman', serif;
      font-size: 34pt; line-height: 1.05; color: #232629;
      letter-spacing: -.02em;
    }}
    .cover-title span {{ color: #ff5e24; }}
    .cover-subtitle {{
      max-width: 135mm; margin: 6mm auto 0; color: #5c6066;
      font-size: 10.5pt; line-height: 1.6;
    }}
    .cover-meta {{
      display: grid; grid-template-columns: 1fr 1fr 1fr;
      gap: 4mm; width: 150mm; margin-top: 12mm;
    }}
    .cover-meta div {{
      padding: 4mm 3mm; border: 1px solid #cfe6fb;
      border-radius: 3mm; background: rgba(255,255,255,.64);
    }}
    .cover-meta span {{
      display: block; color: #5c6066; font-size: 7.4pt; font-weight: 700;
      letter-spacing: .08em; text-transform: uppercase;
    }}
    .cover-meta b {{ display: block; margin-top: 1.5mm; font-size: 9pt; }}
    .cover-members {{
      width: 122mm; margin-top: 10mm; padding: 5mm 7mm;
      background: #fff; border: 1px solid #cfe6fb; border-radius: 3mm;
    }}
    .cover-label {{
      margin: 0 0 2mm; color: #6c3200; font-size: 8pt; font-weight: 800;
      letter-spacing: .14em; text-transform: uppercase;
    }}
    .cover-members ol {{ margin: 0; padding: 0; list-style: none; }}
    .cover-members li {{
      padding: 1.5mm 0; border-bottom: 1px dashed #e3f1fe; font-size: 9.6pt;
    }}
    .cover-members li:last-child {{ border-bottom: 0; }}
    .cover-inst {{ margin-top: auto; padding-top: 9mm; color: #232629; }}
    .cover-inst p {{ margin: 1mm 0; font-size: 9pt; }}
    .cover-year {{ margin-top: 4mm !important; font-weight: 700; color: #6c3200; }}

    h1 {{
      page-break-before: always;
      margin: 0 0 5mm;
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 21pt; line-height: 1.2; color: #232629;
      border-bottom: 2px solid #ff5e24; padding-bottom: 2.5mm;
    }}
    h1:first-of-type {{ page-break-before: auto; }}
    h2 {{
      margin: 7mm 0 2.4mm; font-family: Georgia, 'Times New Roman', serif;
      font-size: 14pt; line-height: 1.3; color: #6c3200;
      page-break-after: avoid;
    }}
    h3 {{
      margin: 5mm 0 1.8mm; font-size: 11.2pt; color: #232629;
      page-break-after: avoid;
    }}
    p {{ margin: 0 0 2.5mm; text-align: justify; }}
    ul, ol {{ margin: 0 0 3mm 5mm; padding-left: 3mm; }}
    li {{ margin-bottom: 1mm; }}
    strong {{ font-weight: 700; }}
    code {{
      font-family: 'Cascadia Code', Consolas, monospace; font-size: 9pt;
      background: #f5f8fb; border: 1px solid #e3f1fe;
      border-radius: 1mm; padding: .2mm 1mm;
    }}
    pre {{
      margin: 2.5mm 0 3.5mm; padding: 3mm 4mm;
      background: #f5f8fb; border: 1px solid #d3e6f9; border-radius: 2mm;
      white-space: pre-wrap; overflow-wrap: anywhere;
      page-break-inside: avoid;
    }}
    pre code {{ border: 0; background: transparent; padding: 0; font-size: 8.7pt; line-height: 1.45; }}
    table {{
      width: 100%; margin: 2.5mm 0 4mm; border-collapse: collapse;
      font-size: 8.8pt; page-break-inside: auto;
    }}
    th, td {{ border: 1px solid #d3e6f9; padding: 1.5mm 2mm; vertical-align: top; }}
    th {{ background: #e3f1fe; color: #232629; text-align: left; font-weight: 700; }}
    tr {{ page-break-inside: avoid; }}
    img {{
      max-width: 100%; max-height: 150mm; display: block;
      margin: 3mm auto 2mm; border: 1px solid #d3e6f9;
      border-radius: 2mm; page-break-inside: avoid;
    }}
    blockquote {{
      margin: 3mm 0; padding: 2.5mm 4mm; border-left: 3px solid #ff5e24;
      background: #fff8f4; color: #5c6066;
    }}
    .page-break {{ page-break-after: always; }}
    a {{ color: #1d5d8c; text-decoration: none; }}
    """

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<base href="../">
<title>Laporan Kelompok 4 — Secure Multiplayer Game Simulator</title>
<style>{css}</style>
</head>
<body>
{cover_html(cover_lines)}
{body}
</body>
</html>
"""


def main() -> None:
    HTML_PATH.write_text(build_html(), encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page()
        page.goto(HTML_PATH.as_uri(), wait_until="load")
        page.wait_for_timeout(800)
        page.pdf(
            path=str(OUT_PATH),
            format="A4",
            print_background=True,
            margin={"top": "16mm", "right": "17mm", "bottom": "18mm", "left": "17mm"},
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=(
                "<div style=\"width:100%;padding:0 17mm;font-family:Segoe UI,Arial,sans-serif;"
                "font-size:7.2pt;color:#5c6066;display:flex;justify-content:space-between;\">"
                "<span>Secure Multiplayer Game Simulator · Kriptografi (C) · Kelompok 4</span>"
                "<span>Halaman <span class=\"pageNumber\"></span> / <span class=\"totalPages\"></span></span>"
                "</div>"
            ),
        )
        browser.close()
    HTML_PATH.unlink(missing_ok=True)
    print(f"PDF ditulis: {OUT_PATH}")


if __name__ == "__main__":
    main()