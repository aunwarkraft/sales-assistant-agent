"""
Semantic search functionality for the Sales Assistant Agent.
Uses embeddings to find semantically similar content across company data.
"""

import numpy as np
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Any


def calculate_similarity(embedding1, embedding2):
    """Calculate cosine similarity between two embeddings."""
    if not embedding1 or not embedding2:
        return 0.0

    # Reshape embeddings for sklearn
    e1 = np.array(embedding1).reshape(1, -1)
    e2 = np.array(embedding2).reshape(1, -1)

    # Calculate cosine similarity
    sim_score = cosine_similarity(e1, e2)[0][0]
    return float(sim_score)


def extract_section(text, section_marker):
    """Extract a specific section from the structured text."""
    if not text or not section_marker:
        return ""

    start_idx = text.find(section_marker)
    if start_idx == -1:
        return ""

    # Find the start of the content after the marker
    content_start = text.find("\n", start_idx)
    if content_start == -1:
        return ""

    # Find the next section marker
    next_marker_idx = -1
    for marker in ["COMPANY NAME:", "COMPANY DESCRIPTION:", "MAIN HEADINGS:",
                   "ABOUT/MISSION:", "LEADERSHIP INFORMATION:", "JOB POSTINGS",
                   "FINANCIAL INFORMATION:", "MAIN CONTENT:"]:
        if marker == section_marker:
            continue

        idx = text.find(marker, content_start)
        if idx != -1 and (next_marker_idx == -1 or idx < next_marker_idx):
            next_marker_idx = idx

    if next_marker_idx == -1:
        section_content = text[content_start:].strip()
    else:
        section_content = text[content_start:next_marker_idx].strip()

    return section_content


def search_with_embeddings(query: str, company_data: dict, threshold: float = 0.5) -> dict:
    """
    Search company data using embeddings to find semantic matches for a query.

    Args:
        query: The search query
        company_data: Company data dictionary with embeddings
        threshold: Minimum similarity score threshold

    Returns:
        Dictionary of search results with scores
    """
    # Generate embedding for query
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_embedding = model.encode(query).tolist()

    results = {}

    # Search through structured embeddings
    embeddings = company_data.get("embeddings", {})

    for section_name, section_embedding in embeddings.items():
        similarity = calculate_similarity(query_embedding, section_embedding)

        if similarity >= threshold:
            # Extract corresponding text content for context
            content = ""
            if section_name == "company_description":
                content = extract_section(company_data.get(
                    "content", ""), "COMPANY DESCRIPTION:")
            elif section_name == "about":
                content = extract_section(company_data.get(
                    "content", ""), "ABOUT/MISSION:")
            elif section_name == "leadership":
                content = extract_section(company_data.get(
                    "content", ""), "LEADERSHIP INFORMATION:")
            elif section_name == "jobs":
                content = extract_section(
                    company_data.get("content", ""), "JOB POSTINGS")
            elif section_name == "financial":
                content = extract_section(company_data.get(
                    "content", ""), "FINANCIAL INFORMATION:")
            elif section_name == "main_content":
                content = extract_section(
                    company_data.get("content", ""), "MAIN CONTENT:")
            elif section_name == "press":
                content = company_data.get("press_content", "")

            results[section_name] = {
                "score": similarity,
                "content": content
            }

    return results


def find_product_category_matches(product_category: str, company_data: dict) -> dict:
    """Find matches between product category and company content using embeddings."""
    search_results = search_with_embeddings(
        product_category, company_data, threshold=0.4)

    # Format results for easier consumption
    matches = {
        "high_relevance": [],
        "medium_relevance": [],
        "low_relevance": []
    }

    for section, result in search_results.items():
        score = result["score"]
        content = result["content"]

        # Extract a relevant snippet around the concept
        sentences = content.split('.')
        relevant_sentences = []

        # Simple extraction of sentences that might be most relevant
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  # Skip very short fragments
                relevant_sentences.append(sentence)

        snippet = '. '.join(
            relevant_sentences[:3]) if relevant_sentences else content[:200]

        if score >= 0.65:
            matches["high_relevance"].append({
                "section": section,
                "score": score,
                "snippet": snippet
            })
        elif score >= 0.5:
            matches["medium_relevance"].append({
                "section": section,
                "score": score,
                "snippet": snippet
            })
        else:
            matches["low_relevance"].append({
                "section": section,
                "score": score,
                "snippet": snippet
            })

    return matches


def find_competitor_semantic_mentions(competitor_name: str, company_data: dict) -> list:
    """Find semantic mentions of competitors beyond exact text matches."""
    search_results = search_with_embeddings(
        f"companies like {competitor_name} or similar to {competitor_name}",
        company_data,
        threshold=0.6
    )

    semantic_mentions = []

    for section, result in search_results.items():
        score = result["score"]
        content = result["content"]

        # Extract snippets around potential implicit mentions
        sentences = content.replace('\n', '. ').split('.')
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Skip very short fragments
                # Look for competitor-comparison related phrases
                comparison_phrases = [
                    'alternative', 'competitor', 'similar', 'compared',
                    'versus', 'vs', 'unlike', 'like', 'better than'
                ]

                if any(phrase in sentence.lower() for phrase in comparison_phrases):
                    semantic_mentions.append({
                        "section": section,
                        "score": score,
                        "context": sentence
                    })

    return semantic_mentions
