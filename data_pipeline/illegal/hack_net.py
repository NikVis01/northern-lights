"""
Northern Lights - Finansinspektionen (FI) Document Retrieval

Automates retrieval of regulatory documents from the Swedish Finansinspektionen
search portal using browser automation (Playwright) to handle ASP.NET ViewState.

Extracts portfolio companies from annual reports using Gemini AI.
"""

import json
import logging
import os
import re
import sys
import tempfile
import warnings
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse

import google.generativeai as genai
import requests
from dotenv import load_dotenv
from pdf2image import convert_from_path
from PIL import Image
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from pypdf import PdfReader, PdfWriter

# Suppress pypdf warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pypdf")
logging.getLogger("pypdf").setLevel(logging.ERROR)

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# Load environment variables
load_dotenv()

# Constants
SEARCH_URL = "https://finanscentralen.fi.se/search/Search.aspx"
ORG_NUMBER_FIELD_ID = "ctl00$main$txtOrganizationNumber"
SEARCH_BUTTON_ID = "ctl00$main$btnSearch"

# Timeouts (milliseconds)
FORM_LOAD_TIMEOUT = 30000
RESULTS_WAIT_TIMEOUT = 60000
LINK_WAIT_TIMEOUT = 30000
NETWORK_IDLE_TIMEOUT = 60000
ADDITIONAL_WAIT = 10000

# Document processing
MAX_PDF_PAGES = 25
MAX_PDF_PAGES_SEARCH = 50
MAX_IMAGE_PAGES = 10
PDF_DPI = 200
MAX_CHARS_TEXT = 80000
MAX_CHARS_HTML = 500000

# Portfolio keywords
PORTFOLIO_KEYWORDS = [
    "portfolio", "portfölj", "holdings", "ägda bolag", "investeringar",
    "investments", "företagsportfölj", "bolagsportfölj", "ägda företag",
    "major holdings", "stora innehav", "aktieinnehav", "shareholdings",
    "företagsinnehav", "bolagsinnehav", "ägda", "innehav", "andel"
]

# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        GEMINI_MODEL = genai.GenerativeModel("gemini-2.0-flash-exp")
    except:
        GEMINI_MODEL = genai.GenerativeModel("gemini-1.5-pro")
else:
    GEMINI_MODEL = None
    print("⚠️  Warning: GEMINI_API_KEY not set. Portfolio extraction will be disabled.", file=sys.stderr)


# ============================================================================
# Helper Functions
# ============================================================================

def detect_file_type(content: bytes, content_type: str = None) -> str:
    """Detect file type from content bytes (magic numbers)."""
    if content.startswith(b"PK\x03\x04") or content.startswith(b"PK\x05\x06"):
        return ".zip"
    elif content.startswith(b"%PDF"):
        return ".pdf"
    elif content.startswith((b"<!DOCTYPE", b"<html", b"<HTML")):
        return ".html"
    elif content_type:
        if "zip" in content_type.lower():
            return ".zip"
        elif "pdf" in content_type.lower():
            return ".pdf"
        elif "html" in content_type.lower():
            return ".html"
    return ".zip"


def normalize_url(href: str, base_url: str) -> str:
    """Convert relative URL to absolute."""
    if href.startswith("http"):
        return href
    elif href.startswith("/"):
        return urljoin(base_url, href)
    else:
        return urljoin(base_url, href)


def find_element_by_selectors(page, selectors: List[str]):
    """Try multiple selectors to find an element."""
    for selector in selectors:
        try:
            elem = page.query_selector(selector)
            if elem:
                return elem
        except:
            continue
    return None


# ============================================================================
# FI Portal Search
# ============================================================================

