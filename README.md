# Sales Assistant Agent

A prototype of a sales assistant agent that helps sales representatives gain insights into prospective accounts, understand competitors, and grasp company strategies.

## Features

- **Company Analysis**: Extract key information from company websites including strategy, leadership, and focus areas
- **Competitor Analysis**: Analyze competitor websites and find mentions on target company sites
- **PDF Processing**: Upload product documents for additional context
- **LLM-Powered Insights**: Uses GPT-4 to generate structured, actionable insights for sales representatives

## Setup

1. Clone this repository
```bash
git clone https://github.com/aunwarkraft/sales-assistant-agent.git
cd sales-assistant-agent
```

2. Create and activate a virtual environment
First, create a virtual environment:
```bash
python3 -m venv venv
```

Then activate it:
- For macOS/Linux:
```bash
source venv/bin/activate
```
- For Windows:
```bash
.\venv\Scripts\activate
```
You'll know it's activated when you see `(venv)` in your terminal prompt.

3. Install the required dependencies
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with your OpenAI API key
```
OPENAI_API_KEY=your_openai_api_key_here
```

5. Run the Streamlit application
```bash
streamlit run app/main.py
```
The application should open in your default web browser automatically.

## Usage

1. Enter the product name you're selling
2. Provide the URL of the target company
3. Enter the product category
4. Add competitor URLs (comma-separated)
5. Describe your value proposition
6. Specify the target customer
7. Optionally upload a product overview PDF
8. Click "Generate Insights" to create the sales intelligence report

## Technical Details

- **Frontend**: Streamlit for a simple, user-friendly interface
- **NLP**: OpenAI GPT-4 for natural language processing and insight generation
- **Web Scraping**: BeautifulSoup for company data extraction
- **Embeddings**: Sentence Transformers for text embedding generation
- **PDF Processing**: PyPDF2 for parsing product documents

## Limitations

- Web scraping may be affected by website structures and content accessibility
- Company data extraction depends on publicly available information
- LLM-generated insights should be reviewed for accuracy
- The quality of competitor analysis depends on the accuracy of website data

## Troubleshooting

If you encounter SSL/OpenSSL errors with urllib3, try pinning it to a compatible version:
```bash
pip install urllib3<2.0.0
```

For Python 3.7 environments, some packages may require specific version constraints.
