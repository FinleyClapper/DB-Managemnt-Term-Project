from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import os
import sqlite3
import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi

# Load environment variables
load_dotenv()

# App setup
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), '../frontend/templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '../frontend/static')
)
app.secret_key = "your_secret_key"

# Database paths
DATABASE = os.path.join(os.path.dirname(__file__), '../frontend/static/rhythmix.db')
db_path = DATABASE
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# SQLite helpers
def get_db():
    db_conn = getattr(g, '_database', None)
    if db_conn is None:
        db_conn = g._database = sqlite3.connect(DATABASE)
        db_conn.row_factory = sqlite3.Row
    return db_conn

@app.teardown_appcontext
def close_connection(exception):
    db_conn = getattr(g, '_database', None)
    if db_conn is not None:
        db_conn.close()

# Load Spotify dataset
dataset_path = os.path.join(os.path.dirname(__file__), 'data/dataset.csv')
if not os.path.exists(dataset_path):
    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files('maharshipandya/-spotify-tracks-dataset', path='data', unzip=True)
    print("Spotify dataset downloaded and unzipped")

df = pd.read_csv(dataset_path)
print("Shape:", df.shape)
print("Columns:", df.columns.tolist())

# Routes
@app.route('/')
def index():
    genres = sorted(df['track_genre'].dropna().unique())
    selected_genre = request.args.get('genre')
    filtered = df[df['track_genre'] == selected_genre] if selected_genre else df
    return render_template(
        'index.html',
        genres=genres,
        tracks=filtered[['track_name', 'artists', 'track_genre']].dropna().to_dict(orient='records'),
        selected_genre=selected_genre
    )

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        query = request.form.get('query', '').lower()
        results_df = df[df['track_name'].str.lower().str.contains(query) |
                        df['artists'].str.lower().str.contains(query)]
        results = results_df[['track_name','artists','track_genre','duration_ms']].rename(
            columns={'track_name':'title','artists':'artist','track_genre':'genre','duration_ms':'duration'}
        ).to_dict(orient='records')
        for r in results:
            r['duration'] = int(r['duration'] / 1000)
    return render_template('search.html', results=results)

@app.route('/register', methods=['GET', 'POST'])
def register():
    db_conn = get_db()
    cursor = db_conn.cursor()

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Validate input
        if not username or not email or not password:
            flash("All fields are required.")
            return redirect(url_for('register'))

        # Check if username already exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            flash("Username already taken.")
            return redirect(url_for('register'))

        # Hash the password and insert user
        pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, pw_hash)
        )
        db_conn.commit()

        flash("Account created successfully! You can now log in.")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    db_conn = get_db()
    cursor = db_conn.cursor()

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash("Username and password required")
            return redirect(url_for('login'))

        # Look up the user in the database
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user['password'], password):
            # Store user info in session
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f"Welcome, {username}!")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/playlist', methods=['GET', 'POST'])
def playlist():
    if 'user_id' not in session:
        flash("You must be logged in to create a playlist.")
        return redirect(url_for('login'))

    db_conn = get_db()
    cursor = db_conn.cursor()

    user_id = session['user_id']

    # Handle playlist creation
    if request.method == 'POST':
        playlist_name = request.form.get('name')
        selected_songs = request.form.getlist('songs')

        if playlist_name:
            cursor.execute(
                "INSERT INTO playlists (name, user_id) VALUES (?, ?)",
                (playlist_name, user_id)
            )
            playlist_id = cursor.lastrowid

            for song_title in selected_songs:
                cursor.execute(
                    "INSERT INTO playlist_songs (playlist_id, song_title) VALUES (?, ?)",
                    (playlist_id, song_title)
                )

            db_conn.commit()
            flash("Playlist created successfully!")
            return redirect(url_for('playlist'))

    # Genre filtering and search
    selected_genre = request.args.get('genre')
    query = request.args.get('query', '').lower()
    songs_df = df.copy()

    if selected_genre:
        songs_df = songs_df[songs_df['track_genre'] == selected_genre]
    if query:
        songs_df = songs_df[
            songs_df['track_name'].str.lower().str.contains(query) |
            songs_df['artists'].str.lower().str.contains(query)
            ]

    songs = songs_df[['track_name', 'artists', 'track_genre']].to_dict(orient='records')

    # Fetch this user's playlists only
    cursor.execute("SELECT * FROM playlists WHERE user_id = ?", (user_id,))
    playlists_rows = cursor.fetchall()

    playlists = []
    for row in playlists_rows:
        cursor.execute(
            "SELECT song_title FROM playlist_songs WHERE playlist_id = ?",
            (row['id'],)
        )
        songs_list = [r['song_title'] for r in cursor.fetchall()]
        playlists.append({'id': row['id'], 'name': row['name'], 'songs': songs_list})

    genres = sorted(df['track_genre'].dropna().unique())

    return render_template(
        'playlist.html',
        songs=songs,
        playlists=playlists,
        genres=genres,
        selected_genre=selected_genre,
        query=query
    )

    # Genre filtering & search
    selected_genre = request.args.get('genre')
    query = request.args.get('query', '').lower()
    songs_df = df.copy()
    if selected_genre:
        songs_df = songs_df[songs_df['track_genre'] == selected_genre]
    if query:
        songs_df = songs_df[songs_df['track_name'].str.lower().str.contains(query) |
                            songs_df['artists'].str.lower().str.contains(query)]

    songs = songs_df[['track_name', 'artists', 'track_genre']].to_dict(orient='records')

    # Fetch playlists for logged-in user
    cursor.execute("SELECT * FROM playlists WHERE user_id = ?", (session['user_id'],))
    playlists_rows = cursor.fetchall()
    playlists = []
    for row in playlists_rows:
        cursor.execute(
            "SELECT song_title FROM playlist_songs WHERE playlist_id = ?",
            (row['id'],)
        )
        songs_list = [r['song_title'] for r in cursor.fetchall()]
        playlists.append({'id': row['id'], 'name': row['name'], 'songs': songs_list})

    genres = sorted(df['track_genre'].dropna().unique())

    return render_template(
        'playlist.html',
        songs=songs,
        playlists=playlists,
        genres=genres,
        selected_genre=selected_genre,
        query=query
    )

@app.route('/account')
def account():
    if 'user_id' not in session:
        flash("Please log in to view your account.")
        return redirect(url_for('login'))

    db_conn = get_db()
    cursor = db_conn.cursor()
    user_id = session['user_id']

    cursor.execute("SELECT * FROM playlists WHERE user_id = ?", (user_id,))
    playlists_rows = cursor.fetchall()

    playlists = []
    for row in playlists_rows:
        cursor.execute(
            "SELECT song_title FROM playlist_songs WHERE playlist_id = ?",
            (row['id'],)
        )
        songs_list = [r['song_title'] for r in cursor.fetchall()]
        playlists.append({'id': row['id'], 'name': row['name'], 'songs': songs_list})

    return render_template('account.html', playlists=playlists)

@app.route('/playlist/<int:playlist_id>/edit')
def edit_playlist(playlist_id):
    return f"Edit playlist {playlist_id} (not implemented yet)"

@app.route('/playlist/<int:playlist_id>/delete')
def delete_playlist(playlist_id):
    return f"Delete playlist {playlist_id} (not implemented yet)"

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
