import os
import hashlib
import requests
from io import BytesIO
from utils.logging import log_to_redis, read_from_redis
from utils.media import validate_audio_mime_type, get_media_metadata, get_media_file_from_meta


def convert_audio_to_text(audio_buffer: BytesIO, audio_mime_type: str) -> str:
    """
    Send an audio to the OpenAI API and get the transcription
    """
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


def transcribe_audio(audio_id: str) -> list[str]:
    """
    Get an audio file from the Meta Graph API using the media ID, transcribe it, and return the transcription as a list of strings
    """
    file_url, file_hash, file_mime_type, file_size = get_media_metadata(audio_id)
    if not validate_audio_mime_type(file_mime_type):
        return [f"Lo siento, el formato del audio no es válido. Los formatos válidos son: flac, mp3, mp4, mpeg, mpga, m4a, ogg, wav y webm. El formato del audio que enviaste es: `{file_mime_type}`"]
    if file_size > 25 * 1024 * 1024:
        return [f"Lo siento, el tamaño del audio es muy grande. El tamaño máximo permitido es de 25MB. El tamaño del audio que enviaste es: `{file_size} bytes, {file_size / (1024 * 1024)} MB`"]
    with get_media_file_from_meta(file_url, media_id=audio_id) as audio_file:
        file_bytes = audio_file.getvalue()
        hashed_file = hashlib.sha256(file_bytes).hexdigest()
        if hashed_file != file_hash:
            return [f"Lo siento, el audio que enviaste está corrupto. Por favor, intenta enviarlo de nuevo. `{hashed_file} != {file_hash}`"]
        transcription = convert_audio_to_text(audio_file, file_mime_type)
        if len(transcription) > 4000:
            return [transcription[i:i+4000] for i in range(0, len(transcription), 4000)]
        else:
            return [transcription]


def get_voice_list() -> list[str]:
    """
    Get the list of voices available in the Microsoft Speech API
    """
    url = f"https://{os.getenv('MS_SPEECH_REGION')}.tts.speech.microsoft.com/cognitiveservices/voices/list"
    headers = {
        "Ocp-Apim-Subscription-Key": f"{os.getenv('MS_SPEECH_KEY')}",
        "User-Agent": "doslsfn:whatsapp_utils:v1.1"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return [{'short_name': voice["ShortName"], 'lang': voice["Locale"], 'gender': voice["Gender"]} for voice in response.json()]


def save_voice(sender: str, voice: dict[str, str]) -> None:
    """
    Save the chosen voice to Redis
    """
    log_to_redis(key=f"{sender}|voice_short_name|lang|gender", value=f"{voice['sender']}|{voice['short_name']}|{voice['lang']}", value_is_sender=False)


def get_voice(sender: str) -> dict[str, str]:
    """
    Get the chosen voice from Redis
    """
    voice = read_from_redis(f"{sender}|voice_short_name|lang|gender")
    voice = voice.split('|')
    return {'short_name': voice[0], 'lang': voice[1], 'gender': voice[2]}


def read_text(text: str, voice: dict[str, str]) -> tuple[BytesIO, str]:
    """
    Convert a text to an audio file using the Microsoft Speech API
    """
    url = f"https://{os.getenv('MS_SPEECH_REGION')}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": f"{os.getenv('MS_SPEECH_KEY')}",
        "Content-Type": "application/ssml+xml; charset=utf-8",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
        "User-Agent": "doslsfn:whatsapp_utils:v1.1"
    }
    body = f"""
    <speak version="1.0" xml:lang="{voice['lang']}">
        <voice xml:lang="{voice['lang']}" xml:gender="{voice['gender']}" name="{voice['voice_short_name']}">
            {text}
        </voice>
    </speak>
    """
    response = requests.post(url, headers=headers, data=body.encode('utf-8'))
    response.raise_for_status()
    return BytesIO(response.content), response.headers['Content-Type']
