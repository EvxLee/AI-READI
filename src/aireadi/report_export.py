"""Export a report to ONE self-contained HTML file.

A markdown report links its figures by relative path
(`../papers/p1-.../results/E1_4_forest_figure.png`). That works in an editor
and breaks the moment the file travels: attach the `.md` to Slack or email and
the recipient sees broken image references, because the images were never part
of the file.

This inlines every image as a base64 `data:` URI and ships the CSS in a
`<style>` block, so the result is a single file with **no external references
at all**. It opens in any browser, works offline, survives being emailed, and
prints to PDF cleanly.

    python3 -m aireadi.report_export --pdf reports/2026-08-12-phase1-report.md

Writes `<name>.html` beside the source unless `-o` says otherwise. With `--pdf`
it also prints `pdf/<name>.pdf` — the PDF goes in its own subdirectory because
it is the only one of the three meant to be read, the `.md` being the source
and the verifier's target and the `.html` the step that inlines the figures.
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import re
import shutil
import subprocess
import sys
from pathlib import Path

import markdown

__all__ = ["render", "export"]

CSS = """\
:root {
  --ink: #17181c; --ink-soft: #4a4d55; --muted: #767a85;
  --surface: #ffffff; --plane: #f4f5f7;
  --rule: #e3e5ea; --accent: #2a78d6; --flag: #d03b3b;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 40px 24px 80px;
  background: var(--plane); color: var(--ink);
  font: 16px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  -webkit-text-size-adjust: 100%;
}
.sheet {
  max-width: 940px; margin: 0 auto; padding: 56px 60px 64px;
  background: var(--surface); border-radius: 10px;
  box-shadow: 0 1px 3px rgba(20,22,28,.09), 0 10px 34px rgba(20,22,28,.06);
}
h1, h2, h3, h4 { line-height: 1.25; font-weight: 700; margin: 2em 0 .6em; }
h1 { font-size: 1.95em; margin-top: 0; letter-spacing: -.02em; }
h2 { font-size: 1.42em; padding-top: .7em; border-top: 1px solid var(--rule); }
h3 { font-size: 1.13em; }
h1 + p, h2 + p { margin-top: .4em; }
p, li { color: var(--ink-soft); }
strong { color: var(--ink); font-weight: 650; }
a { color: var(--accent); }
hr { border: 0; border-top: 1px solid var(--rule); margin: 2.4em 0; }

/* Figures: the whole point of the export. */
img { display: block; width: 100%; height: auto; margin: 1.6em 0 .5em;
      border: 1px solid var(--rule); border-radius: 8px; background: #fff; }

.tablewrap { overflow-x: auto; margin: 1.3em 0; -webkit-overflow-scrolling: touch; }
table { border-collapse: collapse; width: 100%; font-size: .89em; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--rule);
         vertical-align: top; }
th { font-weight: 650; color: var(--ink); background: var(--plane);
     white-space: nowrap; }
td { color: var(--ink-soft); }
tbody tr:last-child td { border-bottom: 0; }
table sub { color: var(--muted); font-size: .82em; }

blockquote { margin: 1.4em 0; padding: .7em 1.2em; background: var(--plane);
             border-left: 3px solid var(--accent); border-radius: 0 6px 6px 0; }
blockquote p { margin: .4em 0; }
code { font: .87em ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
       background: var(--plane); padding: .12em .38em; border-radius: 4px;
       color: var(--ink); }
pre { background: var(--plane); padding: 14px 16px; border-radius: 8px;
      overflow-x: auto; }
pre code { background: none; padding: 0; }

.exportnote { margin-top: 3.5em; padding-top: 1.2em; border-top: 1px solid var(--rule);
              font-size: .8em; color: var(--muted); }

