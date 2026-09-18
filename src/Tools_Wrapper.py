# src/step17_tools.py
import json
from duckduckgo_search import DDGS

# Safely import our existing tools from the original file!
from tools import get_telugu_translation, save_user_mistake, review_past_mistakes

def search_internet(query: str) -> str:
    """
    Searches the live internet for current events, news, or factual information.
    Use this tool when the user asks about recent events, today's news, or topics outside your training data.
    
    Args:
        query: The search query to look up on the internet.
        
    Returns:
        A JSON string containing the top search results with titles and summaries.
    """
    try:
        # Fetch the top 3 results from DuckDuckGo
        results = DDGS().text(query, max_results=3)
        return json.dumps(results)
    except Exception as e:
        return f"Search failed: {e}"


