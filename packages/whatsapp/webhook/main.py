import os
import json
import hashlib
import requests
from time import sleep
from io import BytesIO


GET_RESULT_CONTENT_TYPE = {'Content-Type': 'text/plain'}


def confirm_webhook_subscription(event: dict) -> dict:
    if event.get('hub.mode', '') != 'subscribe':
        return {"body": "Invalid mode", "statusCode": 400, "headers": GET_RESULT_CONTENT_TYPE}
    elif event.get('hub.verify_token', '') != os.environ.get("VERIFICATION_TOKEN"):
        return {"body": "Verification token mismatch", "statusCode": 403, "headers": GET_RESULT_CONTENT_TYPE}
    else:
        return {"body": event.get('hub.challenge', ''), "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}


def mark_as_read(phone_number_id: str, message_id: str):
    response = requests.post(
        f"https://graph.facebook.com/v19.0/{phone_number_id}/messages",
        headers={
            "Authorization": f'Bearer {os.environ.get("GRAPH_API_TOKEN")}'
        },
        json={
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
    )
    response.raise_for_status()


def process_text(phone_number_id: str, sender: str, text: str, reply_to_id: str = None):
    url = f"https://graph.facebook.com/v19.0/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": sender,
        "type": "text",
        "text": {
            "preview_url": "false",
            "body": text
        }
    }
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {os.environ.get("GRAPH_API_TOKEN")}',
    }
    if reply_to_id:
        payload['context'] = {'message_id': reply_to_id}
    response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()


def validate_mime_type(audio_mime_type: str) -> bool:
    valid_mime_types = ['flac', 'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'ogg', 'wav', 'webm']
    return any(mime_type in audio_mime_type for mime_type in valid_mime_types)


def get_audio_metadata(audio_id: str) -> tuple[str, str, str, str]:
    url = f"https://graph.facebook.com/v19.0/{audio_id}/"
    headers = {
        'Authorization': f'Bearer {os.environ.get("GRAPH_API_TOKEN")}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_json = response.json()
    return response_json['url'], response_json['sha256'], response_json['mime_type'], response_json['file_size']


def get_audio_file(file_url: str) -> BytesIO:
    headers = {
        'Authorization': f'Bearer {os.environ.get("GRAPH_API_TOKEN")}'
    }
    file_response = requests.get(file_url, headers=headers)
    file_response.raise_for_status()
    return BytesIO(file_response.content)


def transcribe_audio(audio_buffer: BytesIO, audio_mime_type: str) -> str:
    headers = {
        'Authorization': f"Bearer {os.getenv('OPENAI_API_KEY')}",
    }
    files = {
        'file': ('audio', audio_buffer, audio_mime_type),
        'model': (None, 'whisper-1'),
        'temperature': (None, '0.7'),
    }
    response = requests.post('https://api.openai.com/v1/audio/transcriptions', headers=headers, files=files)
    return response.json()['text']


def process_audio(audio_id: str) -> list[str]:
    file_url, file_hash, file_mime_type, file_size = get_audio_metadata(audio_id)
    if not validate_mime_type(file_mime_type):
        return [f"Lo siento, el formato del audio no es válido. Los formatos válidos son: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav y webm. El formato del audio que enviaste es: ```{file_mime_type}```"]
    if file_size > 25 * 1024 * 1024:
        return [f"Lo siento, el tamaño del audio es muy grande. El tamaño máximo permitido es de 25MB. El tamaño del audio que enviaste es: ```{file_size} bytes, {file_size / (1024 * 1024)} MB```"]
    with get_audio_file(file_url) as audio_file:
        file_bytes = audio_file.getvalue()
        hashed_file = hashlib.sha256(file_bytes).hexdigest()
        if hashed_file != file_hash:
            return [f"Lo siento, el audio que enviaste está corrupto. Por favor, intenta enviarlo de nuevo. ```{hashed_file} != {file_hash}```"]
        transcription = transcribe_audio(audio_file, file_mime_type)
        if len(transcription) > 4000:
            return [transcription[i:i+4000] for i in range(0, len(transcription), 4000)]
        else:
            return [transcription]


def process_change(change: dict):
    if 'value' not in change or 'messages' not in change['value'] or 'metadata' not in change['value'] or len(change['value']['messages']) == 0:
        return
    print("New request received")
    value = change['value']
    messages = value['messages']
    metadata = value['metadata']
    for message in messages:
        message_id = message['id']
        mark_as_read(phone_number_id=metadata['phone_number_id'], message_id=message_id)
        if message['type'] == 'audio':
            for result in process_audio(audio_id=message['audio']['id']):
                process_text(
                    phone_number_id=metadata['phone_number_id'],
                    sender=f'+{message["from"]}',
                    text=result,
                    reply_to_id=message_id
                )
                sleep(1)
        elif message['type'] == 'text':
            process_text(
                phone_number_id=metadata['phone_number_id'],
                sender=f'+{message["from"]}',
                text="¡Hola! Envíame un audio para responderte con la transcripción de este.",
                reply_to_id=message_id
            )
        else:
            process_text(
                phone_number_id=metadata['phone_number_id'],
                sender=f'+{message["from"]}',
                text=f"Lo siento, no puedo procesar este mensaje de tipo: ```{message['type']}```",
                reply_to_id=message_id
            )
            raise ValueError(f"Unsupported message type: {message['type']} in message: {message}")


def process_event(event: dict):
    if 'entry' not in event or len(event['entry']) == 0:
        return
    entries = event['entry']
    for entry in entries:
        if 'changes' not in entry or len(entry['changes']) == 0:
            return
        changes = entry['changes']
        for change in changes:
            if change['field'] == 'messages':
                process_change(change)


def main(event: dict, _) -> dict:
    if event.get('heartbeat', False):
        return {"body": "I'm alive", "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}
    elif 'http' not in event:
        return {"body": "Invalid request", "statusCode": 400, "headers": GET_RESULT_CONTENT_TYPE}
    elif event['http']['method'] == 'GET':
        if event['http']['path'] == '/heatbeat':
            return {"body": "I'm alive", "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}
        return confirm_webhook_subscription(event)
    elif event['http']['method'] == 'POST':
        try:
            process_event(event)
        except Exception as e:
            print(f"Failed to process the request: {str(e)}")
            clean_event = {key: value for key, value in event.items() if not (key.startswith('__ow') or key == 'http')}
            print(f"Request body: {json.dumps(clean_event)}")
            return {"body": "", "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}
        return {"body": "", "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}
