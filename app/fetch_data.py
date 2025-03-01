from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
import re
import time
import json
from utils import safe_request, generate_embedding


def extract_company_name(soup: BeautifulSoup, url: str) -> str:
    """Extract the core company name from a website, avoiding taglines and descriptions."""

    # Extract from org schema if available (most reliable)
    org_schema = None
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get('@type') in ['Organization', 'Corporation', 'Company']:
                org_schema = data
                break
            # Handle array of schemas
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get('@type') in ['Organization', 'Corporation', 'Company']:
                        org_schema = item
                        break
        except:
            continue

    if org_schema and 'name' in org_schema:
        return org_schema['name']

    # Try extracting from meta tags with company/org name
    meta_org = soup.find('meta', property='og:site_name')
    if meta_org and meta_org.get('content'):
        org_name = meta_org.get('content').strip()
        # Remove common tagline patterns
        org_name = re.sub(r'\s*[-|]\s*.+$', '', org_name)
        if len(org_name) > 2:  # Avoid empty or very short names
            return org_name

    # Try to get from title tag (but clean it up)
    title = soup.find('title')
    if title:
        title_text = title.get_text().strip()
        # Remove common tagline patterns
        title_text = re.sub(r'\s*[-|:]\s*.+$', '', title_text)
        # Remove common words like "Home", "Official Site", etc.
        title_text = re.sub(r'\b(Home|Official Site|Welcome to)\b',
                            '', title_text, flags=re.IGNORECASE).strip()
        if len(title_text) > 2:
            return title_text

    # Try to get from logo alt text
    logo = soup.find('img', class_=re.compile(r'(logo|brand)', re.I))
    if logo and logo.get('alt'):
        logo_text = logo.get('alt').strip()
        # Remove common words like "logo"
        logo_text = re.sub(r'\b(logo|brand|image)\b', '',
                           logo_text, flags=re.IGNORECASE).strip()
        if len(logo_text) > 2:
            return logo_text

    # Extract domain name as fallback, but make it more presentable
    domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if domain_match:
        domain = domain_match.group(1)
        # Handle common TLDs
        domain_name = re.sub(
            r'\.(com|org|net|io|ai|co|us|gov|edu)$', '', domain.split('.')[0])
        # Convert to title case and fix spacing for multi-word domains
        domain_name = ' '.join(word.capitalize()
                               for word in re.findall(r'[a-zA-Z][a-z]*', domain_name))
        return domain_name

    return "Unknown Company"


