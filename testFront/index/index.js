const API_BASE = 'http://127.0.0.1:5000/api';
document.getElementById("logoutBtn").addEventListener("click", async () => {
    console.log('here');
    const response = await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        credentials: "include"
    });

    const data = await response.json();
    console.log(data.message);
    window.location.reload();
});