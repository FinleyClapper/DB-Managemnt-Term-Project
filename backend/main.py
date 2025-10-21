import os
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import pandas as pd
from kaggle.api.kaggle_api_extended import KaggleApi

#Load environment variables from .env file
load_dotenv()

#Tell flash where to find templates and static files.
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__),'../frontend/templates'),
    static_folder=os.path.join(os.path.dirname(__file__),'../frontend/static')
)
#Download only if file doesn't exist
dataset_path = os.path.join(os.path.dirname(__file__), 'data/dataset.csv')
if not os.path.exists(dataset_path):
    api=KaggleApi()
    api.authenticate()
    #THE DATASET:
    api.dataset_download_files('maharshipandya/-spotify-tracks-dataset', path='data', unzip=True)
    print("Spotify dataset downloaded and unzipped")
    
#Load dataset with pandas
df = pd.read_csv(dataset_path)
print("Shape:", df.shape)
print("Columns:", df.columns.tolist())
#print(df.head())

playlists = []

#define routes
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

# Flask serves "search.html" template When someone visits /search
@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        query = request.form.get('query', '').lower()
        results_df = df[df['track_name'].str.lower().str.contains(query) | df['artists'].str.lower().str.contains(query)]
        results = results_df[['track_name','artists','track_genre','duration_ms']].rename(
            columns={'track_name':'title','artists':'artist','track_genre':'genre','duration_ms':'duration'}
        ).to_dict(orient='records')
        # Convert duration from ms to sec
        for r in results:
            r['duration'] = int(r['duration'] / 1000)
    return render_template('search.html', results=results)

@app.route('/playlist', methods=['GET', 'POST'])
def playlist():
    # Playlist creation (basic placeholder for now)
    if request.method == 'POST':
        name = request.form.get('name')
        # Save to DB or mock list later
        print(f"Created playlist: {name}")
        # You could store playlists in a global or session for now
        return redirect(url_for('playlist'))

    # Filters
    selected_genre = request.args.get('genre')
    query = request.args.get('query')

    # Get genres
    genres = sorted(df['track_genre'].dropna().unique())

    # Filter dataset
    filtered = df.copy()
    if selected_genre:
        filtered = filtered[filtered['track_genre'] == selected_genre]
    if query:
        filtered = filtered[
            filtered['track_name'].str.contains(query, case=False, na=False)
            | filtered['artists'].str.contains(query, case=False, na=False)
            ]

    # Dummy playlists for now
    playlists = [
        {'name': 'My Chill Mix', 'songs': ['Song A', 'Song B']},
        {'name': 'Workout Vibes', 'songs': ['Track X', 'Track Y', 'Track Z']},
    ]

    return render_template(
        'playlist.html',
        genres=genres,
        selected_genre=selected_genre,
        query=query,
        songs=filtered[['track_name', 'artists', 'track_genre']].dropna().to_dict(orient='records'),
        playlists=playlists
    )

@app.route('/add_song', methods=['GET', 'POST'])
def add_song():
    if request.method == 'POST':
        # Call logic teammate’s function here
        return redirect(url_for('index'))
    return render_template('add_song.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/account')
def account():
    # TODO: replace with real database query for the logged-in user
    # Placeholder: empty list for now
    playlists = []  # Later: fetch playlists from DB for current user

    return render_template(
        'account.html',
        playlists=playlists
    )
@app.route('/playlist/<int:playlist_id>/edit')
def edit_playlist(playlist_id):
    # TODO: implement edit functionality
    return f"Edit playlist {playlist_id} (not implemented yet)"

@app.route('/playlist/<int:playlist_id>/delete')
def delete_playlist(playlist_id):
    # TODO: implement delete functionality
    return f"Delete playlist {playlist_id} (not implemented yet)"



#Run The App
if __name__ == '__main__':
    app.run(debug=True)