"""author: Justin Baratta
date: Summer 2026
version: 3.13.10

Utilities to test embedding generation and vector similarity for tool selection.
"""

from Tools.ALL_TOOLS import TOOLS
from sentence_transformers import SentenceTransformer, util

embedder = SentenceTransformer('all-MiniLM-L6-v2')

tools_map = {
    # --- Calendar Tools ---
    "read_upcoming_events": "Retrieves upcoming Google Calendar events.",
    "add_event": "Creates a new event on Google Calendar given a summary, start time, and end time.",
    "delete_event": "Deletes an existing Google Calendar event using its event ID.",
    "get_now": "Returns the current ISO date and time for the America/Los_Angeles timezone.",
    "get_events_and_ids": "Returns a mapping of upcoming Google Calendar event names to their IDs and start times.",

    # --- Weather Tools ---
    "get_current_weather": "Gets current weather conditions (temperature, wind speed, precipitation, weather code) for a city.",
    "get_forecast": "Gets daily weather forecast max/min temperatures and conditions for a city.",
    "get_weather_summary": "Returns a compact current weather snapshot combined with a multi-day forecast for a city.",
    "get_forecast_summary": "Returns a human-readable text forecast summary for a city across specified days.",

    # --- Web Tools ---
    "search_and_lookup": "Searches Wikipedia or DuckDuckGo web search for general knowledge, current events, and facts.",
    "get_stock_prices": "Fetches current stock price details, day high/low, and company info for ticker symbols.",
    "get_news_headlines": "Fetches top news article headlines.",

    # --- Writing / Local Storage Tools ---
    "create_notes_entry": "Creates a new text note entry saved locally for today's date.",
    "create_todo_entry": "Creates a new todo list entry with tasks and optional tags for today's date.",
    "create_journal_entry": "Creates a new journal entry saved locally for today's date.",
    "list_writing_entries": "Lists local writing entries (notes, todos, or journals) matching a search query.",
    "search_entries": "Searches local writing entries by title or content using substring matching.",
    "read_entry": "Reads full content of a specific local writing entry by its title.",
    "complete_todo": "Marks a specific task inside a todo file as complete.",
    "get_incomplete_todos": "Retrieves all incomplete todo tasks across all local todo files.",
    "get_todo_summary": "Provides a high-level summary of total, completed, and incomplete todo tasks and tags.",
    "add_task": "Appends a new task to an existing local todo entry file.",
    "update_entry": "Updates or appends text content to an existing local note or journal entry.",
    "get_today": "Returns today's date in YYYY-MM-DD format."
}

tool_names, tool_descriptions = list(tools_map.keys()), list(tools_map.values())
tool_embeddings = embedder.encode(tool_descriptions, convert_to_tensor=True)

def get_relevant_tools(user_query: str, top_k: int = 5):
    query_embedding = embedder.encode(user_query, convert_to_tensor=True)

    hits = util.semantic_search(query_embedding, tool_embeddings, top_k=top_k)[0]
    
    selected_tools = [tool_names[hit['corpus_id']] for hit in hits] #type: ignore
    return selected_tools

print(get_relevant_tools("What's the weather in Reno, Nevada today?"))