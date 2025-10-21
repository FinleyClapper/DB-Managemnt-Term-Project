const API_BASE = 'http://127.0.0.1:5000/api';

        function switchTab(tab) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');

            // Update forms
            document.querySelectorAll('.form-container').forEach(f => f.classList.remove('active'));
            document.getElementById(tab + 'Form').classList.add('active');

            // Clear messages
            hideMessages();
        }

        function showError(message) {
            const errorDiv = document.getElementById('errorMessage');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
            document.getElementById('successMessage').style.display = 'none';
        }

        function showSuccess(message) {
            const successDiv = document.getElementById('successMessage');
            successDiv.textContent = message;
            successDiv.style.display = 'block';
            document.getElementById('errorMessage').style.display = 'none';
        }

        function hideMessages() {
            document.getElementById('errorMessage').style.display = 'none';
            document.getElementById('successMessage').style.display = 'none';
        }

        async function handleLogin(event) {
            event.preventDefault();
            hideMessages();

            const username = document.getElementById('loginUsername').value.trim();
            const password = document.getElementById('loginPassword').value;

            const loadingDiv = document.getElementById('loginLoading');
            loadingDiv.style.display = 'block';

            try {
                const response = await fetch(`${API_BASE}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (response.ok) {
                    showSuccess('Login successful! Redirecting...');
                    setTimeout(() => {
                        window.location.href = 'home.html';
                    }, 1000);
                } else {
                    showError(data.error || 'Login failed');
                }
            } catch (error) {
                showError('Network error: ' + error.message);
            } finally {
                loadingDiv.style.display = 'none';
            }
        }

        async function handleSignup(event) {
            event.preventDefault();
            hideMessages();

            const username = document.getElementById('signupUsername').value.trim();
            const email = document.getElementById('signupEmail').value.trim();
            const password = document.getElementById('signupPassword').value;
            const confirmPassword = document.getElementById('signupConfirmPassword').value;

            if (password !== confirmPassword) {
                showError('Passwords do not match');
                return;
            }

            if (password.length < 6) {
                showError('Password must be at least 6 characters');
                return;
            }

            const loadingDiv = document.getElementById('signupLoading');
            loadingDiv.style.display = 'block';

            try {
                const response = await fetch(`${API_BASE}/auth/signup`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ username, email, password })
                });

                const data = await response.json();

                if (response.ok) {
                    showSuccess('Account created! Redirecting...');
                    setTimeout(() => {
                        window.location.href = 'home.html';
                    }, 1000);
                } else {
                    showError(data.error || 'Signup failed');
                }
            } catch (error) {
                showError('Network error: ' + error.message);
            } finally {
                loadingDiv.style.display = 'none';
            }
        }

        // Check if already logged in
        async function checkAuth() {
            try {
                const response = await fetch(`${API_BASE}/auth/me`, {
                    credentials: 'include'
                });

                if (response.ok) {
                    // Already logged in, redirect to home
                    window.location.href = 'home.html';
                }
            } catch (error) {
                // Not logged in, stay on login page
            }
        }

        checkAuth();