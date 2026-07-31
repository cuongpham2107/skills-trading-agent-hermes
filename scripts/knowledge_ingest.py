#!/usr/bin/env python3
"""
Knowledge Ingest — chunk markdown files in knowledge/ and build TF-IDF index.
Uses sklearn TfidfVectorizer (local, no API call, no GPU needed).

Usage:
  PYTHONPATH="" .venv/bin/python3 scripts/knowledge_ingest.py              # index all
  PYTHONPATH="" .venv/bin/python3 scripts/knowledge_ingest.py --reset      # re-index
  PYTHONPATH="" .venv/bin/python3 scripts/knowledge_ingest.py --file banking.md
"""

import sys, json, os, re, pickle
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWLEDGE_DIR = os.path.join(SKILL_DIR, "knowledge")
INDEX_DIR = os.path.join(KNOWLEDGE_DIR, ".index")

def parse_front_matter(content):
    """Extract YAML-like front-matter from markdown."""
    meta = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = parts[2].strip()
    return meta, body

def chunk_markdown(content, max_chars=600):
    """Split markdown into chunks at paragraph boundaries."""
    paragraphs = content.split("\n\n")
    chunks = []
    current = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks

def main():
    import argparse
    from sklearn.feature_extraction.text import TfidfVectorizer
    
    p = argparse.ArgumentParser()
    p.add_argument("--reset", action="store_true")
    p.add_argument("--file", help="Single file relative to knowledge/")
    args = p.parse_args()
    
    os.makedirs(INDEX_DIR, exist_ok=True)
    index_file = os.path.join(INDEX_DIR, "tfidf_index.pkl")
    
    # Collect files
    if args.file:
        filepath = os.path.join(KNOWLEDGE_DIR, args.file)
        files = [args.file] if os.path.exists(filepath) else []
    else:
        files = []
        for root, dirs, fs in os.walk(KNOWLEDGE_DIR):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in fs:
                if f.endswith(".md") and f != "_index.md":
                    files.append(os.path.relpath(os.path.join(root, f), KNOWLEDGE_DIR))
    
    if not files:
        print(json.dumps({"error": "No markdown files found in knowledge/"}))
        sys.exit(1)
    
    # Chunk and collect metadata
    documents = []
    metadatas = []
    
    for rel_path in files:
        full_path = os.path.join(KNOWLEDGE_DIR, rel_path)
        with open(full_path) as f:
            content = f.read()
        
        meta, body = parse_front_matter(content)
        chunks = chunk_markdown(body)
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "source": rel_path,
                "chunk_index": i,
                "tags": meta.get("tags", ""),
                "keywords": meta.get("keywords", ""),
                "updated": meta.get("updated", "unknown"),
                "title": meta.get("summary", rel_path),
            })
    
    # Build TF-IDF matrix
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        strip_accents="unicode",
    )
    tfidf_matrix = vectorizer.fit_transform(documents)
    
    # Save
    with open(index_file, "wb") as f:
        pickle.dump({
            "vectorizer": vectorizer,
            "tfidf_matrix": tfidf_matrix,
            "documents": documents,
            "metadatas": metadatas,
            "built_at": datetime.now().isoformat(),
            "num_files": len(files),
            "num_chunks": len(documents),
        }, f)
    
    print(json.dumps({
        "status": "ok",
        "files": len(files),
        "chunks": len(documents),
        "index_file": index_file,
        "features": tfidf_matrix.shape[1],
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
