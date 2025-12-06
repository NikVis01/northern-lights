"""
Northern Lights - Finansinspektionen (FI) Document Retrieval

Automates retrieval of regulatory documents from the Swedish Finansinspektionen
search portal using browser automation (Playwright) to handle ASP.NET ViewState.

Extracts portfolio companies from annual reports using Gemini AI.
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from urllib.parse import urljoin, urlparse
import sys
import os
import requests
import zipfile
import tempfile
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from pypdf import PdfReader, PdfWriter
from PIL import Image
import io

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


# Load environment variables
load_dotenv()

# Constants
SEARCH_URL = "https://finanscentralen.fi.se/search/Search.aspx"
ORGANIZATION_NUMBER = "556043-4200"

# Field IDs (ASP.NET uses $ for nested controls)
ORG_NUMBER_FIELD_ID = "ctl00$main$txtOrganizationNumber"
SEARCH_BUTTON_ID = "ctl00$main$btnSearch"

# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Try gemini-2.0-flash-exp, fallback to gemini-1.5-pro
    try:
        GEMINI_MODEL = genai.GenerativeModel("gemini-2.0-flash-exp")
    except:
        GEMINI_MODEL = genai.GenerativeModel("gemini-1.5-pro")
else:
    GEMINI_MODEL = None
    print("⚠️  Warning: GEMINI_API_KEY not set. Portfolio extraction will be disabled.")


def extract_download_links(page, base_url: str) -> List[str]:
    """
    Extract all download links from the results page.
    Links contain the pattern 'GetFile.aspx?fid=...'
    """
    download_links = []
    
    try:
        # Wait for results to load (look for file links or results table)
        # Use a more lenient wait - just wait for any content
        try:
            page.wait_for_selector("a[href*='GetFile.aspx']", timeout=20000)
        except PlaywrightTimeoutError:
            # If no links found, wait a bit more and check for any links
            page.wait_for_timeout(3000)
            # Check if page has any links at all
            all_links = page.query_selector_all("a")
            if not all_links:
                print("⚠️  No links found on page")
                return []
        
        # Find all links containing 'GetFile.aspx'
        links = page.query_selector_all("a[href*='GetFile.aspx']")
        
        for link in links:
            href = link.get_attribute("href")
            if href:
                # Convert relative URLs to absolute
                if href.startswith("/"):
                    full_url = urljoin(base_url, href)
                elif href.startswith("http"):
                    full_url = href
                else:
                    # Relative path
                    full_url = urljoin(base_url, href)
                
                if "GetFile.aspx?fid=" in full_url:
                    download_links.append(full_url)
        
        # Also check for links in tables or other containers
        # Some ASP.NET pages might render links differently
        all_links = page.query_selector_all("a")
        for link in all_links:
            href = link.get_attribute("href")
            if href and "GetFile.aspx?fid=" in href:
                full_url = urljoin(base_url, href) if not href.startswith("http") else href
                if full_url not in download_links:
                    download_links.append(full_url)
    
    except PlaywrightTimeoutError:
        print("⚠️  Warning: Timeout waiting for results. Page may not have loaded correctly.")
    
    return download_links


def search_fi_documents(organization_number: str) -> List[str]:
    """
    Main function to search FI portal and extract download links.
    
    Args:
        organization_number: Swedish organization number (e.g., "556043-4200")
    
    Returns:
        List of full URLs to downloadable documents
    """
    download_links = []
    base_url = f"{urlparse(SEARCH_URL).scheme}://{urlparse(SEARCH_URL).netloc}/search/"
    
    with sync_playwright() as p:
        # Launch browser (headless=False for debugging, set to True for production)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        try:
            print(f"🌐 Navigating to: {SEARCH_URL}")
            page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for the form to be ready - try multiple approaches
            print("⏳ Waiting for form to load...")
            try:
                # Wait for any input field to appear (more lenient)
                page.wait_for_selector("input[type='text']", timeout=30000)
            except PlaywrightTimeoutError:
                # If that fails, wait a bit and continue anyway
                page.wait_for_timeout(3000)
            
            # Fill in organization number
            # ASP.NET uses $ in IDs, but in DOM they're often _ or different
            # Try multiple selector strategies
            org_field_selectors = [
                f"#{ORG_NUMBER_FIELD_ID.replace('$', '_')}",  # $ -> _
                f"#{ORG_NUMBER_FIELD_ID}",  # Original with $
                f"input[name='{ORG_NUMBER_FIELD_ID}']",  # By name attribute
                f"input[id*='txtOrganizationNumber']",  # Partial ID match
            ]
            
            org_field = None
            for selector in org_field_selectors:
                try:
                    org_field = page.query_selector(selector)
                    if org_field:
                        break
                except:
                    continue
            
            if not org_field:
                # Fallback: find by label or placeholder text
                org_field = page.query_selector("input[type='text']")
            
            if not org_field:
                raise Exception("Could not find organization number input field")
            
            print(f"📝 Entering organization number: {organization_number}")
            org_field.fill(organization_number)
            
            # Find and click search button
            search_button_selectors = [
                f"#{SEARCH_BUTTON_ID.replace('$', '_')}",
                f"#{SEARCH_BUTTON_ID}",
                f"input[name='{SEARCH_BUTTON_ID}']",
                f"input[type='submit'][value*='Sök']",  # Swedish "Search"
                f"input[type='submit'][id*='btnSearch']",
                "input[type='submit']",  # Last resort
            ]
            
            search_button = None
            for selector in search_button_selectors:
                try:
                    search_button = page.query_selector(selector)
                    if search_button:
                        break
                except:
                    continue
            
            if not search_button:
                raise Exception("Could not find search button")
            
            print("🔍 Submitting search form...")
            # Playwright automatically handles ViewState tokens
            page.click(selector=search_button_selectors[0] if search_button else "input[type='submit']")
            
            # Wait for results page to load
            print("⏳ Waiting for results...")
            try:
                # Wait for page to be interactive
                page.wait_for_load_state("domcontentloaded", timeout=30000)
                # Additional wait for dynamic content (ASP.NET can be slow)
                page.wait_for_timeout(5000)
                # Try to wait for network idle, but don't fail if it times out
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except PlaywrightTimeoutError:
                    print("⚠️  Warning: Network idle timeout, but continuing...")
            except PlaywrightTimeoutError:
                print("⚠️  Warning: Page load timeout, but continuing...")
            
            # Extract download links
            print("🔗 Extracting download links...")
            download_links = extract_download_links(page, base_url)
            
        except Exception as e:
            print(f"❌ Error during search: {e}", file=sys.stderr)
            raise
        
        finally:
            browser.close()
    
    return download_links


def detect_file_type(content: bytes, content_type: str = None) -> str:
    """
    Detect file type from content bytes (magic numbers).
    Returns file extension.
    """
    # Check magic numbers
    if content.startswith(b"PK\x03\x04") or content.startswith(b"PK\x05\x06"):
        return ".zip"
    elif content.startswith(b"%PDF"):
        return ".pdf"
    elif content.startswith(b"<!DOCTYPE") or content.startswith(b"<html") or content.startswith(b"<HTML"):
        return ".html"
    elif content_type:
        if "zip" in content_type.lower():
            return ".zip"
        elif "pdf" in content_type.lower():
            return ".pdf"
        elif "html" in content_type.lower():
            return ".html"
        elif "application/zip" in content_type.lower():
            return ".zip"
        elif "application/pdf" in content_type.lower():
            return ".pdf"
        elif "text/html" in content_type.lower():
            return ".html"
    
    return ".zip"  # Default to zip for FI documents


def download_file(url: str, output_dir: Path) -> Path:
    """
    Download a file from URL to temporary directory.
    
    Returns:
        Path to downloaded file
    """
    print(f"📥 Downloading: {url}")
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    
    # Read first chunk to detect file type
    first_chunk = b""
    content_type = response.headers.get("Content-Type", "")
    content_disposition = response.headers.get("Content-Disposition", "")
    
    # Check Content-Disposition header for filename
    filename = None
    if content_disposition:
        import re
        match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^\s;]+)', content_disposition)
        if match:
            filename = match.group(1).strip('"\'')
            print(f"📄 Filename from header: {filename}")
    
    # Download and detect file type
    chunks = []
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            chunks.append(chunk)
            if not first_chunk and len(chunk) >= 4:
                first_chunk = chunk[:4]
    
    file_content = b"".join(chunks)
    
    # Detect file type from content
    if first_chunk:
        ext = detect_file_type(first_chunk, content_type)
    elif filename:
        ext = Path(filename).suffix or ".zip"
    else:
        ext = detect_file_type(file_content[:1024], content_type)
    
    print(f"🔍 Detected file type: {ext} (Content-Type: {content_type})")
    
    file_path = output_dir / f"document{ext}"
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    print(f"✅ Downloaded to: {file_path} ({len(file_content)} bytes)")
    return file_path


def extract_pdf_pages(pdf_path: Path, num_pages: int = 10) -> Path:
    """
    Extract first N pages from PDF.
    
    Returns:
        Path to extracted PDF with first N pages
    """
    print(f"📄 Extracting first {num_pages} pages from PDF...")
    
    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    pages_to_extract = min(num_pages, total_pages)
    
    writer = PdfWriter()
    for i in range(pages_to_extract):
        writer.add_page(reader.pages[i])
    
    output_path = pdf_path.parent / f"{pdf_path.stem}_first_{pages_to_extract}_pages.pdf"
    with open(output_path, "wb") as f:
        writer.write(f)
    
    print(f"✅ Extracted {pages_to_extract} pages (of {total_pages} total)")
    return output_path


def search_pdf_for_portfolio_section(pdf_path: Path, max_pages: int = 30) -> Optional[int]:
    """
    Search through PDF pages to find which page contains portfolio section.
    Returns page number (0-indexed) or None if not found.
    """
    try:
        reader = PdfReader(str(pdf_path))
        portfolio_keywords = [
            "portfolio", "portfölj", "holdings", "ägda bolag", "investeringar",
            "investments", "företagsportfölj", "bolagsportfölj"
        ]
        
        pages_to_check = min(max_pages, len(reader.pages))
        
        for i in range(pages_to_check):
            try:
                page = reader.pages[i]
                text = page.extract_text()
                if text:
                    text_lower = text.lower()
                    # Count keyword matches
                    matches = sum(1 for keyword in portfolio_keywords if keyword in text_lower)
                    if matches >= 2:  # At least 2 keyword matches
                        print(f"✅ Found portfolio section on page {i+1}")
                        return i
            except:
                continue
        
        print("⚠️  Could not find portfolio section in first pages")
        return None
    except Exception as e:
        print(f"⚠️  Error searching PDF: {e}")
        return None


def unzip_if_needed(file_path: Path) -> List[Path]:
    """
    If file is a ZIP, extract it and return list of extracted files.
    Otherwise, return list with single file.
    """
    extracted_files = []
    
    # Check if file is actually a ZIP by reading magic bytes
    is_zip = False
    try:
        with open(file_path, "rb") as f:
            magic = f.read(4)
            is_zip = magic.startswith(b"PK\x03\x04") or magic.startswith(b"PK\x05\x06")
    except:
        pass
    
    if file_path.suffix.lower() == ".zip" or is_zip:
        print(f"📦 Extracting ZIP archive...")
        extract_dir = file_path.parent / file_path.stem
        extract_dir.mkdir(exist_ok=True)
        
        try:
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                # List all files in ZIP
                file_list = zip_ref.namelist()
                print(f"📋 ZIP contains {len(file_list)} file(s):")
                for fname in file_list[:10]:  # Show first 10
                    print(f"   - {fname}")
                if len(file_list) > 10:
                    print(f"   ... and {len(file_list) - 10} more")
                
                zip_ref.extractall(extract_dir)
                
                # Search for PDFs and HTML/XHTML files recursively (including root level)
                extracted_files = (
                    list(extract_dir.rglob("*.pdf")) + 
                    list(extract_dir.rglob("*.html")) + 
                    list(extract_dir.rglob("*.xhtml")) +
                    list(extract_dir.rglob("*.htm"))
                )
                
                # Also check root level explicitly
                root_pdfs = [f for f in extract_dir.glob("*.pdf") if f.is_file()]
                root_htmls = [f for f in extract_dir.glob("*.html") if f.is_file()]
                root_xhtmls = [f for f in extract_dir.glob("*.xhtml") if f.is_file()]
                root_htms = [f for f in extract_dir.glob("*.htm") if f.is_file()]
                for pdf in root_pdfs:
                    if pdf not in extracted_files:
                        extracted_files.append(pdf)
                for html in root_htmls:
                    if html not in extracted_files:
                        extracted_files.append(html)
                for xhtml in root_xhtmls:
                    if xhtml not in extracted_files:
                        extracted_files.append(xhtml)
                for htm in root_htms:
                    if htm not in extracted_files:
                        extracted_files.append(htm)
                
                # Debug: Show what we found
                if extracted_files:
                    pdf_count = sum(1 for f in extracted_files if f.suffix.lower() == ".pdf")
                    html_count = sum(1 for f in extracted_files if f.suffix.lower() in [".html", ".xhtml", ".htm"])
                    print(f"📄 Found {len(extracted_files)} document file(s): {pdf_count} PDF(s), {html_count} HTML/XHTML(s)")
                    for doc in extracted_files:
                        print(f"   - {doc.name} ({doc.parent.relative_to(extract_dir)})")
                else:
                    # No documents found, list all files for debugging
                    all_files = list(extract_dir.rglob("*"))
                    all_files = [f for f in all_files if f.is_file()]
                    print(f"⚠️  No PDF/HTML/XHTML files found in ZIP, but found {len(all_files)} other file(s):")
                    for f in all_files[:10]:
                        print(f"   - {f.name} ({f.suffix})")
                    if len(all_files) > 10:
                        print(f"   ... and {len(all_files) - 10} more")
        
        except zipfile.BadZipFile as e:
            print(f"⚠️  File is not a valid ZIP: {e}, treating as single file")
            extracted_files = [file_path]
        except Exception as e:
            print(f"⚠️  Error extracting ZIP: {e}")
            extracted_files = [file_path]
        
        if extracted_files:
            print(f"✅ Extracted {len(extracted_files)} file(s) ready for processing")
    else:
        extracted_files = [file_path]
    
    return extracted_files


def find_portfolio_section(text: str) -> str:
    """
    Find the portfolio/holdings section in the document text.
    Returns the relevant section or the full text if not found.
    """
    # Keywords that indicate portfolio sections
    portfolio_keywords = [
        "portfolio", "portfölj", "holdings", "ägda bolag", "investeringar",
        "investments", "företagsportfölj", "bolagsportfölj", "ägda företag",
        "major holdings", "stora innehav", "aktieinnehav", "shareholdings"
    ]
    
    text_lower = text.lower()
    
    # Find sections containing portfolio keywords
    lines = text.split("\n")
    portfolio_sections = []
    in_portfolio_section = False
    current_section = []
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # Check if this line contains portfolio keywords
        if any(keyword in line_lower for keyword in portfolio_keywords):
            in_portfolio_section = True
            current_section = [line]
            # Include previous line for context
            if i > 0:
                current_section.insert(0, lines[i-1])
        elif in_portfolio_section:
            # Continue collecting until we hit a new major section
            if line.strip() and (line.isupper() or line.startswith("---")):
                # Might be a new section header
                if len(current_section) > 5:  # Only save if we have content
                    portfolio_sections.append("\n".join(current_section))
                current_section = []
                in_portfolio_section = False
            else:
                current_section.append(line)
                # Limit section size
                if len(current_section) > 200:
                    portfolio_sections.append("\n".join(current_section))
                    current_section = []
                    in_portfolio_section = False
    
    # Add final section if still collecting
    if in_portfolio_section and current_section:
        portfolio_sections.append("\n".join(current_section))
    
    if portfolio_sections:
        print(f"✅ Found {len(portfolio_sections)} portfolio-related section(s)")
        return "\n\n---\n\n".join(portfolio_sections)
    
    # If no specific section found, return full text but prioritize pages with keywords
    print("⚠️  No specific portfolio section found, using full document")
    return text


def extract_text_from_html(html_path: Path, debug: bool = False) -> str:
    """
    Extract text from HTML/XHTML file.
    Returns text content.
    """
    try:
        from bs4 import BeautifulSoup
        
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            html_content = f.read()
        
        # Use lxml parser if available (better for XHTML), fallback to html.parser
        try:
            soup = BeautifulSoup(html_content, "lxml")
        except:
            soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator="\n", strip=True)
        
        if debug:
            print(f"\n📄 Sample of extracted HTML/XHTML text (first 500 chars):")
            print("-" * 60)
            print(text[:500])
            print("-" * 60)
        
        return text
    except ImportError:
        print("⚠️  BeautifulSoup4 not installed. Install with: pip install beautifulsoup4")
        # Fallback: basic text extraction
        try:
            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # Simple regex to extract text between tags
            import re
            text = re.sub(r'<[^>]+>', ' ', content)
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except Exception as e:
            print(f"⚠️  Error extracting text from HTML: {e}")
            return ""
    except Exception as e:
        print(f"⚠️  Error reading HTML/XHTML: {e}")
        return ""


def extract_text_from_pdf(pdf_path: Path, debug: bool = False) -> str:
    """
    Extract text from PDF (first 10 pages, or more if needed).
    Returns empty string if extraction fails.
    """
    try:
        reader = PdfReader(str(pdf_path))
        text_parts = []
        
        # Try first 10 pages, but if no portfolio keywords found, try more
        num_pages = min(10, len(reader.pages))
        
        for i in range(num_pages):
            try:
                page = reader.pages[i]
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(f"--- Page {i+1} ---\n{text}\n")
            except Exception as e:
                print(f"⚠️  Error extracting page {i+1}: {e}")
                continue
        
        if not text_parts:
            print("⚠️  No text extracted from PDF. Document may be image-based.")
            return ""
        
        full_text = "\n".join(text_parts)
        
        # Debug: Show sample of extracted text
        if debug:
            print("\n📄 Sample of extracted text (first 500 chars):")
            print("-" * 60)
            print(full_text[:500])
            print("-" * 60)
        
        # Try to find portfolio section
        portfolio_text = find_portfolio_section(full_text)
        
        # If portfolio section is much smaller, we found a specific section
        if len(portfolio_text) < len(full_text) * 0.5:
            print(f"✅ Using portfolio-specific section ({len(portfolio_text)} chars vs {len(full_text)} total)")
            return portfolio_text
        
        return full_text
    except Exception as e:
        print(f"⚠️  Error reading PDF: {e}")
        return ""


def pdf_pages_to_images(pdf_path: Path, max_pages: int = 10, dpi: int = 200) -> List[Image.Image]:
    """
    Convert PDF pages to images.
    
    Returns:
        List of PIL Image objects
    """
    if not PDF2IMAGE_AVAILABLE:
        print("⚠️  pdf2image not available, falling back to text extraction")
        return []
    
    try:
        print(f"🖼️  Converting PDF pages to images (DPI: {dpi})...")
        images = convert_from_path(
            str(pdf_path),
            dpi=dpi,
            first_page=1,
            last_page=max_pages,
            fmt='PNG'
        )
        print(f"✅ Converted {len(images)} page(s) to images")
        return images
    except Exception as e:
        print(f"⚠️  Error converting PDF to images: {e}")
        return []


def extract_portfolio_companies_from_images(images: List[Image.Image]) -> List[Dict[str, Any]]:
    """
    Use Gemini Vision to extract portfolio companies from PDF page images.
    Preserves table structure and formatting.
    
    Returns:
        List of portfolio companies with ownership info
    """
    if not GEMINI_MODEL:
        print("❌ Gemini API not configured. Cannot extract portfolio companies.")
        return []
    
    if not images:
        print("⚠️  No images provided.")
        return []
    
    prompt = """You are analyzing a Swedish annual report or financial document. 
