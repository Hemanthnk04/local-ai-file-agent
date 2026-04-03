"""
chunker.py — context window awareness for large files.

Before sending file content to the LLM, check if it fits within MAX_FILE_CHARS.
If not, split into overlapping chunks and process each, then merge results.

Used by: rewrite_file, diff_preview, folder_analysis
"""

import os
from .config import MAX_FILE_CHARS, CHUNK_OVERLAP


def fits_in_context(text):
    """Return True if the text is small enough to send in one LLM call."""
    return len(text) <= MAX_FILE_CHARS


def split_into_chunks(text, chunk_size=None, overlap=None):
    """
    Split text into overlapping chunks that fit within the context window.
    Tries to split on line boundaries to avoid cutting mid-line.

    Returns list of (chunk_text, start_line, end_line) tuples.
    """
    chunk_size = chunk_size or MAX_FILE_CHARS
    overlap    = overlap    or CHUNK_OVERLAP

    if len(text) <= chunk_size:
        return [(text, 0, text.count("\n"))]

    lines   = text.splitlines(keepends=True)
    chunks  = []
    start   = 0       # line index
    char_pos = 0

    while start < len(lines):
        # Accumulate lines until we hit the chunk size
        end       = start
        chunk_chars = 0
        while end < len(lines) and chunk_chars + len(lines[end]) <= chunk_size:
            chunk_chars += len(lines[end])
            end += 1

        if end == start:
            # Single line exceeds chunk size — force include it
            end = start + 1

        chunk_text = "".join(lines[start:end])
        chunks.append((chunk_text, start + 1, end))   # 1-indexed line numbers

        # Advance with overlap
        overlap_lines = 0
        overlap_chars = 0
        for i in range(end - 1, start - 1, -1):
            if overlap_chars + len(lines[i]) > overlap:
                break
            overlap_chars += len(lines[i])
            overlap_lines += 1

        start = max(start + 1, end - overlap_lines)

    return chunks


def warn_if_large(text, filename="file"):
    """
    Print a warning if the file exceeds context window limits.
    Returns (fits, n_chunks).
    """
    if fits_in_context(text):
        return True, 1

    n_chunks = len(split_into_chunks(text))
    size_kb  = len(text) // 1024
    print(f"  ⚠  '{filename}' is {size_kb} KB ({len(text):,} chars) — exceeds "
          f"context window ({MAX_FILE_CHARS:,} chars).")
    print(f"     Will process in {n_chunks} chunk(s). Results will be merged.")
    return False, n_chunks


def chunk_rewrite(original_text, rewrite_fn, filename=""):
    """
    Apply rewrite_fn to a large file by processing it in chunks.

    rewrite_fn(chunk_text) → rewritten_chunk_text

    Returns the merged result, or None on failure.
    """
    if fits_in_context(original_text):
        return rewrite_fn(original_text)

    chunks  = split_into_chunks(original_text)
    results = []
    total   = len(chunks)

    for i, (chunk, start_line, end_line) in enumerate(chunks, 1):
        print(f"  Processing chunk {i}/{total} (lines {start_line}–{end_line})...")
        result = rewrite_fn(chunk)
        if not result:
            print(f"  ❌ Chunk {i} failed — aborting.")
            return None

        # Remove overlap from previous chunk's end when appending
        if i > 1 and results:
            # Strip the overlap lines from the end of previous result
            prev_lines   = results[-1].splitlines()
            chunk_lines  = chunk.splitlines()
            # Detect how many leading lines of this chunk were in the overlap
            # by comparing with the end of the previous chunk
            overlap_count = 0
            for j in range(min(len(prev_lines), CHUNK_OVERLAP // 80 + 5)):
                if (j < len(chunk_lines) and
                        prev_lines[-(j+1)].strip() == chunk_lines[j].strip()):
                    overlap_count = j + 1

            result_lines = result.splitlines()
            results.append("\n".join(result_lines[overlap_count:]))
        else:
            results.append(result)

    return "\n".join(results)
