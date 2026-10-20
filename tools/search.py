import os
from langchain.tools import tool
from firecrawl import Firecrawl


@tool
def web_search(queary: str):
    """answer the queay using search the web
    """
    firecrawl = Firecrawl(
        api_key=os.environ["FIRECRAWL_API_KEY"],
    )

    results = firecrawl.search(
        query=queary,
        limit=3,
    )
    return(results)
    