def extract_download_links(page, base_url: str) -> List[str]:
    """Extract all download links from the results page."""
    download_links = []
    
    try:
        page.wait_for_timeout(5000)
        
        try:
            page.wait_for_selector("a[href*='GetFile.aspx']", timeout=LINK_WAIT_TIMEOUT)
        except PlaywrightTimeoutError:
            page.wait_for_timeout(5000)
        
        all_links = page.query_selector_all("a")
        if not all_links:
            return []
        
        # Try multiple link patterns
        link_patterns = ["a[href*='GetFile.aspx']", "a[href*='GetFile']", "a[href*='fid=']"]
        
        for pattern in link_patterns:
            try:
                links = page.query_selector_all(pattern)
                for link in links:
                    href = link.get_attribute("href")
                    if href:
                        full_url = normalize_url(href, base_url)
                        if ("GetFile.aspx?fid=" in full_url or "GetFile?fid=" in full_url) and full_url not in download_links:
                            download_links.append(full_url)
            except:
                continue
        
        # Check all links for GetFile pattern
        for link in all_links:
            href = link.get_attribute("href")
            if href and "fid=" in href:
                full_url = normalize_url(href, base_url)
                if full_url not in download_links:
                    download_links.append(full_url)
    
    except Exception as e:
        print(f"⚠️  Warning: Error extracting links: {e}", file=sys.stderr)
    
    return download_links


def wait_for_results(page):
    """Wait for search results to load."""
    try:
        page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT)
        page.wait_for_timeout(ADDITIONAL_WAIT)
    except PlaywrightTimeoutError:
        page.wait_for_timeout(ADDITIONAL_WAIT)
    
    if "Search.aspx" in page.url:
        page.wait_for_timeout(ADDITIONAL_WAIT)


def debug_page_state(page):
    """Print debugging information about page state."""
    print(f"   Page title: {page.title()}", file=sys.stderr)
    print(f"   Current URL: {page.url}", file=sys.stderr)
    
    error_selectors = ["span.error", "div.error", ".error-message", ".alert", "[class*='error']"]
    for selector in error_selectors:
        try:
            errors = page.query_selector_all(selector)
            for elem in errors[:5]:
                error_text = elem.inner_text()
                if error_text.strip():
                    print(f"   Error/Message: {error_text[:200]}", file=sys.stderr)
        except:
            continue
    
    all_links = page.query_selector_all("a")
    print(f"   Total links on page: {len(all_links)}", file=sys.stderr)
    for i, link in enumerate(all_links[:15]):
        try:
            href = link.get_attribute("href")
            text = link.inner_text()[:50]
            if href:
                print(f"   Link {i+1}: '{text}' -> {href[:100]}", file=sys.stderr)
        except:
            continue


def search_fi_documents(organization_number: str) -> List[str]:
    """Search FI portal and extract download links."""
    base_url = f"{urlparse(SEARCH_URL).scheme}://{urlparse(SEARCH_URL).netloc}/search/"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        
        try:
            print(f"🌐 Navigating to: {SEARCH_URL}", file=sys.stderr)
            page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
            
            print("⏳ Waiting for form to load...", file=sys.stderr)
            try:
                page.wait_for_selector("input[type='text']", timeout=FORM_LOAD_TIMEOUT)
            except PlaywrightTimeoutError:
                page.wait_for_timeout(3000)
            
            # Find organization number field
            org_field_selectors = [
                f"#{ORG_NUMBER_FIELD_ID.replace('$', '_')}",
                f"#{ORG_NUMBER_FIELD_ID}",
                f"input[name='{ORG_NUMBER_FIELD_ID}']",
                f"input[id*='txtOrganizationNumber']",
            ]
            org_field = find_element_by_selectors(page, org_field_selectors) or page.query_selector("input[type='text']")
            
            if not org_field:
                raise Exception("Could not find organization number input field")
            
            print(f"📝 Entering organization number: {organization_number}", file=sys.stderr)
            org_field.fill(organization_number)
            
            # Find and click search button
            search_button_selectors = [
                f"#{SEARCH_BUTTON_ID.replace('$', '_')}",
                f"#{SEARCH_BUTTON_ID}",
                f"input[name='{SEARCH_BUTTON_ID}']",
                f"input[type='submit'][value*='Sök']",
                f"input[type='submit'][id*='btnSearch']",
                "input[type='submit']",
            ]
            search_button = find_element_by_selectors(page, search_button_selectors)
            
            if not search_button:
                raise Exception("Could not find search button")
            
            print("🔍 Submitting search form...", file=sys.stderr)
            page.click(selector=search_button_selectors[0])
            
            print("⏳ Waiting for results...", file=sys.stderr)
            wait_for_results(page)
            
            print("🔗 Extracting download links...", file=sys.stderr)
            download_links = extract_download_links(page, base_url)
            
            if not download_links:
                print("⚠️  No download links found on first attempt. Waiting longer and retrying...", file=sys.stderr)
                page.wait_for_timeout(15000)
                download_links = extract_download_links(page, base_url)
            
            if not download_links:
                print("⚠️  No download links found. Debugging page state...", file=sys.stderr)
                debug_page_state(page)
        
        except Exception as e:
            print(f"❌ Error during search: {e}", file=sys.stderr)
            raise
        finally:
            browser.close()
    
    return download_links


