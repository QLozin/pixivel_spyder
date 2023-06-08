from io import BytesIO
from PIL import Image

def parse_image(img: bytes) -> dict:
    img_data = Image.open(BytesIO(img))
    return {"pic_weight": img_data.width, "pic_height": img_data.height,"MIME":Image.MIME[img_data.format]}