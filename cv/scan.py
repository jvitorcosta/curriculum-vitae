"""Advisory scanner for a saved job posting (HTML or text).

It looks for text a person would not see but an AI reading the page might:
hidden HTML, invisible characters, Unicode tag characters, instruction-shaped
lines, look-alike letters and URLs that only appear in hidden content.
It never blocks and never edits the posting; findings quote what it saw.
Everything it reads is untrusted data. Standard library only.
"""

import re
import unicodedata
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
SKIP = {"script", "style", "noscript", "template"}
BLOCK_TAGS = {"p", "div", "li", "br", "tr", "h1", "h2", "h3", "h4", "ul", "ol"}

HIDDEN_STYLE = [
    r"display\s*:\s*none",
    r"visibility\s*:\s*hidden",
    r"(?<![\w-])opacity\s*:\s*0*(\.0*)?\s*(?![\d.])",
    r"font-size\s*:\s*0*(\.0*)?(px|pt|em|rem|%|vw|vh)?\s*(?![\d.\w])",
    r"(?<![\w-])color\s*:\s*(transparent|rgba\([^)]*,\s*0*(\.0*)?\s*\))",
    r"text-indent\s*:\s*-\d{3,}",
    r"(left|top|right|bottom)\s*:\s*-\d{3,}",
    r"clip(-path)?\s*:\s*(rect\(\s*0|inset\(\s*50%)",
]
HIDDEN_RE = re.compile("|".join(HIDDEN_STYLE), re.I)

# zero-width, bidi controls, soft hyphen, BOM, word joiners, Mongolian vowel separator
INVISIBLE = set(range(0x200B, 0x2010)) | set(range(0x202A, 0x202F)) | set(range(0x2060, 0x2065)) | set(range(0x2066, 0x206A))
INVISIBLE |= {0x00AD, 0xFEFF, 0x180E, 0x034F}
TAG_LO, TAG_HI = 0xE0000, 0xE007F
TAG_RE = re.compile("[\U000E0000-\U000E007F]+")

INSTRUCTIONS = [
    r"\b(ignore|disregard|forget)\b[^.\n]{0,30}\b(previous|prior|above|earlier|all)\b[^.\n]{0,30}\b(instructions?|prompts?|rules)\b",
    r"\bsend\s+(the\s+|your\s+|my\s+|a\s+)?(cv|resume|r[eé]sum[eé]|application|profile)\s+to\b",
    r"\breply\s+with\b",
    r"\byou\s+are\s+(an?\s+)?(ai|a\.i\.|llm|language\s+model|chatbot|assistant|bot)\b",
    r"\bas\s+an\s+ai\b",
    r"\b(system\s+prompt|new\s+instructions?)\b",
    r"\bdo\s+not\s+(tell|mention|reveal)\b[^.\n]{0,30}\b(user|candidate|applicant)\b",
]
INSTRUCTION_RE = re.compile("|".join(f"(?:{p})" for p in INSTRUCTIONS), re.I)

URL_RE = re.compile(r"https?://[^\s<>\"'`)\]]+", re.I)
WORD_RE = re.compile(r"\w+", re.UNICODE)
EXCERPT = 200


def _hidden_element(attrs: list) -> bool:
    d = {k: (v or "") for k, v in attrs}
    if "hidden" in d or d.get("aria-hidden", "").strip().lower() == "true":
        return True
    return bool(HIDDEN_RE.search(d.get("style", "")))


class _Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool]] = []
        self.skip_depth = 0
        self.visible: list[str] = []
        self.blocks: list[list[str]] = []  # one entry per outermost hidden element
        self.hidden_hrefs: list[str] = []
        self.visible_hrefs: list[str] = []

    @property
    def hidden(self) -> bool:
        return any(h for _, h in self.stack)

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            self._hrefs(attrs)
            if tag == "br" and not self.hidden:
                self.visible.append("\n")
            return
        was_hidden = self.hidden
        h = _hidden_element(attrs)
        self.stack.append((tag, h))
        if tag in SKIP:
            self.skip_depth += 1
        if h and not was_hidden:
            self.blocks.append([])
        self._hrefs(attrs)

    def handle_startendtag(self, tag, attrs):
        self._hrefs(attrs)

    def _hrefs(self, attrs):
        for k, v in attrs:
            if k in ("href", "src") and v and URL_RE.match(v.strip()):
                (self.hidden_hrefs if self.hidden else self.visible_hrefs).append(v.strip())

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for t, _ in self.stack[i:]:
                    if t in SKIP:
                        self.skip_depth -= 1
                del self.stack[i:]
                break
        if tag in BLOCK_TAGS and not self.hidden:
            self.visible.append("\n")

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.hidden:
            if self.blocks:
                self.blocks[-1].append(data)
        else:
            self.visible.append(data)