# ============================================================================
# File Download & Extraction
# ============================================================================

def download_file(url: str, output_dir: Path) -> Path:
    """Download a file from URL to temporary directory."""
    print(f"📥 Downloading: {url}", file=sys.stderr)
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    
    content_type = response.headers.get("Content-Type", "")
    content_disposition = response.headers.get("Content-Disposition", "")
    
    filename = None
    if content_disposition:
        match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^\s;]+)', content_disposition)
        if match:
            filename = match.group(1).strip('"\'')
    
    chunks = []
    first_chunk = b""
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            chunks.append(chunk)
            if not first_chunk and len(chunk) >= 4:
                first_chunk = chunk[:4]
    
    file_content = b"".join(chunks)
    
    if first_chunk:
        ext = detect_file_type(first_chunk, content_type)
    elif filename:
        ext = Path(filename).suffix or ".zip"
    else:
        ext = detect_file_type(file_content[:1024], content_type)
    
    print(f"🔍 Detected file type: {ext}", file=sys.stderr)
    
    file_path = output_dir / f"document{ext}"
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    print(f"✅ Downloaded to: {file_path} ({len(file_content)} bytes)", file=sys.stderr)
    return file_path


def unzip_if_needed(file_path: Path) -> List[Path]:
    """If file is a ZIP, extract it and return list of extracted files."""
    is_zip = False
    try:
        with open(file_path, "rb") as f:
            is_zip = f.read(4).startswith((b"PK\x03\x04", b"PK\x05\x06"))
    except:
        pass
    
    if file_path.suffix.lower() == ".zip" or is_zip:
        print(f"📦 Extracting ZIP archive...", file=sys.stderr)
        extract_dir = file_path.parent / file_path.stem
        extract_dir.mkdir(exist_ok=True)
        
        try:
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                file_list = zip_ref.namelist()
                print(f"📋 ZIP contains {len(file_list)} file(s)", file=sys.stderr)
                zip_ref.extractall(extract_dir)
                
                extracted_files = (
                    list(extract_dir.rglob("*.pdf")) +
                    list(extract_dir.rglob("*.html")) +
                    list(extract_dir.rglob("*.xhtml")) +
                    list(extract_dir.rglob("*.htm"))
                )
                
                # Check root level explicitly
                for pattern in ["*.pdf", "*.html", "*.xhtml", "*.htm"]:
                    for f in extract_dir.glob(pattern):
                        if f.is_file() and f not in extracted_files:
                            extracted_files.append(f)
                
                if extracted_files:
                    pdf_count = sum(1 for f in extracted_files if f.suffix.lower() == ".pdf")
                    html_count = sum(1 for f in extracted_files if f.suffix.lower() in [".html", ".xhtml", ".htm"])
                    print(f"📄 Found {len(extracted_files)} document file(s): {pdf_count} PDF(s), {html_count} HTML/XHTML(s)", file=sys.stderr)
                else:
                    all_files = [f for f in extract_dir.rglob("*") if f.is_file()]
                    print(f"⚠️  No PDF/HTML/XHTML files found in ZIP, but found {len(all_files)} other file(s)", file=sys.stderr)
        except zipfile.BadZipFile:
            return [file_path]
        except Exception as e:
            print(f"⚠️  Error extracting ZIP: {e}", file=sys.stderr)
            return [file_path]
        
        return extracted_files if extracted_files else [file_path]
    
    return [file_path]


# ============================================================================
# PDF Processing
# ============================================================================

