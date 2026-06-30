// Sticky Navbar Effect
function setupNavbarScroll() {
    window.addEventListener('scroll', () => {
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        }
    });
}

// Fade out flash messages after 5 seconds
function setupFlashMessages() {
    const messages = document.querySelectorAll('.alert');
    messages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    setupNavbarScroll();
    setupFlashMessages();
});
