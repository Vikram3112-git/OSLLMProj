"""PyMuPDF import that works with both new (pymupdf) and old (fitz) package names."""
try:
    import pymupdf  # noqa: F401
except ImportError:  # older PyMuPDF versions
    import fitz as pymupdf  # noqa: F401
