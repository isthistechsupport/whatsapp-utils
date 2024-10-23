import os
import json
import logging
from time import sleep
from utils.media import MediaProcessingError
from utils.logging import log_to_redis, init_logging
from utils.vision import alter_image, ImageProcessingError
from utils.messaging import mark_as_read, send_text, send_media
from utils.healthcheck import healthcheck_routing, EMPTY_200_RESPONSE
from utils.speech import transcribe_audio, read_text, get_voice_list, save_voice, get_voice


logger = logging.getLogger(__name__)


def process_audio(message: dict, metadata: dict, ctx):
    logger.info(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Processing audio transcription request from {message['from']}")
    log_to_redis(key=message['audio']['id'], value=message['from'])
    for result in transcribe_audio(audio_id=message['audio']['id']):
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Replying with audio transcription result")
        send_text(
            phone_number_id=metadata['phone_number_id'],
            sender=f'+{message["from"]}',
            text=result,
            reply_to_id=message['id']
        )
        sleep(0.25)


def get_voices(message: dict, metadata: dict, ctx):
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Replying with available voices")
    voices = get_voice_list()
    voice_groups = []
    current_group = []
    current_length = 0
    for voice in voices:
        voice_str = voice['short_name']
        if current_length + len(voice_str) + 1 > 4000:  # +1 for the linebreak
            voice_groups.append(current_group)
            current_group = []
            current_length = 0
        current_group.append(voice_str)
        current_length += len(voice_str) + 1  # +1 for the linebreak
    if current_group:
        voice_groups.append(current_group)
    for group in voice_groups:
        send_text(
            phone_number_id=metadata['phone_number_id'],
            sender=f'+{message["from"]}',
            text=f"```{'\n'.join(group)}```",
            reply_to_id=message['id']
        )
        sleep(0.25)


def process_text(message: dict, metadata: dict, ctx):
    text = message['text']['body']
    if text.startswith('/tts'):
        if text.split(' ')[1] == 'get_voices':
            get_voices(message, metadata, ctx)
        elif text.split(' ')[1] == 'set_voice':
            voice_short_name = text.split(' ')[2]
            voices = get_voice_list()
            voice = next((voice for voice in voices if voice['short_name'] == voice_short_name), None)
            save_voice(sender=message['from'], voice=voice)
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Replying with voice set confirmation")
            send_text(
                phone_number_id=metadata['phone_number_id'],
                sender=f'+{message["from"]}',
                text=f"Voz seleccionada: `{voice}`",
                reply_to_id=message['id']
            )
        elif text.split(' ')[1] == 'get_voice':
            voice = get_voice(sender=message['from'])
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Replying with current voice")
            send_text(
                phone_number_id=metadata['phone_number_id'],
                sender=f'+{message["from"]}',
                text=f"Voz seleccionada: `{voice}`",
                reply_to_id=message['id']
            )
        else:
            logger.info(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Processing text-to-speech request from {message['from']}")
            text = text[4:].strip()
            audio_buffer, mime_type = read_text(text, voice=get_voice(sender=message['from']))
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
    log_to_redis(key=message['image']['id'], value=message['from'])
    caption: str = message['image'].get('caption', '')
    logger.info(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Processing image request from {message['from']}")
    result = alter_image(caption=caption, image_id=message['image']['id'], ctx=ctx)
    if isinstance(result, tuple):
        image_result, mime_type = result
        send_media(
            phone_number_id=metadata['phone_number_id'],
            sender=f'+{message["from"]}',
            mime_type=mime_type,
            media_buffer=image_result,
            reply_to_id=message['id']
        )
    else:
        for text in result:
            send_text(
                phone_number_id=metadata['phone_number_id'],
                sender=f'+{message["from"]}',
                text=text,
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
        log_to_redis(key=ctx.activation_id, value=message['from'])
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
        except (MediaProcessingError, ImageProcessingError) as e:
            send_text(
                phone_number_id=metadata['phone_number_id'],
                sender=f'+{message["from"]}',
                text=str(e),
                reply_to_id=message['id']
            )
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
    init_logging()
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