Extract ONLY companies that are actually OWNED by the company whose report this is.

Look specifically for sections titled:
- "Portfolio" / "Portfölj"
- "Holdings" / "Innehav" 
- "Investments" / "Investeringar"
- "Owned Companies" / "Ägda bolag"
- "Major Holdings" / "Stora innehav"
- "Shareholdings" / "Aktieinnehav"
- Tables or lists of companies with ownership percentages

Pay special attention to TABLES - extract every row that contains a company name and ownership information.

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
- If you see a table with company names and percentages, extract ALL rows from that table
- Read tables carefully, including multi-column tables

IT IS PERFECTLY OKAY IF THE COMPANY OWNS NOTHING:
- If no portfolio companies are found, return an empty array []
- Do not make up or guess companies just to have results
- Only extract companies that are clearly and explicitly listed as owned/invested in

If no portfolio companies are found, return an empty array [].
"""
    
    try:
        # Prepare content with images
        content_parts = [prompt]
        for i, img in enumerate(images):
            content_parts.append(f"Page {i+1}:")
            content_parts.append(img)
        
        response = GEMINI_MODEL.generate_content(
            content_parts,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Handle response text
        response_text = response.text.strip()
        
        # Sometimes Gemini wraps JSON in markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
        
        result = json.loads(response_text)
        
        # Ensure it's a list
        if isinstance(result, dict):
            if "portfolio_companies" in result:
                portfolio = result["portfolio_companies"]
            elif "companies" in result:
                portfolio = result["companies"]
            elif "holdings" in result:
                portfolio = result["holdings"]
            else:
                portfolio = [result] if not isinstance(result, list) else result
        elif isinstance(result, list):
            portfolio = result
        else:
            portfolio = []
        
        # Validate portfolio items and keep only company_name and ownership_percentage
        validated_portfolio = []
        for item in portfolio:
            if isinstance(item, dict) and "company_name" in item:
                validated_portfolio.append({
                    "company_name": item.get("company_name"),
                    "ownership_percentage": item.get("ownership_percentage")
                })
        
        return validated_portfolio
    
    except json.JSONDecodeError as e:
        return []
    except Exception as e:
        return []


def extract_portfolio_companies(document_text: str) -> List[Dict[str, Any]]:
    """
    Use Gemini to extract portfolio companies from document text.
    
    Returns:
        List of portfolio companies with ownership info
    """
    if not GEMINI_MODEL:
        return []
    
    if not document_text or not document_text.strip():
        return []
    
    prompt = """You are analyzing a Swedish annual report or financial document. 
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

