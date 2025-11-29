from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
import pandas as pd
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import sessionmaker, scoped_session
from werkzeug.security import check_password_hash, generate_password_hash
import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, text

#Load environment variables from .env file
load_dotenv()
#CHECK KAGGLE CONFIG
#if not os.getenv("KAGGLE_CONFIG_DIR"):
 #   print("⚠️ Warning: KAGGLE_CONFIG_DIR is not set. Please configure it before running.")
#rom kaggle.api.kaggle_api_extended import KaggleApi
# === SAFE KAGGLE DOWNLOAD (only runs when needed) ===
dataset_path = os.path.join(os.path.dirname(__file__), 'data/dataset.csv')

if not os.path.exists(dataset_path):
    print("Dataset not found — downloading from Kaggle...")
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
        api.dataset_download_files('maharshipandya/-spotify-tracks-dataset', path='data', unzip=True)
        print("Spotify dataset downloaded and unzipped")
    except Exception as e:
        print("Could not download dataset automatically:", e)
        print("Please download it manually or set up Kaggle API properly.")
else:
    print("Dataset already exists — skipping download")
# ====================================================
#Tell flash where to find templates and static files.
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__),'../frontend/templates'),
    static_folder=os.path.join(os.path.dirname(__file__),'../frontend/static')
)
app.secret_key = os.getenv("SECRET_KEY", "super-secret-key-change-in-production")  # Must have!

# Database setup
eng = create_engine("sqlite:///spotify.db")
metadata = MetaData()

#Download only if file doesn't exist
dataset_path = os.path.join(os.path.dirname(__file__), 'data/dataset.csv')
if not os.path.exists(dataset_path):
    api=KaggleApi()
    api.authenticate()
    #THE DATASET:
    api.dataset_download_files('maharshipandya/-spotify-tracks-dataset', path='data', unzip=True)
    print("Spotify dataset downloaded and unzipped")
    
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'           # redirect unauthenticated users here
login_manager.login_message_category = "info"

# Simple in-memory user class for flask_login
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    with eng.begin() as conn:
        row = conn.execute(text("SELECT id, username, email FROM users WHERE id = :id"), {"id": user_id}).fetchone()
        if row:
            return User(row.id, row.username, row.email)
    return None

#Load dataset with pandas
df = pd.read_csv(dataset_path)
print("Shape:", df.shape)
print("Columns:", df.columns.tolist())
#print(df.head())

playlists = Table(
    "playlists",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, nullable=False)
)
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String, nullable=False),
    Column("email", String, nullable=False),
    Column("password", String, nullable=False)
)

metadata.create_all(eng)

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
        for r in results:  # Convert duration from ms to sec
            r['duration'] = int(r['duration'] / 1000)
    return render_template('search.html', results=results)

@app.route('/playlist', methods=['GET', 'POST'])
def playlist():
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            with eng.begin() as conn:
                conn.execute(
                    text("INSERT INTO playlists (name) VALUES (:name)"),
                    {"name": name}
                )
                print(pd.read_sql("SELECT * FROM users", eng))
        return redirect(url_for('account'))  # after creating, go to account page

        # --- GET request: build context ---
    selected_genre = request.args.get('genre')
    query = request.args.get('query', '').lower()

    # Genres list
    genres = sorted(df['track_genre'].dropna().unique())

    # Filter songs
    songs_df = df
    if selected_genre:
        songs_df = songs_df[songs_df['track_genre'] == selected_genre]
    if query:
        songs_df = songs_df[
            songs_df['track_name'].str.lower().str.contains(query) |
            songs_df['artists'].str.lower().str.contains(query)
        ]

    songs = songs_df[['track_name', 'artists', 'track_genre']].dropna().to_dict(orient='records')

    # Fetch playlists from DB
    with eng.begin() as conn:
        rows = conn.execute(text("SELECT * FROM playlists")).fetchall()

    return render_template(
        'playlist.html',
        genres=genres,
        selected_genre=selected_genre,
        query=query,
        songs=songs,
        playlists=rows
    )

@app.route('/add_song', methods=['GET', 'POST'])
def add_song():
    if request.method == 'POST':
        return redirect(url_for('index'))
    return render_template('add_song.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return render_template('login.html', error="Please fill in all fields")

        with eng.begin() as conn:
            user_row = conn.execute(
                text("SELECT id, username, email, password FROM users WHERE username = :u"),
                {"u": username}
            ).fetchone()

            if user_row and check_password_hash(user_row.password, password):
                user_obj = User(user_row.id, user_row.username, user_row.email)
                login_user(user_obj)
                return redirect(url_for('account'))  # or wherever you want after login
            else:
                return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    print("\n" + "="*60)
    print("REGISTER ROUTE WAS CALLED!")
    print("Method:", request.method)
    print("Form data:", request.form)
    print("="*60 + "\n")

    if request.method == 'POST':
        print("POST received! Processing registration...")

        username = request.form.get('username')
        email    = request.form.get('email')
        password = request.form.get('password')

        print(f"Received → username: {username}, email: {email}, password: {'*' * len(password) if password else None}")

        if not all([username, email, password]):
            print("Missing fields!")
            return render_template('register.html', error="All fields required")

        hashed_pw = generate_password_hash(password)
        print("Password hashed")

        try:
            with eng.begin() as conn:
                # Check duplicate
                exists = conn.execute(text("SELECT 1 FROM users WHERE username = :u OR email = :e"),
                                    {"u": username, "e": email}).fetchone()
                if exists:
                    print("User/email already exists")
                    return render_template('register.html', error="Already taken")

                # INSERT
                result = conn.execute(
                    text("INSERT INTO users (username, email, password) VALUES (:u, :e, :p)"),
                    {"u": username, "e": email, "p": hashed_pw}
                )
                print(f"SUCCESS! New user ID: {result.lastrowid}")

            print("Redirecting to login...")
            return redirect(url_for('login'))

        except Exception as e:
            print("DATABASE ERROR:", e)
            import traceback
            traceback.print_exc()
            return render_template('register.html', error="Server error")

    # GET request
    print("Serving register form (GET)")
    return render_template('register.html')

@app.route('/account')
def account():
    with eng.begin() as conn:
        rows = conn.execute(text("SELECT * FROM playlists")).fetchall()
    return render_template('account.html', playlists=rows)

@app.route('/playlist/<int:playlist_id>/edit')
def edit_playlist(playlist_id):
    # TODO: implement edit functionality
    return f"Edit playlist {playlist_id} (not implemented yet)"

@app.route('/playlist/<int:playlist_id>/delete')
def delete_playlist(playlist_id):
    # TODO: implement delete functionality
    return f"Delete playlist {playlist_id} (not implemented yet)"

@app.route('/debug-users')
def debug_users():
    # Force a fresh connection – this bypasses ANY scoping issues
    temp_engine = create_engine("sqlite:///spotify.db")
    
    try:
        df = pd.read_sql("SELECT id, username, email FROM users", temp_engine)
        print("\n" + "="*70)
        print("USERS FOUND IN DATABASE (debug route)")
        print("="*70)
        if df.empty:
            print("No users registered yet.")
        else:
            print(df.to_string(index=False))
        print("="*70 + "\n")
    except Exception as e:
        print("ERROR reading users table:", e)
    
    return "Check your terminal – users printed above!"

#Run The App
if __name__ == '__main__':
    app.run(debug=True)