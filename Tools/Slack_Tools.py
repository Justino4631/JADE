from strands.models.ollama import OllamaModel
from strands import Agent, tool
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import os
from dotenv import load_dotenv
import json

load_dotenv()

class SlackBot():
    def __init__(self, client) -> None:
        self.client = client
        self.last_fetched = []
        self._load_all()

    def _load_users(self) -> None:
        response = self.client.users_list()
        self.users = {user["id"]: user["real_name"] for user in response["members"] if not user["deleted"]}

    def _load_channels(self):
        response = self.client.conversations_list()
        self.channels = {channel["id"]: channel["name"] for channel in response["channels"]}

    def _load_all(self) -> None:
        self._load_users()
        self._load_channels()

    def _get_channel_id(self, channel: str) -> str | None:
        return next((cid for cid, name in self.channels.items() if name.lower() == channel.lower()), None)

    def _get_user_id(self, user: str) -> str | None:
        return next((uid for uid, name in self.users.items() if name.lower() == user.lower()), None)

    def _open_dm(self, user: str):
        user_id = self._get_user_id(user)
        if not user_id:
            return None, f"User '{user}' not found"
        dm = self.client.conversations_open(users=user_id)
        return dm["channel"]["id"], None

    @tool
    def get_users(self) -> dict:
        return self.users

    @tool 
    def get_channels(self) -> dict:
        return self.channels

    @tool
    def get_messages(self, channel: str = "", num_messages: int = 5) -> list | str:
        """Get messages from a specific channel by name, or all channels if none specified"""
        if channel:
            channel_id = self._get_channel_id(channel)
            if not channel_id:
                return f"Channel '{channel}' not found"
            channels = {channel_id: channel}
        else:
            channels = self.channels

        messages = []
        for chan_id, chan_name in channels.items():
            try:
                response = self.client.conversations_history(channel=chan_id, limit=num_messages)
                for message in response["messages"]:
                    messages.append({
                        "channel": chan_name,
                        "user": self.users.get(message.get("user"), "Unknown"),
                        "text": message.get("text"),
                        "timestamp": message.get("ts")
                    })
            except SlackApiError:
                print(f"Bot not in {chan_name}")
                continue

        self.last_fetched = messages
        return messages

    @tool
    def get_new_messages(self) -> list:
        """Get only messages newer than the last saved fetch across all channels"""
        try:
            with open("slack_messages/latest_messages.json") as f:
                prev_messages = json.load(f)
        except FileNotFoundError:
            prev_messages = {}
        
        new_messages = []
        for chan_id, chan_name in self.channels.items():
            try:
                latest_timestamp = prev_messages.get(chan_id, "0")
                response = self.client.conversations_history(channel=chan_id, oldest=latest_timestamp)

                for message in response["messages"]:
                    new_messages.append({
                        "channel": chan_name,
                        "user": self.users.get(message.get("user"), "Unknown"),
                        "text": message.get("text"),
                        "timestamp": message.get("ts")
                    })
            except SlackApiError as e:
                print(f"An error occurred: {e}")
                continue
            
        with open("slack_messages/latest_messages.json", "w") as file:
            json.dump(new_messages, file)
            
        self.last_fetched = new_messages
        return new_messages

    @tool
    def get_messages_dm(self, user: str, num_messages: int = 5) -> list | str:
        """Get DM messages with a user by their name"""
        dm_id, error = self._open_dm(user)
        if error:
            return error

        try:
            response = self.client.conversations_history(channel=dm_id, limit=num_messages)
            messages = [
                {
                    "user": self.users.get(message.get("user"), "Unknown"),
                    "text": message.get("text"),
                    "timestamp": message.get("ts")
                }
                for message in response["messages"]
            ]
            self.last_fetched = messages
            return messages
        except SlackApiError as e:
            return f"Error fetching DMs: {e.response['error']}"
    
    @tool
    def get_new_messages_dm(self, user: str) -> list | str:
        """Get new DM messages from a user since last fetch"""
        dm_id, error = self._open_dm(user)
        if error:
            return error
        
        try:
            with open("slack_messages/latest_dm_messages.json") as f:
                prev_latest_messages = json.load(f)
        except FileNotFoundError:
            prev_latest_messages = {}
        
        try:
            latest_ts = prev_latest_messages.get(dm_id, "0")
            response = self.client.conversations_history(channel=dm_id, oldest=latest_ts)

            new_messages = [
                {
                    "user": self.users.get(message.get("user"), "Unknown"),
                    "text": message.get("text"),
                    "timestamp": message.get("ts")
                }
                for message in response["messages"]
            ]

            with open("slack_messages/latest_dm_messages.json", "w") as f:
                json.dump(new_messages, f)
            
            self.last_fetched = new_messages
            return new_messages
        
        except SlackApiError as e:
            return f"Error fetching new DMs: {e.response['error']}"

    @tool
    def get_replies(self, message_index: int, channel: str = "") -> list | str:
        """Get replies to a message by its index in the last fetched messages"""
        if not self.last_fetched:
            return "No messages fetched yet, call get_messages first"
        
        if message_index >= len(self.last_fetched):
            return f"Message index {message_index} out of range"

        message = self.last_fetched[message_index]
        thread_ts = message["timestamp"]

        if channel:
            chan_id = self._get_channel_id(channel)
        else:
            chan_id = next((cid for cid, name in self.channels.items() if name == message.get("channel")), None)

        if not chan_id:
            return "Could not determine channel for this message"

        try:
            response = self.client.conversations_replies(channel=chan_id, ts=thread_ts)
            return [
                {
                    "user": self.users.get(m.get("user"), "Unknown"),
                    "text": m.get("text"),
                    "timestamp": m.get("ts")
                }
                for m in response["messages"][1:]
            ]
        except SlackApiError as e:
            return f"Error fetching replies: {e.response['error']}"

    @tool
    def search_messages(self, query: str) -> list:
        """Search for messages containing a keyword across all channels and DMs"""
        results = []

        for chan_id, chan_name in self.channels.items():
            try:
                response = self.client.conversations_history(channel=chan_id, limit=100)
                for m in response["messages"]:
                    if query.lower() in m.get("text", "").lower():
                        results.append({
                            "channel": chan_name,
                            "user": self.users.get(m.get("user"), "Unknown"),
                            "text": m.get("text"),
                            "timestamp": m.get("ts")
                        })
            except SlackApiError:
                continue

        for user_id, user_name in self.users.items():
            try:
                dm = self.client.conversations_open(users=user_id)
                dm_id = dm["channel"]["id"]
                response = self.client.conversations_history(channel=dm_id, limit=100)
                for m in response["messages"]:
                    if query.lower() in m.get("text", "").lower():
                        results.append({
                            "channel": f"DM with {user_name}",
                            "user": self.users.get(m.get("user"), "Unknown"),
                            "text": m.get("text"),
                            "timestamp": m.get("ts")
                        })
            except SlackApiError:
                continue

        return results

    @tool
    def send_message(self, channel: str, message: str) -> str:
        """Send a message to a channel by name"""
        chan_id = self._get_channel_id(channel)
        if not chan_id:
            return f"Channel '{channel}' not found"
        try:
            self.client.chat_postMessage(channel=chan_id, text=message)
            return f"Message sent to #{channel}"
        except SlackApiError as e:
            return f"Error sending message: {e.response['error']}"

    @tool
    def send_dm(self, user: str, message: str) -> str:
        """Send a direct message to a user by name"""
        dm_id, error = self._open_dm(user)
        if error:
            return error
        try:
            self.client.chat_postMessage(channel=dm_id, text=message)
            return f"DM sent to {user}"
        except SlackApiError as e:
            return f"Error sending DM: {e.response['error']}"

    @tool
    def reply_to_thread(self, message_index: int, reply: str, channel: str = "") -> str:
        """Reply to a message by its index in the last fetched messages"""
        if not self.last_fetched:
            return "No messages fetched yet, call get_messages first"

        if message_index >= len(self.last_fetched):
            return f"Message index {message_index} out of range"

        message = self.last_fetched[message_index]
        thread_ts = message["timestamp"]

        if channel:
            chan_id = self._get_channel_id(channel)
        else:
            chan_id = next((cid for cid, name in self.channels.items() if name == message.get("channel")), None)

        if not chan_id:
            return "Could not determine channel for this message"

        try:
            self.client.chat_postMessage(channel=chan_id, text=reply, thread_ts=thread_ts)
            return f"Reply sent successfully"
        except SlackApiError as e:
            return f"Error sending reply: {e.response['error']}"

    def list_slack_tools(self) -> list:
        return [
            self.get_users, self.get_channels, self.get_messages,
            self.get_messages_dm, self.get_new_messages, self.get_new_messages_dm,
            self.get_replies, self.search_messages, self.send_message,
            self.send_dm, self.reply_to_thread
        ]

def use_slack_bot(message: str) -> str:
    slackbot = SlackBot(WebClient(token=os.getenv("SLACK_BOT_TOKEN")))

    model = OllamaModel(
        model_id="granite4.1:8b",
        host="http://localhost:11434"
    )

    agent = Agent(
        model=model,
        system_prompt="You are a helpful slack bot assistant that tracks conversations and provides helpful responses. You are able to search, read, and write messages in channels. If an error occurs, simply return the error and its source.",
        tools=slackbot.list_slack_tools()
    )

    response = agent(message)

    try:
        return response.message["content"][0]["text"] #type: ignore
    except (KeyError, IndexError):
        return "I'm sorry, I couldn't retrieve the information."