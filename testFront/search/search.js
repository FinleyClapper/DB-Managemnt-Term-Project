const API_BASE = 'http://127.0.0.1:5000/api';
        async function searchByTitle() {
            const query = document.getElementById('searchInput').value.trim();
            if (query.length < 2) {
                showError('Please enter at least 2 characters');
                return;
            }
            
            showLoading();
            try {
                const response = await fetch(`${API_BASE}/search/title?title=${encodeURIComponent(query)}`);
                const songs = await response.json();
                displayResults(songs);
            } catch (error) {
                showError('Failed to fetch results: ' + error.message);
            }
        }

        async function searchByArtist() {
            const query = document.getElementById('searchInput').value.trim();
            if (query.length < 2) {
                showError('Please enter at least 2 characters');
                return;
            }
            
            showLoading();
            try {
                const response = await fetch(`${API_BASE}/search/artist?artist=${encodeURIComponent(query)}`);
                const songs = await response.json();
                displayResults(songs);
            } catch (error) {
                showError('Failed to fetch results: ' + error.message);
            }
        }

        function displayResults(songs) {
            const resultsDiv = document.getElementById('results');
            
            if (songs.length === 0) {
                resultsDiv.innerHTML = '<p>No results found.</p>';
                return;
            }

            resultsDiv.innerHTML = `<h3>Found ${songs.length} songs:</h3>`;
            
            songs.forEach(song => {
                const songCard = document.createElement('div');
                songCard.className = 'song-card';
                
                songCard.innerHTML = `
                    <div class="song-title">${song.track_name || 'Unknown Title'}</div>
                    <div class="song-artist">Artist: ${song.artists || 'Unknown Artist'}</div>
                    <div class="song-details">
                        Genre: ${song.track_genre || 'N/A'} | 
                        Duration: ${song.duration_ms ? (song.duration_ms / 1000).toFixed(1) : 'N/A'}s |
                        Popularity: ${song.popularity || 'N/A'}
                    </div>
                `;
                
                resultsDiv.appendChild(songCard);
            });
        }

        function showLoading() {
            document.getElementById('results').innerHTML = '<p class="loading">Loading...</p>';
        }

        function showError(message) {
            document.getElementById('results').innerHTML = `<p class="error">${message}</p>`;
        }

        // Allow Enter key to search
        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchByTitle();
            }
        });