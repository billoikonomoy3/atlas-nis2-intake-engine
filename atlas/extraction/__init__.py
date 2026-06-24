"""Document extraction — THE ONLY place a model runs.

ingest.py turns PDFs/DOCX into per-page text chunks (deterministic, offline).
extract.py asks a model to LOCATE + QUOTE evidence for a control (schema-locked).
The model bridges vocabulary and points at evidence; it assigns NO maturity level and
makes NO legal judgment. Facts without a source_quote are discarded downstream.
"""
