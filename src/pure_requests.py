# Literally pure requests to telegram API
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any
from dotenv import load_dotenv, set_key, get_key
from os import getenv
import requests


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH) # load .env file with token and so on

TOKEN: str | None = getenv("TOKEN")  # load telegram-bot token from .env file
BASE_URL: str = f"https://api.telegram.org/bot{TOKEN}"  # telegram-api url layout for requests

# handling error with load .env
if not TOKEN:
    print("Failed to load token from .env")

type Messages = list[dict[str, Any]] # type alias for the final appearance of messages
type default_dict = dict[str, str | int | bool | None]

# makes a request to telegram API and converts the result
def get_messages(timeout: int) -> Messages | str:
    info: Messages = []

    # handling error with parse .env
    raw_id: str | None = get_key(ENV_PATH, "LAST_UPDATE_ID")
    try:
        last_update_id = int(raw_id) # emphasizing this in IDE is normal, errors are handled
    except (ValueError, TypeError):
        error = "Failed to parse last update id from .env"
        print(f"\nError: {error}")
        return error

    try:
        response = requests.get(f"{BASE_URL}/getUpdates", params={
            "offset": last_update_id + 1, # the last update id + 1 for deleting messages after they are received
            "timeout": timeout
        }).json()
    except ConnectionError as e:
        print(f"Request error: ({e})\nCheck your internet connection or telegram services status")
        return str(e)

    # handling errors with a request to the telegram api
    if not response['ok']:
        error: str = f"Error {response['error_code']}: {response['description']}"
        print(f"\nRequest error: ({error})")
        return error

    if response["result"]:
        set_key(ENV_PATH, "LAST_UPDATE_ID", response["result"][-1]["update_id"])

    for i in response['result']:
        message_from: dict[str, Any] = i['message']['from']
        if not message_from['is_bot']:
            message: dict[str, Any] = i['message']

            # adding all data required for the bot
            info.append({
                "id": message_from['id'],
                "user": {
                    "first_name": message_from['first_name'],
                    "last_name": message_from.get('last_name'),
                    "username": message_from.get('username'),
                    "is_premium": message_from.get('is_premium')
                },
                "data": {
                    "language_code": message_from.get('language_code'),
                    "date": datetime.fromtimestamp(message['date'], ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M")
                }
            })

            # adding content
            base: list[str] = ['file_id', 'file_unique_id', 'file_size']
            keys: dict[str, list[str]] = {
                "video": base + ['duration'],
                "animation": ['file_id', 'file_unique_id', 'duration'],
                "document": base + ['file_name', 'mime_type'],
                "sticker": ['file_id', 'emoji', 'set_name'],
                "location": ['latitude', 'longitude'],
                "checklist": ['title', 'tasks', 'others_can_add_tasks', 'others_can_mark_tasks_as_done'],
                "poll": ['id', 'question', 'options', 'is_closed', 'is_anonymous', 'allows_multiple_answers', 'allows_revoting']
            }
            photo_keys: list[str] = base
            info[-1]["content"] = {}

            if 'text' in message:
                info[-1]["content"] = message['text']
            elif 'photo' in message:
                photo: default_dict = message['photo'][-1]
                place: default_dict = info[-1]["content"]
                info[-1]["data"]["content_type"] = "photo"
                for j in photo_keys:
                    place[j] = photo.get(j)
            else:
                for j in keys:
                    if j in message:
                        place: default_dict = info[-1]["content"]
                        content: default_dict = message[j]
                        info[-1]["data"]["content_type"] = j
                        for k in keys[j]:
                            place[k] = content.get(k)
                        break
            if 'caption' in message:
                info[-1]["content"]["caption"] = message['caption']
    print(response)
    return info