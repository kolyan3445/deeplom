
import requests
from logger import logger

class ESP32Client:
    def __init__(self, ip): self.ip=ip

    def get_frame(self):

        url = f"http://{self.ip}/image"

        r = requests.get(url, timeout=(15))

        logger.info(f"ESP32 response: {r.status_code}")

        return r.content
#print(ESP32Client(ip="192.168.0.110").get_frame())