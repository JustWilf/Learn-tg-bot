# Literally pure requests to telegram API
from dotenv import load_dotenv
import os
import requests

load_dotenv()
TOKEN:str|None = os.environ.get("TOKEN")
BASE_URL:str = f"https://api.telegram.org/bot{TOKEN}"

def get_messages() -> list[dict[str, str|dict[str, str]]] | str:
    global TOKEN, BASE_URL
    info = []
    r = requests.get(f"{BASE_URL}/getUpdates").json()

    if not r['ok']:
        return f"{r['error_code']}, {r['description']}"

    for i in r['result']:
        message_from = i['message']['from']
        if not message_from['is_bot']:
            message = i['message']

            # Adding else message data to the info (not content)
            info.append({
                "id": message_from['id'],
                "user": {
                    "first_name": message_from['first_name'],
                    "username": message_from['username'],
                    "is_premium": message_from['is_premium']
                },
                "data": {
                    "update_id": i['update_id'],
                    "date": message['date'],
                    "language_code": message_from['language_code']
                }
            })

            # Adding the message content to the info
            if 'text' in message:
                info[-1]["text"] = message['text']
            elif 'photo' in message:
                info[-1]["photo"] = __extract_file(message['photo'][-1]) # -1 to select the maximum resolution photo

            elif 'video' in message:
                info[-1]["video"] = __extract_file(message['video'], "duration")

                if 'caption' in message:
                    info[-1]["video"]["caption"] = message['caption']

            elif 'animation' in message:
                info[-1]["animation"] = __extract_file(message['animation'], "duration")
                info[-1]["animation"].pop("file_size", None)

            elif 'document' in message:
                info[-1]["document"] = __extract_file(message['document'], "file_name", "mime_type")

                if 'caption' in message:
                    info[-1]["document"]["caption"] = message['caption']

            elif 'sticker' in message:
                info[-1]["sticker"] = __extract_file(message['sticker'], "emoji", "is_animated")

            elif 'poll' in message: info[-1]["content_type"] = "poll"
            elif 'checklist' in message: info[-1]["content_type"] = "checklist"
            elif 'location' in message: info[-1]["content_type"] = "location"
            else: info[-1]["content_type"] = "transfer"
            # print(info[-1]) # for easy data viewing during development

    return info

# Handler for only get_messages()
def __extract_file(obj, *extra):
    keys = ("file_id", "file_unique_id", "file_size", *extra)
    return {k: obj[k] for k in keys if k in obj}

print(get_messages())