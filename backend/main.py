from flask import Flask, render_template, request, redirect, url_for, abort, flash, jsonify
from dotenv import load_dotenv
import pandas as pd
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from sqlalchemy.orm import sessionmaker, scoped_session
from werkzeug.security import check_password_hash, generate_password_hash
import os
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, text, inspect
from math import ceil

#Load environment variables from .env file
load_dotenv()

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
    def __init__(self, id, username, email, description=None, full_name=None):
        self.id = id
        self.username = username
        self.email = email
        self.description = description
        self.full_name = full_name

@login_manager.user_loader
def load_user(user_id):
    with eng.begin() as conn:
        row = conn.execute(text("SELECT id, username, email, description, full_name FROM users WHERE id = :id"), {"id": user_id}).fetchone()
        if row:
            return User(row.id, row.username, row.email, getattr(row, 'description', None), getattr(row, 'full_name', None))
    return None

#Load dataset with pandas
df = pd.read_csv(dataset_path)
df = df.reset_index().rename(columns={'index': 'row_id'})  # Add stable row_id
print("Shape:", df.shape)
print("Columns:", df.columns.tolist())
#print(df.head())

playlists = Table(
    "playlists",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, nullable=False),
    Column("user_id", Integer, nullable=False)  # ← NEW: who owns this playlist
)
users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("username", String, nullable=False),
    Column("email", String, nullable=False),
    Column("password", String, nullable=False),
    Column("description", String, nullable=True),
    Column("full_name", String, nullable=True)
)
playlist_songs = Table(
    "playlist_songs",
    metadata,
    Column("playlist_id", Integer, primary_key=True),
    Column("song_row_id", Integer, primary_key=True),  # refers to row number in CSV (or add real song ID later)
    Column("position", Integer, nullable=False, default=0)
)

metadata.create_all(eng)
with eng.begin() as conn:
    try:
        conn.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_song_per_playlist 
            ON playlist_songs (playlist_id, song_row_id)
        """))
    except:
        pass  # already exists
# === MIGRATION: Add user_id column if it doesn't exist yet ===
with eng.connect() as conn:
    inspector = inspect(eng)
    if "playlists" in inspector.get_table_names():
        columns = [col["name"] for col in inspector.get_columns("playlists")]
        if "user_id" not in columns:
            print("Adding user_id column to playlists table...")
            conn.execute(text("ALTER TABLE playlists ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1"))
            conn.commit()
            print("Migration complete!")

    # === MIGRATION: add description column to users table if missing ===
    if "users" in inspector.get_table_names():
        user_cols = [col["name"] for col in inspector.get_columns("users")]
        if "description" not in user_cols:
            try:
                print("Adding description column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN description TEXT"))
                conn.commit()
                print("Added description column to users table")
            except Exception as e:
                print("Could not add description column (might already exist):", e)
        # === MIGRATION: add full_name column to users table if missing ===
        if "full_name" not in user_cols:
            try:
                print("Adding full_name column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN full_name TEXT"))
                conn.commit()
                print("Added full_name column to users table")
            except Exception as e:
                print("Could not add full_name column (might already exist):", e)

    # Ensure user_favorites table exists (stores up to N favorites per user)
    try:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_favorites (
                user_id INTEGER NOT NULL,
                song_row_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (user_id, position)
            )
        """))
        conn.commit()
    except Exception as e:
        print("Could not ensure user_favorites table:", e)