@media (max-width: 720px) {
  body { padding: 0; }
  .sheet { padding: 32px 20px 40px; border-radius: 0; box-shadow: none; }
  h1 { font-size: 1.6em; }
}
@media print {
  body { background: #fff; padding: 0; }
  .sheet { max-width: none; padding: 0; box-shadow: none; border-radius: 0; }
  h2 { break-after: avoid; } img, table { break-inside: avoid; }
  .exportnote { display: none; }
}
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
<main class="sheet">
{body}
<p class="exportnote">{note}</p>
</main>
</body>
</html>
"""


def _embed_images(html: str, base: Path) -> tuple[str, int, list[str]]:
    """Replace every local <img src> with a base64 data: URI."""
    embedded, missing = 0, []

    def repl(match: re.Match) -> str:
        nonlocal embedded
        src = match.group("src")
        if src.startswith(("data:", "http://", "https://")):
            return match.group(0)

        path = (base / src).resolve()
        if not path.exists():
            missing.append(src)
            return match.group(0)

        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
        embedded += 1
        return match.group(0).replace(src, f"data:{mime};base64,{payload}")

    out = re.sub(r'<img[^>]*\bsrc="(?P<src>[^"]+)"', repl, html)
    return out, embedded, missing


def render(source: Path) -> tuple[str, int, list[str]]:
    """Markdown file -> one self-contained HTML string."""
    text = source.read_text(encoding="utf-8")

    html = markdown.markdown(
        text,
        # `toc` is here for the id attributes it puts on headings, so the
        # exported file supports #deep-links.
        extensions=["tables", "fenced_code", "sane_lists", "attr_list",
                    "md_in_html", "toc"],
    )
    html, embedded, missing = _embed_images(html, source.parent)

    # Wide tables scroll inside their own box rather than stretching the page.
    html = re.sub(r"<table>", '<div class="tablewrap"><table>', html)
    html = re.sub(r"</table>", "</table></div>", html)

    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else source.stem

    note = (f"Self-contained export of <code>{source.name}</code> — "
            f"{embedded} figure(s) embedded directly in this file. No internet "
            f"connection or external files required.")

    return PAGE.format(title=title, css=CSS, body=html, note=note), embedded, missing


def export(source: Path, out: Path | None = None) -> Path:
    html, embedded, missing = render(source)
    out = out or source.with_suffix(".html")
    out.write_text(html, encoding="utf-8")

    size_mb = out.stat().st_size / 1e6
    print(f"{source.name} -> {out.name}  ({size_mb:.2f} MB, {embedded} figures embedded)")
    if missing:
        print(f"  WARNING: {len(missing)} image(s) not found and left as links:")
        for src in missing:
            print(f"    {src}")
    return out


PDF_SUBDIR = "pdf"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome", "chromium", "chromium-browser",
]


def _find_chrome() -> str | None:
    for candidate in CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def to_pdf(html_path: Path, out: Path | None = None) -> Path | None:
    """Print the self-contained HTML to PDF via headless Chrome.

    Worth having because Slack previews a PDF inline in the message, while an
    HTML attachment has to be downloaded and opened. The print stylesheet in
    CSS above is what makes this come out cleanly.

    The PDF lands in a `pdf/` subdirectory rather than beside its source. The
    `.md` and `.html` are build inputs -- the markdown is the source and the
    verifier's target, the HTML is where the figures get inlined -- but the PDF
    is the one anybody actually opens, and three formats interleaved in one
    listing buries it. Pass `out` to override.
    """
    chrome = _find_chrome()
    if not chrome:
        print("  (no Chrome/Chromium found -- skipping PDF)", file=sys.stderr)
        return None

    out = out or html_path.parent / PDF_SUBDIR / f"{html_path.stem}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={out}", html_path.resolve().as_uri()],
        check=True, capture_output=True,
    )
    print(f"{html_path.name} -> {PDF_SUBDIR}/{out.name}  "
          f"({out.stat().st_size / 1e6:.2f} MB)")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("report", type=Path, nargs="+")
    ap.add_argument("-o", "--out", type=Path, default=None)
    ap.add_argument("--pdf", action="store_true",
                    help="also print a PDF (Slack previews these inline)")
    args = ap.parse_args(argv)

    if args.out and len(args.report) > 1:
        ap.error("-o takes a single report")
    for report in args.report:
        if not report.exists():
            print(f"no such report: {report}", file=sys.stderr)
            return 1
        html = export(report, args.out)
        if args.pdf:
            to_pdf(html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
