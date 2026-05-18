#!/usr/bin/env python3
"""Extrae texto de los PDFs del banco de preguntas."""

from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent

for fname in ["etica.pdf", "Resumen de Todos los Test.pdf"]:
    path = ROOT / fname
    if not path.exists():
        print(f"No encontrado: {path}")
        continue
    reader = PdfReader(path)
    text = ""
    for i, page in enumerate(reader.pages):
        text += f"\n=== PAGE {i + 1} ===\n{page.extract_text() or ''}"
    out = ROOT / fname.replace(".pdf", "_extracted.txt")
    out.write_text(text, encoding="utf-8")
    print(f"{fname}: {len(reader.pages)} páginas → {out.name}")
