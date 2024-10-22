import logging
from PIL import Image
from io import BytesIO


logger = logging.getLogger(__name__)


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


def convert_png_to_jpeg(image_buffer: BytesIO, background_color_name: str, background_color_rgb: tuple[int, int, int] = (255, 255, 255)):
    if background_color_name is None:
        background_color = background_color_rgb
    else:
        background_color = convert_color_name_to_rgb(background_color_name)
    image = Image.open(image_buffer)
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        # Autocrop the image
        image = autocrop_image(image_buffer, border=10)
        # Create a new image with the specified background color
        background = Image.new("RGB", image.size, background_color)
        background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
        image = background
    else:
        image = image.convert("RGB")
    
    jpeg_buffer = BytesIO()
    image.save(jpeg_buffer, "JPEG")
    jpeg_buffer.seek(0)
    return jpeg_buffer


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
            tgt_width = 256
            tgt_height = int((256 / src_width) * src_height)
        else:
            tgt_height = 256
            tgt_width = int((256 / src_height) * src_width)
    
    return tgt_width, tgt_height


def resize_image(image_buffer: BytesIO, tgt_width=None, tgt_height=None) -> tuple[int, int]:
    image = Image.open(image_buffer)
    src_width, src_height = image.size
    return resize_dimensions(src_width, src_height, tgt_width, tgt_height)
