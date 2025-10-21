from flask import Flask, jsonify, request
from sqlalchemy import *
import pandas as pd
#config flask an db
app = Flask(__name__)
df = pd.read_csv("data/SpotifyTracks.csv")
eng = create_engine("sqlite:///spotify.db")
df.to_sql("tracks", con=eng, if_exists="replace", index=False)

@app.route("/search/title")
def search_title():
    title = request.args.get("title", "").strip()
    querry = text("SELECT * FROM tracks WHERE track_name LIKE :title")
    params = {
        "title": f"%{title}%"
    }
    songs = pd.read_sql(querry,eng,params=params)
    return jsonify(songs.to_dict(orient="records"))
@app.route("/search/artist")
def search_artist():
    artist = request.args.get("artist", "").strip()
    querry = text("SELECT * FROM tracks WHERE artists=:artist")
    params = {
        "artist": f"%{artist}%"
    }
    songs = pd.read_sql(querry,eng,params=params)
    return jsonify(songs.to_dict(orient="records"))
@app.route("/search/genre")
def search_artist():
    genre = request.args.get("genre", "").strip()
    querry = text("SELECT * FROM tracks WHERE track_genre=:genre")
    params = {
        "genre": f"%{genre}%"
    }
    songs = pd.read_sql(querry,eng,params=params)
    return jsonify(songs.to_dict(orient="records"))
@app.route("/edit/genre")
def edit_genre():
    pass