def extract_company_description(soup: BeautifulSoup, url: str) -> str:
    """Extract company description from meta tags or about section."""
    # Try meta description
    meta_desc = soup.find('meta', {'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        return meta_desc.get('content').strip()

    # Try og:description
    og_desc = soup.find('meta', {'property': 'og:description'})
    if og_desc and og_desc.get('content'):
        return og_desc.get('content').strip()

    # Try to find description in about section
    about_section = soup.find(
        ['div', 'section'], id=re.compile(r'about', re.I))
    if about_section:
        paragraphs = about_section.find_all('p')
        if paragraphs:
            return paragraphs[0].get_text().strip()

    # Extract the first substantial paragraph from the page
    for p in soup.find_all('p'):
        text = p.get_text().strip()
        if len(text) > 100:  # Only consider substantial paragraphs
            return text

    return "No description available"


def extract_main_features(soup: BeautifulSoup, url: str) -> str:
    """Extract main features or solutions from the website."""
    # Look for features/solutions sections
    feature_sections = []

    # Try to find by ID or class
    for pattern in ['feature', 'solution', 'product', 'service', 'benefit']:
        elements = soup.find_all(
            ['div', 'section'], id=re.compile(pattern, re.I))
        elements.extend(soup.find_all(
            ['div', 'section'], class_=re.compile(pattern, re.I)))
        feature_sections.extend(elements)

    # Extract content from these sections
    features_content = ""
    for section in feature_sections:
        # Get headings
        headings = section.find_all(['h1', 'h2', 'h3'])
        for heading in headings:
            features_content += f"{heading.get_text().strip()}: "
            # Get the paragraph after this heading
            next_p = heading.find_next('p')
            if next_p:
                features_content += f"{next_p.get_text().strip()}\n"

    # If we couldn't find structured features, try all h2 + p combinations
    if not features_content:
        h2_elements = soup.find_all('h2')
        for h2 in h2_elements[:3]:  # Limit to first 3 to avoid getting too much
            features_content += f"{h2.get_text().strip()}: "
            next_p = h2.find_next('p')
            if next_p:
                features_content += f"{next_p.get_text().strip()}\n"

    return features_content if features_content else "No feature information available"


def extract_key_differentiators(company_name: str) -> str:
    """Provide insights about known competitors based on company name."""
    # Dictionary of known competitors and their key differentiators
    known_companies = {
        "Salesforce": "Salesforce is the market leader in CRM with a comprehensive platform, extensive ecosystem, and robust AI capabilities (Einstein). They offer a wide range of integrated products but can be complex and expensive for smaller businesses.",

        "HubSpot": "HubSpot offers an all-in-one marketing, sales, and service platform with a focus on inbound methodology. They provide a generous free tier, user-friendly interface, and strong content marketing tools, but may lack some advanced features of enterprise solutions.",

        "Zendesk": "Zendesk excels in customer service and help desk functionality with intuitive ticket management. They offer omnichannel support capabilities and flexible pricing, but their sales CRM capabilities are less mature than dedicated CRM platforms.",

        "Zoho": "Zoho CRM is known for affordability and extensive integration with Zoho's productivity suite. They offer strong customization options and international support, but may have a steeper learning curve and less polished UI than some competitors.",

        "Microsoft Dynamics": "Microsoft Dynamics 365 offers deep integration with Microsoft products (Office 365, Teams, etc.) and strong enterprise capabilities. It provides powerful customization through Power Platform but can be complex to implement and use.",

        "Oracle": "Oracle CX Cloud Suite provides enterprise-grade solutions with strong database integration and analytics. They offer comprehensive industry-specific solutions but can be expensive and complex to implement.",

        "SAP": "SAP Customer Experience (formerly C/4HANA) delivers robust enterprise solutions with strong ERP integration. They excel in data management and business process optimization but require significant implementation resources.",

        "Pipedrive": "Pipedrive focuses on sales pipeline management with an intuitive visual interface. They offer strong sales-focused features and activity-based selling methodology but have more limited marketing and service capabilities.",

        "Freshworks": "Freshworks (Freshsales) provides affordable, user-friendly CRM with strong automation. They offer quick implementation and good customer support but may lack some advanced enterprise features.",

        "Atlassian": "Atlassian's products (particularly Jira, Confluence, and OpsGenie) are known for robust issue tracking, extensive integrations, and strong collaboration features. Their solutions are developer-centric with flexible workflows, though they can have a steep learning curve.",

        "PagerDuty": "PagerDuty is a digital operations management platform that helps organizations respond to incidents and outages. It's known for reliable alerting, flexible routing rules, and extensive integration capabilities.",

        "Zenduty": "Zenduty is an incident management platform focused on alerting, on-call scheduling, and incident response. It offers competitive pricing and core features similar to PagerDuty but may have a smaller ecosystem of integrations.",
    }

    # Check if we have information about this competitor
    for key, value in known_companies.items():
        if key.lower() in company_name.lower():
            return value

    # Generic response if company not found
    return "This competitor's differentiators are not specifically identified in our database."


def find_all_competitor_mentions(company_content: str, competitor_name: str) -> List[Dict[str, Any]]:
    """Find all mentions of competitors on the target company website with context."""
    mentions = []

    # Extract company name without any parenthetical information
    base_name = re.sub(r'\s*\(.*?\)', '', competitor_name).strip()

    # Normalize text for comparison
    company_content_lower = company_content.lower()
    competitor_name_lower = base_name.lower()

    # Various forms of the competitor name to check
    name_variants = [
        competitor_name_lower,
        competitor_name_lower.replace(' ', ''),  # No spaces
        competitor_name_lower.replace('.com', '')  # Without domain
    ]

    # Find all occurrences of each variant
    for variant in name_variants:
        start_pos = 0
        while True:
            index = company_content_lower.find(variant, start_pos)
            if index == -1:
                break

            # Get context around the mention (100 chars before and after)
            start = max(0, index - 100)
            end = min(len(company_content), index + len(variant) + 100)
            context = company_content[start:end]

            # Clean up the context
            context = context.replace('\n', ' ').replace('\r', ' ')
            context = re.sub(r'\s+', ' ', context).strip()

            # Check if this is a duplicate context (avoid showing the same mention multiple times)
            is_duplicate = False
            for existing_mention in mentions:
                if existing_mention.get('context') == context:
                    is_duplicate = True
                    break

            # Only add if not a duplicate
            if not is_duplicate:
                mentions.append({
                    'variant': variant,
                    'context': f"...{context}..."
                })

            # Move to next potential occurrence
            start_pos = index + len(variant)

    return mentions


def get_competitor_mentions(company_url: str, competitors: List[str]) -> Dict[str, Any]:
    """Analyze competitor info and check for mentions on the target company website."""
    analysis_results = {
        "company_url": company_url,
        "competitors": {},
    }

    # Get company content for searching competitor mentions
    print(f"Scraping content from target company: {company_url}")
    company_response = safe_request(company_url)
    company_content = ""

    # Try to get content from multiple pages for more thorough mention analysis
    if company_response:
        company_soup = BeautifulSoup(company_response.content, 'html.parser')
        company_content = company_soup.get_text()

        # Also try to find and scrape important pages like partners, integrations, etc.
        important_pages = []

        # Find links to potentially relevant pages
        for a_tag in company_soup.find_all('a', href=True):
            href = a_tag.get('href')
            text = a_tag.get_text().lower()

            # Skip external links and anchors
            if href.startswith('#') or (href.startswith('http') and company_url not in href):
                continue

            # Check for relevant keywords in link text or URL
            relevant_keywords = ['partner', 'integrat', 'app', 'marketplace', 'ecosystem',
                                 'connect', 'plugin', 'extension', 'comparison', 'vs',
                                 'alternative', 'technology', 'stack', 'api']

            if any(keyword in text or keyword in href.lower() for keyword in relevant_keywords):
                # Handle relative URLs
                if href.startswith('/'):
                    full_url = '/'.join(company_url.split('/')[:3]) + href
                elif not href.startswith('http'):
                    full_url = company_url.rstrip('/') + '/' + href.lstrip('/')
                else:
                    full_url = href

                if full_url not in important_pages:
                    important_pages.append(full_url)

        # Limit to 3 additional pages to avoid too many requests
        for page_url in important_pages[:3]:
            try:
                print(f"Checking additional page for mentions: {page_url}")
                page_response = safe_request(page_url)
                if page_response:
                    page_soup = BeautifulSoup(
                        page_response.content, 'html.parser')
                    company_content += "\n" + page_soup.get_text()
                time.sleep(0.5)  # Small delay to avoid rate limiting
            except Exception as e:
                print(f"Error scraping additional page {page_url}: {str(e)}")

    # Process each competitor
    for competitor_url in competitors:
        if not competitor_url.strip():
            continue

        try:
            # Standardize URL format
            if not competitor_url.startswith(('http://', 'https://')):
                competitor_url = 'https://' + competitor_url

            print(f"Analyzing competitor: {competitor_url}")
            response = safe_request(competitor_url)
            if not response:
                analysis_results["competitors"][competitor_url] = {
                    "url": competitor_url,
                    "name": "Could not access website",
                    "description": "Failed to retrieve data",
                    "main_features": "",
                    "mentions": []
                }
                continue

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract company name
            name = extract_company_name(soup, competitor_url)

            # Extract description
            description = extract_company_description(soup, competitor_url)

            # Extract main features/solutions
            main_features = extract_main_features(soup, competitor_url)

            # Get key differentiators
            differentiators = extract_key_differentiators(name)

            # Find ALL mentions of this competitor on the target company site
            all_mentions = find_all_competitor_mentions(company_content, name)

            # Format mentions for display
            formatted_mentions = []
            if all_mentions:
                formatted_mentions.append(
                    f"Found {len(all_mentions)} mention(s) of {name} on the {company_url} website")
                for mention in all_mentions:
                    formatted_mentions.append(f"Context: {mention['context']}")
            else:
                formatted_mentions.append(
                    f"No mentions of {name} found on the {company_url} website")

            # Store competitor data
            competitor_data = {
                "url": competitor_url,
                "name": name,
                "description": description[:500] if description else "No description available",
                "main_features": main_features[:800] if main_features else "No feature information available",
                "differentiators": differentiators,
                "mentions": formatted_mentions
            }
            analysis_results["competitors"][competitor_url] = competitor_data

            # Add a small delay to avoid rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"Error processing {competitor_url}: {str(e)}")
            analysis_results["competitors"][competitor_url] = {
                "url": competitor_url,
                "name": "Error",
                "description": f"Error processing: {str(e)}",
                "main_features": "",
                "mentions": []
            }

    return analysis_results
