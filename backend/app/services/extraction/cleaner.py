import re
import unicodedata

# PDF text layers carry typographic artefacts that break downstream regex and
# confuse an LLM. Normalising them here keeps every extractor's output uniform.

_LIGATURES = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
}

_PUNCTUATION = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "–": "-", "—": "-", "‒": "-", "―": "-", "−": "-",
    "…": "...",
    " ": " ", " ": " ", " ": " ", " ": " ", "　": " ",
}

# zero-width space / non-joiner / joiner, word joiner, BOM, soft hyphen
_ZERO_WIDTH = dict.fromkeys(
    map(ord, "​‌‍⁠﻿­"), None
)

_BULLET_CHARS = "•●○■▪◦‣⁃·∙▸➢➔»❖"

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_BULLET_LINE = re.compile(rf"^[\s{_BULLET_CHARS}]*[{_BULLET_CHARS}]\s*")
_DASH_BULLET_LINE = re.compile(r"^\s*[-*]\s+")
_SOFT_HYPHEN_WRAP = re.compile(r"(\w)-\n(\w)")
_TRAILING_SPACES = re.compile(r"[ \t]+$", re.MULTILINE)
_INLINE_SPACES = re.compile(r"[ \t]{2,}")
_EXCESS_BLANK_LINES = re.compile(r"\n{3,}")

_PRINTABLE_EXTRA = set(".,;:!?'\"()[]{}/-@&+#%$_|*=<>~^`\\")


def clean_text(text: str) -> str:
    """Normalise raw extractor output into stable, parseable plain text."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.translate(_ZERO_WIDTH)

    for source, replacement in _LIGATURES.items():
        text = text.replace(source, replacement)

    text = unicodedata.normalize("NFKC", text)

    for source, replacement in _PUNCTUATION.items():
        text = text.replace(source, replacement)

    text = _CONTROL_CHARS.sub("", text)
    text = _rejoin_hyphenated_words(text)
    text = "\n".join(_normalize_bullet(line) for line in text.split("\n"))
    text = _INLINE_SPACES.sub(" ", text)
    text = _TRAILING_SPACES.sub("", text)
    text = _EXCESS_BLANK_LINES.sub("\n\n", text)

    return text.strip()


def _rejoin_hyphenated_words(text: str) -> str:
    """Repair words the PDF layout broke across lines.

    A lowercase continuation means the hyphen was a line-wrap artefact
    ("produc-\\ntion" -> "production"). An uppercase continuation means a real
    compound ("Retrieval-\\nAugmented" -> "Retrieval-Augmented").
    """

    def _join(match: re.Match) -> str:
        before, after = match.group(1), match.group(2)
        return f"{before}-{after}" if after.isupper() else f"{before}{after}"

    return _SOFT_HYPHEN_WRAP.sub(_join, text)


def _normalize_bullet(line: str) -> str:
    """Render every bullet glyph as '- ' so section parsing sees one shape."""
    if _BULLET_LINE.match(line):
        return "- " + _BULLET_LINE.sub("", line).strip()
    if _DASH_BULLET_LINE.match(line):
        return "- " + _DASH_BULLET_LINE.sub("", line).strip()
    return line.strip()


def text_quality_ratio(text: str) -> float:
    """Share of characters that are letters, digits, whitespace, or ordinary punctuation.

    A healthy text layer scores well above 0.9. Garbled font-encoding output
    scores low, letting the pipeline flag a bad extraction instead of passing
    noise downstream.
    """
    if not text:
        return 0.0
    printable = sum(
        1 for char in text
        if char.isalnum() or char.isspace() or char in _PRINTABLE_EXTRA
    )
    return printable / len(text)
