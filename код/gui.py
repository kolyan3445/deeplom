import tkinter as tk 
import json
import os
from tkinter import ttk, messagebox
from PIL import ImageTk, Image
from database import DatabaseManager
from monitoring import MonitoringThread
from exporter import CSVExporter
from report_generator import ReportGenerator
from esp32_client import ESP32Client
from datetime import datetime

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

class ThermalMonitorApp:

    def __init__(self, settings, session_id, is_new_session=False):

        self.settings=settings
        self.session_id=session_id
        self.is_new_session = is_new_session

        self.root=tk.Tk()
        self.root.title(f"Мониторинг - Сессия №{session_id}")
        self.root.geometry("1200x1000")
    
        self.db=DatabaseManager(settings)

        self.connected = False
        self.monitor_thread = None

        self.image_label=tk.Label(self.root)
        self.image_label.pack(expand=True)

        self.info_frame = ttk.Frame(self.root)
        self.info_frame.pack(fill="x", padx=10, pady=5)

        self.lbl_points = ttk.Label(self.info_frame, text="Точек: -")
        self.lbl_points.pack(anchor="w")

        self.lbl_min = ttk.Label(self.info_frame, text="Мин. температура: -")
        self.lbl_min.pack(anchor="w")

        self.lbl_max = ttk.Label(self.info_frame, text="Макс. температура: -")
        self.lbl_max.pack(anchor="w")

        self.lbl_avg = ttk.Label(self.info_frame, text="Средняя температура: -")
        self.lbl_avg.pack(anchor="w")

        if self.is_new_session:
            self.connect_btn = ttk.Button(self.root, text="Подключиться", command=self.connect)
            self.connect_btn.pack()

            self.start_btn = ttk.Button(self.root, text="Старт", command=self.start_monitoring)
            self.start_btn.pack()

            self.stop_btn = ttk.Button(self.root, text="Стоп", command=self.stop_monitoring)
            self.stop_btn.pack()

        ttk.Button(self.root,text="Экспорт в CSV",command=self.export_csv).pack()
        ttk.Button(self.root,text="Создать отчёт DOCX",command=self.export_docx).pack()
        ttk.Button(self.root,text="Назад",command=self.back_to_sessions).pack()

        if not self.is_new_session:
            self.load_last_image()


    def update_monitor( self, image, stats, ts):

        self.root.after(0, lambda: self._update_ui(image, stats))


    def _u(self,image):
        #print("GUI получил изображение", image.size)

        image.thumbnail((900,600))
        p=ImageTk.PhotoImage(image)
        self.current_image=p
        self.image_label.configure(image=p)


    def _update_ui(self, image, stats):

        self._u(image)

        self.lbl_points.configure( text=f"Точек: {stats['points']}")

        self.lbl_min.configure(text=(
                f"Мин. температура: "
                f"{stats['tmin']:.2f} °C"))

        self.lbl_max.configure(text=(
                f"Макс. температура: "
                f"{stats['tmax']:.2f} °C"))

        self.lbl_avg.configure(text=(
                f"Средняя температура: "
                f"{stats['tavg']:.2f} °C"))


    def load_last_image(self):

        path = self.db.get_last_image(self.session_id)

        if not path:
            return
        
        try:
            image = Image.open(path)
            self._u(image)

        except Exception as e:
            print(f"Ошибка загрузки изображения: {e}")


    def connect(self):
        try:
            client = ESP32Client(self.settings["esp32_ip"])

            client.get_frame()
            self.connected = True
            print("ESP32 подключена")

        except Exception as e:
            self.connected = False
            print("Ошибка подключения:",e)

    
    def start_monitoring(self):

        if not self.connected:
            print("Сначала выполните подключение")
            return

        if (self.monitor_thread and self.monitor_thread.is_alive()):
            return

        self.monitor_thread = MonitoringThread(self.session_id, self.settings["esp32_ip"], self.db, self.update_monitor)

        self.monitor_thread.start()


    def stop_monitoring(self):

        if self.monitor_thread:

            self.monitor_thread.stop()
            self.monitor_thread = None


    def export_csv(self):
        os.makedirs("exports", exist_ok=True)
        filename = (f"exports/"f"session_{self.session_id}_{stamp}.csv")

        CSVExporter.export(self.db.get_session_points(self.session_id), filename)

        messagebox.showinfo(title="Успешно", message=f"csv файл сохранён в exports под названием session_{self.session_id}_{stamp}.csv")

    def export_docx(self):
        os.makedirs("reports", exist_ok=True)
        filename = (f"reports/"f"session_{self.session_id}_{stamp}.docx")

        ReportGenerator.generate(filename, self.session_id,
            self.db.get_measurements(self.session_id),
            self.db.get_session_points(self.session_id),
            self.db.get_last_image(self.session_id))
        
        messagebox.showinfo(title="Успешно", message=f"Отчёт создан и сохранён в reports под названием session_{self.session_id}_{stamp}.docx")
            

    def back_to_sessions(self):

        if self.monitor_thread:
            self.monitor_thread.stop()
        self.root.destroy()

        from session_selector import SessionSelector
        SessionSelector(self.settings).run()


    def run(self):
        self.root.mainloop()