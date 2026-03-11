import logging
import time
from typing import List
import requests

from .scraper import PageContent, ScrapeResult, Section

logger = logging.getLogger(__name__)

def parse_markdown_to_sections(md_text: str) -> List[Section]:
    """Parse raw Markdown from Cloudflare into Section objects."""
    sections: List[Section] = []
    lines = md_text.splitlines()
    
    current_heading = ""
    current_level = 1
    current_body_parts = []
    current_code_blocks = []
    
    in_code_block = False
    current_code = []
    
    for line in lines:
        if line.startswith("```"):
            if not in_code_block:
                in_code_block = True
                current_code = []
            else:
                in_code_block = False
                current_code_blocks.append("\n".join(current_code))
                current_code = []
            continue
            
        if in_code_block:
            current_code.append(line)
            continue
            
        if line.startswith("#"):
            # Flush previous section if it has content
            body_text = "\n".join(current_body_parts).strip()
            if body_text or current_code_blocks:
                sections.append(Section(
                    heading=current_heading,
                    level=current_level,
                    body=body_text,
                    code_blocks=list(current_code_blocks)
                ))
            
            # Start new section
            parts = line.split(" ", 1)
            if len(parts) == 2:
                heading = parts[1].strip()
                level = min(len(parts[0]), 6)
            else:
                heading = line.strip("#").strip()
                level = min(len(line), 6)
                
            current_heading = heading
            current_level = level
            current_body_parts = []
            current_code_blocks = []
        else:
            if line.strip():
                current_body_parts.append(line.strip())
                
    # Flush last section
    body_text = "\n".join(current_body_parts).strip()
    if body_text or current_code_blocks or current_heading:
        sections.append(Section(
            heading=current_heading,
            level=current_level,
            body=body_text,
            code_blocks=list(current_code_blocks)
        ))
        
    return sections


def scrape_docs_cloudflare(
    start_url: str,
    account_id: str,
    api_token: str,
    max_pages: int = 500,
) -> ScrapeResult:
    """Uses Cloudflare Browser Rendering API to crawl an SPA."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/browser-rendering/crawl"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    logger.info("Initiating Cloudflare crawl job for %s", start_url)
    resp = requests.post(url, headers=headers, json={"url": start_url}, timeout=10)
    
    try:
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Cloudflare API error: %s - %s", e, resp.text)
        raise
        
    data = resp.json()
    job_id = data.get("result")
    if not job_id:
        raise ValueError(f"No job_id returned by Cloudflare API: {data}")
        
    logger.info("Cloudflare crawl job started with ID: %s", job_id)
    
    status_url = f"{url}/{job_id}?limit=1"
    delay_s = 5
    
    # 60 attempts * 5 seconds = 5 minutes timeout for the job to complete
    completed = False
    for i in range(120): # up to 10 minutes
        poll_resp = requests.get(status_url, headers=headers, timeout=10)
        poll_resp.raise_for_status()
        poll_data = poll_resp.json().get("result", {})
        
        status = poll_data.get("status")
        logger.info("Job %s status: %s (attempt %d/120)", job_id, status, i+1)
        
        if status != "running":
            completed = True
            break
            
        time.sleep(delay_s)
        
    if not completed:
        logger.warning("Cloudflare crawl job %s timed out waiting for completion.", job_id)
        
    # Job finished. Fetch paginated records.
    logger.info("Fetching results for job %s...", job_id)
    
    result = ScrapeResult()
    cursor = None
    
    while True:
        fetch_url = f"{url}/{job_id}?limit=100&status=completed"
        if cursor:
            fetch_url += f"&cursor={cursor}"
            
        res_resp = requests.get(fetch_url, headers=headers, timeout=15)
        res_resp.raise_for_status()
        
        res_data = res_resp.json().get("result", {})
        records = res_data.get("records", [])
        
        for r in records:
            page_url = r.get("url")
            markdown = r.get("markdown", "")
            if not page_url or not markdown:
                continue
                
            title = r.get("metadata", {}).get("title", page_url)
            sections = parse_markdown_to_sections(markdown)
            
            page = PageContent(url=page_url, title=title, sections=sections)
            result.pages.append(page)
            
            if len(result.pages) >= max_pages:
                break
                
        cursor = res_data.get("cursor")
        if not cursor or len(result.pages) >= max_pages:
            break
            
    logger.info("Fetched %d completed pages from Cloudflare job %s", len(result.pages), job_id)
    return result
