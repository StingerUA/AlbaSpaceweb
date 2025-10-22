#!/usr/bin/env python3
"""
Normalize malformed asset paths in HTML files under the repo root.

Fixes patterns like:
  //assets///assets/foo.png  -> /assets/foo.png
  //assets/foo.png           -> /assets/foo.png
  ///assets/foo.png          -> /assets/foo.png
  https://assets.zyrosite.com/... -> /assets/<basename>

The script edits files in-place and writes a small report to stdout.
"""
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

HTML_GLOB_PATTERN = '**/*.html'

# pattern for any URL that contains 'assets' in the hostname/path
url_assets_host_pattern = re.compile(r'https?://[^\s"\']*assets[^\s"\']*', flags=re.IGNORECASE)

def normalize_src(s: str) -> str:
    if not s:
        return s
    # If the value is a full URL to an assets host, return just the basename under /assets/
    m = url_assets_host_pattern.search(s)
    if m:
        p = urlparse(m.group(0))
        return '/assets/' + Path(p.path).name

    # Normalize multiple slashes around assets path
    s = re.sub(r'(?<!:)/{2,}assets', '/assets', s)
    s = re.sub(r'^/{2,}assets', '/assets', s)
    # collapse sequences like /assets//assets/... -> /assets/...
    s = re.sub(r'/assets(?:/+assets)+', '/assets', s)
    # remove repeated slashes anywhere
    s = re.sub(r'/{2,}', '/', s)
    return s

def process_file(path: Path) -> int:
    changed = 0
    txt = path.read_text(encoding='utf-8', errors='ignore')
    orig = txt

    # Fix srcset attributes (comma separated list)
    def fix_srcset(match):
        val = match.group(1)
        parts = [p.strip() for p in val.split(',') if p.strip()]
        new_parts = []
        for p in parts:
            sub = p.split()  # may be 'url 300w'
            sub[0] = normalize_src(sub[0])
            new_parts.append(' '.join(sub))
        return 'srcset="' + ','.join(new_parts) + '"'

    txt = re.sub(r'srcset\s*=\s*"([^"]+)"', fix_srcset, txt, flags=re.IGNORECASE)

    # Fix src attributes
    def fix_src_attr(match):
        val = match.group(1)
        new = normalize_src(val)
        return 'src="' + new + '"'

    txt = re.sub(r'src\s*=\s*"([^"]+)"', fix_src_attr, txt, flags=re.IGNORECASE)

    # Also fix occurrences in inline styles or data-attributes referencing assets hosts
    txt = re.sub(r'https?://[^\s"\']*assets[^\s"\']*/([^\s"\')]+)', r'/assets/\1', txt)

    if txt != orig:
        path.write_text(txt, encoding='utf-8')
        changed = 1
    return changed

def main():
    files = list(ROOT.rglob(HTML_GLOB_PATTERN))
    files = [p for p in files if p.is_file()]
    total = 0
    changed_files = []
    for f in files:
        c = process_file(f)
        total += c
        if c:
            changed_files.append(str(f.relative_to(ROOT)))
            print('Fixed:', f.relative_to(ROOT))
    print('\nSummary: fixed', total, 'files')
    if changed_files:
        print('\nFiles changed:')
        for x in changed_files:
            print('-', x)

if __name__ == '__main__':
    main()