def extract_pdf_pages(pdf_path: Path, num_pages: int = MAX_PDF_PAGES) -> Path:
    """Extract first N pages from PDF."""
    print(f"📄 Extracting first {num_pages} pages from PDF...", file=sys.stderr)
    
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        reader = PdfReader(str(pdf_path), strict=False)
    
    total_pages = len(reader.pages)
    pages_to_extract = min(num_pages, total_pages)
    
    writer = PdfWriter()
    for i in range(pages_to_extract):
        writer.add_page(reader.pages[i])
    
    output_path = pdf_path.parent / f"{pdf_path.stem}_first_{pages_to_extract}_pages.pdf"
    with open(output_path, "wb") as f:
        writer.write(f)
    
    print(f"✅ Extracted {pages_to_extract} pages (of {total_pages} total)", file=sys.stderr)
    return output_path


def search_pdf_for_portfolio_section(pdf_path: Path, max_pages: int = MAX_PDF_PAGES_SEARCH) -> Optional[int]:
    """Search through PDF pages to find portfolio section. Returns page number (0-indexed) or None."""
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            reader = PdfReader(str(pdf_path), strict=False)
        
        pages_to_check = min(max_pages, len(reader.pages))
        
        # Check early pages first
        for i in range(min(20, pages_to_check)):
            try:
                page = reader.pages[i]
                text = page.extract_text()
                if text:
                    text_lower = text.lower()
                    matches = sum(1 for keyword in PORTFOLIO_KEYWORDS if keyword in text_lower)
                    company_percentage = re.search(
                        r'[A-ZÅÄÖ][a-zåäö\s]+(?:AB|AB publ|Group)[\s:]*\d+[.,]?\d*\s*%',
                        text, re.IGNORECASE
                    )
                    
                    if matches >= 1 or company_percentage:
                        print(f"✅ Found portfolio section on page {i+1}", file=sys.stderr)
                        return i
            except:
                continue
        
        # Check rest of pages
        for i in range(20, pages_to_check):
            try:
                page = reader.pages[i]
                text = page.extract_text()
                if text:
                    text_lower = text.lower()
                    matches = sum(1 for keyword in PORTFOLIO_KEYWORDS if keyword in text_lower)
                    if matches >= 2:
                        print(f"✅ Found portfolio section on page {i+1}", file=sys.stderr)
                        return i
            except:
                continue
        
        return None
    except Exception as e:
        print(f"⚠️  Error searching PDF: {e}", file=sys.stderr)
        return None


def extract_text_from_pdf(pdf_path: Path, debug: bool = False) -> str:
    """Extract text from PDF (first 10 pages, or more if needed)."""
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            reader = PdfReader(str(pdf_path), strict=False)
        
        text_parts = []
        num_pages = min(10, len(reader.pages))
        
        for i in range(num_pages):
            try:
                page = reader.pages[i]
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(f"--- Page {i+1} ---\n{text}\n")
            except Exception as e:
                print(f"⚠️  Error extracting page {i+1}: {e}", file=sys.stderr)
                continue
        
        if not text_parts:
            print("⚠️  No text extracted from PDF. Document may be image-based.", file=sys.stderr)
            return ""
        
        full_text = "\n".join(text_parts)
        portfolio_text = find_portfolio_section(full_text)
        
        if len(portfolio_text) < len(full_text) * 0.5:
            print(f"✅ Using portfolio-specific section ({len(portfolio_text)} chars vs {len(full_text)} total)", file=sys.stderr)
            return portfolio_text
        
        return full_text
    except Exception as e:
        print(f"⚠️  Error reading PDF: {e}", file=sys.stderr)
        return ""
if len(pdf_files) > 0:
                        with warnings.catch_warnings():
                            warnings.filterwarnings("ignore")
                            reader = PdfReader(str(pdf_path), strict=False)
                        if len(reader.pages) > 10:
                            print(f"📄 Document has {len(reader.pages)} pages, trying first 20 pages...")
                            extracted_pdf = extract_pdf_pages(pdf_path, num_pages=20)
                            # Try images again with more pages
                            images = pdf_pages_to_images(extracted_pdf, max_pages=20, dpi=200)
                            if images:
                                portfolio = extract_portfolio_companies_from_images(images)
                            else:
                                document_text = extract_text_from_pdf(extracted_pdf, debug=True)
                                if document_text:
                                    portfolio = extract_portfolio_companies(document_text)
                                else:
                                    portfolio = []
                        else:
                            portfolio = []
                    else:
                        portfolio = []
            
            # If still no portfolio found, return empty list
            if not portfolio:
                portfolio = []
            
            return portfolio
        
        except Exception as e:
            print(f"❌ Error processing document: {e}")
            return []