#define routes
@app.route('/')
def index():
    # Core genre list
    genres = sorted(df['track_genre'].dropna().unique())
    selected_genre = request.args.get('genre')

    # Featured genres (top 6 by overall track count)
    genre_counts = df['track_genre'].value_counts().dropna()
    featured_genres = list(genre_counts.head(6).index)

    # Popular tracks (by how often added to playlists)
    with eng.begin() as conn:
        counts_rows = conn.execute(text("SELECT song_row_id, COUNT(*) as cnt FROM playlist_songs GROUP BY song_row_id")).fetchall()
    counts = {r.song_row_id: r.cnt for r in counts_rows}
    popular_ids = sorted(counts.keys(), key=lambda k: counts[k], reverse=True)[:12]
    popular = []
    for sid in popular_ids:
        if sid in df.index:
            row = df.loc[sid]
            popular.append({'title': row['track_name'], 'artist': row['artists'], 'genre': row.get('track_genre', None), 'row_id': sid, 'count': counts.get(sid,0)})

    # Personalized recommendations for logged-in users: pick top genres from their playlists
    recommendations = []
    if current_user and getattr(current_user, 'is_authenticated', False):
        with eng.begin() as conn:
            user_song_rows = conn.execute(text("SELECT song_row_id FROM playlist_songs WHERE playlist_id IN (SELECT id FROM playlists WHERE user_id = :uid)"), {"uid": current_user.id}).fetchall()
        user_song_ids = [r.song_row_id for r in user_song_rows]
        # compute genre preferences
        user_genres = []
        for sid in user_song_ids:
            if sid in df.index:
                user_genres.append(df.loc[sid].get('track_genre'))
        if user_genres:
            from collections import Counter
            top_genres = [g for g,_ in Counter(user_genres).most_common(3)]
            # pick top tracks from these genres that user doesn't already have
            for g in top_genres:
                sub = df[df['track_genre'] == g].copy()
                sub['pop'] = sub.index.map(lambda i: counts.get(i,0))
                sub_sorted = sub.sort_values(by=['pop','track_name'], ascending=[False, True]).head(6)
                for _, r in sub_sorted.iterrows():
                    if r.name not in user_song_ids:
                        recommendations.append({'title': r['track_name'], 'artist': r['artists'], 'genre': g, 'row_id': r.name, 'pop': int(r['pop'])})
                if len(recommendations) >= 12:
                    break

    # If logged-in, fetch user's playlists for adding recommended tracks
    current_user_playlists = []
    if current_user and getattr(current_user, 'is_authenticated', False):
        with eng.begin() as conn:
            rows = conn.execute(text("SELECT id, name FROM playlists WHERE user_id = :uid ORDER BY id DESC"), {"uid": current_user.id}).fetchall()
            current_user_playlists = [{"id": r.id, "name": r.name} for r in rows]

    # If user is signed in but we couldn't build personalized recommendations,
    # fall back to popular tracks so they still see useful suggestions.
    is_personal_rec = bool(recommendations)
    if (current_user and getattr(current_user, 'is_authenticated', False)) and not is_personal_rec:
        # Use popular picks as a fallback (excluding tracks already in user's playlists)
        # popular list is already computed above
        fallback = []
        user_song_set = set()
        if current_user and getattr(current_user, 'is_authenticated', False):
            with eng.begin() as conn:
                rows = conn.execute(text("SELECT song_row_id FROM playlist_songs WHERE playlist_id IN (SELECT id FROM playlists WHERE user_id = :uid)"), {"uid": current_user.id}).fetchall()
            user_song_set = {r.song_row_id for r in rows}

        for p in popular:
            if p['row_id'] not in user_song_set:
                fallback.append(p)
            if len(fallback) >= 8:
                break
        # If fallback empty (user already has most popular), just use first popular items
        if not fallback:
            fallback = popular[:8]
        recommendations = fallback
        is_personal_rec = False

    # Build track listing for current selection and include row_id for actions
    # NOTE: avoid sending the entire dataset to the template — paginate the results
    try:
        page = max(1, int(request.args.get('page', 1)))
    except Exception:
        page = 1
    try:
        per_page = min(200, max(10, int(request.args.get('per_page', 50))))
    except Exception:
        per_page = 50

    filtered = df[df['track_genre'] == selected_genre] if selected_genre else df
    total_tracks = len(filtered)
    total_pages = ceil(total_tracks / per_page) if per_page else 1
    start = (page - 1) * per_page
    end = start + per_page
    page_df = filtered.iloc[start:end]

    tracks = []
    temp = page_df[['track_name', 'artists', 'track_genre']].dropna()
    for idx, row in temp.iterrows():
        tracks.append({
            'track_name': row['track_name'],
            'artists': row['artists'],
            'track_genre': row['track_genre'],
            'row_id': int(idx)
        })

    return render_template('index.html', genres=genres, featured_genres=featured_genres, popular=popular, recommendations=recommendations, tracks=tracks, selected_genre=selected_genre, current_user_playlists=current_user_playlists, is_personal_rec=is_personal_rec, page=page, per_page=per_page, total_pages=total_pages, total_tracks=total_tracks)

