const API_BASE = 'http://127.0.0.1:5000/api';
async function checkAuth() {
            try {
                const response = await fetch(`${API_BASE}/auth/me`, {
                    credentials: 'include'
                });
                console.log(response)
                if (response.ok) {
                    // Already logged in, redirect to home
                    
                }
                else{
                    console.log('this one');
                    window.location.href = '../index/index.html';}
            } catch (error) {
                // Not logged in, stay on login page
                
            }
        }
        checkAuth();