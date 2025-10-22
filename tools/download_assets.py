#!/usr/bin/env python3
"""
Небольшой утилитный скрипт для обработки HTML/CSS/JS в репозитории,
сборки уникальных внешних URL-ов ассетов (assets.zyrosite.com, cdn.zyrosite.com и др.),
скачивания их в папку ./assets/ и замены ссылок в файлах на относительные.

Использование:
  python3 tools/download_assets.py --scan-only    # собрать список URL и оценить объём
  python3 tools/download_assets.py --download     # скачать файлы и создать маппинг
  python3 tools/download_assets.py --apply        # применить замену путей в файлах

Примечания:
 - Скрипт делает безопасные бэкапы файлов, изменяемых при --apply
 - Из-за объёма ассетов скачивание может занять время и место на диске
"""

import argparse
import os
import re
import sys
import hashlib
from urllib.parse import urlparse
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS_DIR = os.path.join(ROOT, "assets")
REPORT = os.path.join(ROOT, "assets_report.txt")

# regex: ищем внешние ссылки на картинки, шрифты и cdn.zyrosite
URL_RE = re.compile(r"https?://[^\s'\"<>)]+\.(?:png|jpg|jpeg|gif|webp|svg|woff2|woff|ttf|css|js)")
ZYRO_RE = re.compile(r"https?://(?:assets|cdn|cdn-ecommerce)\.zyrosite\.com/[^\s'\"<>]+")
GENERIC_URL_RE = re.compile(r"https?://[^\s'\"<>]+")

HEADERS = {"User-Agent": "asset-downloader/1.0 (+https://github.com)"}


def find_files(root):
    exts = ('.html', '.htm', '.css', '.js')
    for dirpath, dirnames, filenames in os.walk(root):
        # skip node_modules, .git, assets
        if any(p in dirpath for p in (".git", "node_modules", "/assets")):
            continue
        for fn in filenames:
            if fn.lower().endswith(exts):
                yield os.path.join(dirpath, fn)


def extract_urls_from_file(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        txt = f.read()
    urls = set()
    for m in GENERIC_URL_RE.finditer(txt):
        u = m.group(0)
        # only include common asset extensions
        if re.search(r"\.(?:png|jpg|jpeg|gif|webp|svg|woff2|woff|ttf|css|js)(?:\?|$)", u, re.I):
            urls.add(u.split('\')')[0] if '\\' in u else u)
    return urls


def scan_urls(root):
    urls = set()
    for path in find_files(root):
        try:
            found = extract_urls_from_file(path)
            if found:
                for u in found:
                    urls.add((u, path))
        except Exception as e:
            print(f"Error reading {path}: {e}")
    return urls


def scan_and_group(root):
    mapping = {}
    for path in find_files(root):
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            txt = f.read()
        for m in GENERIC_URL_RE.finditer(txt):
            u = m.group(0)
            if re.search(r"\.(?:png|jpg|jpeg|gif|webp|svg|woff2|woff|ttf|css|js)(?:\?|$)", u, re.I):
                mapping.setdefault(u, set()).add(path)
    return mapping


def guess_filename(url):
    parsed = urlparse(url)
    base = os.path.basename(parsed.path)
    if not base:
        base = hashlib.sha1(url.encode()).hexdigest()
    # append simple query-hash for uniqueness
    q = parsed.query
    if q:
        base += '-' + hashlib.sha1(q.encode()).hexdigest()[:8]
    return base


def download_url(url, dest):
    try:
        r = requests.get(url, headers=HEADERS, stream=True, timeout=15)
        r.raise_for_status()
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(1024 * 32):
                if chunk:
                    f.write(chunk)
        return os.path.getsize(dest)
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--scan-only', action='store_true')
    p.add_argument('--download', action='store_true')
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()

    mapping = scan_and_group(ROOT)
    print(f"Found {len(mapping)} unique asset URLs in repository")

    with open(REPORT, 'w', encoding='utf-8') as rep:
        rep.write(f"Found {len(mapping)} unique asset URLs\n\n")
        for url, files in sorted(mapping.items()):
            rep.write(url + '\n')
            for f in files:
                rep.write('  - ' + f + '\n')
            rep.write('\n')
    print(f"Wrote report to {REPORT}")

    if args.scan_only:
        return

    os.makedirs(ASSETS_DIR, exist_ok=True)
    manifests = []
    total = 0
    for url in mapping.keys():
        filename = guess_filename(url)
        dest = os.path.join('assets', filename)
        full_dest = os.path.join(ROOT, dest)
        size = 0
        if args.download:
            print(f"Downloading {url} -> {dest}")
            size = download_url(url, full_dest)
            print(f"  size: {size}")
        manifests.append((url, dest, size))
        total += size
    manifest_path = os.path.join(ROOT, 'assets_manifest.txt')
    with open(manifest_path, 'w', encoding='utf-8') as mf:
        for url, dest, size in manifests:
            mf.write(f"{url} -> {dest} ({size} bytes)\n")
    print(f"Wrote manifest to {manifest_path}; total downloaded bytes: {total}")

    if args.apply:
        # replace URLs in files with relative paths (simple replace)
        backup_dir = os.path.join(ROOT, 'backup_before_asset_replace')
        os.makedirs(backup_dir, exist_ok=True)
        for url, dest, size in manifests:
            for path in mapping[url]:
                # backup file once
                bkp = os.path.join(backup_dir, os.path.relpath(path, ROOT))
                os.makedirs(os.path.dirname(bkp), exist_ok=True)
                if not os.path.exists(bkp):
                    with open(path, 'rb') as src, open(bkp, 'wb') as dst:
                        dst.write(src.read())
                # replace in file
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    txt = f.read()
                txt2 = txt.replace(url, dest)
                if txt2 != txt:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(txt2)
                    print(f"Replaced {url} in {path}")

if __name__ == '__main__':
    main()
