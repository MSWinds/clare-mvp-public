import os
import asyncio
from playwright.async_api import async_playwright
import subprocess

notebook_dir = "data/labs"
html_dir = os.path.join(notebook_dir, "html")
pdf_dir = os.path.join(notebook_dir, "pdfs")

os.makedirs(html_dir, exist_ok=True)
os.makedirs(pdf_dir, exist_ok=True)

# Step 1: Convert .ipynb to .html
for file in os.listdir(notebook_dir):
    if file.endswith(".ipynb"):
        ipynb_path = os.path.join(notebook_dir, file)
        subprocess.run([
            "jupyter", "nbconvert", "--to", "html", ipynb_path,
            "--output-dir", html_dir
        ])
        print(f"Converted to HTML: {file}")

# Step 2: Convert .html to .pdf using Playwright
async def html_to_pdf():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()

        for file in os.listdir(html_dir):
            if file.endswith(".html"):
                html_path = os.path.join(html_dir, file)
                pdf_path = os.path.join(pdf_dir, file.replace(".html", ".pdf"))
                page = await context.new_page()
                await page.goto(f"file://{os.path.abspath(html_path)}")
                await page.pdf(path=pdf_path, format="A4")
                print(f"Saved PDF: {pdf_path}")

        await browser.close()

asyncio.run(html_to_pdf())
