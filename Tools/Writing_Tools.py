from strands import tool, Agent
from strands.models.ollama import OllamaModel
from datetime import date
import time
import json
import os

class Writer():
    def __init__(self) -> None:
        pass

    @tool
    def create_notes_entry(self, content: str) -> None:
        """Create a new notes entry."""
        today = date.today()
        today = today.strftime("%Y-%m-%d")
        file_name = f"{today}_Notes"

        json_to_write = {
            "date": today,
            "content": content
        }

        with open(f"notes/{file_name}.json", "w") as file:
            json.dump(json_to_write, file)
    
    @tool
    def create_todo_entry(self, tasks: list, tags: list = []) -> None:
        """Create a new todo entry."""
        today = date.today()
        today = today.strftime("%Y-%m-%d")
        file_name = f"{today}_Todos"

        json_to_write = {
            "date": today,
            "todos": [
                {
                    "task": task,
                    "completed": False,
                    "tag": tags[i] if i < len(tags) else ""
                }
                for i, task in enumerate(tasks)
            ]
        }

        with open(f"todos/{file_name}.json", "w") as file:
            json.dump(json_to_write, file, indent=2)
    
    @tool
    def create_journal_entry(self, content: str) -> None:
        """Create a new journal entry."""
        today = date.today()
        today = today.strftime("%Y-%m-%d")
        file_name = f"{today}_Journals"

        json_to_write = {
            "date": today,
            "content": content
        }

        with open(f"journals/{file_name}.json", "w") as file:
            json.dump(json_to_write, file)

    @tool
    def list_writing_entries(self, query: str = "", type_entry: str = "notes") -> dict:
        """Return a list of writing entries based on the query and type. If the user asks about todos, for example, the type_entry should be 'todos'."""
        if type_entry not in ["notes", "todos", "journals"]:
            return {}

        files = os.listdir(f"{type_entry}/")
        results = {}

        for file in files:
            if query.lower() in file.lower() or not query:
                with open(f"{type_entry}/{file}") as f:
                    data = json.load(f)
                
                if type_entry == "todos":
                    preview = [t["task"] for t in data.get("todos", [])]
                else:
                    preview = data.get("content", "")[:75]
                
                results[file.replace(".json", "")] = preview

        return results
    
    @tool
    def read_entry(self, file_title: str) -> dict:
        """Read a writing entry by its title."""
        for type_entry in ["notes", "todos", "journals"]:
            path = f"{type_entry}/{file_title}.json"
            if os.path.exists(path):
                with open(path) as f:
                    return json.load(f)
        
        return {}
    
    @tool
    def complete_todo(self, file_title: str, task: str) -> str:
        """Mark a todo as complete."""
        path = f"todos/{file_title}.json"
        if not os.path.exists(path):
            return f"Todo '{file_title}' not found"
        
        with open(path) as file:
            data = json.load(file)
        
        todo_match = next((t for t in data["todos"] if t["task"].lower() == task.lower()), None)
        if not todo_match:
            return f"Task '{task}' not found in '{file_title}'"
        
        todo_match['completed'] = True
        
        with open(path, 'w') as file:
            json.dump(data, file)
        
        return f"Task '{task}' marked as complete"
    
    @tool
    def get_incomplete_todos(self) -> dict:
        """Return a list of all incomplete todos."""
        results = {}
        for file in os.listdir("todos/"):
            with open(f"todos/{file}") as f:
                data = json.load(f)

            incomplete = [task for task in data['todos'] if not task['completed']]
            if incomplete:
                results[file.replace(".json", "")] = incomplete
            
        return results

    @tool
    def add_task(self, file_title: str, task: str, tag: str = "") -> str:
        """Add a new task to a todo entry."""
        path = f"todos/{file_title}.json"
        if not os.path.exists(path):
            return f"Todo '{file_title}' not found"
        
        with open(path) as f:
            data = json.load(f)
        
        data['todos'].append({
            "task": task,
            "completed": False,
            "tag": tag
        })

        with open(path, "w") as f:
            json.dump(data, f)
        
        return f"Task '{task}' added to '{file_title}'"

    @tool
    def update_entry(self, file_title: str, content: str, mode: str = "w") -> str:
        """Update a writing entry by its title."""
        for type_entry in ["notes", "journals"]:
            path = f"{type_entry}/{file_title}.json"

            if os.path.exists(path):
                with open(path) as f:
                    data = json.load(f)
            
            if mode == "a":
                data["content"] += f"\n{content}"
            else:
                data['content'] = content
            
            with open(path, "w") as f:
                json.dump(data, f)
            
            return f"Entry '{file_title}' updated"
        
        return f"Entry '{file_title}' not found"

    @tool
    def get_today(self) -> str:
        return date.today().strftime("%Y-%m-%d")

    def list_writing_tools(self) -> list:
        return [self.create_notes_entry, self.create_journal_entry, self.create_todo_entry, self.list_writing_entries, self.read_entry, self.complete_todo, self.add_task, self.update_entry, self.get_today]

def use_writing_tools(message: str) -> str:

    writer = Writer()

    model = OllamaModel(
        model_id="granite4.1:8b",
        host="http://localhost:11434"
    )

    agent = Agent(
        model=model,
        system_prompt="You are a helpful assistant specializing in reading, writing, and summarizing notes, journals, and todo lists. Note that the titles of the files are just the days they were written.",
        tools=writer.list_writing_tools()
    )
    
    response = agent(message)

    try:
        return response.message["content"][0]['text'] #type: ignore
    except Exception as e:
        return f"An error occurred when doing your request- try again: {e}"

print(use_writing_tools("Alright, clear the todos for today. I forgot to do my Spanish HW and Call Liz."))