#!/usr/bin/env python3
"""
Estimate sizes of external asset URLs found in repository using HEAD requests.
Produces a CSV-like report and domain breakdown.
"""
import os
import re
import sys
from urllib.parse import urlparse
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

GENERIC_URL_RE = re.compile(r"https?://[^\s'\"<>]+")
ASSET_EXT_RE = re.compile(r"\.(?:png|jpg|jpeg|gif|webp|svg|woff2|woff|ttf|mp4|webm|css|js)(?:\?|$)", re.I)

HEADERS = {"User-Agent": "asset-size-estimator/1.0"}
TIMEOUT = 10


def find_files(root):
    exts = ('.html', '.htm', '.css', '.js')
    for dirpath, dirnames, filenames in os.walk(root):
        if any(p in dirpath for p in ('.git', 'node_modules', os.path.join(root, 'assets'))):
            continue
        for fn in filenames:
            if fn.lower().endswith(exts):
                yield os.path.join(dirpath, fn)


def collect_urls(root):
    urls = set()
    for path in find_files(root):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                txt = f.read()
        except Exception:
            continue
        for m in GENERIC_URL_RE.finditer(txt):
            u = m.group(0)
            if ASSET_EXT_RE.search(u):
                # strip trailing characters like '"', ',' or ')'
                u = u.rstrip('\",)')
                urls.add(u)
    return urls


def head_size(url):
    try:
        r = requests.head(url, headers=HEADERS, allow_redirects=True, timeout=TIMEOUT)
        cl = r.headers.get('Content-Length')
        if cl:
            return int(cl)
        # fallback: try GET with Range 0-0
        r2 = requests.get(url, headers=HEADERS, stream=True, timeout=TIMEOUT)
        cl2 = r2.headers.get('Content-Length')
        if cl2:
            return int(cl2)
        return None
    except Exception as e:
        return None


def human(n):
    for unit in ['B','KB','MB','GB']:
        if n < 1024.0:
            return f"{n:3.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}TB"


def main():
    urls = collect_urls(ROOT)
    print(f"Collected {len(urls)} unique candidate asset URLs")
    domains = {}
    results = []
    i = 0
    for u in sorted(urls):
        i += 1
        print(f"[{i}/{len(urls)}] HEAD {u}")
        size = head_size(u)
        parsed = urlparse(u)
        dom = parsed.netloc
        domains.setdefault(dom, {'count':0, 'bytes':0})
        domains[dom]['count'] += 1
        if size:
            domains[dom]['bytes'] += size
            results.append((u, size))
        else:
            results.append((u, None))
    total_known = sum(s for u,s in results if s)
    known_count = sum(1 for u,s in results if s)
    unknown_count = sum(1 for u,s in results if not s)
    # write manifest
    out_manifest = os.path.join(ROOT, 'assets_size_manifest.txt')
    with open(out_manifest, 'w', encoding='utf-8') as f:
        f.write('url,bytes\n')
        for u,s in results:
            f.write(f'"{u}",{s if s else ""}\n')
    print('\nWrote size manifest to', out_manifest)
    print('\nSummary:')
    print('  total URLs:', len(urls))
    print('  known sizes:', known_count)
    print('  unknown sizes:', unknown_count)
    print('  total known bytes:', total_known, '(', human(total_known),')')
    print('\nTop domains by bytes:')
    dom_list = sorted(domains.items(), key=lambda kv: kv[1]['bytes'], reverse=True)
    for dom,info in dom_list[:20]:
        print(f"  {dom}: {info['count']} files, {info['bytes']} bytes ({human(info['bytes'])})")

if __name__ == '__main__':
    main()
