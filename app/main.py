import streamlit as st
from dotenv import load_dotenv
import os
import json
from utils import parse_pdf, scrape_company_data
from llm import generate_insights
from fetch_data import get_competitor_mentions
from semantic_search import find_product_category_matches

# Load environment variables
load_dotenv()

# Page configuration - Must be the first Streamlit command
st.set_page_config(
    page_title="Sales Assistant Agent",
    page_icon="🤖",
    layout="wide"
)


def format_competitor_mentions(mentions: dict) -> str:
    """Format competitor mentions for display with error handling."""
    if not mentions or not isinstance(mentions, dict) or "competitors" not in mentions:
        return "No competitor information available."

    formatted_text = ""

    for competitor_url, data in mentions.get("competitors", {}).items():
        if not isinstance(data, dict):
            continue

        name = data.get('name', 'Unknown Competitor')
        description = data.get('description', 'No description available')
        main_features = data.get(
            'main_features', 'No features information available')
        differentiators = data.get('differentiators', '')
        competitor_mentions = data.get('mentions', [])

        # Start with a summary of mentions
        mention_summary = ""
        if competitor_mentions and len(competitor_mentions) > 0:
            first_mention = competitor_mentions[0]
            if "Found" in first_mention:
                # Ensure proper spacing in the URL
                if "website" in first_mention and " " not in first_mention[-10:]:
                    # Fix the spacing between URL and "website"
                    url_end = first_mention.find("website")
                    if url_end > 0:
                        fixed_mention = first_mention[:url_end] + \
                            " " + first_mention[url_end:]
                        mention_summary = f"**{fixed_mention}**"
                    else:
                        mention_summary = f"**{first_mention}**"
                else:
                    mention_summary = f"**{first_mention}**"
            elif "No mentions" in first_mention:
                mention_summary = f"**{first_mention}**"

        # Format the competitor information with better styling
        formatted_text += f"""
### {name} {mention_summary}

**Website:** {competitor_url}

**Description:**
{description}

**Key Features:**
{main_features}
"""

        # Add differentiators if available
        if differentiators:
            formatted_text += f"""
**Key Differentiators:**
{differentiators}
"""

        # Add detailed mention contexts if available
        if competitor_mentions and len(competitor_mentions) > 1:
            formatted_text += "\n**Mention Details:**\n"
            for i, mention in enumerate(competitor_mentions):
                if i > 0:  # Skip the first item which is the summary
                    # Format all mention contexts consistently with italic formatting
                    if mention.startswith("Context:"):
                        formatted_text += f"- *{mention}*\n"
                    else:
                        formatted_text += f"- *{mention}*\n"

        formatted_text += "\n---\n"

    if not formatted_text:
        return "No competitor information available."

    return formatted_text


def format_article_links(article_links_data):
    """Format article links section properly regardless of format."""
    if not article_links_data:
        return "No article links available."

    # Handle string format
    if isinstance(article_links_data, str):
        return article_links_data

    # Handle dictionary format
    if isinstance(article_links_data, dict):
        formatted_text = ""

        # Format search queries
        if 'search_queries' in article_links_data:
            formatted_text += "### Recommended Search Queries:\n\n"
            if isinstance(article_links_data['search_queries'], list):
                for query in article_links_data['search_queries']:
                    formatted_text += f"- {query}\n"
            else:
                formatted_text += article_links_data['search_queries'] + "\n\n"

        # Format resources
        if 'resources' in article_links_data:
            formatted_text += "\n### Recommended Resources:\n\n"
            if isinstance(article_links_data['resources'], list):
                for resource in article_links_data['resources']:
                    formatted_text += f"- {resource}\n"
            else:
                formatted_text += article_links_data['resources'] + "\n\n"

        # If there are other keys in the dictionary
        for key, value in article_links_data.items():
            if key not in ['search_queries', 'resources']:
                formatted_text += f"\n### {key.replace('_', ' ').title()}:\n\n"
                if isinstance(value, list):
                    for item in value:
                        formatted_text += f"- {item}\n"
                else:
                    formatted_text += value + "\n\n"

        return formatted_text

    # Handle unexpected format
    return str(article_links_data)


def display_semantic_matches(semantic_results):
    """Display semantic search matches for product category."""
    if not semantic_results:
        return

    st.write("### 🔍 Semantic Matches for Product Category")

    # Display high relevance matches
    if semantic_results.get("high_relevance"):
        st.write("#### High Relevance Matches")
        for match in semantic_results["high_relevance"]:
            st.markdown(
                f"**Section:** {match['section'].replace('_', ' ').title()}")
            st.markdown(f"**Relevance Score:** {match['score']:.2f}")
            st.markdown(f"**Content:**\n{match['snippet']}")
            st.markdown("---")

    # Display medium relevance matches
    if semantic_results.get("medium_relevance"):
        st.write("#### Medium Relevance Matches")
        for match in semantic_results["medium_relevance"]:
            st.markdown(
                f"**Section:** {match['section'].replace('_', ' ').title()}")
            st.markdown(f"**Relevance Score:** {match['score']:.2f}")
            st.markdown(f"**Content:**\n{match['snippet']}")
            st.markdown("---")