@app.route('/playlist/<int:playlist_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_playlist(playlist_id):
    # === Fetch playlist ===
    with eng.begin() as conn:
        pl_row = conn.execute(
            text("SELECT id, name, user_id FROM playlists WHERE id = :id"),
            {"id": playlist_id}
        ).fetchone()

    if not pl_row or pl_row.user_id != current_user.id:
        flash("Playlist not found or access denied", "danger")
        return redirect(url_for('account'))

    playlist = pl_row._mapping

    # === Handle POST actions ===
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'rename':
            new_name = request.form.get('playlist_name', '').strip()
            if new_name and new_name != playlist['name']:
                with eng.begin() as conn:
                    conn.execute(
                        text("UPDATE playlists SET name = :name WHERE id = :id"),
                        {"name": new_name, "id": playlist_id}
                    )
                flash("Playlist renamed!", "success")

        elif action == 'add_song':
            song_row_id = int(request.form.get('song_row_id'))
            with eng.begin() as conn:
                # Avoid duplicates
                exists = conn.execute(
                    text("SELECT 1 FROM playlist_songs WHERE playlist_id = :pid AND song_row_id = :sid"),
                    {"pid": playlist_id, "sid": song_row_id}
                ).fetchone()
                if not exists:
                    # Get next position
                    max_pos = conn.execute(
                        text("SELECT MAX(position) FROM playlist_songs WHERE playlist_id = :pid"),
                        {"pid": playlist_id}
                    ).scalar() or -1
                    conn.execute(
                        text("INSERT INTO playlist_songs (playlist_id, song_row_id, position) VALUES (:pid, :sid, :pos)"),
                        {"pid": playlist_id, "sid": song_row_id, "pos": max_pos + 1}
                    )
                    flash("Song added!", "success")

        elif action == 'remove_song':
            song_row_id = int(request.form.get('song_row_id'))
            with eng.begin() as conn:
                conn.execute(
                    text("DELETE FROM playlist_songs WHERE playlist_id = :pid AND song_row_id = :sid"),
                    {"pid": playlist_id, "sid": song_row_id}
                )
            flash("Song removed", "info")

        return redirect(url_for('edit_playlist', playlist_id=playlist_id))

# === Search functionality ===
    search_results = []
    query = request.args.get('q', '').strip().lower()
    if query:
        mask = (
            df['track_name'].str.contains(query, case=False, na=False) |
            df['artists'].str.contains(query, case=False, na=False)
        )
        results_df = df[mask].copy()
        results_df['duration'] = (results_df['duration_ms'] / 1000).astype(int)
        temp_list = results_df[['track_name', 'artists', 'track_genre', 'duration_ms']].rename(columns={
            'track_name': 'title',
            'artists': 'artist',
            'track_genre': 'genre'
        }).to_dict(orient='records')

        # Add the real pandas index (row_id) to each result
        for i, row in enumerate(temp_list):
            pandas_index = results_df.iloc[i].name  # this is the real row_id
            row['duration'] = int(row['duration_ms'] / 1000)
            row['row_id'] = pandas_index
            del row['duration_ms']
            search_results.append(row)

# === Load current songs in playlist (using pandas — no SQL join needed!) ===
    with eng.begin() as conn:
        song_ids_in_playlist = conn.execute(
            text("SELECT song_row_id FROM playlist_songs WHERE playlist_id = :pid ORDER BY position"),
            {"pid": playlist_id}
        ).fetchall()

    current_songs = []
    for (song_row_id,) in song_ids_in_playlist:
        if song_row_id in df.index:  # safety check
            row = df.loc[song_row_id]
            current_songs.append({
                'title': row['track_name'],
                'artist': row['artists'],
                'genre': row['track_genre'],
                'duration': int(row['duration_ms'] / 1000),
                'row_id': song_row_id
            })

    return render_template(
        'edit_playlist.html',
        playlist=playlist,
        songs=current_songs,
        search_results=search_results,
        query=query
    )
@app.route('/playlist/<int:playlist_id>/delete', methods=['POST'])
@login_required
def delete_playlist(playlist_id):
    with eng.begin() as conn:
        result = conn.execute(
            text("SELECT user_id FROM playlists WHERE id = :id"),
            {"id": playlist_id}
        ).fetchone()

        if not result:
            flash("Playlist not found", "danger")
        elif result.user_id != current_user.id:
            flash("Not your playlist!", "danger")
        else:
            conn.execute(
                text("DELETE FROM playlists WHERE id = :id"),
                {"id": playlist_id}
            )
            flash("Playlist deleted!", "success")

    return redirect(url_for('account'))

@app.route('/playlist', methods=['GET', 'POST'])
@login_required  # ← Important! Only logged-in users can create playlists
def playlist():
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            with eng.begin() as conn:
                conn.execute(
                    text("INSERT INTO playlists (name, user_id) VALUES (:name, :user_id)"),
                    {"name": name, "user_id": current_user.id}
                )
            return redirect(url_for('account'))

        # --- GET request: build context ---
    selected_genre = request.args.get('genre')
    query = request.args.get('query', '').lower()

    # Genres list
    genres = sorted(df['track_genre'].dropna().unique())

    # Filter songs (and paginate the results to avoid huge template payloads)
    songs_df = df
    if selected_genre:
        songs_df = songs_df[songs_df['track_genre'] == selected_genre]
    if query:
        songs_df = songs_df[
            songs_df['track_name'].str.lower().str.contains(query) |
            songs_df['artists'].str.lower().str.contains(query)
        ]

    try:
        page = max(1, int(request.args.get('page', 1)))
    except Exception:
        page = 1
    try:
        per_page = min(200, max(10, int(request.args.get('per_page', 50))))
    except Exception:
        per_page = 50

    total_songs = len(songs_df)
    start = (page - 1) * per_page
    end = start + per_page
    page_df = songs_df.iloc[start:end]

    songs = []
    temp = page_df[['track_name', 'artists', 'track_genre']].dropna()
    for _, row in temp.iterrows():
        songs.append({
            'track_name': row['track_name'],
            'artists': row['artists'],
            'track_genre': row['track_genre']
        })

    # Fetch user's playlists from DB along with counts
    with eng.begin() as conn:
        rows = conn.execute(text("""
            SELECT p.id, p.name, COUNT(ps.song_row_id) as song_count
            FROM playlists p
            LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id
            WHERE p.user_id = :uid
            GROUP BY p.id, p.name
            ORDER BY p.id DESC
        """), {"uid": current_user.id}).fetchall()

    user_playlists = [{"id": r.id, "name": r.name, "song_count": r.song_count or 0} for r in rows]

    return render_template(
        'playlist.html',
        genres=genres,
        selected_genre=selected_genre,
        query=query,
        songs=songs,
        playlists=user_playlists,
        page=page,
        per_page=per_page,
        total_songs=total_songs
    )

# Flask serves "search.html" template When someone visits /search
@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    user_playlists = []
    suggestions = []
    if request.method == 'POST':
        query = request.form.get('query', '').lower()
        results_df = df[df['track_name'].str.lower().str.contains(query) | df['artists'].str.lower().str.contains(query)]
        results = results_df[['track_name','artists','track_genre','duration_ms']].rename(
            columns={'track_name':'title','artists':'artist','track_genre':'genre','duration_ms':'duration'}
        ).to_dict(orient='records')
        for i, r in enumerate(results):  # Convert duration from ms to sec and attach row_id
            # results_df retains original pandas index which is the row id
            pandas_index = results_df.iloc[i].name
            r['duration'] = int(r['duration'] / 1000)
            r['row_id'] = pandas_index
        # If the user is logged in, fetch their playlists for quick add
    if current_user and getattr(current_user, 'is_authenticated', False):
        with eng.begin() as conn:
            rows = conn.execute(text("SELECT id, name FROM playlists WHERE user_id = :uid ORDER BY id DESC"), {"uid": current_user.id}).fetchall()
            user_playlists = [{"id": r.id, "name": r.name} for r in rows]

        # Build simple suggestions based on user's playlist genres
        with eng.begin() as conn:
            user_song_rows = conn.execute(text("SELECT song_row_id FROM playlist_songs WHERE playlist_id IN (SELECT id FROM playlists WHERE user_id = :uid)"), {"uid": current_user.id}).fetchall()
        user_song_ids = [r.song_row_id for r in user_song_rows]
        if user_song_ids:
            from collections import Counter
            user_genres = []
            for sid in user_song_ids:
                if sid in df.index:
                    user_genres.append(df.loc[sid].get('track_genre'))
            if user_genres:
                top_genres = [g for g,_ in Counter(user_genres).most_common(2)]
                # pick top tracks from these genres
                for g in top_genres:
                    sub = df[df['track_genre'] == g].copy()
                    sub['pop'] = sub.index.map(lambda i: 0)
                    sub_sorted = sub.sort_values(by=['track_name']).head(6)
                    for _, r in sub_sorted.iterrows():
                        if r.name not in user_song_ids:
                            suggestions.append({'title': r['track_name'], 'artist': r['artists'], 'genre': g, 'row_id': r.name})
                # limit suggestions
                suggestions = suggestions[:8]

    return render_template('search.html', results=results, playlists=user_playlists, suggestions=suggestions)


@app.route('/discover')
def discover():
    # Show genres and most popular songs (by how often they're added to playlists)
    genres = sorted(df['track_genre'].dropna().unique())

    # popularity counts from playlist_songs
    with eng.begin() as conn:
        counts_rows = conn.execute(text("SELECT song_row_id, COUNT(*) as cnt FROM playlist_songs GROUP BY song_row_id")).fetchall()
    counts = {r.song_row_id: r.cnt for r in counts_rows}

    # Top popular songs overall
    popular_ids = sorted(counts.keys(), key=lambda k: counts[k], reverse=True)[:15]
    popular = []
    for sid in popular_ids:
        if sid in df.index:
            row = df.loc[sid]
            popular.append({'title': row['track_name'], 'artist': row['artists'], 'genre': row.get('track_genre', None), 'row_id': sid, 'count': counts.get(sid,0)})

    # If user is logged in, supply their playlists for quick add
    user_playlists = []
    if current_user and getattr(current_user, 'is_authenticated', False):
        with eng.begin() as conn:
            rows = conn.execute(text("SELECT id, name FROM playlists WHERE user_id = :uid ORDER BY id DESC"), {"uid": current_user.id}).fetchall()
            user_playlists = [{"id": r.id, "name": r.name} for r in rows]

    # If a specific genre is requested, show that genre's songs on its own page
    sel = request.args.get('genre')
    if sel:
        genre = sel
        sub = df[df['track_genre'] == genre].copy()
        sub['pop'] = sub.index.map(lambda i: counts.get(i, 0))
        sub_sorted = sub.sort_values(by=['pop', 'track_name'], ascending=[False, True])
        songs = [{'title': r['track_name'], 'artist': r['artists'], 'row_id': r.name, 'pop': int(r['pop'])} for _, r in sub_sorted.iterrows()]
        return render_template('discover.html', genres=genres, selected_genre=genre, songs=songs, popular=popular, current_user_playlists=user_playlists)

    # Default: show list of genres (user can click into each genre)
    return render_template('discover.html', genres=genres, popular=popular, current_user_playlists=user_playlists)


@app.route('/playlist/add-song', methods=['POST'])
@login_required
def add_song_to_playlist():
    try:
        playlist_id = int(request.form.get('playlist_id'))
        song_row_id = int(request.form.get('song_row_id'))
    except Exception:
        flash('Invalid data', 'danger')
        return redirect(request.referrer or url_for('discover'))

    with eng.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM playlists WHERE id = :id AND user_id = :uid"),
            {"id": playlist_id, "uid": current_user.id}
        ).fetchone()
        if not exists:
            flash('Playlist not found or not yours', 'danger')
            return redirect(request.referrer or url_for('discover'))

        # avoid duplicates
        already = conn.execute(
            text("SELECT 1 FROM playlist_songs WHERE playlist_id = :pid AND song_row_id = :sid"),
            {"pid": playlist_id, "sid": song_row_id}
        ).fetchone()
        if already:
            flash('Song already in playlist', 'info')
            return redirect(request.referrer or url_for('discover'))

        max_pos = conn.execute(
            text("SELECT COALESCE(MAX(position), -1) FROM playlist_songs WHERE playlist_id = :pid"),
            {"pid": playlist_id}
        ).scalar()

        conn.execute(
            text("INSERT INTO playlist_songs (playlist_id, song_row_id, position) VALUES (:pid, :sid, :pos)"),
            {"pid": playlist_id, "sid": song_row_id, "pos": (max_pos or -1) + 1}
        )

    # If this is an AJAX request, return JSON for JS handling
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json
    if is_ajax:
        return jsonify({"status": "ok", "message": "Song added to playlist"}), 200

    flash('Song added to playlist', 'success')
    return redirect(request.referrer or url_for('discover'))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        description = request.form.get('description', '')
        full_name = request.form.get('full_name', '')
        # Collect up to 4 favorite song ids
        favs = []
        for i in range(1,5):
            v = request.form.get(f'favorite_{i}')
            try:
                if v:
                    favs.append(int(v))
            except Exception:
                pass

        with eng.begin() as conn:
            conn.execute(text("UPDATE users SET description = :d, full_name = :f WHERE id = :id"), {"d": description, "f": full_name, "id": current_user.id})
            # Replace favorites
            conn.execute(text("DELETE FROM user_favorites WHERE user_id = :uid"), {"uid": current_user.id})
            pos = 1
            for sid in favs[:4]:
                conn.execute(text("INSERT INTO user_favorites (user_id, song_row_id, position) VALUES (:uid, :sid, :pos)"), {"uid": current_user.id, "sid": sid, "pos": pos})
                pos += 1

        flash("Settings updated", "success")
        return redirect(url_for('account'))

    # GET
    current_description = ''
    current_full_name = ''
    current_favs = []
    # Build song options for favorites selection (top 150 popular / or first N)
    song_options = []
    try:
        sample = df.head(200)
        for i, r in sample.iterrows():
            song_options.append({"row_id": int(i), "label": f"{r['track_name']} — {r['artists']}"})
    except Exception:
        song_options = []

    with eng.begin() as conn:
        row = conn.execute(text("SELECT description, full_name FROM users WHERE id = :id"), {"id": current_user.id}).fetchone()
        if row:
            current_description = getattr(row, 'description', '') or ''
            current_full_name = getattr(row, 'full_name', '') or ''
        # favorites
        fav_rows = conn.execute(text("SELECT song_row_id, position FROM user_favorites WHERE user_id = :uid ORDER BY position"), {"uid": current_user.id}).fetchall()
        for r in fav_rows:
            current_favs.append(int(r.song_row_id))

    return render_template('settings.html', description=current_description, full_name=current_full_name, favorites=current_favs, song_options=song_options)


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
                text("SELECT id, username, email, password, description FROM users WHERE username = :u"),
                {"u": username}
            ).fetchone()

            if user_row and check_password_hash(user_row.password, password):
                user_obj = User(user_row.id, user_row.username, user_row.email, getattr(user_row, 'description', None))
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
        full_name = request.form.get('full_name', '').strip()
        email    = request.form.get('email')
        password = request.form.get('password')
        description = request.form.get('description', '')

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
                    text("INSERT INTO users (username, email, password, description, full_name) VALUES (:u, :e, :p, :d, :f)"),
                    {"u": username, "e": email, "p": hashed_pw, "d": description, "f": full_name}
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
@login_required
def account():
    with eng.begin() as conn:
        # Get playlists + song count in ONE query (super fast)
        rows = conn.execute(text("""
            SELECT 
                p.id, 
                p.name, 
                COUNT(ps.song_row_id) as song_count
            FROM playlists p
            LEFT JOIN playlist_songs ps ON p.id = ps.playlist_id
            WHERE p.user_id = :user_id
            GROUP BY p.id, p.name
            ORDER BY p.id DESC
        """), {"user_id": current_user.id}).fetchall()

    # Convert to list of dicts for easier template use
    playlists = [
        {"id": r.id, "name": r.name, "song_count": r.song_count or 0}
        for r in rows
    ]

    # Fetch current user's description and full name to show on account page
    user_description = None
    user_full_name = None
    favorites = []
    with eng.begin() as conn:
        u = conn.execute(text("SELECT description, full_name FROM users WHERE id = :id"), {"id": current_user.id}).fetchone()
        if u:
            user_description = getattr(u, 'description', None)
            user_full_name = getattr(u, 'full_name', None)

        fav_rows = conn.execute(text("SELECT song_row_id, position FROM user_favorites WHERE user_id = :uid ORDER BY position"), {"uid": current_user.id}).fetchall()
        for r in fav_rows:
            sid = int(r.song_row_id)
            if sid in df.index:
                row = df.loc[sid]
                favorites.append({"row_id": sid, "title": row['track_name'], "artist": row['artists']})

    return render_template('account.html', playlists=playlists, description=user_description, full_name=user_full_name, favorites=favorites)

