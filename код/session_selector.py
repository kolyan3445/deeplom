import tkinter as tk
from tkinter import ttk
from database import DatabaseManager
from gui import ThermalMonitorApp

class SessionSelector:

    def __init__(self, settings):
        self.settings = settings
        self.db = DatabaseManager(settings)

        self.root = tk.Tk()
        self.root.title("Выбор сессии")
        self.root.geometry("700x500")

        self.sessions = tk.Listbox(self.root)
        self.sessions.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Button(self.root, text="Открыть", command=self.open_session).pack(fill="x", padx=10, pady=5)
        ttk.Button(self.root, text="Создать новую сессию", command=self.create_session).pack(fill="x", padx=10, pady=5)

        self.load_sessions()

    def load_sessions(self):
        self.sessions.delete(0, tk.END)
        for s in self.db.get_sessions():
            self.sessions.insert(tk.END, f"Сессия №{s['id']} | {s['created_at']}")

    def create_session(self):
        session_id = self.db.create_session()
        self.root.destroy()
        ThermalMonitorApp(self.settings, session_id, is_new_session=True).run()

    def open_session(self):
        sel = self.sessions.curselection()
        if not sel:
            return
        session = self.db.get_sessions()[sel[0]]
        self.root.destroy()
        ThermalMonitorApp(self.settings, session["id"], is_new_session=False).run()

    def run(self):
        self.root.mainloop()