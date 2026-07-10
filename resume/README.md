# Resume

Source and print-ready build of Rob Randhawa's resume.

- `Rob_Randhawa_Resume.html` — the editable source (single file, inline CSS).
- `Rob_Randhawa_Resume.pdf` — the rendered 2-page US-Letter output.
- `render.py` — regenerates the PDF from the HTML.

## Regenerate the PDF

```bash
apt-get install -y fonts-crosextra-carlito   # Calibri-metric font
pip install playwright
CHROMIUM_PATH=/path/to/chromium python resume/render.py
```

The layout is tuned to fit exactly two pages. If you add content, re-render
and confirm the page count stays at 2.
