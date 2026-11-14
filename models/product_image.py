import logging
import os
import secrets
from io import BytesIO

from PIL import Image, ImageOps

# Images are saved here, and Product.imagePath holds the path inside static/
STATIC_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
UPLOAD_FOLDER = "uploads/products"

log = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000
ALLOWED_FORMATS = ("JPEG", "PNG", "WEBP", "GIF")

# Saved images are never wider or taller than this, so the pages stay fast on the Pi
MAX_SIDE = 800

BAD_IMAGE = "That file is not a JPG, PNG, WebP or GIF image."


# Check and shrink an upload. Gives back (data, error). Re-saving also drops GPS data
def read_image(upload):
    if upload is None or not upload.filename:
        return None, None
    try:
        with Image.open(upload.stream, formats=ALLOWED_FORMATS) as image:
            if image.width * image.height > MAX_PIXELS:
                return None, "That image has too many pixels. Please use a smaller one."
            upright = ImageOps.exif_transpose(image)
            upright.thumbnail((MAX_SIDE, MAX_SIDE))
            if upright.mode != "RGB":
                upright = upright.convert("RGBA")   # keeps a see-through background
            data = BytesIO()
            upright.save(data, "WEBP", quality=85)
            return data.getvalue(), None
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return None, BAD_IMAGE


# basename keeps the path inside the upload folder
def _file_on_disk(path):
    # basename so a path from the database can never point outside the upload folder
    return os.path.join(STATIC_FOLDER, UPLOAD_FOLDER, os.path.basename(path))


# Save the image data under a new random name. Gives back the path to put in Product.imagePath
def save_image(data):
    path = f"{UPLOAD_FOLDER}/{secrets.token_hex(8)}.webp"
    os.makedirs(os.path.join(STATIC_FOLDER, UPLOAD_FOLDER), exist_ok=True)
    with open(_file_on_disk(path), "wb") as file:
        file.write(data)
    return path


# Delete a saved image. A missing file or no image at all is fine
def delete_image(path):
    if not path:
        return
    try:
        os.remove(_file_on_disk(path))
    except FileNotFoundError:
        pass
    except OSError as err:
        log.error("Could not delete the image %s: %s", path, err)
