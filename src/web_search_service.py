import logging
from duckduckgo_search import DDGS
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def perform_web_search(query, max_results=5):
    """
    Perform a web search using DuckDuckGo and return structured results.
    """
    try:
        logging.info(f"Performing web search for query: {query}")
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            
            # Structure the results
            structured_results = []
            for result in results:
                structured_results.append({
                    "title": result.get("title", ""),
                    "href": result.get("link", ""),
                    "body": result.get("body", "")
                })
            
            logging.info(f"Found {len(structured_results)} results")
            return structured_results
    except Exception as e:
        logging.error(f"Error performing web search: {e}")
        return []

def format_search_results_for_llama(results):
    """
    Format search results for LLaMA analysis.
    """
    formatted_text = "Based on the following search results:\n\n"
    for i, result in enumerate(results, 1):
        formatted_text += f"{i}. [Title]: {result['title']}\n"
        formatted_text += f"   [Content]: {result['body']}\n\n"
    formatted_text += "\nProvide a concise summary of the key information."
    return formatted_text

def analyze_search_results(results, context_needed):
    """
    Analyze search results using LLaMA to generate a synthesized answer.
    """
    try:
        from llama_api import summarize_text
        
        # Format results for LLaMA
        formatted_input = format_search_results_for_llama(results)
        
        # Add context about what we're looking for
        prompt = f"""Analyze these search results focusing on {context_needed}:

{formatted_input}

Provide a concise, well-structured answer that addresses the original query."""
        
        # Get LLaMA's analysis
        response = summarize_text(prompt)
        if response and "structured_output" in response:
            # Extract the summary from the structured output
            if "### SUMMARY" in response["structured_output"]:
                summary = response["structured_output"].split("### SUMMARY")[1].split("###")[0].strip()
                return summary
        return "Unable to generate a synthesized answer from search results."
    except Exception as e:
        logging.error(f"Error analyzing search results: {e}")
        return "Error analyzing search results." 