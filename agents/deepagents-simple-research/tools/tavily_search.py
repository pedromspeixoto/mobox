import os
from typing import Literal

from langchain_core.tools import tool
from tavily import TavilyClient


@tool
def internet_search(
    query: str,
    max_results: int = 10,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
) -> dict:
    """Search the internet for information on a given query.
    
    Args:
        query: The search query to look up on the internet.
        max_results: Maximum number of results to return (default: 5).
        topic: The topic category for the search - "general", "news", or "finance".
        include_raw_content: Whether to include raw HTML content in results.
    
    Returns:
        Search results containing relevant information from the web.
    """
    # Create client inside function so env vars are loaded first
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    return client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
