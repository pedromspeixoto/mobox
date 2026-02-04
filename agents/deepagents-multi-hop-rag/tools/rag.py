"""
RAG tool for Weaviate.

Uses Weaviate's native vectorization (e.g. text2vec-transformers) when available.
No client-side embedding required.
"""

import json
import os

from langchain_core.tools import tool
from weaviate import WeaviateClient, connect_to_local
from weaviate.classes.query import MetadataQuery


class WeaviateDefaultSettings:
    """Default settings for Weaviate"""
    HOST = "localhost"
    PORT = 9000
    GRPC_PORT = 50051

def get_weaviate_client() -> WeaviateClient:
    """Get the Weaviate client"""

    weaviate_host = os.environ.get("WEAVIATE_HOST", WeaviateDefaultSettings.HOST)
    weaviate_port = os.environ.get("WEAVIATE_PORT", WeaviateDefaultSettings.PORT)
    weaviate_grpc_port = os.environ.get("WEAVIATE_GRPC_PORT", WeaviateDefaultSettings.GRPC_PORT)

    if weaviate_host != WeaviateDefaultSettings.HOST:
        weaviate_api_key = os.environ.get("WEAVIATE_API_KEY")
        if not weaviate_api_key:
            raise ValueError("WEAVIATE_API_KEY is not set")
        return WeaviateClient(
            url=f"http://{weaviate_host}:{weaviate_port}",
            api_key=weaviate_api_key,
        )

    return connect_to_local(
        host=weaviate_host,
        port=weaviate_port,
        grpc_port=weaviate_grpc_port,
    )

@tool
def weaviate_search(
    query: str,
    k: int = 5,
) -> str:
    """Search the Weaviate vector database for information on a given query.
    
    Args:
        query: The search query to look up in the Weaviate vector database.
        k: Maximum number of results to return (default: 5).

    Returns:
        JSON with "results" (list of {content, score, source}) and "sources_for_citation"
        (list of document names). Use ONLY strings from sources_for_citation for citations—copy exactly.
        Note: The score is a distance (lower = more similar). It is not a similarity score.
    """
    with get_weaviate_client() as client:
        collection = client.collections.get("embeddings")
        result = collection.query.hybrid(
            query=query,
            limit=k,
            return_metadata=MetadataQuery(score=True),
        )

        # Process results - use filename or pathname as document name
        results = []
        for obj in result.objects:
            content = obj.properties.get("content", "")
            score = float(obj.metadata.score) if obj.metadata.score is not None else 0.0
            source = (
                obj.properties.get("filename")
                or obj.properties.get("pathname")
                or obj.properties.get("source")
                or obj.properties.get("resource_id")
                or ""
            )
            results.append({"content": content, "score": score, "source": source})

        sources = list(dict.fromkeys(r["source"] for r in results if r["source"]))
        return json.dumps({
            "results": results,
            "sources_for_citation": sources,
        }, ensure_ascii=False)