def pdf_pages_to_images(pdf_path: Path, max_pages: int = MAX_IMAGE_PAGES, dpi: int = PDF_DPI) -> List[Image.Image]:
    """Convert PDF pages to images."""
    if not PDF2IMAGE_AVAILABLE:
        print("⚠️  pdf2image not available, falling back to text extraction", file=sys.stderr)
        return []
    
    try:
        print(f"🖼️  Converting PDF pages to images (DPI: {dpi})...", file=sys.stderr)
        images = convert_from_path(
            str(pdf_path),
            dpi=dpi,
            first_page=1,
            last_page=max_pages,
            fmt='PNG'
        )
        print(f"✅ Converted {len(images)} page(s) to images", file=sys.stderr)
        return images
    except Exception as e:
        print(f"⚠️  Error converting PDF to images: {e}", file=sys.stderr)
        return []


# ============================================================================
# HTML Processing
# ============================================================================

def extract_text_from_html(html_path: Path, debug: bool = False) -> str:
    """Extract text from HTML/XHTML file."""
    if not BS4_AVAILABLE:
        print("⚠️  BeautifulSoup4 not installed. Install with: pip install beautifulsoup4", file=sys.stderr)
        try:
            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            text = re.sub(r'<[^>]+>', ' ', content)
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except Exception as e:
            print(f"⚠️  Error extracting text from HTML: {e}", file=sys.stderr)
            return ""
    
    try:
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
        
        try:
            soup = BeautifulSoup(html_content, "lxml")
        except:
            soup = BeautifulSoup(html_content, "html.parser")
        
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        text_parts = []
        
        # Extract tables
        tables = soup.find_all("table")
        if tables:
            print(f"📊 Found {len(tables)} table(s) in HTML/XHTML", file=sys.stderr)
            for i, table in enumerate(tables):
                table_text = []
                for row in table.find_all("tr"):
                    cells = row.find_all(["td", "th"])
                    if cells:
                        row_text = " | ".join([cell.get_text(strip=True) for cell in cells])
                        if row_text.strip():
                            table_text.append(row_text)
                if table_text:
                    text_parts.append(f"\n--- Table {i+1} ---\n" + "\n".join(table_text) + "\n")
        
        # Extract divs with portfolio keywords
        portfolio_keywords = ["portfolio", "portfölj", "holding", "ägda", "investering", "bolag"]
        for div in soup.find_all(["div", "section"]):
            div_id = div.get("id", "").lower()
            div_class = " ".join(div.get("class", [])).lower()
            div_text = div.get_text(separator=" ", strip=True)
            
            if any(keyword in (div_id + " " + div_class) for keyword in portfolio_keywords) or len(div_text) > 100:
                if div_text.strip() and len(div_text) < 50000:
                    text_parts.append(div_text)
        
        # Get body text
        body = soup.find("body")
        if body:
            body_text = body.get_text(separator="\n", strip=True)
            meaningful_lines = [line for line in body_text.split("\n") if len(line.strip()) > 10]
            if meaningful_lines:
                text_parts.append("\n".join(meaningful_lines))
        
        # Fallback to full text
        if not text_parts or sum(len(part) for part in text_parts) < 1000:
            print("⚠️  Structured extraction didn't yield much, using full text", file=sys.stderr)
            text = soup.get_text(separator="\n", strip=True)
            lines = text.split("\n")
            filtered_lines = [
                line.strip() for line in lines
                if len(line.strip()) > 10 and not line.strip().replace(" ", "").replace("-", "").isdigit()
            ]
            text_parts = ["\n".join(filtered_lines)]
        
        full_text = "\n\n".join(text_parts)
        
        if debug:
            print(f"\n📄 Sample of extracted HTML/XHTML text (first 1000 chars):", file=sys.stderr)
            print("-" * 60, file=sys.stderr)
            print(full_text[:1000], file=sys.stderr)
            print("-" * 60, file=sys.stderr)
            print(f"📊 Total extracted: {len(full_text)} characters", file=sys.stderr)
        
        return full_text
    except Exception as e:
        print(f"⚠️  Error reading HTML/XHTML: {e}", file=sys.stderr)
        return ""