def display_debug_info(data):
    """Display debug information in a collapsible section."""
    with st.expander("Debug Information (Click to expand)"):
        st.write("### Company Data Preview")
        if isinstance(data, dict) and "company_data" in data and isinstance(data["company_data"], dict):
            if "content" in data["company_data"]:
                st.text_area("Company Content Sample",
                             data["company_data"]["content"][:1000] + "...",
                             height=200)

            if "press_content" in data["company_data"]:
                st.text_area("Press Content Sample",
                             data["company_data"]["press_content"][:1000] +
                             "..." if data["company_data"]["press_content"] else "No press content found",
                             height=100)

        st.write("### Raw LLM Response")
        if isinstance(data, dict) and "raw_response" in data:
            st.text_area("Raw LLM Response", data["raw_response"], height=200)

        st.write("### Semantic Search Results")
        if isinstance(data, dict) and "semantic_search_results" in data:
            st.json(data["semantic_search_results"])


def main():
    st.title("🤖 Sales Assistant Agent")

    # Input section
    st.sidebar.header("Input Information")
    product_name = st.sidebar.text_input("Product Name", "HubSpot")
    company_url = st.sidebar.text_input(
        "Company URL", "https://www.pagerduty.com")
    product_category = st.sidebar.text_input(
        "Product Category", "CRM Software")
    competitors = st.sidebar.text_area(
        "Competitors (URLs, comma-separated)", "https://www.salesforce.com/ca/")
    value_proposition = st.sidebar.text_area("Value Proposition",
                                             "HubSpot CRM empowers PagerDuty to seamlessly integrate incident management with customer relationship data, enhancing response times and customer satisfaction. Our platform automates communication workflows between support and sales teams, providing a unified view of customer interactions. This integration allows PagerDuty to scale operations efficiently, turning incident management into opportunities for stronger customer relationships and business growth.")
    target_customer = st.sidebar.text_area(
        "Target Customer", "Howard Wilson, Chief Financial Officer")

    # Debug mode checkbox
    debug_mode = st.sidebar.checkbox("Enable Debug Mode")
    show_semantic_matches = st.sidebar.checkbox("Show Semantic Matches")

    uploaded_file = st.sidebar.file_uploader(
        "Upload Product Overview Sheet", type="pdf")

    if st.sidebar.button("Generate Insights"):
        if not company_url:
            st.error("Please provide a company URL to analyze.")
            return

        with st.spinner("Generating insights..."):
            try:
                # Process inputs
                competitor_list = [url.strip()
                                   for url in competitors.split(",") if url.strip()]

                # Scrape company data
                st.info("Scraping company data...")
                company_data = scrape_company_data(company_url)

                # Get competitor mentions and generate embeddings
                if competitor_list:
                    st.info("Analyzing competitors and checking for mentions...")
                    mentions = get_competitor_mentions(
                        company_url, competitor_list)
                else:
                    mentions = {"competitors": {}}

                # Parse PDF if uploaded
                pdf_content = ""
                if uploaded_file:
                    st.info("Parsing product overview...")
                    pdf_content = parse_pdf(uploaded_file)

                # Generate insights with all available data
                st.info("Generating comprehensive insights...")
                insights = generate_insights({
                    "product_name": product_name,
                    "company_data": company_data,
                    "product_category": product_category,
                    "value_proposition": value_proposition,
                    "target_customer": target_customer,
                    "pdf_content": pdf_content,
                    "competitor_info": mentions
                })

                # Display outputs in a clean format
                st.title("Sales Intelligence One-Pager")

                # Display debug information if enabled
                if debug_mode and isinstance(insights, dict):
                    display_debug_info(insights)

                # Display semantic matches if enabled
                if show_semantic_matches and isinstance(insights, dict) and "semantic_search_results" in insights:
                    display_semantic_matches(
                        insights["semantic_search_results"])

                # Display sections IN THE EXACT ORDER specified in requirements

                # 1. Company Strategy (FIRST)
                st.markdown("### 📊 Company Strategy")
                if isinstance(insights, dict):
                    st.markdown(insights.get("company_strategy",
                                "No company strategy information available."))
                st.markdown("---")

                # 2. Competitor Mentions (SECOND)
                st.markdown("### 🥊 Competitor Mentions")
                formatted_mentions = format_competitor_mentions(mentions)
                st.markdown(formatted_mentions)
                st.markdown("---")

                # 3. Leadership Information (THIRD)
                st.markdown("### 👥 Leadership Information")
                if isinstance(insights, dict):
                    st.markdown(insights.get("leadership_information",
                                "No leadership information available."))
                st.markdown("---")

                # 4. Product/Strategy Summary (FOURTH)
                st.markdown("### 🚀 Product/Strategy Summary")
                if isinstance(insights, dict):
                    st.markdown(insights.get("product_strategy_summary",
                                "No product strategy information available."))
                st.markdown("---")

                # 5. Article Links (FIFTH/LAST)
                st.markdown("### 🔗 Article Links")
                if isinstance(insights, dict):
                    article_links = insights.get(
                        "article_links", "No article links available.")
                    formatted_article_links = format_article_links(
                        article_links)
                    st.markdown(formatted_article_links)

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                import traceback
                st.error(traceback.format_exc())

    st.markdown("---")
    st.markdown("💡 Built with Streamlit & GPT-4 Turbo")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set up your OpenAI API key in the .env file!")
    else:
        main()
