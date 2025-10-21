const API_BASE = 'http://127.0.0.1:5000/api';
        let currentPlaylist = null;

        let playlists = [
            
        ];


        window.onload = function() {
            loadPlaylists();
        };

        function loadPlaylists() {

            const grid = document.getElementById('playlistsGrid');
            
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
                        ${playlist.songCount} songs<br>
                        ${playlist.description || 'No description'}
                    </div>
                    <div class="playlist-actions">
                        <button class="view-btn" onclick="event.stopPropagation(); viewPlaylist(${playlist.id})">View</button>
                        <button class="delete-btn" onclick="event.stopPropagation(); deletePlaylist(${playlist.id})">Delete</button>
                    </div>
                `;
                
                grid.appendChild(card);
            });
        }

        function createPlaylist() {
            const name = document.getElementById('playlistName').value.trim();
            const description = document.getElementById('playlistDescription').value.trim();

            if (!name) {
                alert('Please enter a playlist name');
                return;
            }

            const newPlaylist = {
                id: playlists.length + 1,
                name: name,
                description: description,
                songCount: 0,
                songs: []
            };

            playlists.push(newPlaylist);
            
            document.getElementById('playlistName').value = '';
            document.getElementById('playlistDescription').value = '';
            
            loadPlaylists();
        }

        function deletePlaylist(id) {
            playlists = playlists.filter(p => p.id !== id);
            
            if (currentPlaylist && currentPlaylist.id === id) {
                document.getElementById('playlistDetails').style.display = 'none';
                currentPlaylist = null;
            }
            
            loadPlaylists();
        }

        function viewPlaylist(id) {
            const playlist = playlists.find(p => p.id === id);
            if (!playlist) return;

            currentPlaylist = playlist;

            document.getElementById('selectedPlaylistName').textContent = playlist.name;
            document.getElementById('selectedPlaylistDesc').textContent = playlist.description || 'No description';
            document.getElementById('playlistDetails').style.display = 'block';

            document.querySelectorAll('.playlist-card').forEach(card => {
                card.classList.remove('selected');
            });

            displayPlaylistSongs(playlist.songs);

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
                        <button class="add-btn" onclick='addSongToPlaylist(${JSON.stringify(song)})'>Add</button>
                    `;
                    
                    resultsDiv.appendChild(resultItem);
                });
            } catch (error) {
                resultsDiv.innerHTML = `<div class="error">Error searching: ${error.message}</div>`;
            }
        }

        function addSongToPlaylist(song) {
            if (!currentPlaylist) return;
            if (currentPlaylist.songs.find(s => s.track_name === song.track_name && s.artists === song.artists)) {
                alert('Song already in playlist!');
                return;
            }

            currentPlaylist.songs.push(song);
            currentPlaylist.songCount = currentPlaylist.songs.length;

            displayPlaylistSongs(currentPlaylist.songs);
            loadPlaylists();
            
            document.getElementById('searchResults').innerHTML = '';
            document.getElementById('songSearchInput').value = '';
        }

        function removeSongFromPlaylist(songId) {
            if (!currentPlaylist) return;
            currentPlaylist.songs = currentPlaylist.songs.filter(s => s.id !== songId);
            currentPlaylist.songCount = currentPlaylist.songs.length;
            displayPlaylistSongs(currentPlaylist.songs);
            loadPlaylists();
        }