IT IS PERFECTLY OKAY IF THE COMPANY OWNS NOTHING:
- If no portfolio companies are found, return an empty array []
- Do not make up or guess companies just to have results
- Only extract companies that are clearly and explicitly listed as owned/invested in

If no portfolio companies are found, return an empty array [].

Document content:
""" + document_text[:80000]  # Increased limit to capture more content
    
    try:
        response = GEMINI_MODEL.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # Handle response text
        response_text = response.text.strip()
        
        # Sometimes Gemini wraps JSON in markdown code blocks
        if response_text.startswith("```"):
            # Extract JSON from code block
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
        
        result = json.loads(response_text)
        
        # Ensure it's a list
        if isinstance(result, dict):
            # Check common keys
            if "portfolio_companies" in result:
                portfolio = result["portfolio_companies"]
            elif "companies" in result:
                portfolio = result["companies"]
            elif "holdings" in result:
                portfolio = result["holdings"]
            else:
                # If dict has list-like structure, try to extract
                portfolio = [result] if not isinstance(result, list) else result
        elif isinstance(result, list):
            portfolio = result
        else:
            portfolio = []
        
        # Validate portfolio items and keep only company_name and ownership_percentage
        validated_portfolio = []
        for item in portfolio:
            if isinstance(item, dict) and "company_name" in item:
                validated_portfolio.append({
                    "company_name": item.get("company_name"),
                    "ownership_percentage": item.get("ownership_percentage")
                })
        
        return validated_portfolio
    
    except json.JSONDecodeError as e:
        return []
    except Exception as e:
        return []


def process_document(url: str, organization_number: str) -> List[Dict[str, Any]]:
    """
    Download, extract, and analyze a document to find portfolio companies.
    
    Returns:
        List of portfolio companies with ownership information
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # Download file
            file_path = download_file(url, temp_path)
            
            # Unzip if needed
            extracted_files = unzip_if_needed(file_path)
            
            # Process first PDF or HTML/XHTML found
            pdf_files = [f for f in extracted_files if f.suffix.lower() == ".pdf" and f.is_file()]
            html_files = [f for f in extracted_files if f.suffix.lower() in [".html", ".xhtml", ".htm"] and f.is_file()]
            
            if not pdf_files and not html_files:
                print("⚠️  No PDF or HTML files found in document")
                print(f"   Extracted files: {[str(f) for f in extracted_files]}")
                return []
            
            # Prefer PDF, fallback to HTML
            if pdf_files:
                doc_path = pdf_files[0]
                doc_type = "PDF"
                print(f"📄 Processing PDF: {doc_path.name}")
            else:
                doc_path = html_files[0]
                doc_type = "HTML"
                print(f"🌐 Processing HTML: {doc_path.name}")
            
            # Handle HTML files
            if doc_type == "HTML":
                document_text = extract_text_from_html(doc_path, debug=True)
                if not document_text:
                    print("⚠️  Could not extract text from HTML")
                    return []
                
                # Use Gemini to extract portfolio from HTML text
                print("🧠 Analyzing HTML content with Gemini...")
                portfolio = extract_portfolio_companies(document_text)
                return portfolio
            
            # Continue with PDF processing (existing code)
            pdf_path = doc_path
            
            # Try to find portfolio section first
            portfolio_page = search_pdf_for_portfolio_section(pdf_path, max_pages=30)
            
            if portfolio_page is not None:
                # Extract pages around the portfolio section (5 pages before, 10 after)
                reader = PdfReader(str(pdf_path))
                total_pages = len(reader.pages)
                start_page = max(0, portfolio_page - 5)
                end_page = min(total_pages, portfolio_page + 15)
                
                print(f"📄 Extracting pages {start_page+1} to {end_page} (portfolio section found on page {portfolio_page+1})")
                
                # Extract specific page range
                writer = PdfWriter()
                for i in range(start_page, end_page):
                    writer.add_page(reader.pages[i])
                
                extracted_pdf_path = temp_path / f"{pdf_path.stem}_portfolio_section.pdf"
                with open(extracted_pdf_path, "wb") as f:
                    writer.write(f)
                extracted_pdf = extracted_pdf_path
            else:
                # Fallback: Extract first 10 pages
                print("📄 Portfolio section not found, extracting first 10 pages...")
                extracted_pdf = extract_pdf_pages(pdf_path, num_pages=10)
            
            # Try image-based extraction first (preserves table structure)
            print("🖼️  Attempting image-based extraction (preserves table structure)...")
            images = pdf_pages_to_images(extracted_pdf, max_pages=10, dpi=200)
            
            if images:
                # Use Gemini Vision with images
                portfolio = extract_portfolio_companies_from_images(images)
            else:
                # Fallback to text extraction
                print("📝 Falling back to text extraction...")
                document_text = extract_text_from_pdf(extracted_pdf, debug=True)
                
                if not document_text:
                    print("⚠️  Could not extract text from PDF")
                    print("💡 Trying to extract more pages...")
                    # Try extracting more pages
                    if len(pdf_files) > 0:
                        reader = PdfReader(str(pdf_path))
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
                                    return []
                        else:
                            return []
                    else:
                        return []
                else:
                    # Extract portfolio companies using Gemini text
                    portfolio = extract_portfolio_companies(document_text)
            
            return portfolio
        
        except Exception as e:
            print(f"❌ Error processing document: {e}")
            return []


def main():
    """Main entry point."""
    # Allow organization number to be passed as command-line argument
    org_number = sys.argv[1] if len(sys.argv) > 1 else ORGANIZATION_NUMBER
    
    try:
        links = search_fi_documents(org_number)
        
        if links:
            # Process first (latest) document
            top_link = links[0]
            portfolio = process_document(top_link, org_number)
            
            # Output only JSON
            print(json.dumps(portfolio, ensure_ascii=False))
        else:
            # Output empty array if no documents found
            print("[]")
    
    except Exception as e:
        print("[]", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

