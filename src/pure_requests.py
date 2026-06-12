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

class Getting:
    # makes a request to telegram API and converts the result
    @staticmethod
    def get_messages(timeout: int) -> Messages:
        info: Messages = []

        # handling error with parse .env
        raw_id: str | None = get_key(ENV_PATH, "LAST_UPDATE_ID")
        try:
            last_update_id = int(raw_id) # emphasizing this in IDE is normal, errors are handled
        except (ValueError, TypeError) as Error:
            error = "Failed to parse last update id from .env"
            print(f"\nError: Failed to parse last update id from .env")
            raise Error(error)

        try:
            response = requests.get(f"{BASE_URL}/getUpdates", json={
                "offset": last_update_id + 1, # the last update id + 1 for deleting messages after they are received
                "timeout": timeout,
                "allowed_updates": ["message", "edited_message", "business_message", "edited_business_message", "deleted_business_messages"]
            }).json()

        # handling errors with a request to the telegram api
        except requests.exceptions.RequestException as e:
            print(f"Request error: ({e})\nCheck your internet connection or telegram services status")
            raise requests.exceptions.RequestException(e)
        if not response['ok']:
            error: str = f"Error {response['error_code']}, {response['description']}"
            print(f"\nRequest error: ({error})")
            raise requests.exceptions.RequestException(error)

        if response["result"]:
            set_key(ENV_PATH, "LAST_UPDATE_ID", str(response["result"][-1]["update_id"]))

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
                        "message_id": message['message_id'],
                        "language_code": message_from.get('language_code'),
                        "date": datetime.fromtimestamp(message['date'], ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M")
                    }
                })

                # adding content
                base: list[str] = ['file_id', 'file_unique_id', 'file_size']
                duration: list[str] = base + ['duration']
                keys: dict[str, list[str]] = {
                    "video": duration,
                    "animation": ['file_id', 'file_unique_id', 'duration'],
                    "document": base + ['file_name', 'mime_type'],
                    "sticker": ['file_id', 'emoji', 'set_name'],
                    "checklist": ['title', 'tasks', 'others_can_add_tasks', 'others_can_mark_tasks_as_done'],
                    "poll": ['id', 'question', 'options', 'is_closed', 'is_anonymous', 'allows_multiple_answers', 'allows_revoting'],
                    "video_note": duration,
                    "voice": ['file_id', 'file_unique_id', 'duration'],
                    "audio": duration,
                    "contact": ['phone_number', 'first_name', 'last_name', 'user_id']
                }
                photo_keys: list[str] = base
                info[-1]["content"] = {
                    "media_group_id": message.get('media_group_id')
                }

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

        return info

class Sending:
    @staticmethod
    def send_text(chat_id: str,
                  text: str,
                  disable_notification: bool = False,
                  protect_content: bool = False,
                  enable_link_preview: bool = False) -> str:
        try:
            response = requests.post(f"{BASE_URL}/sendMessage", json={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_notification': disable_notification,
                'protect_content': protect_content,
                'link_preview_options': {
                    'is_disabled': not enable_link_preview
                }
            }).json()

        # handling errors with a request to the telegram api
        except requests.exceptions.RequestException as e:
            print(f"Request error: ({e})\nCheck your internet connection or telegram services status")
            raise requests.exceptions.RequestException(e)
        if not response['ok']:
            error: str = f"Error {response['error_code']}, {response['description']}"
            print(f"\nRequest error: ({error})")
            raise requests.exceptions.RequestException(error)

        return "success"

    @staticmethod
    def send_reply_text(chat_id: str,
                        text: str,
                        reply_message_id: str,
                        disable_notification: bool = False,
                        protect_content: bool = False,
                        enable_link_preview: bool = False,
                        quote: str | None = None) -> str:
        data: dict[str, Any] = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_notification': disable_notification,
            'protect_content': protect_content,
            'link_preview_options': {
                'is_disabled': not enable_link_preview
            }
        }

        if quote:
            data['reply_parameters'] = {
                'message_id': reply_message_id,
                'quote': quote,
                'quote_parse_mode': 'HTML'
            }
        else:
            data['reply_parameters'] = {'message_id': reply_message_id}

        try:
            response = requests.post(f"{BASE_URL}/sendMessage", json=data).json()

        # handling errors with a request to the telegram api
        except requests.exceptions.RequestException as e:
            print(f"Request error: ({e})\nCheck your internet connection or telegram services status")
            return str(e)
        if not response['ok']:
            error: str = f"Error {response['error_code']}, {response['description']}"
            print(f"\nRequest error: ({error})")
            raise requests.exceptions.RequestException(error)

        return "success"

    @staticmethod
    def send_photo(chat_id: str,
                   photo_id: str,
                   disable_notification: bool = False,
                   protect_content: bool = False,
                   caption: str | None = None,
                   show_caption_above_media: bool = False,
                   has_spoiler: bool = False) -> str:
        data = {
            'chat_id': chat_id,
            'photo': photo_id,
            'disable_notification': disable_notification,
            'protect_content': protect_content,
            'parse_mode': 'HTML',
            'caption': caption,
            'has_spoiler': has_spoiler
        }
        if caption and show_caption_above_media:
            data['show_caption_above_media'] = show_caption_above_media

        try:
            response = requests.get(f"{BASE_URL}/sendMessage", params=data).json()

        # handling errors with a request to the telegram api
        except requests.exceptions.RequestException as e:
            print(f"Request error: ({e})\nCheck your internet connection or telegram services status")
            return str(e)
        if not response['ok']:
            error: str = f"Error {response['error_code']}, {response['description']}"
            print(f"\nRequest error: ({error})")
            return error

        return "success"