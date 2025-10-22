const API_BASE = 'http://127.0.0.1:5000/api';
document.getElementById("logoutBtn").addEventListener("click", async () => {
    console.log('here');
    const response = await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "include"  // ✅ send session cookie to the server
    });

    const data = await response.json();
    console.log(data.message);

    // Optional: redirect to login page or hide authenticated sections
    window.location.reload(); // reload page to reset state
});