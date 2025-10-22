const API_BASE = 'http://127.0.0.1:5000/api';
        let currentPlaylist = null;


        window.onload = function() {
            loadPlaylists();
        };

        async function loadPlaylists() {
            const grid = document.getElementById('playlistsGrid');
            grid.innerHTML = '<div class="loading">Loading playlists...</div>';
            
            try {
                const response = await fetch(`${API_BASE}/playlist/fetch`,{
                    credentials: 'include'
                });
                
                if (!response.ok) {
                    throw new Error('Failed to fetch playlists');
                }
                
                const playlists = await response.json();
                
                if (playlists.length === 0) {
                    grid.innerHTML = '<div class="empty-state">No playlists yet. Create your first playlist above!</div>';
                    return;
                }
                
                grid.innerHTML = '';
                playlists.forEach(playlist => {
                    const card = document.createElement('div');
                    card.className = 'playlist-card';
                    card.onclick = () => viewPlaylist(playlist.id);
                    
                    card.innerHTML = `
                        <div class="playlist-name">${playlist.name}</div>
                        <div class="playlist-info">
                            ${playlist.description || 'No description'}
                        </div>
                        <div class="playlist-actions">
                            <button class="view-btn" onclick="event.stopPropagation(); viewPlaylist(${playlist.id})">View</button>
                            <button class="delete-btn" onclick="event.stopPropagation(); deletePlaylist(${playlist.id})">Delete</button>
                        </div>
                    `;
                    
                    grid.appendChild(card);
                });
            } catch (error) {
                grid.innerHTML = `<div class="error">Error loading playlists: ${error.message}</div>`;
            }
        }
        async function createPlaylist() {
            const name = document.getElementById('playlistName').value.trim();
            const description = document.getElementById('playlistDescription').value.trim();

            if (!name) {
                alert('Please enter a playlist name');
                return;
            }

            const newPlaylist = {
                name: name,
                description: description,
                songs: [],
                songCount: 0
            };
            try{
                const response = await fetch(`${API_BASE}/playlist/create?name=${name}&description=${description}`,{
                    credentials: 'include'
                });
            }
            catch (error) {
                resultsDiv.innerHTML = `<div class="error">Error searching: ${error.message}</div>`;
            }
            playlists.push(newPlaylist);
            document.getElementById('playlistName').value = '';
            document.getElementById('playlistDescription').value = '';
            
            loadPlaylists();
        }

        async function deletePlaylist(id) {
            const response = await fetch(`${API_BASE}/playlist/remove/playlist?id=${id}`);
            loadPlaylists();
        }

        async function viewPlaylist(id) {
            
            const playlist = await fetch(`${API_BASE}/playlist/fetch/id?id=${id}`);
            if (!playlist) return;
            currentPlaylist = id;
            
            document.getElementById('selectedPlaylistName').textContent = playlist.name;
            document.getElementById('selectedPlaylistDesc').textContent = playlist.description || 'No description';
            document.getElementById('playlistDetails').style.display = 'block';

            document.querySelectorAll('.playlist-card').forEach(card => {
                card.classList.remove('selected');
            });
            const response = await fetch(`${API_BASE}/playlist/fetch/songs/id?id=${id}`);
            const songs = await response.json();
            displayPlaylistSongs(songs);

            document.getElementById('playlistDetails').scrollIntoView({ behavior: 'smooth' });
        }

        function displayPlaylistSongs(songs) {
            const songsDiv = document.getElementById('playlistSongs');
            
            if (songs.length === 0) {
                songsDiv.innerHTML = '<div class="empty-state">No songs in this playlist yet. Search and add songs above!</div>';
                return;
            }
            songsDiv.innerHTML = '';
            songs.forEach(song => {
                const songItem = document.createElement('div');
                songItem.className = 'song-item';
                songItem.innerHTML = `
                    <div class="song-info">
                        <div class="song-title">${song.track_name}</div>
                        <div class="song-artist">${song.artists} • ${song.track_genre || 'Unknown genre'}</div>
                    </div>
                    <button class="remove-song-btn" onclick="removeSongFromPlaylist(${song.id})">Remove</button>
                `;
                
                songsDiv.appendChild(songItem);
            });
        }

        async function searchSongsToAdd() {
            const query = document.getElementById('songSearchInput').value.trim();
            if (query.length < 2) {
                alert('Please enter at least 2 characters');
                return;
            }

            const resultsDiv = document.getElementById('searchResults');
            resultsDiv.innerHTML = '<div class="loading">Searching...</div>';

            try {
                const response = await fetch(`${API_BASE}/search/title?title=${encodeURIComponent(query)}`);
                const songs = await response.json();

                if (songs.length === 0) {
                    resultsDiv.innerHTML = '<div class="empty-state">No songs found</div>';
                    return;
                }

                resultsDiv.innerHTML = '';
                songs.forEach(song => {
                    const resultItem = document.createElement('div');
                    resultItem.className = 'search-result-item';
                    resultItem.innerHTML = `
  <div class="song-info">
    <div class="song-title">${song.track_name}</div>
    <div class="song-artist">${song.artists}</div>
  </div>
  <button
    type="button"
    class="add-btn"
    onclick="event.stopPropagation(); addSongToPlaylist(JSON.parse(decodeURIComponent('${encodeURIComponent(JSON.stringify(song))}')))"
  >Add</button>
`;
                    
                    resultsDiv.appendChild(resultItem);
                });
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">Error searching: ${error.message}</div>`;
            }
        }

        async function addSongToPlaylist(song) {
            
            console.log(currentPlaylist);
            console.log(song);
            const resp = await fetch(`${API_BASE}/playlist/add?track_name=${song.track_name}&track_genre=${song.track_genre}&track_id=${song.track_id}&artist=${song.artists}&playlist_id=${currentPlaylist}`)
            const response = await fetch(`${API_BASE}/playlist/fetch/songs/id?id=${id}`);
            const songs = await response.json();
            loadPlaylists();
            
            document.getElementById('searchResults').innerHTML = '';
            document.getElementById('songSearchInput').value = '';
        }

        async function removeSongFromPlaylist(songId) {
            console.log(songId);
            const response = await fetch(`${API_BASE}/playlist/song/remove?id=${songId}`);
            if (!currentPlaylist) return;
            displayPlaylistSongs(currentPlaylist.songs);
            loadPlaylists();
        }
        