# ============================================================================
# Portfolio Section Detection
# ============================================================================

def find_portfolio_section(text: str) -> str:
    """Find the portfolio/holdings section in the document text."""
    text_lower = text.lower()
    lines = text.split("\n")
    
    # Find lines with portfolio keywords
    portfolio_line_indices = [
        i for i, line in enumerate(lines)
        if any(keyword in line.lower() for keyword in PORTFOLIO_KEYWORDS)
    ]
    
    if portfolio_line_indices:
        start_idx = max(0, min(portfolio_line_indices) - 50)
        end_idx = min(len(lines), max(portfolio_line_indices) + 200)
        portfolio_section = "\n".join(lines[start_idx:end_idx])
        
        if re.search(r'\d+[.,]\d*\s*%|\d+\s*%', portfolio_section):
            print(f"✅ Found portfolio section with percentages ({len(portfolio_section)} chars)", file=sys.stderr)
            return portfolio_section
        else:
            print(f"✅ Found portfolio-related section ({len(portfolio_section)} chars)", file=sys.stderr)
            return portfolio_section
    
    # Look for company-percentage patterns
    company_percentage_pattern = r'[A-ZÅÄÖ][a-zåäö\s]+(?:AB|AB publ|AB \(publ\)|Group|Holdings)[\s:]*\d+[.,]?\d*\s*%'
    if re.search(company_percentage_pattern, text, re.IGNORECASE):
        print(f"✅ Found company-percentage patterns, using relevant section", file=sys.stderr)
        matches = list(re.finditer(company_percentage_pattern, text, re.IGNORECASE))
        if matches:
            first_match = matches[0]
            start_pos = max(0, first_match.start() - 5000)
            end_pos = min(len(text), matches[-1].end() + 10000)
            return text[start_pos:end_pos]
    
    print("⚠️  No specific portfolio section found, using full document", file=sys.stderr)
    return text


# ============================================================================
# Gemini Portfolio Extraction
# ============================================================================

PORTFOLIO_EXTRACTION_PROMPT = """You are analyzing a Swedish annual report or financial document. 
Extract ONLY companies that are actually OWNED by the company whose report this is.

Look specifically for sections titled:
- "Portfolio" / "Portfölj"
- "Holdings" / "Innehav" 
- "Investments" / "Investeringar"
- "Owned Companies" / "Ägda bolag"
- "Major Holdings" / "Stora innehav"
- "Shareholdings" / "Aktieinnehav"
- Tables or lists of companies with ownership percentages

Return a JSON array where each object contains:
- "company_name": The full legal name of the portfolio company (e.g., "Ericsson AB", "Atlas Copco AB")
- "ownership_percentage": Percentage owned (as a number, e.g., 22.5 for 22.5%), or null if not mentioned

CRITICAL RULES:
- ONLY extract companies that are clearly OWNED by the company in this report
- DO NOT extract companies that are just mentioned, customers, suppliers, or competitors
- DO NOT extract companies from sections about "Related Parties" unless they are clearly owned
- Companies must be in portfolio/holdings/investments sections - not just mentioned elsewhere
- If ownership percentage is missing, only include if clearly in a portfolio/holdings table
- Company names often end with "AB", "AB publ", "AB (publ)", etc.
- Include both direct and indirect holdings
- If you see a table with company names and percentages, extract all rows from that table
- For HTML/XHTML documents, pay special attention to structured data, tables, and lists

IT IS PERFECTLY OKAY IF THE COMPANY OWNS NOTHING:
- If no portfolio companies are found, return an empty array []
- Do not make up or guess companies just to have results
- Only extract companies that are clearly and explicitly listed as owned/invested in

If no portfolio companies are found, return an empty array [].
"""


