import os
import boto3
import logging
import requests
from io import BytesIO


logger = logging.getLogger(__name__)


def validate_audio_mime_type(audio_mime_type: str) -> bool:
    """
    Validate if the audio mime type is supported by the OpenAI API
    """
    valid_mime_types = ['flac', 'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'ogg', 'wav', 'webm']
    return any(mime_type in audio_mime_type for mime_type in valid_mime_types)


def validate_image_mime_type(image_mime_type: str) -> bool:
    """
    Validate if the image mime type is supported by the Microsoft Vision API
    """
    valid_mime_types = ['jpeg', 'png']
    return any(mime_type in image_mime_type for mime_type in valid_mime_types)


def get_media_extension(mime_type: str) -> str:
    """
    Get the media extension from the mime type
    """
    return mime_type.split('/')[-1]


def get_media_metadata(media_id: str) -> tuple[str, str, str, str]:
    """
    Get the metadata of a media file from the Meta Graph API
    """
    url = f"https://graph.facebook.com/v19.0/{media_id}/"
    headers = {
        'Authorization': f'Bearer {os.environ.get("GRAPH_API_TOKEN")}'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response_json = response.json()
    return response_json['url'], response_json['sha256'], response_json['mime_type'], response_json['file_size']


def backup_media_file(media_id: str, media_buffer: BytesIO, mime_type: str) -> str:
    """
    Backup the media file to DigitalOcean Spaces
    """
    try:
        session = boto3.session.Session()
        client = session.client(
            's3',
            region_name='nyc3',
            endpoint_url='https://nyc3.digitaloceanspaces.com',
            aws_access_key_id=os.getenv('SPACES_KEY'),
            aws_secret_access_key=os.getenv('SPACES_SECRET')
        )
        logger.debug(f"Backing up media file {media_id=} to {os.getenv('SPACES_NAME')=} with {mime_type=}")
        client.put_object(
            Bucket=os.getenv('SPACES_NAME'),
            Key=f'{media_id}.{get_media_extension(mime_type)}',
            Body=media_buffer,
            ContentType=mime_type,
            ACL='private'
        )
    except Exception as e:
        logger.error(f"Error backing up media file: {e}", exc_info=True, stack_info=True)


def get_media_file_from_meta(file_url: str, media_id: str) -> BytesIO:
    """
    Get the media file from the Meta Graph API
    """
    headers = {
        'Authorization': f'Bearer {os.environ.get("GRAPH_API_TOKEN")}'
    }
    file_response = requests.get(file_url, headers=headers)
    file_response.raise_for_status()
    try:
        backup_media_file(media_id, BytesIO(file_response.content), file_response.headers['Content-Type'])
    except Exception as e:
        logger.error(f"Error backing up media file: {e}", exc_info=True, stack_info=True)
    return BytesIO(file_response.content)


def post_media_file_to_meta(phone_number_id: str, media_buffer: BytesIO, mime_type: str) -> str:
    """
    Post the media file to the Meta Graph API and get the posted media ID
    """
    url = f'https://graph.facebook.com/v21.0/{phone_number_id}/media'
    headers = {
        'Authorization': f'Bearer {os.environ.get("GRAPH_API_TOKEN")}',
    }
    media_extension = get_media_extension(mime_type)
    files={
        'file': (f'file.{media_extension}', media_buffer, mime_type),
        'type': (None, mime_type),
        'messaging_product': (None, 'whatsapp')
    }
    response = requests.request("POST", url, headers=headers, files=files)
    response.raise_for_status()
    try:
        assert media_buffer.seek(0) == 0, "Media buffer couldn't be rewinded"
        backup_media_file(response.json()['id'], media_buffer, mime_type)
    except Exception as e:
        logger.error(f"Error backing up media file: {e}", exc_info=True, stack_info=True)
    return response.json()['id']


def get_media_file_from_spaces(media_id: str, delete: bool = False) -> BytesIO:
    """
    Get the media file from DigitalOcean Spaces
    """
    session = boto3.session.Session()
    client = session.client(
        's3',
        region_name='nyc3',
        endpoint_url='https://nyc3.digitaloceanspaces.com',
        aws_access_key_id=os.getenv('SPACES_KEY'),
        aws_secret_access_key=os.getenv('SPACES_SECRET')
    )
    response = client.get_object(
        Bucket=os.getenv('SPACES_NAME'),
        Key=media_id
    )
    if delete:
        client.delete_object(
            Bucket=os.getenv('SPACES_NAME'),
            Key=media_id
        )
    return BytesIO(response['Body'].read())
