import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class ResearchEngine:
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.api_url = "https://api.tavily.com/search"

    def search_trusted_sources(self, product_name: str) -> str:
        """
        Searches the web for technical specifications of a product using Tavily API.
        Filters out forums and generic Q&A pages as per blacklist requirements.
        """
        if not self.api_key or self.api_key == "mock_key" or self.api_key.strip() == "":
            logger.warning("Tavily API key not configured. Skipping external research.")
            return "No additional source context found (Tavily API key not configured)."

        # Exclude discussions/forums as requested
        exclude_domains = [
            "reddit.com", "quora.com", "wikipedia.org", "facebook.com", 
            "twitter.com", "instagram.com", "pinterest.com", "youtube.com"
        ]

        payload = {
            "api_key": self.api_key,
            "query": f"detailed product specification sheet {product_name}",
            "search_depth": "basic",
            "exclude_domains": exclude_domains,
            "max_results": 3
        }

        try:
            logger.info(f"Querying Tavily for: {product_name}")
            response = httpx.post(self.api_url, json=payload, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                context_parts = []
                for idx, r in enumerate(results):
                    title = r.get("title", "Untitled Source")
                    url = r.get("url", "")
                    content = r.get("content", "")
                    context_parts.append(f"Source [{idx+1}]: {title} ({url})\nContent: {content}\n")
                
                if not context_parts:
                    return "No relevant specification details found on trusted web stores."
                return "\n".join(context_parts)
            else:
                logger.error(f"Tavily API error: Status {response.status_code} - {response.text}")
                return "Failed to fetch external research details due to API status error."
        except Exception as e:
            logger.error(f"Exception executing Tavily API search: {str(e)}")
            return "Error occurred during external context search."
