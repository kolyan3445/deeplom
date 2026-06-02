CREATE DATABASE IF NOT EXISTS thermal_monitor;
USE thermal_monitor;


CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS measurements (

    id INT AUTO_INCREMENT PRIMARY KEY,

    session_id INT NOT NULL,

    timestamp DATETIME NOT NULL,

    image_path VARCHAR(255) NOT NULL,

    FOREIGN KEY(session_id)
        REFERENCES sessions(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS temperature_points (

    id INT AUTO_INCREMENT PRIMARY KEY,

    measurement_id INT NOT NULL,

    pos_x INT NOT NULL,

    pos_y INT NOT NULL,

    temperature DECIMAL(6,2) NOT NULL,

    FOREIGN KEY(measurement_id)
        REFERENCES measurements(id)
        ON DELETE CASCADE
);