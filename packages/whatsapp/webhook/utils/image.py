import logging
from PIL import Image
from io import BytesIO


logger = logging.getLogger(__name__)


class CaptionParsingError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


def autocrop_image(image_buffer: BytesIO, border = 0):
    image = Image.open(image_buffer)

    # Get the bounding box
    bbox = image.getbbox()

    # Crop the image to the contents of the bounding box
    image = image.crop(bbox)

    # Determine the width and height of the cropped image
    (width, height) = image.size

    # Add border
    width += border * 2
    height += border * 2
    
    # Create a new image object for the output image
    cropped_image = Image.new("RGBA", (width, height), (0,0,0,0))

    # Paste the cropped image onto the new image
    cropped_image.paste(image, (border, border))

    # Done!
    return cropped_image


def convert_color_name_to_rgb(color_name: str):
    color_name = color_name.lower()
    colors = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "purple": (128, 0, 128),
        "orange": (255, 165, 0),
        "pink": (255, 192, 203),
        "brown": (165, 42, 42),
        "gray": (128, 128, 128),
        "grey": (128, 128, 128)
    }
    return colors.get(color_name, (255, 255, 255))


def convert_png_to_jpeg(image_buffer: BytesIO, background_color_name: str, background_color_rgb: tuple[int, int, int] = (255, 255, 255), ctx=None) -> tuple[BytesIO, str]:
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Comverting PNG image to JPEG")
    image = Image.open(image_buffer)
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        if background_color_name is None:
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} No background color provided, using white as the default background color")
            background_color = background_color_rgb
        else:
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Detected background color: {background_color_name}")
            background_color = convert_color_name_to_rgb(background_color_name)
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Converted background color to RGB: {background_color}")
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Detected image with transparency")
        # Autocrop the image
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Autocropping the canvas to exclude transparent borders around the image")
        image = autocrop_image(image_buffer, border=10)
        # Create a new image with the specified background color
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Creating a new canvas with the background color: {background_color}")
        background = Image.new("RGB", image.size, background_color)
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Pasting the image onto the new canvas")
        background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
        image = background
    else:
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Detected image without transparency")
        image_mode = image.mode
        logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Image mode detected: {image_mode}")
        if image_mode == 'P' or image_mode == 'L' or image_mode == '1' or image_mode == 'CMYK' or image_mode == 'YCbCr' or image_mode == 'LAB' or image_mode == 'HSV' or image_mode == 'I' or image_mode == 'F':
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Converting the image to RGB color space")
            image = image.convert("RGB")
            logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Image converted")
    
    jpeg_buffer = BytesIO()
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Saving the image as a JPEG")
    image.save(jpeg_buffer, "JPEG")
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Rewinding the JPEG image buffer")
    jpeg_buffer.seek(0)
    logger.debug(f"ActvID {ctx.activation_id} Remaining millis {ctx.get_remaining_time_in_millis()} Returning the JPEG image buffer")
    return jpeg_buffer, 'image/jpeg'


def read_image_to_asciiart_params(params: dict) -> tuple[bool, str | None, int | None, int | None]:
    background = bool(params.get('bg', False))
    background_color_name = params.get('bgcolor')
    width_str = params.get('w')
    height_str = params.get('h')
    width = int(width_str) if width_str is not None else None
    height = int(height_str) if height_str is not None else None
    return f'i2a{" bg" if background else ""}', 'image to asciiart', background_color_name, width, height


def parse_image_caption(caption: str) -> tuple[str, str, str | None] | tuple[str, str, bool, str | None, int | None, int | None]:
    """
    Parse the caption of an image message
    """
    caption = caption.strip()
    if caption.startswith('/'):
        parts = caption.split()
        op = parts[0][1:]
        params = {}
        for part in parts[1:]:
            if '=' in part:
                key, value = part.split('=')
                params[key] = value
            else:
                params[part] = True
        if op == 'bg':
            background_color_name = params.get('bgcolor')
            return 'bg', 'background removal', background_color_name
        elif op == 'i2a':
            return read_image_to_asciiart_params(params)
        raise ValueError(f"Lo siento, la operación que intentas realizar no es válida. Las operaciones válidas son: bg (remover fondo de imagen) e i2a (convertir imagen a arte ASCII). La operación que intentaste realizar es: `{op}`")
    return 'i2t', 'image transcription', None


def resize_dimensions(src_width, src_height, tgt_width=None, tgt_height=None):
    """
    Resize the dimensions of the image to the target width and height.
    If both dimensions are provided, the target width and height are
    returned unchanged. If only one of the target width or height is
    provided, the other is calculated based on the aspect ratio of the
    source image. If neither is provided, the shorter dimension is resized
    to 256 and the other is calculated based on the aspect ratio of the
    source image.
    """
    if tgt_width is not None and tgt_height is not None:
        return tgt_width, tgt_height
    elif tgt_width is not None:
        aspect_ratio = src_height / src_width
        tgt_height = int(tgt_width * aspect_ratio)
    elif tgt_height is not None:
        aspect_ratio = src_width / src_height
        tgt_width = int(tgt_height * aspect_ratio)
    else:
        if src_width < src_height:
            tgt_width = 128
            tgt_height = int((128 / src_width) * src_height)
        else:
            tgt_height = 128
            tgt_width = int((128 / src_height) * src_width)
    
    return tgt_width, tgt_height


def resize_image(image_buffer: BytesIO, tgt_width=None, tgt_height=None) -> tuple[int, int]:
    image = Image.open(image_buffer)
    src_width, src_height = image.size
    return resize_dimensions(src_width, src_height, tgt_width, tgt_height)
