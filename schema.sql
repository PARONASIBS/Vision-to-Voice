CREATE DATABASE vision_to_voice;
USE vision_to_voice;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(512) NOT NULL
);

CREATE TABLE comics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    title VARCHAR(200),
    image_path VARCHAR(255),
    audio_path VARCHAR(255),
    caption_text TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

