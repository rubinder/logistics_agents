"""Render Rob_Randhawa_Resume.html to a print-ready 2-page PDF.

Usage:
    python resume/render.py

Requires: playwright (`pip install playwright`) plus a Chromium build. The
resume uses Carlito, a metric-compatible substitute for Calibri
(`apt-get install fonts-crosextra-carlito`), so the layout matches the
Word-exported original.
"""
import os
import pathlib

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
SRC = (HERE / "Rob_Randhawa_Resume.html").as_uri()
OUT = str(HERE / "Rob_Randhawa_Resume.pdf")

# Allow overriding the browser binary (e.g. a preinstalled Chromium).
EXECUTABLE = os.environ.get("CHROMIUM_PATH")

with sync_playwright() as p:
    launch_kwargs = {"executable_path": EXECUTABLE} if EXECUTABLE else {}
    browser = p.chromium.launch(**launch_kwargs)
    page = browser.new_page()
    page.goto(SRC, wait_until="networkidle")
    page.pdf(path=OUT, prefer_css_page_size=True, print_background=True)
    browser.close()

print(f"Rendered {OUT}")
