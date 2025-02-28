import PyPDF2
import requests
from bs4 import BeautifulSoup
import os
import re
import time
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer


def load_api_key() -> Optional[str]:
    """Load and validate OpenAI API key from environment variables."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    return api_key


def parse_pdf(file_obj) -> str:
    """Parse uploaded PDF file and extract text content."""
    try:
        pdf_reader = PyPDF2.PdfReader(file_obj)
        text_content = ""
        for page in pdf_reader.pages:
            text_content += page.extract_text()
        return text_content
    except Exception as e:
        return f"Error parsing PDF: {str(e)}"


def safe_request(url: str, timeout: int = 15) -> Optional[requests.Response]:
    """Make a safe HTTP request with error handling."""
    # Add standard headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    # Ensure URL has http/https prefix
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            return response
        else:
            print(f"Request failed with status code: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Request exception for {url}: {str(e)}")
        return None


def extract_leadership_info(soup: BeautifulSoup, url: str) -> str:
    """Extract leadership information from website with improved detection."""
    leadership_info = ""

    # Method 1: Check for team/about/leadership pages
    leadership_keywords = ['leadership', 'team', 'management',
                           'executives', 'board', 'directors', 'founders']
    leadership_links = []

    # Find links that might contain leadership info
    for a_tag in soup.find_all('a', href=True):
        href = a_tag.get('href')
        link_text = a_tag.get_text().strip().lower()

        # Check for leadership-related keywords in link text or href
        if any(keyword in link_text or keyword in href.lower() for keyword in leadership_keywords):
            # Handle relative and absolute URLs
            if href.startswith('/'):
                full_url = '/'.join(url.split('/')[:3]) + href
            elif not href.startswith(('http://', 'https://')):
                full_url = url.rstrip('/') + '/' + href.lstrip('/')
            else:
                full_url = href

            leadership_links.append((full_url, link_text))

    # Visit leadership pages to extract information
    # Limit to first 3 to avoid too many requests
    for leader_url, link_text in leadership_links[:3]:
        try:
            print(f"Checking leadership page: {leader_url}")
            leader_response = safe_request(leader_url)
            if leader_response:
                leader_soup = BeautifulSoup(
                    leader_response.content, 'html.parser')

                # Look for profiles - often in cards or list items
                profiles = leader_soup.find_all(['div', 'li'], class_=re.compile(
                    r'(profile|card|member|team-member|executive)', re.I))

                for profile in profiles:
                    # Extract name (usually in headings)
                    name_elem = profile.find(['h2', 'h3', 'h4', 'strong'])
                    name = name_elem.get_text().strip() if name_elem else ""

                    # Extract title/role (often in paragraph or specific class)
                    title_elem = profile.find(
                        ['p', 'span', 'div'], class_=re.compile(r'(title|role|position)', re.I))
                    if not title_elem:
                        # Try the first paragraph if no specific title element
                        title_elem = profile.find('p')

                    title = title_elem.get_text().strip() if title_elem else ""

                    # Look for biographical information
                    bio = ""
                    bio_elements = profile.find_all('p')
                    if len(bio_elements) > 1:  # If there's more than just the title paragraph
                        bio = bio_elements[1].get_text().strip()

                    # Only add if we found both name and title
                    if name and title:
                        leadership_info += f"{name} - {title}\n"
                        if bio:
                            leadership_info += f"Bio: {bio}\n"
                        leadership_info += "\n"

            # Add a small delay to avoid rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"Error processing leadership page {leader_url}: {str(e)}")

    # Method 2: Look for leadership sections on the main page
    if not leadership_info:
        team_sections = soup.find_all(['section', 'div'], class_=re.compile(
            r'(team|leadership|management|executives)', re.I))
        team_sections.extend(soup.find_all(['section', 'div'], id=re.compile(
            r'(team|leadership|management|executives)', re.I)))

        for section in team_sections:
            # Extract all headings and following paragraphs
            for heading in section.find_all(['h2', 'h3', 'h4']):
                name = heading.get_text().strip()
                # Look for adjacent or following title
                title_elem = heading.find_next(['p', 'span', 'div'])
                title = title_elem.get_text().strip() if title_elem else ""

                if name and title:
                    leadership_info += f"{name} - {title}\n"

    return leadership_info


def extract_job_postings(url: str) -> str:
    """Extract job postings data to analyze company strategy and tech stack."""
    base_url = '/'.join(url.split('/')[:3])
    careers_paths = ['/careers', '/jobs',
                     '/work-with-us', '/join-us', '/company/careers']
    job_content = ""

    # Try each common careers path
    for path in careers_paths:
        careers_url = base_url + path
        try:
            response = safe_request(careers_url)
            if not response:
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for job listings
            job_listings = []
            job_elements = soup.find_all(['div', 'li'], class_=re.compile(
                r'(job|position|opening|vacancy)', re.I))
            job_elements.extend(soup.find_all(['div', 'li'], id=re.compile(
                r'(job|position|opening|vacancy)', re.I)))

            for job_elem in job_elements:
                # Extract job title
                title_elem = job_elem.find(['h2', 'h3', 'h4', 'a', 'strong'])
                job_title = title_elem.get_text().strip() if title_elem else ""

                # Extract job description/requirements if available
                desc_elem = job_elem.find(
                    ['p', 'div'], class_=re.compile(r'(description|summary)', re.I))
                job_desc = desc_elem.get_text().strip() if desc_elem else ""

                if job_title:
                    job_listings.append({
                        "title": job_title,
                        "description": job_desc
                    })

            # If we found job listings, format them
            if job_listings:
                job_content += f"## Job Postings from {careers_url}:\n\n"
                for job in job_listings[:10]:  # Limit to 10 jobs
                    job_content += f"- {job['title']}\n"
                    if job['description']:
                        job_content += f"  Description: {job['description'][:200]}...\n"
                break  # Stop after finding a valid careers page

        except Exception as e:
            print(f"Error processing careers page {careers_url}: {str(e)}")

    # If we couldn't find job listings, check if company has jobs on LinkedIn, Indeed, etc.
    if not job_content:
        job_content = "No job postings found on company website. Consider checking LinkedIn, Indeed, or Glassdoor for job postings that would reveal technology stack and skill requirements."

    return job_content


def extract_financial_info(url: str) -> str:
    """Extract financial information for public companies (10-K, annual reports)."""
    base_url = '/'.join(url.split('/')[:3])
    investor_paths = ['/investor-relations', '/investors',
                      '/financials', '/annual-report', '/ir']
    financial_content = ""

    # Try each common investor relations path
    for path in investor_paths:
        investor_url = base_url + path
        try:
            response = safe_request(investor_url)
            if not response:
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for financial reports and filings
            financial_content += f"## Financial Information from {investor_url}:\n\n"

            # Look for links to annual reports, 10-K, etc.
            report_links = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag.get('href')
                text = a_tag.get_text().lower()

                if any(term in text or term in href.lower() for term in ['annual report', '10-k', '10k', 'financial report', 'earnings']):
                    report_links.append({
                        "text": a_tag.get_text().strip(),
                        "url": href if href.startswith('http') else base_url + href if href.startswith('/') else base_url + '/' + href
                    })

            # Add found report links
            if report_links:
                financial_content += "### Financial Reports:\n\n"
                for link in report_links:
                    financial_content += f"- [{link['text']}]({link['url']})\n"

            # Extract any visible financial data on the page
            financial_sections = soup.find_all(['section', 'div'], class_=re.compile(
                r'(financial|earnings|results|performance)', re.I))
            financial_sections.extend(soup.find_all(['section', 'div'], id=re.compile(
                r'(financial|earnings|results|performance)', re.I)))

            if financial_sections:
                financial_content += "\n### Financial Highlights:\n\n"
                for section in financial_sections:
                    # Get all paragraphs in this section
                    paragraphs = section.find_all('p')
                    for p in paragraphs:
                        text = p.get_text().strip()
                        if text and len(text) > 20:  # Only substantial paragraphs
                            financial_content += f"- {text}\n"

            break  # Stop after finding a valid investor relations page

        except Exception as e:
            print(
                f"Error processing investor relations page {investor_url}: {str(e)}")

    # If we couldn't find financial information
    if not financial_content or financial_content == f"## Financial Information from {investor_url}:\n\n":
        # Check if it's likely a public company
        is_public = False
        try:
            # Common stock tickers for large companies
            stock_check_url = f"https://finance.yahoo.com/quote/{url.split('.')[-2].split('/')[-1]}"
            stock_response = safe_request(stock_check_url)
            if stock_response and "not found" not in stock_response.text.lower():
                is_public = True
        except:
            pass

        if is_public:
            financial_content = "This appears to be a public company, but financial information couldn't be automatically extracted. Recommend checking SEC EDGAR database or Yahoo Finance for 10-K reports and financial information."
        else:
            financial_content = "This may be a private company. Limited public financial information is available. Consider checking Crunchbase, PitchBook, or news articles for funding rounds and financial insights."

    return financial_content


def scrape_website_content(url: str) -> str:
    """Scrape the content of the provided URL with improved structure."""
    response = safe_request(url)
    if not response:
        return f"Could not access {url}"

    soup = BeautifulSoup(response.content, 'html.parser')

    # Remove unwanted elements
    for unwanted in soup(['script', 'style', 'nav', 'footer', 'iframe']):
        unwanted.extract()

    # Extract title
    title = soup.find('title')
    title_text = title.get_text().strip() if title else 'No title found'

    # Extract meta description
    meta_description = soup.find('meta', {'name': 'description'})
    meta_content = meta_description['content'] if meta_description and 'content' in meta_description.attrs else ''

    # Extract all headings for structure
    headings_text = ""
    for h_tag in soup.find_all(['h1', 'h2', 'h3']):
        heading_text = h_tag.get_text().strip()
        if heading_text:
            headings_text += f"{heading_text}\n"

    # Extract main content sections
    main_content = ""
    main_tags = ['main', 'article', 'section', 'div']
    main_classes = ['content', 'main', 'body', 'container', 'wrapper']

    # Try to find the main content area
    main_element = None
    for tag in main_tags:
        for class_name in main_classes:
            elements = soup.find_all(tag, class_=re.compile(class_name, re.I))
            for element in elements:
                # Choose elements with substantial content
                if len(element.get_text().strip()) > 200:
                    main_element = element
                    break
            if main_element:
                break
        if main_element:
            break

    # If we found a main content element, extract paragraphs from it
    if main_element:
        for p in main_element.find_all('p'):
            p_text = p.get_text().strip()
            if p_text:
                main_content += f"{p_text}\n\n"
    else:
        # Fallback to all paragraphs on the page
        for p in soup.find_all('p'):
            p_text = p.get_text().strip()
            if p_text and len(p_text) > 50:  # Only substantial paragraphs
                main_content += f"{p_text}\n\n"

    # Extract leadership information
    leadership_info = extract_leadership_info(soup, url)

    # Try to extract company mission/about content
    about_content = ""
    about_sections = soup.find_all(['section', 'div'], class_=re.compile(
        r'(about|mission|vision|values)', re.I))
    about_sections.extend(soup.find_all(
        ['section', 'div'], id=re.compile(r'(about|mission|vision|values)', re.I)))

    for section in about_sections:
        for p in section.find_all('p'):
            p_text = p.get_text().strip()
            if p_text:
                about_content += f"{p_text}\n\n"

    # Extract job postings data
    job_postings = extract_job_postings(url)

    # Extract financial information
    financial_info = extract_financial_info(url)

    # Combine extracted content with clear section markers
    content = f"""
