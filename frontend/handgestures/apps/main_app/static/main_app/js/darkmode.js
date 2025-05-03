// Dark mode toggle logic for all pages
const body = document.body;
const navbar = document.getElementById('mainNavbar');
const footer = document.getElementById('mainFooter');
const toggleButton = document.getElementById('toggleDarkMode');

function enableDarkMode() {
  navbar?.classList.add('bg-dark', 'navbar-dark');
  navbar?.classList.remove('bg-body-tertiary');
  if (footer) {
    footer.style.backgroundColor = '#212529';
    footer.style.color = '#f0f0f0';
  }
  if (toggleButton) {
    toggleButton.innerText = '☀️';
    toggleButton.classList.remove('btn-outline-dark');
    toggleButton.classList.add('btn-outline-light');
  }
  localStorage.setItem('theme', 'dark');
}

function disableDarkMode() {
  navbar?.classList.remove('bg-dark', 'navbar-dark');
  navbar?.classList.add('bg-body-tertiary');
  if (footer) {
    footer.style.backgroundColor = '#212529';
    footer.style.color = '#f0f0f0';
  }
  if (toggleButton) {
    toggleButton.innerText = '🌙';
    toggleButton.classList.add('btn-outline-dark');
    toggleButton.classList.remove('btn-outline-light');
  }
  localStorage.setItem('theme', 'light');
} 