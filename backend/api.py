from flask import Flask, jsonify, request
from sqlalchemy import *
import pandas as pd
import kagglehub
from flask_cors import CORS
metadata = MetaData()
path = kagglehub.dataset_download("maharshipandya/-spotify-tracks-dataset")
app = Flask(__name__)
CORS(app)
df = pd.read_csv(f'{path}/dataset.csv')
needed_collumns = ['track_name','artists','track_genre']
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
playlists = Table("playlists",metadata,
                Column("id",Integer,primary_key=True,unique=True,nullable=False,autoincrement=True),
                Column("name",String,unique=True,nullable=False),
                Column("description",String,unique=False,nullable=True))
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
    return jsonify({"message": "Login successful"}), 200
@app.route('/api/playlist/create')
def create_playlist():
    print(request.view_args)
    name = request.args.get("name", "").strip()
    description = request.args.get("description", "").strip()
    with eng.begin() as conn:
        params = {
            "name": name,
            "description": description
        }
        conn.execute(text("INSERT INTO playlists (name, description) VALUES (:name, :description)"),parameters=params)
        return jsonify({"message": "Playlist Created"}), 201
app.run(debug=True, port=5000)
