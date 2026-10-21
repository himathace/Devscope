import os

from managed_deepagents import define_mcp
from dotenv import load_dotenv

load_dotenv()

firecrawl_api_key = os.environ["FIRECRAWL_API_KEY"]

mcp = define_mcp(
    servers={
        "firecrawl": {
            "transport": "http",
            "url": "https://mcp.firecrawl.dev/v2/mcp",
            "headers": {
                "Authorization": f"Bearer {firecrawl_api_key}",
            },
            "include_tools": [
                "firecrawl_search",
                "firecrawl_developer_search",
                "firecrawl_scrape",
                "firecrawl_map",
                "firecrawl_crawl",
                "firecrawl_check_crawl_status",
                "firecrawl_parse",
            ],
        },
    },
)