import requests
from strands.models.ollama import OllamaModel
from strands import Agent, tool
from bs4 import BeautifulSoup
import wikipedia
import time
import os
from dotenv import load_dotenv
from newsapi import NewsApiClient
import yfinance as yf

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
API = NewsApiClient(NEWS_API_KEY)

wikipedia.set_user_agent("JADE/1.0")

class WebTools():
    def __init__(self) -> None:
        return

    @tool
    def definition(self, word:str) -> str:
        """Get the definition of something from merriam webster."""

        response = requests.get(f"https://www.merriam-webster.com/dictionary/{word}")
        if not response.ok:
            raise Exception(f"Merriam-Webster API request failed: {response.status_code}")
        
        soup = BeautifulSoup(response.content, "html.parser")
        definition = soup.find("span", class_="dtText")

        if not definition:
            raise Exception(f"Definition for '{word}' not found.")
        
        definition = definition.get_text().strip(": ").strip()
        return f"The definition of '{word} is {definition}"
    
    @tool
    def get_wikipedia_possible_searches(self, topic:str) -> str:
        """Get the possible wikipedia article titles for a specific topic"""
        try:
            results = wikipedia.search(topic)
            return f"Possible articles for {topic}: {results}"
        except Exception as e:
            return f"An error occurred when searching for topic on wikipedia: {e}"
    
    @tool
    def get_wikipedia_summary(self, article_title:str) -> str:
        """Get a summary of a topic on wikipedia based on an article"""
        try:
            summary = wikipedia.summary(article_title, auto_suggest=False)
            return f"Summary of {article_title}: {summary}"
        except Exception as e:
            return f"An error occurred when getting the summary for a topic on wikipedia: {e}"
    
    @tool
    def random_wikipedia_article_summary(self) -> str:
        """You learn something new every day!"""
        try:
            article_title = wikipedia.random()
        except requests.exceptions.JSONDecodeError:
            print("Error with fetchinbg to wikipedia, waiting 20 seconds")
            time.sleep(20)
            article_title = wikipedia.random()

        try:
            summary = wikipedia.summary(article_title, auto_suggest=False)
            return f"You learn something new every day!\n{article_title}: {summary}"
        except wikipedia.exceptions.DisambiguationError as e:
            article_title = wikipedia.search(article_title)[0]
            summary = wikipedia.summary(article_title, auto_suggest=False)
            return f"You learn something new every day!\n{article_title}: {summary}"
        except Exception as e:
            print(f"An error occurred when getting summary from wikipedia: {e}")
            return ""
    
    @tool
    def get_news_headlines(self) -> list:
        """Get the top 10 news headlines from news API"""
        top_headlines = API.get_top_headlines()
        top_10_headlines = top_headlines["articles"][:10]

        return top_10_headlines

    @tool
    def get_stock_prices(self, tickers:list) -> dict:
        """Get the stock price ticker of a stock(s)"""
        prices = {}
        for ticker in tickers:
            time.sleep(3)
            stock = yf.Ticker(ticker)
            info = stock.info

            prices[ticker] = {
                "symbol": ticker.upper(),
                "price": info.get("currentPrice"),
                "open": info.get("open"),
                "high": info.get("dayHigh"),
                "low": info.get("dayLow"),
                "volume": info.get("volume"),
                "market_cap": info.get("marketCap"),
                "company": info.get("longName"),
            }
        return prices

    def list_web_tools(self) -> list:
        return [self.definition, self.get_wikipedia_possible_searches, self.get_wikipedia_summary, self.random_wikipedia_article_summary, self.get_news_headlines, self.get_stock_prices]

def use_web_tools(message: str) -> str:
    web_tools = WebTools()

    model = OllamaModel(
        model_id="granite4.1:8b",
        host="http://localhost:11434"
    )

    agent = Agent(
        model=model,
        tools=web_tools.list_web_tools(),
        system_prompt="You are a helpful assistant that provides information from the web. Use the available tools to fetch definitions, wikipedia summaries, news headlines, or stock prices based on the user's request."
    )

    response = agent(message)
    return response.message["content"][0]["text"] #type: ignore

use_web_tools("What's up today? What are the news headlines and teach me something new!")