COMPANY NAME: {title_text}

COMPANY DESCRIPTION: {meta_content}

MAIN HEADINGS:
{headings_text}

ABOUT/MISSION:
{about_content}

LEADERSHIP INFORMATION:
{leadership_info}

JOB POSTINGS (TECH STACK INDICATORS):
{job_postings}

FINANCIAL INFORMATION:
{financial_info}

MAIN CONTENT:
{main_content[:3000]}
"""
    return content


def find_press_releases(company_url: str) -> str:
    """Find and scrape press releases or news from the company website."""
    base_url = '/'.join(company_url.split('/')[:3])

    # Common paths for press/news pages
    press_paths = ['/news', '/press', '/press-releases',
                   '/newsroom', '/media', '/about/news', '/company/news']

    # Initialize news_links here to avoid UnboundLocalError
    news_links = []

    # First, check if there are links to news/press on the homepage
    homepage_response = safe_request(company_url)
    if homepage_response:
        homepage_soup = BeautifulSoup(homepage_response.content, 'html.parser')

        # Look for news/press links
        for a_tag in homepage_soup.find_all('a', href=True):
            href = a_tag.get('href')
            text = a_tag.get_text().lower()

            if any(keyword in text or keyword in href.lower() for keyword in ['news', 'press', 'blog', 'media', 'announcement']):
                # Handle relative and absolute URLs
                if href.startswith('/'):
                    full_url = base_url + href
                elif not href.startswith(('http://', 'https://')):
                    full_url = company_url.rstrip('/') + '/' + href.lstrip('/')
                else:
                    full_url = href

                news_links.append(full_url)

    # Add common paths to the list
    for path in press_paths:
        news_links.append(base_url + path)

    press_content = ""
    # Try each path (limit to 3 to avoid too many requests)
    for i, press_url in enumerate(news_links[:3]):
        try:
            print(f"Checking press/news page: {press_url}")
            response = safe_request(press_url)

            if response:
                press_soup = BeautifulSoup(response.content, 'html.parser')

                # Extract article titles and contents
                articles = []

                # Look for article containers
                article_elements = press_soup.find_all(['article', 'div'], class_=re.compile(
                    r'(news|press|article|post|release)', re.I))

                # Limit to first 7 articles
                for article in article_elements[:7]:
                    title_elem = article.find(['h1', 'h2', 'h3', 'h4'])
                    title = title_elem.get_text().strip() if title_elem else ""

                    # Extract date if available
                    date_elem = article.find(['time', 'span', 'div'], class_=re.compile(
                        r'(date|time|published)', re.I))
                    date = date_elem.get_text().strip() if date_elem else ""

                    # Extract summary
                    summary_elem = article.find(['p', 'div'], class_=re.compile(
                        r'(summary|excerpt|description)', re.I))
                    if not summary_elem:
                        # Try first paragraph if no specific summary element
                        summary_elem = article.find('p')

                    summary = summary_elem.get_text().strip() if summary_elem else ""

                    # Look for link to full article
                    link = ""
                    link_elem = title_elem.find_parent(
                        'a') if title_elem else None
                    if link_elem and link_elem.get('href'):
                        href = link_elem.get('href')
                        if href.startswith('/'):
                            link = base_url + href
                        elif not href.startswith(('http://', 'https://')):
                            link = company_url.rstrip(
                                '/') + '/' + href.lstrip('/')
                        else:
                            link = href

                    if title:
                        article_text = f"TITLE: {title}\n"
                        if date:
                            article_text += f"DATE: {date}\n"
                        if summary:
                            article_text += f"SUMMARY: {summary}\n"
                        if link:
                            article_text += f"LINK: {link}\n"
                        articles.append(article_text)

                if articles:
                    press_content += f"PRESS/NEWS FROM {press_url}:\n\n" + "\n\n".join(
                        articles) + "\n\n"
                    break  # Stop after finding one valid press page with articles

            # Add a small delay to avoid rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"Error processing press page {press_url}: {str(e)}")

    return press_content


def generate_structured_embeddings(company_data: Dict[str, Any]) -> Dict[str, List[float]]:
    """Generate separate embeddings for different sections of company data."""
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = {}

        # Extract structured content from the company_data
        content = company_data.get("content", "")
        press_content = company_data.get("press_content", "")

        # Extract specific sections using regex
        sections = {
            "company_description": re.search(r"COMPANY DESCRIPTION: (.*?)(?=\n\n)", content, re.DOTALL),
            "about": re.search(r"ABOUT/MISSION:\n(.*?)(?=\n\nLEADERSHIP INFORMATION)", content, re.DOTALL),
            "leadership": re.search(r"LEADERSHIP INFORMATION:\n(.*?)(?=\n\nJOB POSTINGS)", content, re.DOTALL),
            "jobs": re.search(r"JOB POSTINGS \(TECH STACK INDICATORS\):\n(.*?)(?=\n\nFINANCIAL INFORMATION)", content, re.DOTALL),
            "financial": re.search(r"FINANCIAL INFORMATION:\n(.*?)(?=\n\nMAIN CONTENT)", content, re.DOTALL),
            "main_content": re.search(r"MAIN CONTENT:\n(.*?)$", content, re.DOTALL),
            "press": press_content
        }

        # Generate embeddings for each non-empty section
        for section_name, section_match in sections.items():
            section_content = section_match.group(
                1).strip() if section_match else ""
            if section_name == "press":
                section_content = press_content

            # Only embed substantial content
            if section_content and len(section_content) > 50:
                # Truncate long content for embedding efficiency
                if len(section_content) > 5000:
                    section_content = section_content[:5000]
                embeddings[section_name] = model.encode(
                    section_content).tolist()

        # Also create a combined embedding for general similarity matching
        combined_text = (
            sections.get("company_description", "").group(
                1) if sections.get("company_description") else ""
        ) + " " + (
            sections.get("about", "").group(1) if sections.get("about") else ""
        )
        if combined_text:
            embeddings["combined"] = model.encode(
                combined_text[:5000]).tolist()

        return embeddings

    except Exception as e:
        print(f"Error generating structured embeddings: {str(e)}")
        return {"error": str(e)}


def generate_embedding(text: str) -> List[float]:
    """Generate an embedding for the given text using a pre-trained model.
    This is a simple method for backward compatibility."""
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        # Limit text length for embedding to avoid issues
        if len(text) > 5000:
            text = text[:5000]
        embedding = model.encode(text).tolist()
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return []


def scrape_company_data(company_url: str) -> Dict[str, Any]:
    """Scrape comprehensive company information from the provided URL."""
    print(f"Scraping company data from: {company_url}")

    # Main website content
    content = scrape_website_content(company_url)

    # Press releases/news
    press_content = find_press_releases(company_url)

    # Create the base company data dictionary
    company_data = {
        "url": company_url,
        "content": content,
        "press_content": press_content
    }

    # Generate structured embeddings
    company_data["embeddings"] = generate_structured_embeddings(company_data)

    # Keep a single embedding for backward compatibility
    company_data["embedding"] = company_data["embeddings"].get(
        "combined", generate_embedding(content))

    return company_data
