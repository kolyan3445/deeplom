from PIL import Image
from io import BytesIO

class ImageProcessor:

    @staticmethod
    def load_image(frame):
        image = Image.open(BytesIO(frame)).convert("RGB")

        return image