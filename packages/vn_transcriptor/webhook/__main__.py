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


def process_text(phone_number_id: str, sender: str, text: str = ""):
    if text == "":
        message = "Hola! Envíame un audio para responderte con la transcripción del mismo."
    else:
        message = text
    response = requests.post(
        url=f"https://graph.facebook.com/v19.0/{phone_number_id}/messages",
        headers={'Authorization': f'Bearer {os.environ.get("GRAPH_API_TOKEN")}'},
        data={
            'messaging_product': 'whatsapp',
            'to': f'{sender}',
            'text': { 'body': f'{message}' },
        }
    )
    response.raise_for_status()


def validate_mime_type(audio_mime_type: str) -> bool:
    valid_mime_types = ['flac', 'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'ogg', 'wav', 'webm']
    return any(mime_type in audio_mime_type for mime_type in valid_mime_types)


def get_audio_file(audio_id: str) -> BytesIO:
    url = f"https://graph.facebook.com/v19.0/{audio_id}/"
    headers = {
        'Authorization': f'Bearer {os.environ.get("GRAPH_API_TOKEN")}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_json = response.json()
    file_url, file_hash = response_json()['url'], response_json()['sha256']
    file_response = requests.get(file_url, headers=headers)
    file_response.raise_for_status()
    hashed_content = hashlib.sha256(file_response.content).hexdigest()
    if hashed_content != file_hash:
        raise requests.HTTPError()
    return BytesIO(file_response.content)


def process_audio(audio_id: str, audio_mime_type: str, phone_number_id: str, sender: str, client: OpenAI):
    if not validate_mime_type(audio_mime_type):
        process_text(
            phone_number_id,
            sender,
            f"Lo siento, el formato del audio no es válido. Los formatos válidos son: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav y webm. El formato del audio que enviaste es: ```{audio_mime_type}```"
        )
    with get_audio_file(audio_id) as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file,
            temperature=0.7
        ).text
        process_text(phone_number_id, sender, transcription)


def process_change(change: dict, client: OpenAI):
    if 'value' not in change or 'messages' not in change['value'] or 'metadata' not in change['value'] or len(change['value']['messages']) == 0:
        raise requests.HTTPError()
    value = change['value']
    messages = value['messages']
    metadata = value['metadata']
    for message in messages:
        if message['type'] == 'audio':
            process_audio(
                audio_id=message['audio']['id'],
                audio_mime_type=message['audio']['mime_type'],
                phone_number_id=metadata['phone_number_id'],
                sender=message['from'],
                client=client
            )
        if message['type'] == 'text':
            process_text(metadata['phone_number_id'], message['from'])
        else:
            process_text(metadata['phone_number_id'], message['from'], f"Lo siento, no puedo procesar este mensaje de tipo: ```{message['type']}```.")


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
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        try:
            process_event(event, client)
        except Exception as e:
            print(f"Failed to process the request: {str(e)}")
            clean_event = {key: value for key, value in event.items() if not (key.startswith('__ow') or key == 'http')}
            print(f"Request body: {json.dumps(clean_event)}")
            return {"body": "", "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}
        return {"body": "", "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}
