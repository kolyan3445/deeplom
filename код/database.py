import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG
import json
import base64
import requests
from io import BytesIO
from PIL import Image

def get_connection():
    """Get DB connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"DB Error: {e}")
        return None

def ensure_table():
    """Create monitoring table if not exists."""
    conn = get_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitoring (
            id INT AUTO_INCREMENT PRIMARY KEY,
            first_time BIGINT,
            first_temp FLOAT,
            image_base64 LONGTEXT,
            points_json TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
    """)
    conn.commit()
    cursor.close()
    conn.close()
    return True

def list_sessions():
    """List sessions: [(id, first_time, first_temp), ...]."""
    conn = get_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("SELECT id, first_time, first_temp FROM monitoring ORDER BY id DESC")
    sessions = cursor.fetchall()
    cursor.close()
    conn.close()
    return sessions

def save_session(points):
    """Save session: first_time/temp/image_base64/points."""
    if not points:
        return None
    first_point = points[0]
    first_time = first_point['time']
    first_temp = first_point['point']['temp']
    points_json = json.dumps(points)
    
    # Get current image and base64 encode
    try:
        resp = requests.get(IMAGE_URL, timeout=5)
        img = Image.open(BytesIO(resp.content))
        img.thumbnail(IMAGE_MAX_SIZE, Image.Resampling.LANCZOS)
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        image_base64 = base64.b64encode(img_buffer.getvalue()).decode('ascii')
    except:
        image_base64 = ""
    
    conn = get_connection()
    if not conn:
        return None
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO monitoring (first_time, first_temp, image_base64, points_json) VALUES (%s, %s, %s, %s)",
        (first_time, first_temp, image_base64, points_json)
    )
    conn.commit()
    session_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return session_id

def load_session(session_id):
    """Load points and image_base64."""
    conn = get_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    cursor.execute("SELECT image_base64, points_json FROM monitoring WHERE id = %s", (session_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        image_base64, points_json = result
        return {'image_base64': image_base64, 'points': json.loads(points_json)}
    return []

