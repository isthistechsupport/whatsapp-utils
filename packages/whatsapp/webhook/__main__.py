import os
import json
import logging
import utils.logging
from time import sleep
#from utils.image import convert_png_to_jpeg
from utils.speech import transcribe_audio, read_text
from utils.vision import transcribe_image, remove_background
from utils.messaging import mark_as_read, send_text, send_media
from utils.healthcheck import healthcheck_routing, EMPTY_200_RESPONSE


logger = logging.getLogger(__name__)


def process_audio(message: dict, metadata: dict, ctx):
    for result in transcribe_audio(audio_id=message['audio']['id']):
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Replying with audio transcription result")
        send_text(
            phone_number_id=metadata['phone_number_id'],
            sender=f'+{message["from"]}',
            text=result,
            reply_to_id=message['id']
        )
        sleep(0.25)


def process_text(message: dict, metadata: dict, ctx):
    text = message['text']['body']
    if text.startswith('/tts'):
        text = text[4:].strip()
        audio_buffer, mime_type = read_text(text)
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Replying with audio message")
        send_media(
            phone_number_id=metadata['phone_number_id'],
            sender=f'+{message["from"]}',
            mime_type=mime_type,
            media_buffer=audio_buffer,
            reply_to_id=message['id']
        )
    else:
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Replying with help message")
        send_text(
            phone_number_id=metadata['phone_number_id'],
            sender=f'+{message["from"]}',
            text="¡Hola! Envíame un audio para responderte con la transcripción de este, o escribe `/tts` seguido de un texto para convertirlo en audio.",
            reply_to_id=message['id']
        )


def process_image(message: dict, metadata: dict, ctx):
    caption: str = message['image'].get('caption', '')
    if 'bg' in caption:
        send_text(
            phone_number_id=metadata['phone_number_id'],
            sender=f'+{message["from"]}',
            text="Lo siento, la funcionalidad de remover el fondo de una imagen está deshabilitada temporalmente. Por favor, intenta de nuevo más tarde.",
            reply_to_id=message['id']
        )
        # logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Processing image background removal")
        # image_result, mime_type = remove_background(image_id=message['image']['id'], ctx=ctx)
        # if isinstance(image_result, str):
        #     logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Replying with error message")
        #     send_text(
        #         phone_number_id=metadata['phone_number_id'],
        #         sender=f'+{message["from"]}',
        #         text=image_result,
        #         reply_to_id=message['id']
        #     )
        #     return
        # if mime_type == 'image/png':
        #     background_color_name = caption.split(' ')[-1].strip()
        #     image_result, mime_type = convert_png_to_jpeg(image_result, background_color_name), 'image/jpeg'
        # logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Replying with image background removal result")
        # send_media(
        #     phone_number_id=metadata['phone_number_id'],
        #     sender=f'+{message["from"]}',
        #     mime_type=mime_type,
        #     media_buffer=image_result,
        #     reply_to_id=message['id']
        # )
    else:
        for result in transcribe_image(image_id=message['image']['id'], ctx=ctx):
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Replying with image transcription result")
            send_text(
                phone_number_id=metadata['phone_number_id'],
                sender=f'+{message["from"]}',
                text=result,
                reply_to_id=message['id']
            )
            sleep(0.25)


def process_unsupported(message: dict, metadata: dict, ctx):
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Unsupported message type: {message['type']} in message: {message}")
    send_text(
        phone_number_id=metadata['phone_number_id'],
        sender=f'+{message["from"]}',
        text=f"Lo siento, no puedo procesar este mensaje de tipo: `{message['type']}`",
        reply_to_id=message['id']
    )


def process_change(change: dict, ctx: dict):
    """
    Process a change event
    """
    if 'value' not in change or 'messages' not in change['value'] or 'metadata' not in change['value'] or len(change['value']['messages']) == 0:
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Skipped change: %s", change)
        return
    logger.info(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Processing new change with {len(change['value']['messages'])} messages")
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Change: {json.dumps(change)}")
    value = change['value']
    messages = value['messages']
    metadata = value['metadata']
    for message in messages:
        mark_as_read(phone_number_id=metadata['phone_number_id'], message_id=message['id'])
        try:
            if message['type'] == 'audio':
                logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Processing audio message: {json.dumps(message)}")
                process_audio(message, metadata, ctx)
            elif message['type'] == 'text':
                logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Processing text message: {json.dumps(message)}")
                process_text(message, metadata, ctx)
            elif message['type'] == 'image':
                logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Processing image message: {json.dumps(message)}")
                process_image(message, metadata, ctx)
            else:
                logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Processing unsupported message: {json.dumps(message)}")
                process_unsupported(message, metadata, ctx)
        except Exception as e:
            send_text(
                phone_number_id=metadata['phone_number_id'],
                sender=f'+{message["from"]}',
                text=f"Lo siento, algo salió mal al procesar tu mensaje. Por favor, intenta de nuevo más tarde. Si el problema persiste, contacta a soporte con la siguiente info: `actv_id = {ctx.activation_id}, remaining_ms = {ctx.get_remaining_time_in_millis()}`",
                reply_to_id=message['id']
            )
            raise e


def process_event(event: dict, ctx: dict):
    if 'entry' not in event or len(event['entry']) == 0:
        return
    entries = event['entry']
    for entry in entries:
        if 'changes' not in entry or len(entry['changes']) == 0:
            return
        changes = entry['changes']
        for change in changes:
            if change['field'] == 'messages':
                process_change(change, ctx)


def main(event: dict, ctx) -> dict:
    utils.logging.init_logging()
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Received event: {json.dumps(event)}")
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Existing env vars: {os.environ=}")
    if event.get('healthcheck', False) or 'http' not in event or event['http']['method'] == 'GET':
        return healthcheck_routing(event, ctx)
    elif event['http']['method'] == 'POST':
        try:
            process_event(event, ctx)
        except Exception as e:
            logger.error(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Failed to process the request: %s", e, exc_info=True, stack_info=True)
            clean_event = {key: value for key, value in event.items() if not (key.startswith('__ow') or key == 'http')}
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Request body: {json.dumps(clean_event)}")
        return EMPTY_200_RESPONSE
