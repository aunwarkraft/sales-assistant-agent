from openai import OpenAI
from utils import load_api_key
import json

client = OpenAI(api_key=load_api_key())


def generate_insights(data: dict) -> dict:
    """Generate insights using GPT-4 based on input data with specific output requirements."""
    # Extract company data for better context
    company_url = data.get('company_data', {}).get('url', 'Unknown')
    company_content = data.get('company_data', {}).get('content', '')
    press_content = data.get('company_data', {}).get('press_content', '')

    # Format prompt with clear sections matching the exact output requirements
    prompt = f"""
    You are a sales intelligence agent helping a sales representative prepare for a meeting with a potential client.
    
    ### SALES CONTEXT
    - You're helping sell: {data.get('product_name', 'N/A')} (Product Category: {data.get('product_category', 'N/A')})
    - Target company: {company_url}
    - Target stakeholders: {data.get('target_customer', 'N/A')}
    - Value proposition: {data.get('value_proposition', 'N/A')}
    
    ### TARGET COMPANY DATA
    {company_content[:3000]}
    
    ### PRESS/NEWS CONTENT
    {press_content[:1000]}
    
    ### TASK
    Create a detailed sales intelligence one-pager with the following SPECIFIC sections exactly as described:
    
    1. COMPANY STRATEGY: 
       - Provide a summary of the company's activities in the industry relevant to {data.get('product_name', 'your product')}.
       - Extract and highlight any public statements, press releases, or articles where key executives have discussed relevant topics.
       - Analyze job postings or other indicators that hint at the company's strategy or technology stack (e.g., skills required in job postings).
    
    2. LEADERSHIP INFORMATION: 
       - Identify key leaders at the prospect company who would be involved in purchasing decisions for {data.get('product_category', 'this type of solution')}.
       - Highlight their relevance to this potential purchase (e.g., those quoted in press releases over the last year).
       - Include specific titles, responsibilities, and decision-making authority if available.
    
    3. PRODUCT/STRATEGY SUMMARY: 
       - For public companies, include insights from 10-Ks, annual reports, or other relevant documents available online.
       - Analyze how the company's current strategy and technology align with {data.get('product_name', 'our product')}.
       - Identify specific pain points or challenges that our solution could address.
    
    4. ARTICLE LINKS: 
       - Provide links to full articles, press releases, or other sources mentioned in your analysis.
       - Organize these links by category (e.g., Company Strategy, Leadership, Technology Stack).
       - Include a brief description of what each source contains.
    
    Your response must be formatted as a JSON object with these exact keys: "company_strategy", "leadership_information", "product_strategy_summary", and "article_links".
    
    For the "article_links" section, format it as a string with proper markdown bullet points or numbered lists - not as a nested dictionary or JSON object.
    
    Make each section detailed, specific, and actionable for the sales rep. If you cannot find certain information, explain what is missing and provide your best educated guess based on the company's industry and size.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a sales intelligence agent specialized in helping sales representatives prepare for meetings with potential clients. You extract specific insights from company websites, press releases, job postings, and public documents to help sales reps understand their prospects. Focus on providing factual, accurate information that follows the exact output requirements."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # Lower temperature for more focused, factual responses
            max_tokens=2000   # Ensure we get a substantial response
        )

        # Parse the response
        raw_content = response.choices[0].message.content
        try:
            insights = json.loads(raw_content)

            # Ensure all required keys exist
            required_keys = ["company_strategy", "leadership_information",
                             "product_strategy_summary", "article_links"]
            for key in required_keys:
                if key not in insights:
                    insights[key] = "Information not found in company data."

            # Post-process article links to ensure it's properly formatted if it's still a dictionary
            if isinstance(insights["article_links"], dict):
                formatted_links = "### Article Sources:\n\n"

                if "company_strategy" in insights["article_links"]:
                    formatted_links += "**Company Strategy Sources:**\n"
                    sources = insights["article_links"]["company_strategy"]
                    if isinstance(sources, list):
                        for source in sources:
                            formatted_links += f"- {source}\n"
                    else:
                        formatted_links += f"- {sources}\n"

                if "leadership" in insights["article_links"]:
                    formatted_links += "\n**Leadership Sources:**\n"
                    sources = insights["article_links"]["leadership"]
                    if isinstance(sources, list):
                        for source in sources:
                            formatted_links += f"- {source}\n"
                    else:
                        formatted_links += f"- {sources}\n"

                if "technology" in insights["article_links"]:
                    formatted_links += "\n**Technology & Strategy Sources:**\n"
                    sources = insights["article_links"]["technology"]
                    if isinstance(sources, list):
                        for source in sources:
                            formatted_links += f"- {source}\n"
                    else:
                        formatted_links += f"- {sources}\n"

                insights["article_links"] = formatted_links

            # Add raw response for debugging
            insights["raw_response"] = raw_content

            return insights

        except json.JSONDecodeError:
            # If JSON parsing fails, create our own structured response
            print(f"JSON parsing failed. Raw content: {raw_content[:200]}...")

            # Try to extract sections manually using string markers
            sections = {}
            current_section = None
            lines = raw_content.split('\n')

            for line in lines:
                line = line.strip()
                if "COMPANY STRATEGY" in line.upper() or "company_strategy" in line:
                    current_section = "company_strategy"
                    sections[current_section] = ""
                elif "LEADERSHIP INFORMATION" in line.upper() or "leadership_information" in line:
                    current_section = "leadership_information"
                    sections[current_section] = ""
                elif "PRODUCT/STRATEGY SUMMARY" in line.upper() or "product_strategy_summary" in line:
                    current_section = "product_strategy_summary"
                    sections[current_section] = ""
                elif "ARTICLE LINKS" in line.upper() or "article_links" in line:
                    current_section = "article_links"
                    sections[current_section] = ""
                elif current_section and line:
                    # Remove common JSON formatting characters
                    clean_line = line.replace('"', '').replace(
                        ',', '').replace('{', '').replace('}', '')
                    sections[current_section] += clean_line + "\n"

            # Ensure all required keys exist
            for key in required_keys:
                if key not in sections or not sections[key].strip():
                    sections[key] = "Information not found in company data."

            # Add raw response for debugging
            sections["raw_response"] = raw_content

            return sections

    except Exception as e:
        print(f"Error in generate_insights: {str(e)}")
        return {
            "company_strategy": f"Error generating company strategy insights: {str(e)}",
            "leadership_information": "Error generating leadership information.",
            "product_strategy_summary": "Error generating product strategy summary.",
            "article_links": "Error generating article links.",
            "raw_response": f"Exception occurred: {str(e)}"
        }
