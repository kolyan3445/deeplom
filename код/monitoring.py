import os, random, threading
from datetime import datetime
from esp32_client import ESP32Client
from image_processor import ImageProcessor
from logger import logger
import traceback

class MonitoringThread(threading.Thread):

    def __init__(self, session_id, ip, db, cb):
        super().__init__(daemon=True)
        self.session_id=session_id
        self.ip=ip
        self.db=db
        self.cb=cb
        self.running=False
        self.stop_event=threading.Event()

    def stop(self):
        self.running=False
        self.stop_event.set()

    def run(self):

        self.running = True

        camera = ESP32Client(self.ip)

        while self.running:
            try:
                frame = camera.get_frame()
                ts = datetime.now()
                points = []

                for _ in range(300):

                    points.append(
                        {
                            "x": random.randint(0, 799),
                            "y": random.randint(0, 599),
                            "temp": round(random.uniform(20,90),2)
                        })

                image = ImageProcessor.load_image(frame)

                from heatmap import HeatMapBuilder
                (result_image, tmin, tmax, tavg) = HeatMapBuilder.build_overlay(image,points)

                folder = (f"images/session_"f"{self.session_id}")

                os.makedirs(folder,exist_ok=True)

                path = (f"{folder}/"f"{ts.strftime('%Y%m%d_%H%M%S')}.jpg")

                result_image.convert("RGB").save(path)

                measurement_id = self.db.create_measurement(self.session_id, ts, path)

                self.db.insert_points(measurement_id, points)
                print("Передача изображения в GUI")

                self.cb(result_image,{"tmin": tmin, "tmax": tmax, "tavg": tavg, "points": len(points)}, ts)
                #print("HeatMap:", result_image, tmin, tmax, tavg)

            except Exception:

                logger.error(traceback.format_exc())

            if self.stop_event.wait(5):
                break