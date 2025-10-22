from flask import Flask, jsonify, request,session
from sqlalchemy import *
import pandas as pd
import kagglehub
from flask_cors import CORS
metadata = MetaData()
path = kagglehub.dataset_download("maharshipandya/-spotify-tracks-dataset")
app = Flask(__name__)
app.secret_key = "a8f5f167f44f4964e6c998dee827110c9a34b1b8e5f3f4c1a2d3b4c5d6e7f890"
app.config.update(
    SESSION_COOKIE_SAMESITE=None,
    SESSION_COOKIE_SECURE=False
)
CORS(app, supports_credentials=True, origins=["http://127.0.0.1:5500"])
df = pd.read_csv(f'{path}/dataset.csv')
needed_collumns = ['track_id','track_name','artists','track_genre']
df = df[needed_collumns]
eng = create_engine("sqlite:///spotify.db")
df.to_sql("tracks", con=eng, if_exists="replace", index=False)
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String, unique=True, nullable=False),
    Column("email", String, unique=True, nullable=False),
    Column("password", String, nullable=False)
)
playlists = Table(
    "playlists",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, unique=True, nullable=False),
    Column("name", String, unique=True, nullable=False),
    Column("description", String, nullable=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
)

playlist_songs = Table(
    "playlist_songs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("track_id", Integer, nullable=False),
    Column("playlist_id", Integer, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False),
    Column("track_name", String, nullable=False),
    Column("artists", String, nullable=False),
    Column("track_genre", String, nullable=True),
)
metadata.create_all(eng)
@app.route("/api/search/title")
def search_title():
    title = request.args.get("title", "").strip()
    querry = text("SELECT * FROM tracks WHERE track_name LIKE :title LIMIT 20")
    params = {
        "title": f"%{title}%"
    }
    songs = pd.read_sql(querry,eng,params=params)
    songs = songs.drop_duplicates(subset=['artists', 'track_name'], keep='first')
    songs = songs.to_dict(orient="records")
    return jsonify(songs)
@app.route("/api/search/artist")
def search_artist():
    artist = request.args.get("artist", "").strip()
    querry = text("SELECT * FROM tracks WHERE artists=:artist LIMIT 20")
    params = {
        "artist": f"%{artist}%"
    }
    songs = pd.read_sql(querry,eng,params=params)
    songs = songs.drop_duplicates(subset=['artists', 'track_name'], keep='first')
    return jsonify(songs.to_dict(orient="records"))
@app.route("/api/search/genre")
def search_genre():
    genre = request.args.get("genre", "").strip()
    querry = text("SELECT * FROM tracks WHERE track_genre=:genre LIMIT 20")
    params = {
        "genre": f"%{genre}%"
    }
    songs = pd.read_sql(querry,eng,params=params)
    songs = songs.drop_duplicates(subset=['artists', 'track_name'], keep='first')
    return jsonify(songs.to_dict(orient="records"))
@app.route("/api/auth/signup")
def auth_signup():
    user = request.args.get("user", "").strip()
    email = request.args.get("email", "").strip()
    pswrd = request.args.get("pswrd", "").strip()
    with eng.begin() as conn:
        params = {
            "user": user,
            "email": email,
            "pswrd": pswrd,
        }
        conn.execute(text("INSERT INTO users (username, email, password) VALUES (:user, :email, :pswrd)"),parameters=params)
        return jsonify({"message": "Registered"}), 201
@app.route("/api/auth/login")
def auth_login():
    user = request.args.get("user", "").strip()
    pswrd = request.args.get("pswrd", "").strip()
    with eng.begin() as conn:
        params = {
            "user": user
        }
        username = conn.execute(text("SELECT * FROM users WHERE username=:user"),parameters=params).fetchone()
        if( (not username) or (not username.password == pswrd)):
            return jsonify({"error": "Invalid credentials"}), 401
    session["user_id"] = username.id
    session["username"] = username.username
    return jsonify({"message": "Login successful"}), 200
@app.route('/api/playlist/create')
def create_playlist():
    name = request.args.get("name", "").strip()
    description = request.args.get("description", "").strip()
    with eng.begin() as conn:
        params = {
            "name": name,
            "description": description,
            "user_id": session["user_id"]
        }
        conn.execute(text("INSERT INTO playlists (name, description,user_id) VALUES (:name, :description,:user_id)"),parameters=params)
        return jsonify({"message": "Playlist Created"}), 201
@app.route('/api/playlist/fetch')
def fetch_playlists():
    params = {
        "id": session["user_id"]
    }
    playlists = pd.read_sql(text("SELECT * FROM playlists WHERE user_id=:id "), eng,params=params)
    return jsonify(playlists.to_dict(orient="records")), 200
@app.route('/api/playlist/fetch/id')
def fetch_playlist():
    id = request.args.get("id", "").strip()
    params = {
        "id": id
    }
    playlist = pd.read_sql(text("SELECT * FROM playlists WHERE id=:id"), eng,params=params)
    return jsonify(playlist.to_dict(orient="records")), 200
@app.route('/api/playlist/fetch/songs/id')
def fetch_songs():
    id = request.args.get("id","").strip()
    params = {
        "id": id
    }
    songs = pd.read_sql(text('SELECT * FROM playlist_songs WHERE playlist_id=:id'),eng,params=params)
    return jsonify(songs.to_dict(orient="records")), 200
@app.route('/api/search/track_id')
def search_id():
    id = request.args.get("id","").strip()
    params = {
        "id": id
    }
    songs = pd.read_sql(text('SELECT * FROM tracks WHERE track_id=:id'),eng,params=params)
    return jsonify(songs.to_dict(orient="records")), 200
@app.route('/api/playlist/add')
def add_song():
    artists = request.args.get("artists","").strip()
    track_name = request.args.get("track_name","").strip()
    track_genre = request.args.get("track_genre","").strip()
    track_id = request.args.get("track_id","").strip()
    playlist_id = request.args.get("playlist_id","").strip()
    with eng.begin() as conn:
        params = {
        "artists": artists,
        "track_name": track_name,
        "track_genre": track_genre,
        "track_id": track_id,
        "playlist_id": playlist_id
    }
        conn.execute(text("INSERT INTO playlist_songs (artists, track_name,track_genre,track_id,playlist_id) VALUES (:artists, :track_name, :track_genre, :track_id,:playlist_id)"),parameters=params)
        return jsonify({"message": "Song Added"}), 201
@app.route('/api/playlist/song/remove')
def remove_song():
    id = request.args.get('id','').strip()
    params = {
        "id": id
    }
    with eng.begin() as conn:
        conn.execute(text("DELETE FROM playlist_songs WHERE id=:id"),parameters=params)
    return jsonify({"message": "Song Removed"}), 201
@app.route('/api/playlist/remove/playlist')
def remove_playlist():
    id = request.args.get('id','').strip()
    params = {
        "id": id
    }
    with eng.begin() as conn:
        conn.execute(text("DELETE FROM playlists WHERE id=:id"),parameters=params)
    return jsonify({"message": "Playlist Removed"}), 201
@app.route("/api/auth/me", methods=["GET"])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    with eng.begin() as conn:
        user = conn.execute(
            text("SELECT id, username, email FROM users WHERE id = :id"),
            {"id": session['user_id']}
        ).fetchone()
        
        if not user:
            session.clear()
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({
            "user": {"id": user.id, "username": user.username, "email": user.email}
        }), 200
@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200
app.run(debug=True, port=5000)