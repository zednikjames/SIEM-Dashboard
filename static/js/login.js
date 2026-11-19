const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const submitButton = document.getElementById('submit');

submitButton.addEventListener('click', async () => {
    const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: usernameInput.value,
            password: passwordInput.value,
        }),
    });
    const result = await response.json();
    if (result.success) {
        window.location.href = '/dashboard';
    } else {
        alert(result.error);
    }
});