def _line_text(parts: list[str]) -> str:
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _strip(text: str) -> str:
    return "".join(c for c in text if ord(c) not in INVISIBLE and not TAG_LO <= ord(c) <= TAG_HI)


def _decode_tags(run: str) -> str:
    return "".join(chr(ord(c) - TAG_LO) if 0x20 <= ord(c) - TAG_LO <= 0x7E else "?" for c in run)


def _scripts(word: str) -> set[str]:
    out = set()
    for c in word:
        if c.isalpha():
            n = unicodedata.name(c, "")
            for s in ("LATIN", "CYRILLIC", "GREEK"):
                if n.startswith(s):
                    out.add(s)
    return out


def _clip(s: str) -> str:
    return s if len(s) <= EXCERPT else s[:EXCERPT] + "..."


def scan(raw: str) -> dict:
    """Return {"verdict", "findings", "text"}; text is the visible text with invisible characters removed."""
    page = _Page()
    page.feed(raw)
    page.close()
    visible_raw = "".join(page.visible)
    hidden_raw = "".join("".join(b) for b in page.blocks)
    findings: list[dict] = []

    hidden_texts = []
    for b in page.blocks:
        t = _line_text(b)
        if t:
            hidden_texts.append(t)
            findings.append({"kind": "hidden_html", "excerpt": _clip(t)})

    # characters, over everything the parser saw (visible and hidden)
    seen = visible_raw + hidden_raw
    counts: dict[str, int] = {}
    in_word = 0
    for i, c in enumerate(seen):
        if ord(c) in INVISIBLE:
            key = f"U+{ord(c):04X}"
            counts[key] = counts.get(key, 0) + 1
            prev = seen[i - 1] if i else ""
            nxt = seen[i + 1] if i + 1 < len(seen) else ""
            if prev.isalnum() and nxt.isalnum():
                in_word += 1
    if counts:
        findings.append(
            {"kind": "invisible_chars", "count": sum(counts.values()), "inside_word": in_word, "codepoints": counts}
        )

    decoded_tags = []
    for m in TAG_RE.finditer(seen):
        d = _decode_tags(m.group())
        decoded_tags.append(d)
        findings.append({"kind": "tag_chars", "count": len(m.group()), "decoded": _clip(d)})

    # instruction-shaped lines: visible text, hidden text and decoded tag text
    for n, line in enumerate(_strip(visible_raw).splitlines(), 1):
        if INSTRUCTION_RE.search(line):
            findings.append({"kind": "instruction", "line": n, "quote": _clip(line.strip()), "hidden": False})
    for t in hidden_texts:
        if INSTRUCTION_RE.search(t):
            findings.append({"kind": "instruction", "quote": _clip(t), "hidden": True})
    for d in decoded_tags:
        if INSTRUCTION_RE.search(d):
            findings.append({"kind": "instruction", "quote": _clip(d), "hidden": True, "via": "tag_chars"})

    # mixed scripts
    done = set()
    for w in WORD_RE.findall(_strip(seen)):
        s = _scripts(w)
        if "LATIN" in s and len(s) > 1 and w not in done:
            done.add(w)
            findings.append({"kind": "mixed_script", "word": w, "scripts": sorted(s)})

    # URLs only in hidden content
    visible_urls = set(URL_RE.findall(_strip(visible_raw))) | set(page.visible_hrefs)
    hidden_urls = [*URL_RE.findall(_strip(hidden_raw)), *page.hidden_hrefs]
    hidden_urls += [u for d in decoded_tags for u in URL_RE.findall(d)]
    flagged = set()
    for u in hidden_urls:
        u = u.rstrip(".,;")
        if u not in visible_urls and u not in flagged:
            flagged.add(u)
            findings.append({"kind": "hidden_only_url", "url": u})

    strong = {"tag_chars", "instruction", "hidden_only_url"}
    if any(f["kind"] in strong or (f["kind"] == "invisible_chars" and f["inside_word"]) for f in findings):
        verdict = "suspicious"
    elif findings:
        verdict = "review"
    else:
        verdict = "clean"

    text = _strip(visible_raw)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return {"verdict": verdict, "findings": findings, "text": text}
