import os
import json
import hashlib
import requests
from io import BytesIO
from pydub import AudioSegment
from openai import OpenAI


GET_RESULT_CONTENT_TYPE = {'Content-Type': 'text/plain'}


def confirm_webhook_subscription(event: dict) -> dict:
    if event.get('hub.mode', '') != 'subscribe':
        return {"body": "Invalid mode", "statusCode": 400, "headers": GET_RESULT_CONTENT_TYPE}
    elif event.get('hub.verify_token', '') != os.environ.get("VERIFICATION_TOKEN"):
        return {"body": "Verification token mismatch", "statusCode": 403, "headers": GET_RESULT_CONTENT_TYPE}
    else:
        return {"body": event.get('hub.challenge', ''), "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}


def get_format_from_mime_type(mime_type: str) -> str:
    if mime_type == 'audio/aac':
        return 'aac'
    elif mime_type == 'audio/mp4':
        return 'm4a'
    elif mime_type == 'audio/mpeg':
        return 'mp3'
    elif mime_type == 'audio/amr':
        return 'amr'
    elif mime_type == 'audio/ogg':
        return 'ogg'


def get_audio_file(audio_id: str) -> BytesIO:
    url = f"https://graph.facebook.com/v19.0/{audio_id}/"
    headers = {
        'Authorization': f'Bearer {os.environ.get("GRAPH_API_TOKEN")}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    file_url, file_hash = response.json()['url'], response.json()['sha256']
    file_response = requests.get(file_url, headers=headers)
    file_response.raise_for_status()
    hashed_content = hashlib.sha256(file_response.content).hexdigest()
    if hashed_content != file_hash:
        raise requests.HTTPError()
    return BytesIO(file_response.content)


def convert_audio(audio_file: BytesIO, mime_type: str) -> BytesIO:
    audio_format = get_format_from_mime_type(mime_type)
    if audio_format == 'ogg':
        sound = AudioSegment.from_file(audio_file, format=audio_format, codec='opus')
    else:
        sound = AudioSegment.from_file(audio_file, format=audio_format)
    converted_audio = BytesIO()
    sound.export(converted_audio, format='mp3')
    return converted_audio


def process_audio(audio_id: str, audio_mime_type: str, phone_number_id: str, sender: str, client: OpenAI):
    with get_audio_file(audio_id) as audio_file:
        with convert_audio(audio_file, audio_mime_type) as converted_audio:
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=converted_audio,
                temperature=0.7
            ).text
            response = requests.post(
                url=f"https://graph.facebook.com/v19.0/{phone_number_id}/messages",
                headers={'Authorization': f'Bearer {os.environ.get("GRAPH_API_TOKEN")}'},
                data={
                    'messaging_product': 'whatsapp',
                    'to': f'{sender}',
                    'text': { 'body': f'{transcription}' },
                }
            )
            response.raise_for_status()


def process_text(phone_number_id: str, sender: str):
    response = requests.post(
        url=f"https://graph.facebook.com/v19.0/{phone_number_id}/messages",
        headers={'Authorization': f'Bearer {os.environ.get("GRAPH_API_TOKEN")}'},
        data={
            'messaging_product': 'whatsapp',
            'to': f'{sender}',
            'text': { 'body': 'Hola! Envíame un audio para responderte con la transcripción del mismo.' },
        }
    )
    response.raise_for_status()


def process_change(change: dict, client: OpenAI):
    if 'value' not in change or 'messages' not in change['value'] or 'metadata' not in change['value'] or len(change['value']['messages']) == 0:
        raise requests.HTTPError()
    value = change['value']
    messages = value['messages']
    metadata = value['metadata']
    for message in messages:
        if message['type'] == 'audio':
            process_audio('audio', message['audio']['id'], metadata['phone_number_id'], message['from'], client)
        if message['type'] == 'text':
            process_text(metadata['phone_number_id'], message['from'])


def process_event(event: dict, client: OpenAI):
    if 'entry' not in event or len(event['entry']) == 0:
        raise requests.HTTPError()
    entries = event['entry']
    for entry in entries:
        if 'changes' not in entry or len(entry['changes']) == 0:
            raise requests.HTTPError()
        changes = entry['changes']
        for change in changes:
            process_change(change, client)


def main(event: dict, _) -> dict:
    print("New request received")
    if 'http' not in event:
        return {"body": "Invalid request", "statusCode": 400, "headers": GET_RESULT_CONTENT_TYPE}
    elif event['http']['method'] == 'GET':
        return confirm_webhook_subscription(event)
    elif event['http']['method'] == 'POST':
        client = OpenAI(os.environ.get("OPENAI_API_KEY"))
        try:
            process_event(event, client)
        except Exception as e:
            print(f"Failed to process the request: {str(e)}")
            clean_event = {key: value for key, value in event.items() if not (key.startswith('__ow') or key == 'http')}
            print(f"Request body: {json.dumps(clean_event)}")
            return {"body": "Invalid request", "statusCode": 400, "headers": GET_RESULT_CONTENT_TYPE}
        return {"body": "", "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}
