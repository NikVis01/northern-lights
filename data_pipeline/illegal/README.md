# FI Document Retrieval & Portfolio Extraction Script

## Overview

Automates retrieval of regulatory documents from the Swedish Finansinspektionen (FI) search portal and extracts portfolio companies from annual reports using Gemini AI.

## Features

1. **Document Search**: Automatically searches FI portal for organization filings
2. **Document Download**: Downloads the latest annual report
3. **PDF Processing**: Extracts first 10 pages from PDF documents
4. **Image-Based Extraction**: Converts PDF pages to images to preserve table structure
5. **Portfolio Extraction**: Uses Gemini Vision API to extract portfolio companies with ownership percentages (preserves table formatting)
6. **JSON Output**: Returns structured JSON with company names, organization IDs, and ownership info

## Installation

```bash
# Install dependencies
pip install playwright pypdf google-generativeai requests python-dotenv pdf2image Pillow

# Install Playwright browser binaries
playwright install chromium

# Install poppler (required for pdf2image)
# On Ubuntu/Debian:
sudo apt-get install poppler-utils
# On macOS:
brew install poppler
# On Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases

# Set up environment variables
export GEMINI_API_KEY="your-gemini-api-key"
```

## Usage

```bash
# Use default organization number (556043-4200)
python hack_net.py

# Or specify organization number
python hack_net.py 556043-4200
```

## Output

The script outputs:
1. List of all found document URLs
2. Portfolio companies extracted from the latest document (first 10 pages)
3. JSON format with:
   - `company_name`: Name of portfolio company
   - `organization_id`: Swedish org number (if found)
   - `ownership_percentage`: Percentage owned (if mentioned)
   - `ownership_type`: Type of ownership (direct/indirect/total)

## Example Output

```json
[
  {
    "company_name": "Ericsson AB",
    "organization_id": "556016-0680",
    "ownership_percentage": 22.0,
    "ownership_type": "direct"
  },
  {
    "company_name": "Atlas Copco AB",
    "organization_id": "556009-1518",
    "ownership_percentage": 15.5,
    "ownership_type": "direct"
  }
]
```

## Customization

Edit the constants at the top of `hack_net.py`:

```python
SEARCH_URL = "https://finanscentralen.fi.se/search/Search.aspx"
ORGANIZATION_NUMBER = "556043-4200"  # Change this
```

## Requirements

- **Playwright**: Browser automation for ASP.NET ViewState handling
- **pypdf**: PDF text extraction and page manipulation
- **Google Generative AI**: Gemini API for portfolio extraction
- **Python-dotenv**: Environment variable management

## Troubleshooting

- **Timeout errors**: The page may be slow to load. Increase timeout values in the script.
- **Field not found**: ASP.NET field IDs may have changed. Check the page source for current IDs.
- **No results**: The organization may not have any filings, or the page structure changed.
- **Gemini API errors**: Ensure `GEMINI_API_KEY` is set in your environment or `.env` file.
- **PDF extraction fails**: Document may be image-based. Consider OCR solutions for scanned PDFs.

