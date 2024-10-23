import os
import json
import logging
import hashlib
import requests
from io import BytesIO
from utils.image import resize_image, parse_image_caption, convert_png_to_jpeg, CaptionParsingError, AsciiArtFlags
from utils.media import validate_image_mime_type, get_media_metadata, get_media_file_from_meta, get_media_file_from_spaces, post_media_file_to_spaces, delete_media_file_from_spaces


logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


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


def validate_media(image_id: str, ctx) -> BytesIO:
    """
    Take an image ID and validate the mime type, size, and hash of the image. Return the image file
    """
    file_url, file_hash, file_mime_type, file_size = get_media_metadata(image_id)
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Retrieved metadata of image {image_id}: {file_url}, {file_hash}, {file_mime_type}, {file_size}")
    if not validate_image_mime_type(file_mime_type):
        raise ImageProcessingError(f"Lo siento, el formato de la imagen no es válido. Los formatos válidos son: jpeg, png y tiff. El formato de la imagen que enviaste es: `{file_mime_type}`")
    if file_size > 25 * 1024 * 1024:
        raise ImageProcessingError(f"Lo siento, el tamaño de la imagen es muy grande. El tamaño máximo permitido es de 25MB. El tamaño de la imagen que enviaste es: `{file_size} bytes, {file_size / (1024 * 1024)} MB`")
    with get_media_file_from_meta(file_url, media_id=image_id) as image_file:
        file_bytes = image_file.getvalue()
        hashed_file = hashlib.sha256(file_bytes).hexdigest()
        if hashed_file != file_hash:
            raise ImageProcessingError(f"Lo siento, la imagen que enviaste está corrupta. Por favor, intenta enviarla de nuevo. `{hashed_file} != {file_hash}`")
        return image_file


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


def image_to_asciiart(image_id: str, image_buffer: BytesIO, flags: AsciiArtFlags, ctx = None) -> str:
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Resizing image {image_id}")
    width, height = resize_image(image_buffer=image_buffer, tgt_width=flags.width, tgt_height=flags.height)
    headers = {
        'Content-Type': 'application/json',
    }
    payload = flags._asdict()
    payload['width'] = width
    payload['height'] = height
    payload['media_id'] = image_id
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Sending payload {json.dumps(payload)} to ASCII Art API")
    response = requests.get(
        f'{os.getenv("FUNCTIONS_ENDPOINT")}/api/v1/web/{os.getenv("FUNCTIONS_NAMESPACE")}/whatsapp/aic',
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Returning response from ASCII Art API")
    return response.text


def alter_image(caption: str, image_id: str, ctx) -> tuple[BytesIO, str] | list[str]:
    """
    Get an image file from the Meta Graph API using the media ID, run an operation on it, and return the result
    """
    try:
        parsed_caption = parse_image_caption(caption)
    except CaptionParsingError as e:
        raise ImageProcessingError(str(e))
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Parsed caption: {json.dumps(parsed_caption)}")
    op = parsed_caption[0]
    op_name = parsed_caption[1]
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Received {op_name} request on image {image_id}")
    file_url, file_hash, file_mime_type, file_size = get_media_metadata(image_id)
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Retrieved metadata of image {image_id}: {file_url}, {file_hash}, {file_mime_type}, {file_size}")
    with validate_media(image_id, ctx) as image_file:
        if 'i2t' in op:
            transcription = convert_image_to_text(image_file, file_mime_type, ctx)
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Returning {op_name} result")
            if len(transcription) > 4000:
                return [f"```{transcription[i:i+4000]}```" for i in range(0, len(transcription), 4000)]
            else:
                return [f"```{transcription}```"]
        if 'bg' in op:
            image_file, file_mime_type = remove_image_background(image_file, file_mime_type, ctx)
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Removed background from image {image_id}")
            background_color_name = parsed_caption[2] if isinstance(parsed_caption[2], str) else parsed_caption[2].background_color_name
            image_file, file_mime_type = convert_png_to_jpeg(image_file, background_color_name, ctx=ctx)
        if 'i2a' in op and 'bg' in op:
            post_media_file_to_spaces(f'{image_id}-bgrm', image_file, file_mime_type)
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Posted image with removed background to DigitalOcean Spaces")
            image_id = f'{image_id}-bgrm'
        if 'i2a' in op:
            spaces_key = image_to_asciiart(image_id, image_file, parsed_caption[2], ctx)
            if image_id.endswith('-bgrm'):
                delete_media_file_from_spaces(f'{image_id}-bgrm')
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Received key {spaces_key} from ASCII Art API")
            image_file, file_mime_type = get_media_file_from_spaces(spaces_key, delete=True), 'image/png'
            background_color_name = parsed_caption[2].background_color_name
            image_file, file_mime_type = convert_png_to_jpeg(image_file, background_color_name, ctx=ctx)
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Returning {op_name} result")
        return image_file, file_mime_type
