import mysql.connector
from tkinter import messagebox

class DatabaseManager:

    def __init__(self, c):
        
        try:
            self.connection = mysql.connector.connect(
                host=c["mysql_host"],
                port=c["mysql_port"],
                user=c["mysql_user"],
                password=c["mysql_password"],
                database=c["mysql_database"]
            )

            self.cursor = self.connection.cursor(
                dictionary=True
            )

        except Exception as e:
            from logger import logger
            messagebox.showerror(title="Ошибка БД!", message="Ошибка подключения к базе данных! Проверьте запущен ли у вас MySQL или файл настроек settings.json!")

            logger.error(e)

    def create_session(self):

        self.cursor.execute(
            """
            INSERT INTO sessions(created_at)
            VALUES(NOW())
            """
        )

        self.connection.commit()

        return self.cursor.lastrowid

    def get_sessions(self):

        self.cursor.execute(
            """
            SELECT *
            FROM sessions
            ORDER BY id DESC
            """
        )

        return self.cursor.fetchall()

    def create_measurement(self,session_id,timestamp,image_path):

        self.cursor.execute(
            """
            INSERT INTO measurements
            (session_id, timestamp, image_path)
            VALUES(%s,%s,%s)
            """,
            (session_id, timestamp, image_path))

        self.connection.commit()
        
        return self.cursor.lastrowid

    def insert_points(self, measurement_id, points):
        rows = []

        for p in points:
            rows.append((measurement_id, p["x"], p["y"], p["temp"]))

        self.cursor.executemany(
            """
            INSERT INTO temperature_points
            (
                measurement_id,
                pos_x,
                pos_y,
                temperature
            )
            VALUES(%s,%s,%s,%s)
            """, rows)

        self.connection.commit()

    def get_measurements(self, session_id):

        self.cursor.execute(
            """
            SELECT *
            FROM measurements
            WHERE session_id=%s
            ORDER BY timestamp DESC
            """,
            (session_id,))

        return self.cursor.fetchall()

    def get_points(self, measurement_id):

        self.cursor.execute(
            """
            SELECT
                pos_x,
                pos_y,
                temperature
            FROM temperature_points
            WHERE measurement_id=%s
            """, (measurement_id,))

        return self.cursor.fetchall()

    def get_last_image(self, session_id):

        self.cursor.execute(
            """
            SELECT image_path
            FROM measurements
            WHERE session_id=%s
            ORDER BY timestamp DESC
            LIMIT 1
            """, (session_id,))

        row = self.cursor.fetchone()

        return (row["image_path"] if row else None)

    def close(self):

        try:
            self.cursor.close()
            self.connection.close()

        except Exception:
            pass

    def get_session_points(self,session_id):

        self.cursor.execute(
            """
            SELECT
                m.id AS measurement_id,
                m.timestamp,
                p.pos_x,
                p.pos_y,
                p.temperature
            FROM measurements m
            JOIN temperature_points p
                ON p.measurement_id = m.id
            WHERE m.session_id=%s
            ORDER BY m.timestamp
            """,(session_id,))
        
        return self.cursor.fetchall()