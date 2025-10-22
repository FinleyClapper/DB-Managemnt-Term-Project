import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '../frontend/static/rhythmix.db')

os.makedirs(os.path.dirname(db_path), exist_ok=True)

conn = sqlite3.connect('frontend/static/rhythmix.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS playlists
(
    id
    INTEGER
    PRIMARY
    KEY
    AUTOINCREMENT,
    user_id
    INTEGER
    NOT
    NULL,
    name
    TEXT
    NOT
    NULL,
    FOREIGN
    KEY
(
    user_id
) REFERENCES users
(
    id
)
    );
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    genre TEXT
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS playlists_songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    song_title TEXT NOT NULL,
    artist TEXT,
    genre TEXT,
    FOREIGN KEY (playlist_id) REFERENCES playlists(id)
);
    ''')

conn.commit()
conn.close()
print("Database initialized")