def parse_gemini_response(response_text: str) -> List[Dict[str, Any]]:
    """Parse Gemini JSON response and validate portfolio items."""
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
    
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        return []
    
    # Ensure it's a list
    if isinstance(result, dict):
        portfolio = result.get("portfolio_companies") or result.get("companies") or result.get("holdings") or []
        if not isinstance(portfolio, list):
            portfolio = [result] if not isinstance(result, list) else []
    elif isinstance(result, list):
        portfolio = result
    else:
        portfolio = []
    
    # Validate portfolio items
    validated_portfolio = []
    for item in portfolio:
        if isinstance(item, dict) and "company_name" in item:
            validated_portfolio.append({
                "company_name": item.get("company_name"),
                "ownership_percentage": item.get("ownership_percentage")
            })
    
    return validated_portfolio


def extract_portfolio_companies_from_images(images: List[Image.Image]) -> List[Dict[str, Any]]:
    """Use Gemini Vision to extract portfolio companies from PDF page images."""
    if not GEMINI_MODEL:
        return []
    
    if not images:
        return []
    
    prompt = PORTFOLIO_EXTRACTION_PROMPT + "\n\nPay special attention to TABLES - extract every row that contains a company name and ownership information.\nRead tables carefully, including multi-column tables."
    
    try:
        content_parts = [prompt]
        for i, img in enumerate(images):
            content_parts.append(f"Page {i+1}:")
            content_parts.append(img)
        
        response = GEMINI_MODEL.generate_content(
            content_parts,
            generation_config={"response_mime_type": "application/json"}
        )
        
        return parse_gemini_response(response.text.strip())
    except Exception:
        return []


def extract_portfolio_companies(document_text: str, is_html: bool = False) -> List[Dict[str, Any]]:
    """Use Gemini to extract portfolio companies from document text."""
    if not GEMINI_MODEL or not document_text or not document_text.strip():
        return []
    
    max_chars = MAX_CHARS_HTML if is_html else MAX_CHARS_TEXT
    
    # If document is longer, try to include more relevant content
    if len(document_text) > max_chars:
        portfolio_section = find_portfolio_section(document_text)
        if portfolio_section and len(portfolio_section) > 1000 and len(portfolio_section) < len(document_text) * 0.9:
            section_start = document_text.find(portfolio_section[:200])
            if section_start > 0:
                context_before = max(0, section_start - 50000)
                context_after = min(len(document_text), section_start + len(portfolio_section) + 200000)
                document_text = document_text[context_before:context_after]
                print(f"📄 Using portfolio section with context: {len(document_text)} chars", file=sys.stderr)
            else:
                document_text = portfolio_section[:max_chars]
                print(f"📄 Using portfolio section: {len(document_text)} chars", file=sys.stderr)
        else:
            document_text = document_text[:max_chars]
            print(f"📄 Using first {max_chars} chars of document", file=sys.stderr)
    else:
        print(f"📄 Using full document: {len(document_text)} chars", file=sys.stderr)
    
    prompt = PORTFOLIO_EXTRACTION_PROMPT + "\n\nDocument content:\n" + document_text
    
    try:
        response = GEMINI_MODEL.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return parse_gemini_response(response.text.strip())
    except Exception:
        return []


# ============================================================================
# Main Document Processing
# ============================================================================

