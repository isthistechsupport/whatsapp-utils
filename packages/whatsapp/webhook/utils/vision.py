import os
import logging
import hashlib
import requests
from io import BytesIO
from utils.media import validate_image_mime_type, get_media_metadata, get_media_file


logger = logging.getLogger(__name__)


def convert_image_to_text(image_buffer: BytesIO, image_mime_type: str, ctx) -> str:
    """
    Send an image to the Microsoft Vision API and get the transcription
    """
    headers = {
        'Ocp-Apim-Subscription-Key': f"{os.getenv('MS_VISION_KEY')}",
        'Content-Type': image_mime_type,
    }
    url = f'{os.getenv("MS_VISION_ENDPOINT")}/computervision/imageanalysis:analyze?features=caption,read&model-version=latest&language=en&api-version=2024-02-01'
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Sending image to Microsoft Vision API at {url=}")
    response = requests.post(
        url=url,
        headers=headers,
        data=image_buffer
    )
    response.raise_for_status()
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Received response from Microsoft Vision API")
    resp_json = response.json()
    result = "\n\n".join("\n".join(line['text'] for line in block['lines']) for block in resp_json['readResult']['blocks'])
    return result


def transcribe_image(image_id: str, ctx) -> list[str]:
    """
    Get an image file from the Meta Graph API using the media ID, transcribe it, and return the transcription as a list of strings
    """
    file_url, file_hash, file_mime_type, file_size = get_media_metadata(image_id)
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Retrieved metadata of image {image_id}: {file_url}, {file_hash}, {file_mime_type}, {file_size}")
    if not validate_image_mime_type(file_mime_type):
        return [f"Lo siento, el formato de la imagen no es válido. Los formatos válidos son: jpeg y png. El formato de la imagen que enviaste es: `{file_mime_type}`"]
    if file_size > 25 * 1024 * 1024:
        return [f"Lo siento, el tamaño de la imagen es muy grande. El tamaño máximo permitido es de 25MB. El tamaño de la imagen que enviaste es: `{file_size} bytes, {file_size / (1024 * 1024)} MB`"]
    with get_media_file(file_url, media_id=image_id) as image_file:
        file_bytes = image_file.getvalue()
        hashed_file = hashlib.sha256(file_bytes).hexdigest()
        if hashed_file != file_hash:
            return [f"Lo siento, la imagen que enviaste está corrupta. Por favor, intenta enviarla de nuevo. `{hashed_file} != {file_hash}`"]
        transcription = convert_image_to_text(image_file, file_mime_type, ctx)
        if len(transcription) > 4000:
            return [f"```{transcription[i:i+4000]}```" for i in range(0, len(transcription), 4000)]
        else:
            return [f"```{transcription}```"]


def remove_image_background(image_buffer: BytesIO, image_mime_type: str, ctx) -> tuple[BytesIO, str]:
    headers = {
        'Ocp-Apim-Subscription-Key': f"{os.getenv('MS_VISION_KEY')}",
        'Content-Type': image_mime_type,
    }
    url = f'{os.getenv("MS_VISION_ENDPOINT")}/computervision/imageanalysis:segment?api-version=2023-02-01-preview&mode=backgroundRemoval'
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Sending image to Microsoft Vision API at {url=}")
    response = requests.post(
        url=url,
        headers=headers,
        data=image_buffer
    )
    response.raise_for_status()
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Received response from Microsoft Vision API")
    return BytesIO(response.content), response.headers['Content-Type']


def remove_background(image_id: str, ctx) -> tuple[BytesIO, str] | tuple[str, None]:
    """
    Get an image file from the Meta Graph API using the media ID, remove the background, and return the image foreground
    """
    file_url, file_hash, file_mime_type, file_size = get_media_metadata(image_id)
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Retrieved metadata of image {image_id}: {file_url}, {file_hash}, {file_mime_type}, {file_size}")
    if not validate_image_mime_type(file_mime_type):
        return f"Lo siento, el formato de la imagen no es válido. Los formatos válidos son: jpeg, png y tiff. El formato de la imagen que enviaste es: `{file_mime_type}`", None
    if file_size > 25 * 1024 * 1024:
        return f"Lo siento, el tamaño de la imagen es muy grande. El tamaño máximo permitido es de 25MB. El tamaño de la imagen que enviaste es: `{file_size} bytes, {file_size / (1024 * 1024)} MB`", None
    with get_media_file(file_url, media_id=image_id) as image_file:
        file_bytes = image_file.getvalue()
        hashed_file = hashlib.sha256(file_bytes).hexdigest()
        if hashed_file != file_hash:
            return f"Lo siento, la imagen que enviaste está corrupta. Por favor, intenta enviarla de nuevo. `{hashed_file} != {file_hash}`", None
        return remove_image_background(image_file, file_mime_type, ctx)
