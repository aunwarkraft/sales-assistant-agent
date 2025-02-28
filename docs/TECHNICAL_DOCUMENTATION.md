# Sales Assistant Agent - Technical Documentation

## System Architecture Overview

### Core Components
The Sales Assistant Agent is designed as a modular, web-scraping and AI-powered intelligence gathering system with the following key components:

1. **Web Scraping Layer**
   - Responsible for extracting structured data from company websites
   - Uses BeautifulSoup for HTML parsing
   - Implements robust extraction strategies for different website structures

2. **Data Processing Layer**
   - Sentence Transformer embeddings for semantic analysis
   - Text embedding generation for semantic search and similarity matching
   - PDF content extraction and processing

3. **Insight Generation Layer**
   - Uses OpenAI's GPT-4 to generate actionable sales insights
   - Processes extracted website data, competitor information, and uploaded documents

## Detailed Component Breakdown

### Web Scraping Module (`fetch_data.py`)

#### Key Functions
- `extract_company_name()`: Intelligent company name extraction
  - Prioritizes structured data (JSON-LD schemas)
  - Fallback methods include meta tags, title, and domain parsing
  
- `extract_company_description()`: Multi-strategy description extraction
  - Checks meta descriptions
  - Falls back to about section paragraphs
  - Extracts first substantial paragraph if no specific description found

- `extract_main_features()`: Feature and solution extraction
  - Searches for sections with keywords like 'feature', 'solution'
  - Extracts headings and associated paragraphs
  - Provides fallback methods for finding key product information

#### Extraction Strategies
- Uses regex for flexible matching
- Implements multiple fallback mechanisms
- Handles various website structures and naming conventions

### Competitor Analysis Module

#### Competitor Mention Detection
- `find_all_competitor_mentions()`: Advanced competitor reference tracking
  - Searches for multiple name variants
  - Extracts contextual mentions
  - Provides context around competitor references

#### Competitor Profiling
- Maintains a knowledge base of known companies
- Extracts key differentiators dynamically
- Provides standardized competitor information extraction

### Data Embedding Module

#### Embedding Generation
- Uses Sentence Transformer (`all-MiniLM-L6-v2`)
- Converts text into dense vector representations that capture semantic meaning
- Generates structured embeddings for multiple document sections:
  - Company description
  - About/mission sections
  - Leadership information
  - Job postings
  - Financial information
  - Press releases

#### Embedding Generation
- Enables advanced text understanding beyond keyword matching
- Allows for:
  - Semantic similarity comparisons
  - Content retrieval based on meaning
  - Identifying conceptually related information

### LLM Insight Generation

#### Input Processing
1. Aggregate data from:
   - Website scraping
   - Competitor analysis
   - PDF document
   - User-provided context

2. Prepare structured input for GPT-4
   - Normalize and clean extracted data
   - Create a comprehensive context document

3. Generate insights focusing on:
   - Company strategy
   - Competitive landscape
   - Potential sales opportunities

## Advanced Techniques

### Robust Web Scraping
- Implements safe HTTP requesting
- Handles various URL formats
- Provides error resilience
- Respects website structures

### Semantic Analysis
- Uses embedding techniques for:
  - Contextual understanding
  - Similarity matching
  - Enhanced information retrieval

## Potential Improvements
1. More sophisticated competitor knowledge base
2. Enhanced NLP for context understanding

## Limitations
- Dependent on website accessibility
- Quality of insights tied to available public information
- Requires manual verification of generated insights

## Technology Stack
- Python 3.8+
- Streamlit (Frontend)
- BeautifulSoup (Web Scraping)
- Sentence Transformers (Embeddings)
- PyPDF2 (PDF Processing)
- OpenAI GPT-4 (Insight Generation)

## Recommended Environment
- Virtual environment
- Requirements file for dependency management
- Compatible with major operating systems
