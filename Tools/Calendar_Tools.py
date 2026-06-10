from strands import tool, Agent
from strands.models.ollama import OllamaModel
import datetime
import time
import re

CALENDAR_FILE = "calendar/calendar.txt"

class Calendar():
    def __init__(self) -> None:
        try:
            self._load()
        except FileNotFoundError:
            open(CALENDAR_FILE, "w").close()
            self.calendar = ""

    def _load(self) -> None:
        with open(CALENDAR_FILE, "r") as f:
            self.calendar = f.read()

    def _save(self, lines: list[str]) -> None:
        with open(CALENDAR_FILE, "w") as f:
            f.write("\n".join(line for line in lines if line.strip()))
        self._load()

    @tool
    def add_to_calendar(self, month: int, day: int, event_time: str, activity: str) -> str:
        """Add an activity to the calendar on the given month/day at the given time."""
        lines = self.calendar.splitlines()
        key = f"{month}/{day}"
        updated = False

        for i, entry in enumerate(lines):
            if entry.startswith(f"{key}:"):
                lines[i] += f", {activity} at {event_time}"
                updated = True
                break

        if not updated:
            lines.append(f"{key}: {activity} at {event_time}")

        self._save(lines)
        return f"Added '{activity} at {event_time}' on {key}."

    @tool
    def remove_from_calendar(self, month: int, day: int, activity: str) -> str:
        """Remove a specific activity from the calendar on the given month/day."""
        lines = self.calendar.splitlines()
        key = f"{month}/{day}"
        found = False

        for i, entry in enumerate(lines):
            if entry.startswith(f"{key}:") and activity in entry:
                found = True
                cleaned = re.sub(rf",?\s*{re.escape(activity)} at [^,\n]+", "", entry)
                cleaned = re.sub(r":\s*,", ":", cleaned).strip().rstrip(",").strip()
                lines[i] = cleaned
                break

        if not found:
            return f"No entry for '{activity}' found on {key}."

        self._save(lines)
        return f"Removed '{activity}' from {key}."

    @tool
    def read_calendar(self) -> str:
        """Return the full contents of the calendar."""
        self._load()
        return self.calendar if self.calendar.strip() else "The calendar is empty."

    @tool
    def get_today(self) -> str:
        """Return today's date."""
        return datetime.date.today().strftime("%B %d, %Y")

    @tool
    def get_current_time(self) -> str:
        """Return the current time."""
        return time.strftime("%I:%M %p")

    @tool
    def clear_calendar(self) -> None:
        """Clear all current entries in the calendar."""
        self._save([])
    
    def list_calendar_tools(self) -> list:
        return [
            self.add_to_calendar,
            self.remove_from_calendar,
            self.read_calendar,
            self.get_today,
            self.get_current_time,
            self.clear_calendar
        ]

@tool
def use_calendar(message:str) -> str:
    """Use the calendar tools to manage your calendar effectively."""
    calendar = Calendar()

    model = OllamaModel(
        model_id="granite4.1:8b",
        host="http://localhost:11434"
    )

    agent = Agent(
        model=model,
        tools=calendar.list_calendar_tools(),
        system_prompt="You are a helpful assistant that manages a calendar. You can add events, remove events, read the calendar, and provide today's date and current time. Before running any tasks, ALWAYS CHECK the current day and time to ensure your actions are relevant. Use the tools provided to manage the calendar effectively."
    )
    response = agent(message)
    try:
        return response.message["content"][0]["text"] #type: ignore
    except (KeyError, IndexError):
        return "I'm sorry, I couldn't retrieve the information."
