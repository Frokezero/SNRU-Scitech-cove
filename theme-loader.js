(function() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        document.documentElement.classList.add('dark-theme'); // Use documentElement to avoid body not ready
    }
})();

window.toggleTheme = function() {
    const isDark = document.documentElement.classList.toggle('dark-theme');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    updateThemeIcon();
};

function updateThemeIcon() {
    const icon = document.getElementById('theme-toggle-icon');
    if (!icon) return;
    if (document.documentElement.classList.contains('dark-theme')) {
        icon.className = 'fa-solid fa-sun';
    } else {
        icon.className = 'fa-solid fa-moon';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // If body exists, sync it too just in case
    if (document.documentElement.classList.contains('dark-theme')) {
        document.body.classList.add('dark-theme');
    }
    updateThemeIcon();
});
