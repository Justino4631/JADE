from strands.models.ollama import OllamaModel
from strands import tool, Agent
from Tools.Calendar_Tools import use_calendar as calendar_agent
from Tools.Weather_Tools import use_weather_tools as weather_agent
from Tools.Web_Tools import use_web_tools as web_agent
from Tools.Writing_Tools import use_writing_tools as writing_agent
from Tools.Slack_Tools import use_slack_bot as slack_agent

model = OllamaModel(
    model_id='granite4.1:8b',
    host='http://localhost:11434'
)

agent = Agent(
    model=model,
    tools=[calendar_agent, weather_agent, slack_agent, web_agent, writing_agent],
    system_prompt="You are a helpful agent. When you take in a query, use one of the tools (sub-agents) available to you. Summarize the result of the sub-agent job and if an error occurs."
)

agent("What is the weather tomorrow in Reno?")
