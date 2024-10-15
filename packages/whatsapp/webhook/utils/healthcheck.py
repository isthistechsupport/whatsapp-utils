import os
import logging


GET_RESULT_CONTENT_TYPE = {'Content-Type': 'text/plain'}
EMPTY_200_RESPONSE = {"body": "", "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}
logger = logging.getLogger(__name__)


def confirm_webhook_subscription(event: dict, ctx) -> dict:
    """
    Reply to the required healthchecks for Meta webhook registration
    """
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Confirming webhook subscription with {event=}")
    if event.get('hub.mode', '') != 'subscribe':
        return {"body": "Invalid mode", "statusCode": 400, "headers": GET_RESULT_CONTENT_TYPE}
    elif event.get('hub.verify_token', '') != os.environ.get("VERIFICATION_TOKEN"):
        return {"body": "Verification token mismatch", "statusCode": 403, "headers": GET_RESULT_CONTENT_TYPE}
    else:
        return {"body": event.get('hub.challenge', ''), "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}


def healthcheck_routing(event: dict, ctx) -> dict:
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Routing healthcheck request with {event=}")
    if event.get('healthcheck', False):
        return {"body": "I'm alive", "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}
    elif 'http' not in event:
        return {"body": "Invalid request", "statusCode": 400, "headers": GET_RESULT_CONTENT_TYPE}
    elif event['http']['method'] == 'GET':
        if event['http']['path'] == '/healthcheck':
            return {"body": "I'm alive", "statusCode": 200, "headers": GET_RESULT_CONTENT_TYPE}
        return confirm_webhook_subscription(event, ctx)
    else:
        return EMPTY_200_RESPONSE
