"""
DiaSentry — Automated PDF Ingestion & Semantic Chunking Script
================================================================
This script automates the extraction, cleaning, and semantic chunking of
clinical PDF guidelines (such as ADA Standards of Care 2026 - dc26srev.pdf)
and converts them into structured JSON / Python dictionaries ready for RAG.

Workflow:
  1. Load: Reads the raw PDF file using `pypdf`.
  2. Clean: Strips out headers, footers, copyright notices, and page numbers.
  3. Chunk: Performs Semantic Section Splitting based on clinical headings
            and recommendation numbers.
  4. Export: Saves the clean structured chunks into a JSON file and can
             optionally seed them directly into ChromaDB.

Usage:
    python -m backend.rag.ingest_pdf
"""

import os
import re
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger("DiaSentry.RAG.PDFIngestion")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_and_extract_text(pdf_path: str) -> str:
    """
    Reads a PDF file and extracts raw text from all pages.
    """
    try:
        import pypdf
    except ImportError:
        logger.error("❌ pypdf is not installed. Please run: pip install pypdf")
        raise

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    logger.info(f"📂 Loading PDF file: {pdf_path}")
    reader = pypdf.PdfReader(pdf_path)
    raw_text = ""

    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()
        if page_text:
            raw_text += f"\n--- PAGE {i+1} ---\n" + page_text

    logger.info(f"📄 Extracted {len(reader.pages)} pages ({len(raw_text)} characters).")
    return raw_text


def clean_pdf_noise(raw_text: str) -> str:
    """
    Removes PDF artifacts, headers, footers, copyright notices, and line wraps.
    """
    logger.info("🧹 Cleaning PDF artifacts and noise...")

    # 1. Remove page headers and footers specific to ADA journals
    text = re.sub(r'Diabetes Care\s+Volume\s+\d+.*?202\d+', '', raw_text, flags=re.IGNORECASE)
    text = re.sub(r'Summary\s+of\s+Revisions\s+Diabetes\s+Care.*?S\d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Downloaded\s+from\s+http://.*?by\s+guest\s+on\s+.*?202\d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'S\d+\s+Summary\s+of\s+Revisions', '', text, flags=re.IGNORECASE)
    text = re.sub(r'--- PAGE \d+ ---', '', text)

    # 2. Remove copyright and DOI links
    text = re.sub(r'©\s*202\d+\s+by\s+the\s+American\s+Diabetes\s+Association.*?(license\.)', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'https?://[^\s]+', '', text)

    # 3. Fix hyphenated word breaks at line endings (e.g., "recom-\nwendation" -> "recommendation")
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)

    # 4. Clean up multiple newlines and spaces
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)

    return text.strip()


def semantic_chunking(cleaned_text: str) -> List[Dict[str, Any]]:
    """
    Splits the cleaned text by clinical section headers (e.g., '1. Improving Care...',
    '6. Glycemic Goals...', '7. Diabetes Technology...') into structured JSON chunks.
    """
    logger.info("✂️ Performing semantic section chunking...")

    # Regex pattern to match numbered major sections: e.g., "7. Diabetes Technology" or "6. Glycemic Goals..."
    section_pattern = re.compile(r'\n(\d+\.\s+[A-Z][^\n]+)')
    
    parts = section_pattern.split(cleaned_text)
    chunks: List[Dict[str, Any]] = []

    # If document starts before the first numbered section (e.g., General Changes)
    if parts and parts[0].strip():
        chunks.append({
            "id": "ada_2026_general_changes",
            "topic": "ADA 2026 Standards of Care — General Changes & Overview",
            "content": parts[0].strip()[:1500]  # Limit chunk length
        })

    # Iterate over matched sections and their content
    for i in range(1, len(parts), 2):
        section_title = parts[i].strip()
        section_body = parts[i+1].strip() if i+1 < len(parts) else ""

        # Create a clean ID from section title
        sec_num = section_title.split('.')[0].strip()
        sec_slug = re.sub(r'[^a-z0-9]+', '_', section_title.lower()).strip('_')
        chunk_id = f"ada_2026_sec_{sec_num}_{sec_slug}"[:40]

        # Ensure chunk is not empty or too short
        if len(section_body) > 50:
            chunks.append({
                "id": chunk_id,
                "topic": f"ADA 2026 Guidelines — {section_title}",
                "content": f"{section_title}\n\n{section_body}"
            })

    logger.info(f"✅ Created {len(chunks)} structured semantic chunks.")
    return chunks


def export_to_json(chunks: List[Dict[str, Any]], output_path: str) -> None:
    """
    Saves the extracted chunks to a structured JSON file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"guidelines_year": "2026", "source": "ADA Standards of Care", "chunks": chunks}, f, indent=4, ensure_ascii=False)
    
    logger.info(f"💾 Saved {len(chunks)} chunks to JSON file: {output_path}")


def main():
    # Define paths
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    pdf_path = os.path.join(workspace_root, "dc26srev.pdf")
    output_json_path = os.path.join(workspace_root, "backend", "rag", "ada_2026_extracted.json")

    logger.info("🚀 Starting Automated ADA 2026 PDF Ingestion Pipeline...")

    try:
        # Step 1: Load and extract text
        raw_text = load_and_extract_text(pdf_path)

        # Step 2: Clean noise and artifacts
        clean_text = clean_pdf_noise(raw_text)

        # Step 3: Semantic Chunking
        chunks = semantic_chunking(clean_text)

        # Step 4: Export to JSON
        export_to_json(chunks, output_json_path)

        logger.info("🎉 Pipeline completed successfully! You can now inspect ada_2026_extracted.json")

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
