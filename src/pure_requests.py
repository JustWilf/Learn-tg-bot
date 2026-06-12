# Literally pure requests to telegram API
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any
from dotenv import load_dotenv, set_key, get_key
from os import getenv
import requests
import json


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH) # load .env file with token and so on

TOKEN: str | None = getenv("TOKEN")  # load telegram-bot token from .env file
BASE_URL: str = f"https://api.telegram.org/bot{TOKEN}"  # telegram-api url layout for requests

# handling error with load .env
if not TOKEN:
    print("Failed to load token from .env")

type Messages = list[dict[str, Any]] # type alias for the final appearance of messages
type default_dict = dict[str, Any]

class TelegramError(Exception):
    """Any error with requests to telegram api."""
def _api_request(method: str, data: default_dict) -> str:
    try:
        response = requests.post(f"{BASE_URL}/{method}", json=data, timeout=10).json()

    # handling errors with a request to the telegram api
    except requests.exceptions.RequestException as e:
        print(f"Request error: ({e})\nCheck your internet connection or telegram services status")
        return str(e)
    if not response['ok']:
        error: str = f"Error {response['error_code']}, {response['description']}"
        print(f"\nRequest error: ({error})")
        return error

    return "success"

# makes a request to telegram api and converts the result
class Getting:
    @staticmethod
    def get_messages(timeout: int) -> Messages:
        messages: Messages = []

        # handling error with parse .env
        raw_id: str | None = get_key(ENV_PATH, "LAST_UPDATE_ID")
        try:
            last_update_id = int(raw_id) # emphasizing this in IDE is normal, errors are handled
        except (ValueError, TypeError):
            error = "Failed to parse last update id from .env"
            print(f"\nError: Failed to parse last update id from .env")
            raise TelegramError(error)

        try:
            response = requests.get(f"{BASE_URL}/getUpdates", params={
                "offset": last_update_id + 1, # the last update id + 1 for deleting messages after they are received
                "timeout": timeout,
                "allowed_updates": json.dumps(["message", "edited_message"])
            }).json()

        # handling errors with a request to the telegram api
        except requests.exceptions.RequestException as e:
            print(f"Request error: ({e})\nCheck your internet connection or telegram services status")
            raise TelegramError(e)
        if not response['ok']:
            error: str = f"Error {response['error_code']}, {response['description']}"
            print(f"\nRequest error: ({error})")
            raise TelegramError(error)

        result = response["result"]
        if result:
            set_key(ENV_PATH, "LAST_UPDATE_ID", str(response["result"][-1]["update_id"]))

        for update in result:
            message_from: default_dict = update['message']['from'] if 'message' in update else update['edited_message']['from']
            if not message_from['is_bot']:
                message: default_dict = update['message'] if 'message' in update else update['edited_message']

                # adding all data required for the bot
                messages.append({
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
                messages[-1]["content"] = {
                    "media_group_id": message.get('media_group_id')
                }
                messages[-1]["data"]["content_type"] = None
                content = messages[-1]["content"]

                if 'text' in message:
                    messages[-1]["content"] = message['text']
                elif 'photo' in message:
                    photo: default_dict = message['photo'][-1]
                    place: default_dict = content
                    messages[-1]["data"]["content_type"] = "photo"
                    for field in photo_keys:
                        place[field] = photo.get(field)
                else:
                    for field in keys:
                        if field in message:
                            place: default_dict = content
                            content: default_dict = message[field]
                            messages[-1]["data"]["content_type"] = field
                            for k in keys[field]:
                                place[k] = content.get(k)
                            break
                if 'caption' in message:
                    messages[-1]["content"]["caption"] = message['caption']

        return messages

class Sending:
    @staticmethod
    def send_text(chat_id: str,
                  text: str,
                  disable_notification: bool = False,
                  protect_content: bool = False,
                  enable_link_preview: bool = False) -> str:
        return _api_request("sendMessage", {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_notification': disable_notification,
            'protect_content': protect_content,
            'link_preview_options': {
                'is_disabled': not enable_link_preview
            }
        })

    @staticmethod
    def send_reply_text(chat_id: str,
                        text: str,
                        reply_message_id: str,
                        disable_notification: bool = False,
                        protect_content: bool = False,
                        enable_link_preview: bool = False,
                        quote: str | None = None) -> str:
        data: default_dict = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_notification': disable_notification,
            'protect_content': protect_content,
            'link_preview_options': {
                'is_disabled': not enable_link_preview
            }
        }
        # adding dependent parameters
        if quote:
            data['reply_parameters'] = {
                'message_id': reply_message_id,
                'quote': quote,
                'quote_parse_mode': 'HTML'
            }
        else:
            data['reply_parameters'] = {'message_id': reply_message_id}

        return _api_request("sendMessage", data)

    @staticmethod
    def send_photo(chat_id: str,
                   photo_id: str,
                   disable_notification: bool = False,
                   protect_content: bool = False,
                   caption: str | None = None,
                   show_caption_above_media: bool = False,
                   has_spoiler: bool = False) -> str:
        data: default_dict = {
            'chat_id': chat_id,
            'photo': photo_id,
            'disable_notification': disable_notification,
            'protect_content': protect_content,
            'parse_mode': 'HTML',
            'caption': caption,
            'has_spoiler': has_spoiler
        }
        # adding dependent parameter
        if caption and show_caption_above_media:
            data['show_caption_above_media'] = show_caption_above_media

        return _api_request("sendPhoto", data)

    @staticmethod
    def send_reply_photo(chat_id: str,
                         photo_id: str,
                         reply_message_id: str,
                         disable_notification: bool = False,
                         protect_content: bool = False,
                         caption: str | None = None,
                         show_caption_above_media: bool = False,
                         has_spoiler: bool = False,
                         quote: str | None = None) -> str:
        data: default_dict = {
            'chat_id': chat_id,
            'photo': photo_id,
            'disable_notification': disable_notification,
            'protect_content': protect_content,
            'parse_mode': 'HTML',
            'has_spoiler': has_spoiler
        }
        # adding dependent parameters
        if caption:
            data['caption'] = caption
            if show_caption_above_media:
                data['show_caption_above_media'] = show_caption_above_media
        if quote:
            data['reply_parameters'] = {
                'message_id': reply_message_id,
                'quote': quote,
                'quote_parse_mode': 'HTML'
            }
        else:
            data['reply_parameters'] = {'message_id': reply_message_id}

        return _api_request("sendPhoto", data)

    @staticmethod
    def forward_message(chat_id: str,
                        from_chat_id: str,
                        message_id: str,
                        disable_notification: bool = False,
                        protect_content: bool = False,
                        caption: str | None = None) -> str:
        data: default_dict = {
            'chat_id': chat_id,
            'from_chat_id': from_chat_id,
            'message_id': message_id,
            'disable_notification': disable_notification,
            'protect_content': protect_content,
            'parse_mode': 'HTML'
        }
        # adding dependent parameter
        if caption:
            data['caption'] = caption

        return _api_request("copyMessage", data)

if __name__ == '__main__':
    Sending.send_text('1560997223', '<u><b>ГДЕ МОЕ ДЗ?!!</b></u>')