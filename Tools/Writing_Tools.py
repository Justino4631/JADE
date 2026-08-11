"""author: Justin Baratta
date: Summer 2026
version: 3.13.10

Simple local writing tools: notes, todos, and journals storage helpers.
"""

from strands import tool, Agent
from strands.models.ollama import OllamaModel
from datetime import date
import json
from pathlib import Path


class Writer:
    def __init__(self) -> None:
        self.base_dir = Path.cwd()
        for folder_name in ["notes", "todos", "journals"]:
            # Ensure storage folders exist for notes, todos, and journals
            (self.base_dir / folder_name).mkdir(parents=True, exist_ok=True)

    def _entry_path(self, type_entry: str, file_title: str) -> Path:
        # Build path for a specific entry type and title
        return self.base_dir / type_entry / f"{file_title}.json"

    def _write_json(self, path: Path, payload: dict) -> None:
        # Persist JSON payload to disk with consistent formatting
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)

    @tool
    def create_notes_entry(self, content: str) -> None:
        """Create a new notes entry."""
        today = date.today().strftime("%Y-%m-%d")
        file_name = f"{today}_Notes"
        payload = {"date": today, "content": content}
        # Write a new note file named by date
        self._write_json(self._entry_path("notes", file_name), payload)

    @tool
    def create_todo_entry(self, tasks: list, tags: list | None = None) -> None:
        """Create a new todo entry."""
        tags = tags or []
        today = date.today().strftime("%Y-%m-%d")
        file_name = f"{today}_Todos"
        payload = {
            "date": today,
            "todos": [
                # Each todo includes task text, a completed flag, and optional tag
                {"task": task, "completed": False, "tag": tags[i] if i < len(tags) else ""}
                for i, task in enumerate(tasks)
            ],
        }
        self._write_json(self._entry_path("todos", file_name), payload)

    @tool
    def create_journal_entry(self, content: str) -> None:
        """Create a new journal entry."""
        today = date.today().strftime("%Y-%m-%d")
        file_name = f"{today}_Journals"
        payload = {"date": today, "content": content}
        self._write_json(self._entry_path("journals", file_name), payload)

    @tool
    def list_writing_entries(self, query: str = "", type_entry: str = "notes") -> dict:
        """Return a list of writing entries based on the query and type."""
        if type_entry not in ["notes", "todos", "journals"]:
            return {}

        folder = self.base_dir / type_entry
        results = {}
        for file in sorted(folder.glob("*.json")):
            # Simple substring match against filenames for quick filtering
            if query.lower() in file.name.lower() or not query:
                with file.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)

                if type_entry == "todos":
                    preview = [todo.get("task", "") for todo in data.get("todos", [])]
                else:
                    preview = data.get("content", "")[:75]

                results[file.stem] = preview

        return results

    @tool
    def search_entries(self, query: str = "", type_entry: str = "notes") -> dict:
        """Search writing entries by title or content using a simple substring match."""
        # Delegate to list_writing_entries for the underlying implementation
        return self.list_writing_entries(query=query, type_entry=type_entry)

    @tool
    def read_entry(self, file_title: str) -> dict:
        """Read a writing entry by its title."""
        for type_entry in ["notes", "todos", "journals"]:
            path = self._entry_path(type_entry, file_title)
            if path.exists():
                with path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)

        return {}

    @tool
    def complete_todo(self, file_title: str, task: str) -> str:
        """Mark a todo as complete."""
        path = self._entry_path("todos", file_title)
        if not path.exists():
            return f"Todo '{file_title}' not found"

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        # Find the matching task (case-insensitive) and mark it complete
        todo_match = next((todo for todo in data.get("todos", []) if todo.get("task", "").lower() == task.lower()), None)
        if not todo_match:
            return f"Task '{task}' not found in '{file_title}'"

        todo_match["completed"] = True
        self._write_json(path, data)
        return f"Task '{task}' marked as complete"

    @tool
    def get_incomplete_todos(self) -> dict:
        """Return a list of all incomplete todos."""
        results = {}
        for file in sorted((self.base_dir / "todos").glob("*.json")):
            with file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)

            incomplete = [todo for todo in data.get("todos", []) if not todo.get("completed", False)]
            if incomplete:
                results[file.stem] = incomplete

        return results

    @tool
    def get_todo_summary(self) -> dict:
        """Return a simple summary of todo progress across files."""
        totals = {"files": 0, "tasks": 0, "completed": 0, "incomplete": 0, "by_tag": {}}
        for file in sorted((self.base_dir / "todos").glob("*.json")):
            with file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            totals["files"] += 1
            for todo in data.get("todos", []):
                totals["tasks"] += 1
                if todo.get("completed", False):
                    totals["completed"] += 1
                else:
                    totals["incomplete"] += 1
                tag = todo.get("tag", "") or "untagged"
                totals["by_tag"][tag] = totals["by_tag"].get(tag, 0) + 1
        return totals

    @tool
    def add_task(self, file_title: str, task: str, tag: str = "") -> str:
        """Add a new task to a todo entry."""
        path = self._entry_path("todos", file_title)
        if not path.exists():
            return f"Todo '{file_title}' not found"

        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        data["todos"].append({"task": task, "completed": False, "tag": tag})
        self._write_json(path, data)
        return f"Task '{task}' added to '{file_title}'"

    @tool
    def update_entry(self, file_title: str, content: str, mode: str = "w") -> str:
        """Update a writing entry by its title."""
        for type_entry in ["notes", "journals"]:
            path = self._entry_path(type_entry, file_title)
            if not path.exists():
                continue

            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)

            if mode == "a":
                data["content"] = f"{data.get('content', '')}\n{content}".strip()
            else:
                data["content"] = content

            self._write_json(path, data)
            return f"Entry '{file_title}' updated"

        return f"Entry '{file_title}' not found"

    @tool
    def get_today(self) -> str:
        return date.today().strftime("%Y-%m-%d")

    def list_writing_tools(self) -> list:
        return [
            self.create_notes_entry,
            self.create_journal_entry,
            self.create_todo_entry,
            self.list_writing_entries,
            self.search_entries,
            self.read_entry,
            self.complete_todo,
            self.get_incomplete_todos,
            self.get_todo_summary,
            self.add_task,
            self.update_entry,
            self.get_today,
        ]


@tool
def use_writing_tools(message: str) -> str:
    writer = Writer()

    model = OllamaModel(
        model_id='qwen2.5:1.5b',
        host="http://localhost:11434",
    )

    agent = Agent(
        model=model,
        system_prompt="You are a helpful assistant specializing in reading, writing, and summarizing notes, journals, and todo lists. Note that the titles of the files are just the days they were written.",
        tools=writer.list_writing_tools(),
    )

    response = agent(message)

    try:
        return response.message["content"][0]["text"]  # type: ignore
    except Exception as e:
        return f"An error occurred when doing your request - try again: {e}"