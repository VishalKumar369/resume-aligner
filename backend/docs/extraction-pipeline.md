# Document extraction pipeline

> Delivered in Phase 1. This is the layer that turns an uploaded resume file into text.
> Before it existed the backend stored a placeholder sentence instead of the resume, which
> is why every parsed field came back empty.

## Where it lives

```
backend/app/services/extraction/
├── types.py            FileType, ExtractionMethod, ExtractionWarning, ExtractionResult
├── detector.py         magic-byte file type detection
├── pdf_extractor.py    pdfplumber (primary) -> pypdf (fallback)
├── docx_extractor.py   python-docx, including tables and headers
├── text_extractor.py   plain-text decoding
├── cleaner.py          text normalisation + quality scoring
├── ocr.py              OCR hook (deferred, not implemented)
└── pipeline.py         orchestrator, entry point: extract_document()
```

## Entry point

```python
from app.services.extraction.pipeline import extract_document

result = extract_document(file_bytes, filename="resume.pdf", content_type="application/pdf")
if result.ok:
    text = result.text
```

`ResumeParserService.extract(...)` wraps the same call, so parsing code does not import the
pipeline directly.

## Flow

```
bytes
  │
  ▼
detect_file_type()        magic bytes first, extension only as a fallback
  │
  ├── PDF   ──►  pdfplumber ──(empty)──►  pypdf ──(empty)──►  OCR hook ──►  warning
  ├── DOCX  ──►  python-docx (paragraphs + tables + headers/footers)
  ├── TXT   ──►  multi-encoding decode
  └── DOC / RTF / unknown  ──►  rejected with a specific warning
  │
  ▼
clean_text()              ligatures, smart quotes, bullets, hyphen rejoins, whitespace
  │
  ▼
_finalize()               char/word counts, quality ratio, confidence, warnings
  │
  ▼
ExtractionResult
```

## Why file type comes from magic bytes

Browsers and clients misreport `Content-Type`, and users rename files. `detect_file_type`
reads the signature instead:

| Signature | Type |
|---|---|
| `%PDF` | PDF |
| `PK\x03\x04` **and** the archive contains `word/document.xml` | DOCX |
| `PK\x03\x04` without that entry | UNKNOWN (a `.xlsx`/`.pptx`/plain zip, not a resume) |
| `\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1` | legacy DOC |
| `{\rtf` | RTF |

## Why two PDF engines

`pdfplumber` preserves reading order on the two-column layouts resumes favour, so it is the
primary. `pypdf` runs only when pdfplumber returns nothing, because the two disagree on some
generator quirks and encrypted-but-readable files. The method used is recorded on the result
(`pdf_text` vs `pdf_text_fallback`), and the fallback carries a small confidence penalty.

## Text cleaning

| Problem | Handling |
|---|---|
| `produc-\ntion` (line-wrap hyphen) | rejoined to `production` |
| `Retrieval-\nAugmented` (real compound) | rejoined to `Retrieval-Augmented` |
| `●`, `•`, `▪`, `‣`, `·` … | normalised to `- ` |
| Ligatures `ﬁ ﬂ ﬀ` | expanded to `fi fl ff` |
| Smart quotes, en/em dashes | normalised to ASCII |
| Zero-width and control characters | stripped |
| Runs of blank lines | collapsed to one |

The uppercase-vs-lowercase rule for hyphens is a heuristic: a lowercase continuation means the
hyphen was a layout artefact, an uppercase one means a genuine compound word.

## ExtractionResult

```python
result.ok            # bool - the only thing callers should branch on
result.text          # cleaned text, "" on failure
result.file_type     # FileType enum
result.method        # pdf_text | pdf_text_fallback | docx | plain_text | ocr | none
result.page_count    # PDFs only
result.char_count    # length of the cleaned text
result.word_count
result.used_ocr
result.confidence    # 0.0 - 1.0
result.warnings      # list[ExtractionWarning]
result.detail        # user-facing explanation when something went wrong
```

### Confidence

`(quality_ratio * 0.6) + (volume * 0.4)`, where volume saturates at 1500 characters. It is then
penalised: ×0.9 for the pypdf fallback, ×0.75 for OCR, ×0.5 when the text is suspiciously short.
Real resumes in `uploads/` score `1.0`.

### Warnings

| Warning | Meaning |
|---|---|
| `empty_file` | zero bytes uploaded |
| `unsupported_type` | not a PDF, DOCX, or text file |
| `legacy_doc_format` | old binary `.doc` |
| `scanned_pdf_needs_ocr` | the PDF opened but has no text layer |
| `ocr_not_available` | OCR would help but is not installed |
| `low_text_yield` | under 120 characters extracted |
| `primary_extractor_failed` | pdfplumber failed, pypdf was tried |
| `encrypted_document` | PDF was encrypted |
| `extraction_failed` | unreadable or garbled |

## Failing loudly

A broken parse must never look like a weak candidate. Two mechanisms enforce that:

1. **Upload rejects unreadable files** — `POST /resume/upload` returns 415/422 with an
   explanation instead of persisting an empty record.
2. **Alignment reports parse health** — every `/alignment/generate` response carries
   `extraction_health` (`resume_ok`, `jd_ok`, `warnings`), so a 0% score can be attributed
   to either a genuine mismatch or a failed extraction.

## Upload validation

| Rule | Response |
|---|---|
| Empty file | `400` |
| Larger than 5MB | `413` |
| Not PDF/DOCX/TXT | `415` |
| No readable text | `422` |

## OCR (deferred)

`ocr.py` is a stub by design. Scanned PDFs currently return
`scanned_pdf_needs_ocr` + `ocr_not_available` with a clear message.

To enable it later:

1. `apt install tesseract-ocr poppler-utils`
2. Add `pytesseract` and `pdf2image` to `requirements.txt`
3. Implement `run_ocr()` and flip `is_ocr_available()` to `True`

No pipeline changes are needed — it already routes to this module whenever a PDF has no text layer.

## Tests

`backend/tests/test_extraction.py` covers detection, cleaning, and the pipeline, and runs the
real PDFs in `backend/uploads/` through it. It asserts the old placeholder string
(`"Binary or non-text content"`) can never reappear.

```bash
cd backend && ../.venv/bin/python -m pytest tests -q
```

## Known limitation

`total_experience_years` still comes from the old heuristic regex and returns `0` for most
resumes. Extraction is correct; the *structuring* step on top of it is redesigned in Phase 2.
