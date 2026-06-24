import tkinter as tk
from tkinter import ttk
import serial
import threading
import queue
import time
import re
import io
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

COM_PORT = 'COM3'
CAM_PORT = 'COM4'
BAUD_RATE = 115200
WINDOW_SIZE = 500
FIXED_Y_MIN = 15
FIXED_Y_MAX = 35
VISIBLE_POINTS = 50
COLORS = ['blue', 'red', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
CAM_WIDTH = 1600
CAM_HEIGHT = 1200

try:
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"Connected to {COM_PORT}")
except Exception as e:
    print(f"Error: {e}")
    ser = None

cam_ser = None
try:
    cam_ser = serial.Serial(CAM_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    cam_ser.reset_input_buffer()
    cam_ser.write(b'R')
    cam_ser.flush()
    start = time.time()
    ready = False
    while time.time() - start < 3:
        if cam_ser.in_waiting:
            line = cam_ser.readline().decode('ascii', errors='ignore').strip()
            if line == "READY":
                ready = True
                break
    if ready:
        print(f"Camera on {CAM_PORT} ready")
    else:
        print(f"Camera on {CAM_PORT} not responding")
except Exception as e:
    print(f"Camera error: {e}")
    cam_ser = None

current_pos = (90.0, 90.0)
calibration_pos = (90.0, 90.0)
cal_angle = (90.0, 90.0)
points = []
measurement_data = {}
is_measuring = False
is_paused = False
stop_requested = False
msg_queue = queue.Queue()


def ang_to_pix(ax, ay):
    px = CAM_WIDTH / 2 + (ax - cal_angle[0]) * (CAM_WIDTH / 180)
    py = CAM_HEIGHT / 2 - (ay - cal_angle[1]) * (CAM_HEIGHT / 180)
    px = max(0, min(CAM_WIDTH, px))
    py = max(0, min(CAM_HEIGHT, py))
    return int(px), int(py)


def serial_reader():
    while True:
        if ser and ser.in_waiting:
            try:
                line = ser.readline().decode().strip()
                if line:
                    msg_queue.put(line)
            except Exception:
                pass
        time.sleep(0.01)


def send_command(cmd):
    if ser and ser.is_open:
        ser.write((cmd + '\n').encode())
        print(f"-> {cmd}")


if ser:
    threading.Thread(target=serial_reader, daemon=True).start()


class CalibrationDialog(tk.Toplevel):
    def __init__(self, parent, on_confirm):
        super().__init__(parent)
        self.title("Calibration")
        self.geometry("450x280")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.on_confirm = on_confirm

        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        tk.Label(self, text="1. Use joystick to center motors.\n2. Press button when ready.",
                 justify=tk.CENTER, pady=10, font=("Arial", 11)).pack()

        self.pos_lbl = tk.Label(self, text="Waiting for data...", bg="#fff", fg="#007acc",
                                font=("Consolas", 13), relief=tk.SOLID, padx=15, pady=8)
        self.pos_lbl.pack(pady=10, fill=tk.X)

        tk.Button(self, text="Set as CENTER", command=self.set_as_center,
                  bg="lightgreen", font=("Arial", 12, "bold"), padx=20, pady=8).pack(pady=15)

        self.last_req_time = time.time()
        self.poll_pos()


    def poll_pos(self):
        if time.time() - self.last_req_time > 1.0:
            send_command("GET_POS")
            self.last_req_time = time.time()

        while not msg_queue.empty():
            msg = msg_queue.get()
            if msg.startswith("POS:"):
                try:
                    parts = msg[4:].split(',')
                    if len(parts) >= 2:
                        x = float(parts[0].strip())
                        y = float(parts[1].strip())
                        self.pos_lbl.config(text=f"Current position: X={int(x)}  Y={int(y)}")
                except:
                    pass
        self.after(100, self.poll_pos)


    def set_as_center(self):
        global calibration_pos, cal_angle, current_pos
        text = self.pos_lbl.cget("text")
        try:
            nums = re.findall(r'\d+', text)
            if len(nums) >= 2:
                cal_x = int(nums[0])
                cal_y = int(nums[1])
                calibration_pos = (float(cal_x), float(cal_y))
                cal_angle = calibration_pos
                current_pos = calibration_pos
                print(f"Calibration saved: {calibration_pos}")
        except:
            calibration_pos = (90.0, 90.0)
            cal_angle = (90.0, 90.0)
            current_pos = (90.0, 90.0)

        self.destroy()
        self.on_confirm()

"""
    def capture_photo(self):
        def _capture():
            if cam_ser is None:
                self.root.after(0, lambda: self.status_label.config(text="Camera not connected"))
                return
            try:
                self.root.after(0, lambda: self.status_label.config(text="Capturing..."))
                cam_ser.reset_input_buffer()
                cam_ser.write(b'C')
                cam_ser.flush()
                line = ""
                timeout = time.time() + 3
                while time.time() < timeout:
                    if cam_ser.in_waiting:
                        c = cam_ser.read(1)
                        try:
                            line += c.decode('ascii')
                        except:
                            if "IMG:" not in line:
                                line = ""
                            continue
                        if '\n' in line:
                            break
                    else:
                        time.sleep(0.01)
                line = line.strip()
                if not line.startswith("IMG:"):
                    raise Exception(f"Bad header: {line[:30]}")
                size = int(line.split(':')[1])
                img_data = b''
                timeout = time.time() + 10
                while len(img_data) < size and time.time() < timeout:
                    if cam_ser.in_waiting:
                        img_data += cam_ser.read(min(size - len(img_data), cam_ser.in_waiting))
                    else:
                        time.sleep(0.01)
                if len(img_data) != size:
                    raise Exception(f"Read {len(img_data)}/{size} bytes")
                start = img_data.find(b'\xff\xd8')
                if start == -1:
                    raise Exception("No JPEG header")
                img_data = img_data[start:]
                pil_img = Image.open(io.BytesIO(img_data))
                pil_img = pil_img.resize((WINDOW_SIZE, WINDOW_SIZE), Image.Resampling.LANCZOS)
                self.background_image = ImageTk.PhotoImage(pil_img)
                self.root.after(0, lambda: self.draw_point())
                self.root.after(0, lambda: self.status_label.config(text="Photo loaded"))
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.root.after(0, lambda err=str(e): self.status_label.config(text=f"Error: {err[:50]}"))
        threading.Thread(target=_capture, daemon=True).start()
"""

class Application:
    def __init__(self, root):
        self.root = root
        self.root.title("Laser Scanner")
        self.root.geometry("1400x900")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")

        self.left_frame = tk.Frame(root, width=400, height=880)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        self.left_frame.pack_propagate(False)

        control_frame = tk.LabelFrame(self.left_frame, text="Control")
        control_frame.pack(fill=tk.X, pady=5)

        self.btn_record = tk.Button(control_frame, text="Record mode", command=self.toggle_record, bg="lightblue")
        self.btn_record.pack(fill=tk.X, pady=2)

        self.btn_save = tk.Button(control_frame, text="Save point", command=self.save_current_point, bg="yellow")
        self.btn_save.pack(fill=tk.X, pady=2)

        self.btn_clear = tk.Button(control_frame, text="Clear all", command=self.clear_all, bg="gray")
        self.btn_clear.pack(fill=tk.X, pady=2)

        self.btn_measure = tk.Button(control_frame, text="Start cycle", command=self.start_measurement, bg="lightgreen")
        self.btn_measure.pack(fill=tk.X, pady=2)

        self.btn_pause = tk.Button(control_frame, text="Pause", command=self.toggle_pause, bg="orange", state=tk.DISABLED)
        self.btn_pause.pack(fill=tk.X, pady=2)

        self.btn_stop = tk.Button(control_frame, text="Stop", command=self.stop_measurement, bg="lightcoral", state=tk.DISABLED)
        self.btn_stop.pack(fill=tk.X, pady=2)

        self.btn_home = tk.Button(control_frame, text="Go to center", command=self.go_to_calibration, bg="lightyellow")
        self.btn_home.pack(fill=tk.X, pady=2)

        self.btn_capture = tk.Button(control_frame, text="Capture photo", command=self.capture_photo, bg="lightcyan")
        self.btn_capture.pack(fill=tk.X, pady=2)

        temp_frame = tk.LabelFrame(self.left_frame, text="New point parameters")
        temp_frame.pack(fill=tk.X, pady=5)

        tk.Label(temp_frame, text="Target temperature (C):").pack()
        self.temp_entry = tk.Entry(temp_frame, width=10)
        self.temp_entry.pack()
        self.temp_entry.insert(0, "23.5")

        select_frame = tk.LabelFrame(self.left_frame, text="Show graphs for points")
        select_frame.pack(fill=tk.X, pady=5)

        self.graph_listbox = tk.Listbox(select_frame, height=6, selectmode=tk.MULTIPLE, exportselection=False)
        self.graph_listbox.pack(fill=tk.X, padx=5, pady=5)
        self.graph_listbox.bind('<<ListboxSelect>>', lambda e: self.update_graph())

        btn_frame = tk.Frame(select_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="Show all", command=self.select_all_graphs).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Hide all", command=self.deselect_all_graphs).pack(side=tk.LEFT, padx=2)

        list_frame = tk.LabelFrame(self.left_frame, text="Saved points (pixels)")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.points_listbox = tk.Listbox(list_frame, height=8)
        self.points_listbox.pack(fill=tk.BOTH, expand=True)

        status_frame = tk.Frame(self.left_frame, height=45)
        status_frame.pack(fill=tk.X, pady=5)
        status_frame.pack_propagate(False)
        self.status_label = tk.Label(status_frame, text="Status: Ready", fg="blue", anchor="w", justify=tk.LEFT, wraplength=380)
        self.status_label.pack(fill=tk.BOTH, padx=5, pady=2)

        temp_display_frame = tk.Frame(self.left_frame, height=40)
        temp_display_frame.pack(fill=tk.X, pady=5)
        temp_display_frame.pack_propagate(False)
        self.temp_display = tk.Label(temp_display_frame, text="Temperature: --.-C",
                                     font=("Arial", 12, "bold"), fg="red")
        self.temp_display.pack()

        self.right_frame = tk.Frame(root)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas_frame = tk.LabelFrame(self.right_frame, text="Camera field of view")
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        self.canvas = tk.Canvas(canvas_frame, width=WINDOW_SIZE, height=WINDOW_SIZE, bg='#1a1a1a')
        self.canvas.pack(expand=True)

        self.coord_label = tk.Label(canvas_frame, text=f"Beam: X=800 Y=600 | Angles: 90.0 90.0", fg='cyan', font=('Consolas', 9))
        self.coord_label.pack(pady=2)

        graph_frame = tk.LabelFrame(self.right_frame, text="Temperature graphs")
        graph_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        plot_container = tk.Frame(graph_frame)
        plot_container.pack(fill=tk.BOTH, expand=True)

        scroll_top_frame = tk.Frame(plot_container, height=32, bg="#e8ecef")
        scroll_top_frame.pack(fill=tk.X, side=tk.TOP)
        scroll_top_frame.pack_propagate(False)

        tk.Label(scroll_top_frame, text="Scroll history", bg="#e8ecef", fg="#444", font=("Arial", 8)).pack(side=tk.LEFT, padx=5)

        self.scrollbar = tk.Scrollbar(scroll_top_frame, orient=tk.HORIZONTAL, command=self.on_scroll,
                                      bg="#a0c4ee", troughcolor="#d1dae6", activebackground="#6ba4e7", width=12)
        self.scrollbar.pack(fill=tk.X, padx=10, pady=4)

        self.fig = Figure(figsize=(8, 4.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_ylim(FIXED_Y_MIN, FIXED_Y_MAX)
        self.ax.set_xlim(0, VISIBLE_POINTS)
        self.ax.set_xlabel("Measurement number")
        self.ax.set_ylabel("Temperature (C)")
        self.ax.grid(True)

        self.canvas_graph = FigureCanvasTkAgg(self.fig, master=plot_container)
        self.canvas_graph.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.canvas_graph.get_tk_widget().bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas_graph.get_tk_widget().bind("<Button-4>", self.on_mouse_wheel)
        self.canvas_graph.get_tk_widget().bind("<Button-5>", self.on_mouse_wheel)

        self.view_start = 0.0
        self.view_end = float(VISIBLE_POINTS)
        self.total_width = float(VISIBLE_POINTS)

        self.is_recording = False
        self.measurement_thread = None
        self.current_stop_time = 2.0
        self.background_image = None

        time.sleep(1)
        send_command("GET_POS")
        self.update_ui()
        self.draw_point()


    def go_to_calibration(self):
        global calibration_pos
        self.status_label.config(text=f"Returning to center ({calibration_pos[0]:.1f}, {calibration_pos[1]:.1f})")
        send_command(f"MOVE_TO:{int(calibration_pos[0])},{int(calibration_pos[1])}")


    def on_scroll(self, *args):
        if args[0] == 'moveto':
            pos = float(args[1])
        elif args[0] == 'scroll':
            step = float(args[1])
            range_width = max(1, self.total_width - VISIBLE_POINTS)
            pos = max(0.0, min(1.0, (self.view_start / range_width) + step * 0.1))
        else:
            return
        range_width = max(0, self.total_width - VISIBLE_POINTS)
        self.view_start = pos * range_width
        self.view_end = self.view_start + VISIBLE_POINTS
        self.update_graph()
        self.update_scrollbar()


    def on_mouse_wheel(self, event):
        scroll_up = (hasattr(event, 'delta') and event.delta > 0) or event.num == 4
        step = -3 if scroll_up else 3
        self.view_start = max(0, self.view_start + step)
        self.view_end = self.view_start + VISIBLE_POINTS
        self.update_graph()
        self.update_scrollbar()


    def update_scrollbar(self):
        if self.total_width <= VISIBLE_POINTS:
            self.scrollbar.set(0.0, 1.0)
        else:
            ratio = VISIBLE_POINTS / self.total_width
            start = self.view_start / self.total_width
            self.scrollbar.set(start, min(1.0, start + ratio))


    def update_graph_listbox(self):
        self.graph_listbox.delete(0, tk.END)
        for i, (ax, ay, t) in enumerate(points):
            px, py = ang_to_pix(ax, ay)
            self.graph_listbox.insert(tk.END, f"Point {i+1} (X={px} Y={py} T={t}C)")
            self.graph_listbox.itemconfig(i, fg=COLORS[i % len(COLORS)])


    def select_all_graphs(self):
        self.graph_listbox.select_set(0, tk.END)
        self.update_graph()


    def deselect_all_graphs(self):
        self.graph_listbox.selection_clear(0, tk.END)
        self.update_graph()


    def get_selected_points(self):
        return list(self.graph_listbox.curselection())


    def save_current_point(self):
        try:
            target_temp = float(self.temp_entry.get())
            points.append((current_pos[0], current_pos[1], target_temp))
            measurement_data[len(points)-1] = []
            self.update_points_list()
            self.update_graph_listbox()
            self.update_graph()
            px, py = ang_to_pix(current_pos[0], current_pos[1])
            self.status_label.config(text=f"Point {len(points)} added: X={px} Y={py} T={target_temp}C")
            self.draw_point()
        except ValueError:
            self.status_label.config(text="Error: enter a valid number")


    def clear_all(self):
        global is_measuring, is_paused, stop_requested
        if is_measuring:
            stop_requested = True
            is_measuring = False
            is_paused = False
            if self.measurement_thread and self.measurement_thread.is_alive():
                self.measurement_thread.join(timeout=1.0)
            self.btn_measure.config(state=tk.NORMAL)
            self.btn_pause.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_home.config(state=tk.NORMAL)
            self.btn_pause.config(bg="orange", text="Pause")
            self.status_label.config(text="Cycle stopped during clear")
        
        points.clear()
        measurement_data.clear()
        self.total_width = float(VISIBLE_POINTS)
        self.view_start = 0.0
        self.view_end = float(VISIBLE_POINTS)
        self.update_points_list()
        self.update_graph_listbox()
        self.update_graph()
        self.update_scrollbar()
        self.status_label.config(text="All cleared")
        self.background_image = None
        self.draw_point()
        self.go_to_calibration()
        send_command("CLEAR_HISTORY")


    def update_points_list(self):
        self.points_listbox.delete(0, tk.END)
        for i, (ax, ay, t) in enumerate(points):
            px, py = ang_to_pix(ax, ay)
            color = COLORS[i % len(COLORS)]
            self.points_listbox.insert(tk.END, f"{i+1}. X={px} Y={py} T={t}C")
            self.points_listbox.itemconfig(i, fg=color)


    def toggle_record(self):
        self.is_recording = not self.is_recording
        if self.is_recording:
            self.btn_record.config(bg="red", text="Recording... (press button)")
            self.status_label.config(text="RECORD MODE: press joystick button")
        else:
            self.btn_record.config(bg="lightblue", text="Record mode")
            self.status_label.config(text="Record mode off")


    def toggle_pause(self):
        global is_paused
        is_paused = not is_paused
        if is_paused:
            self.btn_pause.config(bg="red", text="Resume")
            self.status_label.config(text="PAUSED")
        else:
            self.btn_pause.config(bg="orange", text="Pause")
            self.status_label.config(text="Resumed")


    def start_measurement(self):
        global is_measuring, is_paused, stop_requested
        if len(points) == 0:
            self.status_label.config(text="No points to scan!")
            return
        is_measuring = True
        is_paused = False
        stop_requested = False
        self.btn_measure.config(state=tk.DISABLED)
        self.btn_pause.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_home.config(state=tk.DISABLED)
        self.status_label.config(text="CYCLE STARTED")
        self.measurement_thread = threading.Thread(target=self.measurement_loop, daemon=True)
        self.measurement_thread.start()


    def stop_measurement(self):
        global is_measuring, is_paused, stop_requested
        stop_requested = True
        is_measuring = False
        is_paused = False
        self.btn_measure.config(state=tk.NORMAL)
        self.btn_pause.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_home.config(state=tk.NORMAL)
        self.btn_pause.config(bg="orange", text="Pause")
        self.status_label.config(text="CYCLE STOPPED")


    def measurement_loop(self):
        global is_measuring, is_paused, stop_requested

        while is_measuring and not stop_requested:
            for i, (ax, ay, target_temp) in enumerate(points):
                if not is_measuring or stop_requested:
                    break

                while is_paused and is_measuring and not stop_requested:
                    time.sleep(0.5)

                if not is_measuring or stop_requested:
                    break

                safe_x = max(0, min(180, int(ax)))
                safe_y = max(0, min(180, int(ay)))

                self.root.after(0, lambda idx=i: self.status_label.config(
                    text=f"Moving to point {idx+1} ({safe_x}, {safe_y})"))
                send_command(f"MOVE_TO:{safe_x},{safe_y}")
                
                for _ in range(25):
                    if not is_measuring or stop_requested:
                        break
                    time.sleep(0.1)

                if not is_measuring or stop_requested:
                    break

                while is_paused and is_measuring and not stop_requested:
                    time.sleep(0.5)

                if not is_measuring or stop_requested:
                    break

                self.root.after(0, lambda idx=i: self.status_label.config(
                    text=f"Measuring at point {idx+1}..."))
                send_command(f"MEASURE:{i},{target_temp}")

                stop_time = self.current_stop_time
                start_wait = time.time()
                while time.time() - start_wait < 2.0:
                    if not is_measuring or stop_requested:
                        break
                    try:
                        msg = msg_queue.get(timeout=0.1)
                        if msg.startswith("MEASURE_RESULT:"):
                            parts = msg.split(':')[1].split(',')
                            stop_time = float(parts[3])
                            self.root.after(0, lambda st=stop_time: self.status_label.config(
                                text=f"Waiting {st:.1f} sec..."))
                            break
                    except queue.Empty:
                        pass

                if not is_measuring or stop_requested:
                    break

                waited = 0.0
                while waited < stop_time and is_measuring and not stop_requested:
                    if is_paused:
                        while is_paused and is_measuring and not stop_requested:
                            time.sleep(0.5)
                    time.sleep(0.1)
                    waited += 0.1

                if not is_measuring or stop_requested:
                    break

            if is_measuring and not is_paused and not stop_requested:
                self.root.after(0, lambda: self.status_label.config(
                    text="Cycle finished, starting new"))
                for _ in range(20):
                    if not is_measuring or stop_requested:
                        break
                    time.sleep(0.1)

        self.root.after(0, lambda: self.btn_measure.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.btn_pause.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.btn_stop.config(state=tk.DISABLED))
        self.root.after(0, lambda: self.btn_home.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.btn_pause.config(bg="orange", text="Pause"))
        self.root.after(0, lambda: self.status_label.config(
            text="CYCLE STOPPED" if stop_requested else "Cycle completed"))


    def update_graph(self):
        self.ax.clear()
        self.ax.set_ylim(FIXED_Y_MIN, FIXED_Y_MAX)
        self.ax.set_xlim(self.view_start, self.view_end)
        self.ax.set_xlabel("Measurement number")
        self.ax.set_ylabel("Temperature (C)")
        self.ax.grid(True)

        selected = self.get_selected_points()
        max_len = 0
        for point_idx in selected:
            if point_idx in measurement_data:
                max_len = max(max_len, len(measurement_data[point_idx]))

        self.total_width = max(self.total_width, float(max_len))
        self.update_scrollbar()

        for point_idx in selected:
            if point_idx < len(points) and point_idx in measurement_data and measurement_data[point_idx]:
                color = COLORS[point_idx % len(COLORS)]
                target_temp = points[point_idx][2]
                temps = measurement_data[point_idx]
                start_idx = max(0, int(self.view_start))
                end_idx = min(len(temps), int(self.view_end))

                if start_idx < end_idx:
                    x_vals = list(range(start_idx + 1, end_idx + 1))
                    y_vals = temps[start_idx:end_idx]
                    self.ax.plot(x_vals, y_vals, color=color, marker='o', linewidth=2,
                                 label=f"Point {point_idx+1} (target {target_temp}C)")
                    self.ax.axhline(y=target_temp, color=color, linestyle='--', alpha=0.5)

        if selected:
            self.ax.legend(loc='upper right', fontsize=8)
        self.canvas_graph.draw_idle()


    def update_ui(self):
        global current_pos
        updated = False
        while not msg_queue.empty():
            msg = msg_queue.get().strip()
            print(f"<- {msg}")

            if msg.startswith("POS:"):
                try:
                    parts = msg[4:].split(',')
                    if len(parts) >= 2:
                        new_x = float(parts[0].strip())
                        new_y = float(parts[1].strip())
                        current_pos = (max(0, min(180, new_x)), max(0, min(180, new_y)))
                        self.draw_point()
                        px, py = ang_to_pix(current_pos[0], current_pos[1])
                        self.coord_label.config(text=f"Beam: X={px} Y={py} | Angles: {current_pos[0]:.1f} {current_pos[1]:.1f}")
                        updated = True
                except Exception as e:
                    print(f"POS parse error: {e}")

            elif msg.startswith("BUTTON_PRESS"):
                if self.is_recording:
                    self.save_current_point()
                else:
                    self.status_label.config(text="Button pressed (record mode off)")

            elif msg.startswith("BUTTON_TEMP:"):
                try:
                    temp = float(msg.split(':')[1])
                    self.temp_display.config(text=f"Temperature: {temp:.2f}C")
                except:
                    pass

            elif msg.startswith("LIVE_TEMP:"):
                try:
                    temps = re.findall(r'Object=(\d+\.\d+)', msg)
                    if temps:
                        self.temp_display.config(text=f"Temperature: {float(temps[0]):.2f}C")
                except:
                    pass

            elif msg.startswith("TEMP_INFO:"):
                try:
                    temps = re.findall(r'Object=(\d+\.\d+).*Ambient=(\d+\.\d+)', msg)
                    if temps:
                        obj_temp, amb_temp = temps[0]
                        self.temp_display.config(text=f"Obj: {float(obj_temp):.2f}C | Amb: {float(amb_temp):.2f}C")
                except:
                    pass

            elif msg.startswith("MEASURE_RESULT:"):
                parts = msg.split(':')[1].split(',')
                point_id = int(parts[0])
                current_temp = float(parts[1])
                target_temp = float(parts[2])
                stop_time = float(parts[3])
                measurements_count = int(parts[4])
                self.current_stop_time = stop_time
                self.status_label.config(text=f"Point {point_id+1}: T={current_temp:.2f}C | Target={target_temp}C | Wait={stop_time:.1f}s | Count={measurements_count}")
                self.temp_display.config(text=f"Temperature: {current_temp:.2f}C")

            elif msg.startswith("MEASURE_DATA:"):
                try:
                    parts = msg.split(':')[1].split(',')
                    point_id = int(parts[0])
                    temp = float(parts[2])
                    if point_id not in measurement_data:
                        measurement_data[point_id] = []
                    measurement_data[point_id].append(temp)
                    self.update_graph()
                    self.temp_display.config(text=f"Temperature: {temp:.2f}C")
                    updated = True
                except:
                    pass

            elif msg.startswith("MEASURE_COMPLETE"):
                self.status_label.config(text="Measurement complete")

            elif msg.startswith("MEASURE_FINAL_TEMP:"):
                try:
                    parts = msg.split(':')[1].split(',')
                    temp = float(parts[1])
                    self.temp_display.config(text=f"Final temperature: {temp:.2f}C")
                except:
                    pass

            elif msg.startswith("ESP32_READY"):
                self.status_label.config(text="ESP32 ready")

        if updated:
            self.update_scrollbar()

        self.root.after(100, self.update_ui)


    def draw_point(self):
        self.canvas.delete("all")
        w, h = WINDOW_SIZE, WINDOW_SIZE
        scale_x = w / CAM_WIDTH
        scale_y = h / CAM_HEIGHT

        if self.background_image:
            self.canvas.create_image(WINDOW_SIZE//2, WINDOW_SIZE//2, image=self.background_image)

        grid_step_x = CAM_WIDTH // 16
        grid_step_y = CAM_HEIGHT // 16
        for i in range(0, CAM_WIDTH, grid_step_x):
            self.canvas.create_line(i * scale_x, 0, i * scale_x, h, fill='#444', dash=(3, 3))
        for i in range(0, CAM_HEIGHT, grid_step_y):
            self.canvas.create_line(0, i * scale_y, w, i * scale_y, fill='#444', dash=(3, 3))

        px, py = ang_to_pix(current_pos[0], current_pos[1])

        cal_px, cal_py = ang_to_pix(cal_angle[0], cal_angle[1])
        self.canvas.create_oval(cal_px*scale_x-8, cal_py*scale_y-8,
                                cal_px*scale_x+8, cal_py*scale_y+8,
                                fill='', outline='yellow', width=2, dash=(5,5))
        self.canvas.create_text(cal_px*scale_x+15, cal_py*scale_y-15,
                                text="Center", fill='yellow', font=('Arial', 8))

        for i, (ax, ay, t) in enumerate(points):
            cx, cy = ang_to_pix(ax, ay)
            color = COLORS[i % len(COLORS)]
            self.canvas.create_oval(cx*scale_x-6, cy*scale_y-6, cx*scale_x+6, cy*scale_y+6, fill=color, outline='#000')
            self.canvas.create_text(cx*scale_x+10, cy*scale_y-10, text=str(i+1), fill=color, font=('Arial', 9, 'bold'))

        lx = px * scale_x
        ly = py * scale_y
        self.canvas.create_oval(lx-12, ly-12, lx+12, ly+12, fill='red', outline='#fff', width=2)
        self.canvas.create_text(lx, ly, text="+", fill='#fff', font=('Arial', 16, 'bold'))


    def on_close(self):
        global is_measuring, is_paused, stop_requested
        stop_requested = True
        is_measuring = False
        is_paused = False
        if ser and ser.is_open:
            ser.close()
        if cam_ser and cam_ser.is_open:
            cam_ser.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    def launch_app():
        root.deiconify()
        Application(root)
    CalibrationDialog(root, launch_app)
    root.mainloop()