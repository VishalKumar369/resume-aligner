# OCR implementation plan

> **Status: planning.** Nothing in this document is implemented yet. Written before starting so
> the work can proceed step by step, each step verified before the next begins.

## Why this is next

Every other gap listed in [docs/README.md](../../docs/README.md) is either lower-impact or a
larger, separate investment (deployment config, embeddings, rate limiting). This one is
different: a real user hits it as a **hard failure with no workaround**. A scanned resume — a
photo of a printed page, or a PDF exported from a scanner — currently gets:

```
422 "This PDF has no text layer (it looks like a scan or an image). OCR is not
     enabled yet - please upload a text-based PDF or a .docx."
```

There is no way for that user to proceed except finding a different file. That's the bar for
"next": everything else is a missing capability; this is a wall.

## Current state (verified, not assumed)

The hook already exists and is exactly as documented in `backend/docs/extraction-pipeline.md`:

```python
# app/services/extraction/ocr.py
def is_ocr_available() -> bool:
    return False   # <- the only thing that currently blocks OCR

def run_ocr(file_bytes: bytes, dpi: int = 300) -> Optional[str]:
    raise OcrUnavailableError(...)   # <- the only thing to implement
```

`pipeline.py::_try_ocr` already calls into this module whenever a PDF opens successfully but
yields no text layer (`SCANNED_PDF_NEEDS_OCR`), already checks `is_ocr_available()` first, already
catches `OcrUnavailableError` and any other exception so a failed OCR attempt degrades to a
warning rather than a 500, and already applies a confidence penalty (`× 0.75`) when
`result.used_ocr` is true. **No pipeline changes are required** — this plan is scoped to
`ocr.py` and its dependencies only, confirmed by reading the current code before writing this.

## What needs to happen

### 1. System dependencies (outside pip)

OCR needs two system packages that `pip install` cannot provide:

```bash
sudo apt install tesseract-ocr poppler-utils
```

- `tesseract-ocr` — the OCR engine itself
- `poppler-utils` — provides `pdftoppm`, which `pdf2image` shells out to for rasterising PDF
  pages into images

**This is a step the assistant cannot perform** (it needs `sudo`) — it will be called out
explicitly when this plan is executed, not silently assumed.

### 2. Python dependencies

```
pytesseract==0.3.13
pdf2image==1.17.0
```

Added to `backend/requirements.txt` alongside the existing extraction dependencies
(`pypdf`, `pdfplumber`, `python-docx`).

### 3. Implement `run_ocr`

```python
def is_ocr_available() -> bool:
    # Check tesseract is actually on PATH, not just that the packages installed.
    ...

def run_ocr(file_bytes: bytes, dpi: int = 300) -> Optional[str]:
    pages = pdf2image.convert_from_bytes(file_bytes, dpi=dpi)
    texts = [pytesseract.image_to_string(page) for page in pages]
    return "\n".join(texts)
```

Points that need care, not just a naive implementation:

- **Page cap.** A malicious or malformed PDF could have hundreds of pages; OCR is slow (roughly
  1–3s per page at 300 DPI). Cap at a small number (5, matching a realistic resume) and warn if
  the document exceeds it, rather than hanging the request.
- **Timeout.** OCR must not be allowed to block the request indefinitely. `pytesseract` supports
  a `timeout` parameter per page.
- **DPI tradeoff.** 300 DPI is the standard accuracy/speed balance; lower is faster but less
  accurate on small fonts (common in resume contact lines).
- **`is_ocr_available()` must check reality, not intent.** It should attempt to locate the
  `tesseract` binary (e.g. `shutil.which("tesseract")` or catching
  `pytesseract.TesseractNotFoundError`) rather than just returning `True` unconditionally once the
  pip packages are installed — the system package is a separate, easy-to-miss install step.

### 4. Route through the existing cleaning pipeline

