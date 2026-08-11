"""author: Justin Baratta
date: Summer 2026
version: 3.13.10

Web integration tools: search, news, and stock lookups using online APIs.
"""

import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from newsapi import NewsApiClient
import wikipedia
import yfinance as yf
from duckduckgo_search import DDGS
from strands.models.ollama import OllamaModel
from strands import Agent, tool

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
API = NewsApiClient(NEWS_API_KEY) if NEWS_API_KEY else None

wikipedia.set_user_agent("JADE/1.0 (justin_m_baratta@gmail.com)")

def _ddg_search(query: str) -> str:
    try:
        # Lightweight DuckDuckGo text search for quick snippets
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        if not results:
            return f"No results found for: '{query}'"
        return "\n".join(f"Title: {r['title']}\nSnippet: {r['body']}\n" for r in results)
    except Exception as e:
        return f"Search error: {e}"

def _wiki_lookup(topic: str) -> str:
    try:
        # Prefer a concise Wikipedia summary when available
        summary = wikipedia.summary(topic, auto_suggest=True)
        return f"Wikipedia Summary for '{topic}': {summary}"
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Topic ambiguous. Try one of these: {e.options[:3]}"
    except Exception as e:
        return f"Wikipedia error: {e}"

def _fetch_stock(ticker: str) -> dict:
    try:
        # Query yfinance for a ticker's basic info
        info = yf.Ticker(ticker).info
        return {
            "symbol": ticker.upper(),
            "price": info.get("currentPrice"),
            "high": info.get("dayHigh"),
            "low": info.get("dayLow"),
            "company": info.get("longName"),
        }
    except Exception as e:
        return {"error": f"Failed to fetch {ticker}: {e}"}

class WebTools:
    def __init__(self) -> None:
        pass

    @tool
    def search_and_lookup(self, query: str) -> str:
        """Search the live web or Wikipedia for general knowledge and facts.

        If Wikipedia returns an ambiguous result or an error, fall back to DuckDuckGo.
        """
        wiki_res = _wiki_lookup(query)
        if "error" in wiki_res.lower() or "ambiguous" in wiki_res.lower():
            return _ddg_search(query)
        return wiki_res

    @tool
    def get_stock_prices(self, tickers: list) -> dict:
        """Return a map of ticker -> price info. Sleeps briefly between calls.

        The brief sleep helps avoid hitting rate limits for public APIs.
        """
        prices = {}
        for ticker in tickers:
            time.sleep(0.5)  # Quick rate-limit cushion
            prices[ticker] = _fetch_stock(ticker)
        return prices

    @tool
    def get_news_headlines(self) -> list:
        """Fetch top news headlines using NewsAPI if configured.

        Returns a short list of article dicts or a helpful message when unconfigured.
        """
        if not API:
            return [{"title": "News API key missing", "description": "Configure NEWS_API_KEY."}]
        try:
            return API.get_top_headlines().get("articles", [])[:5]
        except Exception as e:
            # Return a minimal failure payload so callers can still surface UI messages
            return [{"title": "News API Error", "description": str(e)}]

    def list_web_tools(self) -> list:
        return [
            self.search_and_lookup,
            self.get_stock_prices,
            self.get_news_headlines,
        ]

@tool
def use_web_tools(message: str) -> str:
    web_tools = WebTools()

    model = OllamaModel(
        model_id="qwen2.5:1.5b",
        host="http://localhost:11434",
    )

    agent = Agent(
        model=model,
        tools=web_tools.list_web_tools(),
        system_prompt=(
            "You are an internet-enabled assistant. Use search_and_lookup for general facts, "
            "get_stock_prices for market tickers, and get_news_headlines for news events."
        ),
    )

    response = agent(message)
    return response.message["content"][0]["text"]  # type: ignore