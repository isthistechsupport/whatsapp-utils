import os
import hashlib
import requests
from io import BytesIO
from utils.media import validate_audio_mime_type, get_media_metadata, get_media_file


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
    with get_media_file(file_url) as audio_file:
        file_bytes = audio_file.getvalue()
        hashed_file = hashlib.sha256(file_bytes).hexdigest()
        if hashed_file != file_hash:
            return [f"Lo siento, el audio que enviaste está corrupto. Por favor, intenta enviarlo de nuevo. `{hashed_file} != {file_hash}`"]
        transcription = convert_audio_to_text(audio_file, file_mime_type)
        if len(transcription) > 4000:
            return [transcription[i:i+4000] for i in range(0, len(transcription), 4000)]
        else:
            return [transcription]


def read_text(text: str) -> BytesIO:
    """
    Convert a text to an audio file using the Microsoft Speech API
    """
    url = f"https://{os.getenv('MS_SPEECH_REGION')}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": f"{os.getenv('MS_SPEECH_KEY')}",
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
        "User-Agent": "doslsfn:whatsapp_utils:v1.1"
    }
    body = f"""
    <speak version="1.0" xml:lang="es-CO">
        <voice xml:lang="es-CO" xml:gender="Female" name="es-CO-SalomeNeural">
            {text}
        </voice>
    </speak>
    """
    response = requests.post(url, headers=headers, data=body)
    response.raise_for_status()
    return BytesIO(response.content)