def process_pdf_document(pdf_path: Path, temp_path: Path) -> List[Dict[str, Any]]:
    """Process a PDF document to extract portfolio companies."""
    # Try to find portfolio section first
    portfolio_page = search_pdf_for_portfolio_section(pdf_path, max_pages=MAX_PDF_PAGES_SEARCH)
    
    if portfolio_page is not None:
        # Extract pages around the portfolio section
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            reader = PdfReader(str(pdf_path), strict=False)
        total_pages = len(reader.pages)
        start_page = max(0, portfolio_page - 3)
        end_page = min(total_pages, portfolio_page + 15)
        
        print(f"📄 Extracting pages {start_page+1} to {end_page} (portfolio section found on page {portfolio_page+1})", file=sys.stderr)
        
        writer = PdfWriter()
        for i in range(start_page, end_page):
            writer.add_page(reader.pages[i])
        
        extracted_pdf_path = temp_path / f"{pdf_path.stem}_portfolio_section.pdf"
        with open(extracted_pdf_path, "wb") as f:
            writer.write(f)
        extracted_pdf = extracted_pdf_path
    else:
        print("📄 Portfolio section not found via keyword search, extracting first 25 pages...", file=sys.stderr)
        extracted_pdf = extract_pdf_pages(pdf_path, num_pages=MAX_PDF_PAGES)
    
    # Try image-based extraction first
    print("🖼️  Attempting image-based extraction (preserves table structure)...", file=sys.stderr)
    images = pdf_pages_to_images(extracted_pdf, max_pages=MAX_IMAGE_PAGES, dpi=PDF_DPI)
    
    portfolio = None
    if images:
        portfolio = extract_portfolio_companies_from_images(images)
    
    # Fallback to text extraction
    if not portfolio:
        print("📝 Falling back to text extraction...", file=sys.stderr)
        document_text = extract_text_from_pdf(extracted_pdf, debug=True)
        
        if document_text:
            portfolio = extract_portfolio_companies(document_text)
        else:
            # Try extracting more pages
            print("💡 Trying to extract more pages...", file=sys.stderr)
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                reader = PdfReader(str(pdf_path), strict=False)
            if len(reader.pages) > 10:
                print(f"📄 Document has {len(reader.pages)} pages, trying first 20 pages...", file=sys.stderr)
                extracted_pdf = extract_pdf_pages(pdf_path, num_pages=20)
                images = pdf_pages_to_images(extracted_pdf, max_pages=20, dpi=PDF_DPI)
                if images:
                    portfolio = extract_portfolio_companies_from_images(images)
                else:
                    document_text = extract_text_from_pdf(extracted_pdf, debug=True)
                    portfolio = extract_portfolio_companies(document_text) if document_text else []
            else:
                portfolio = []
    
    return portfolio or []


def process_html_document(html_path: Path) -> List[Dict[str, Any]]:
    """Process an HTML/XHTML document to extract portfolio companies."""
    document_text = extract_text_from_html(html_path, debug=True)
    if not document_text:
        print("⚠️  Could not extract text from HTML", file=sys.stderr)
        return []
    
    # Try to find portfolio section first
    portfolio_text = find_portfolio_section(document_text)
    if portfolio_text and len(portfolio_text) < len(document_text) * 0.8:
        print(f"✅ Found portfolio section in HTML ({len(portfolio_text)} chars)", file=sys.stderr)
        document_text = portfolio_text
    else:
        print(f"📄 Using full HTML document ({len(document_text)} chars)", file=sys.stderr)
    
    print("🧠 Analyzing HTML content with Gemini...", file=sys.stderr)
    return extract_portfolio_companies(document_text, is_html=True)


def process_document(url: str, organization_number: str) -> List[Dict[str, Any]]:
    """Download, extract, and analyze a document to find portfolio companies."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            file_path = download_file(url, temp_path)
            extracted_files = unzip_if_needed(file_path)
            
            pdf_files = [f for f in extracted_files if f.suffix.lower() == ".pdf" and f.is_file()]
            html_files = [f for f in extracted_files if f.suffix.lower() in [".html", ".xhtml", ".htm"] and f.is_file()]
            
            if not pdf_files and not html_files:
                print("⚠️  No PDF or HTML files found in document", file=sys.stderr)
                return []
            
            # Prefer PDF, fallback to HTML
            if pdf_files:
                print(f"📄 Processing PDF: {pdf_files[0].name}", file=sys.stderr)
                return process_pdf_document(pdf_files[0], temp_path)
            else:
                print(f"🌐 Processing HTML: {html_files[0].name}", file=sys.stderr)
                return process_html_document(html_files[0])
        
        except Exception as e:
            print(f"❌ Error processing document: {e}", file=sys.stderr)
            return []


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    org_number = sys.argv[1] if len(sys.argv) > 1 else "556043-4200"
    
    try:
        links = search_fi_documents(org_number)
        
        if links:
            portfolio = process_document(links[0], org_number)
            print(json.dumps(portfolio, ensure_ascii=False))
        else:
            print("[]")
    
    except Exception as e:
        print("[]", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