OCR output is noisier than a real text layer (misread characters, broken words, inconsistent
spacing). It already passes through `clean_text()` via `_set_text()` — verified in
`pipeline.py::_try_ocr`, which calls `self._set_text(result, text, ExtractionMethod.OCR)`. No
change needed there, but this is exactly why `MIN_QUALITY_RATIO` (0.80) and the confidence penalty
matter: a badly-OCR'd page should score low confidence rather than being trusted at face value.

### 5. Update `.env.example` / setup docs

- `backend/docs/extraction-pipeline.md` currently states OCR is "deliberately unimplemented" —
  update once it lands.
- `docs/getting-started.md` prerequisites section gains the two system packages, since without
  them the app still runs — it just can't OCR.
- `docs/README.md` "Not built" section loses this line item.

## What this deliberately does NOT include

- **No OCR for `.docx`** — a `.docx` with no text (e.g. an embedded image of a resume) is out of
  scope; DOCX extraction already reads whatever text run.paragraphs contain, and there is no
  established "image-only docx" failure mode reported yet.
- **No layout-aware OCR** (column detection, table reconstruction) — plain sequential text per
  page, same as the existing `pdf_text_fallback` path.
- **No OCR language selection** — English only, matching every other heuristic in the parsing
  layer (skill vocabulary, date parsing, section headers are all English-only already).

## Testing plan

Mirrors the structure of `backend/tests/test_extraction.py`:

1. **Unit test `is_ocr_available()`** — mock `shutil.which` / the tesseract check both ways.
2. **Unit test `run_ocr()` against a synthetic scanned PDF** — render known text to an image,
   embed it in a PDF with no text layer (via `reportlab`, already a dependency), OCR it, assert
   the recovered text contains the known words. This avoids needing a real scanned resume fixture
   and keeps the test hermetic.
3. **Pipeline integration test** — feed that same synthetic scanned PDF through
   `extract_document()` and assert: `result.ok`, `result.used_ocr is True`,
   `ExtractionMethod.OCR`, confidence in a sane range (penalised but nonzero), and the warning
   list contains `SCANNED_PDF_NEEDS_OCR` but **not** `OCR_NOT_AVAILABLE`.
4. **Regression test**: confirm `is_ocr_available() is False` still degrades cleanly (the
   current 22 extraction tests already cover this path — must stay green).
5. **Cap/timeout test** — a synthetic multi-page PDF exceeding the page cap should warn rather
   than OCR every page.

No live API key or network call is involved — this entire feature is deterministic and local,
unlike the LLM paths.

## Rollout sequence (how the actual implementation session will proceed)

1. Confirm system packages are installed (ask the user to run the `apt install`, since it needs
   sudo) — **stop and wait for confirmation before continuing**.
2. Add pip dependencies, verify import works.
3. Implement `is_ocr_available()`, write its unit test.
4. Implement `run_ocr()` with the page cap and timeout, write its unit test against a synthetic
   scanned PDF.
5. Run the full existing extraction suite — confirm nothing regresses.
6. Add the pipeline integration test.
7. Manual smoke test: construct a real scanned-looking PDF, upload through the running API, read
   back `extraction_meta` to confirm `used_ocr`, `method`, `confidence`, and `structured_data`
   contains recognisable content.
8. Update the three docs listed above.
9. Report before/after: what a scanned upload does now vs. before.

Each numbered step is small enough to verify independently before moving to the next, per this
session's standing approach on the rest of the project.

## Open questions for the user (to ask before implementation, not assumed)

- **Page cap value** — 5 pages proposed above (matches a realistic resume); confirm or change.
- **OCR timeout per page** — no default proposed yet; needs a number tied to acceptable request
  latency (the rest of the upload flow is synchronous, so this adds directly to response time).
- **Should OCR be gated behind a config flag** (`OCR_ENABLED=true/false` in `.env`), the same way
  the Phase 9.5 LLM budget work gated model features? This would let it be installed but disabled
  without code changes, useful if OCR turns out to be too slow for the synchronous upload path in
  practice.
