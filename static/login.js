function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();
    const usernameError = document.getElementById('username-error');
    const passwordError = document.getElementById('password-error');
    const loginBtn = document.getElementById('login-btn');
    const btnText = loginBtn.querySelector('.btn-text');
    const btnSpinner = loginBtn.querySelector('.btn-spinner');

    // Reset error messages
    usernameError.style.display = 'none';
    usernameError.innerText = '';
    passwordError.style.display = 'none';
    passwordError.innerText = '';

    // Client-side validation
    let isValid = true;
    if (!username) {
        usernameError.innerText = 'Username is required.';
        usernameError.style.display = 'block';
        isValid = false;
    }
    if (!password) {
        passwordError.innerText = 'Password is required.';
        passwordError.style.display = 'block';
        isValid = false;
    }

    if (!isValid) return;

    // Show loading state
    loginBtn.disabled = true;
    btnText.style.display = 'none';
    btnSpinner.style.display = 'inline-block';

    // Submit form data
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('remember-me', document.getElementById('remember-me').checked ? 'on' : 'off');

    fetch('/login', {
        method: 'POST',
        body: formData
    })
    .then(response => response.text())
    .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const errorElement = doc.querySelector('.error-message');

        if (errorElement && errorElement.innerText) {
            showToast(errorElement.innerText, 'error');
            loginBtn.disabled = false;
            btnText.style.display = 'inline-block';
            btnSpinner.style.display = 'none';
        } else {
            showToast('Login successful! Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
        }
    })
    .catch(error => {
        showToast('An error occurred. Please try again.', 'error');
        loginBtn.disabled = false;
        btnText.style.display = 'inline-block';
        btnSpinner.style.display = 'none';
    });
}

function togglePassword() {
    const passwordInput = document.getElementById('password');
    const toggleIcon = document.querySelector('.toggle-password');
    if (passwordInput.type === 'password') {
        passwordInput.type = 'text';
        toggleIcon.classList.remove('fa-eye');
        toggleIcon.classList.add('fa-eye-slash');
    } else {
        passwordInput.type = 'password';
        toggleIcon.classList.remove('fa-eye-slash');
        toggleIcon.classList.add('fa-eye');
    }
}

function showToast(message, type) {
    const toast = document.getElementById('toast');
    toast.innerText = message;
    toast.className = `toast ${type}`;
    toast.style.display = 'block';
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

// Real-time validation
document.getElementById('username').addEventListener('input', function() {
    const usernameError = document.getElementById('username-error');
    if (this.value.trim() === '') {
        usernameError.innerText = 'Username is required.';
        usernameError.style.display = 'block';
    } else {
        usernameError.style.display = 'none';
    }
});

document.getElementById('password').addEventListener('input', function() {
    const passwordError = document.getElementById('password-error');
    if (this.value.trim() === '') {
        passwordError.innerText = 'Password is required.';
        passwordError.style.display = 'block';
    } else {
        passwordError.style.display = 'none';
    }
});