@app.route('/playlist/merge', methods=['POST'])
@login_required
def merge_playlists():
    target_id = request.form.get('target_id', type=int)
    source_id = request.form.get('source_id', type=int)

    if not target_id or not source_id or target_id == source_id:
        flash("Invalid selection", "danger")
        return redirect(url_for('account'))

    with eng.begin() as conn:
        # FIXED: no space after colon
        target = conn.execute(
            text("SELECT id, name FROM playlists WHERE id = :id AND user_id = :uid"),
            {"id": target_id, "uid": current_user.id}
        ).fetchone()

        source = conn.execute(
            text("SELECT id, name FROM playlists WHERE id = :id AND user_id = :uid"),
            {"id": source_id, "uid": current_user.id}
        ).fetchone()

        if not target or not source:
            flash("Playlist not found or not yours", "danger")
            return redirect(url_for('account'))

        # Get highest position in target
        max_pos = conn.execute(
            text("SELECT COALESCE(MAX(position), -1) FROM playlist_songs WHERE playlist_id = :pid"),
            {"pid": target_id}
        ).scalar()

        # Copy songs (skip duplicates)
        songs_to_copy = conn.execute(
            text("SELECT song_row_id FROM playlist_songs WHERE playlist_id = :pid ORDER BY position"),
            {"pid": source_id}
        ).fetchall()

        added_count = 0
        for (song_row_id,) in songs_to_copy:
            exists = conn.execute(
                text("SELECT 1 FROM playlist_songs WHERE playlist_id = :pid AND song_row_id = :sid"),
                {"pid": target_id, "sid": song_row_id}
            ).fetchone()

            if not exists:
                max_pos += 1
                conn.execute(
                    text("INSERT INTO playlist_songs (playlist_id, song_row_id, position) VALUES (:pid, :sid, :pos)"),
                    {"pid": target_id, "sid": song_row_id, "pos": max_pos}
                )
                added_count += 1

        # Delete source
        conn.execute(text("DELETE FROM playlist_songs WHERE playlist_id = :pid"), {"pid": source_id})
        conn.execute(text("DELETE FROM playlists WHERE id = :pid"), {"pid": source_id})

    flash(f'"{source.name}" merged into "{target.name}" — {added_count} new songs added!', "success")
    return redirect(url_for('account'))

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


# Simple API endpoint for searching tracks (used by settings favorites search)
@app.route('/api/search-tracks')
def api_search_tracks():
    q = request.args.get('q', '').strip().lower()
    limit = int(request.args.get('limit', 50))
    results = []
    if not q:
        return jsonify(results)

    try:
        mask = (
            df['track_name'].str.lower().str.contains(q, na=False) |
            df['artists'].str.lower().str.contains(q, na=False)
        )
        rs = df[mask].head(limit)
        for i, row in rs.iterrows():
            label = f"{row.get('track_name','')} — {row.get('artists','')}"
            results.append({"row_id": int(i), "label": label})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(results)

#Run The App
if __name__ == '__main__':
    app.run(debug=True)