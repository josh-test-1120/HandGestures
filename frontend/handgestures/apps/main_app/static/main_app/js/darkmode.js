// Dark mode toggle logic for all pages
const body = document.body;
const navbar = document.getElementById('mainNavbar');
const footer = document.getElementById('mainFooter');
const toggleButton = document.getElementById('toggleDarkMode');

function enableDarkMode() {
  body.classList.add('bg-dark', 'text-white');
  body.classList.remove('bg-light', 'text-dark');
  navbar?.classList.add('bg-dark', 'navbar-dark');
  navbar?.classList.remove('bg-body-tertiary');
  footer?.classList.add('bg-dark', 'text-white');
  footer?.classList.remove('bg-light', 'text-dark');
  if (toggleButton) {
    toggleButton.innerText = '☀️';
    toggleButton.classList.remove('btn-outline-dark');
    toggleButton.classList.add('btn-outline-light');
  }
  localStorage.setItem('theme', 'dark');
}

function disableDarkMode() {
  body.classList.remove('bg-dark', 'text-white');
  body.classList.add('bg-light', 'text-dark');
  navbar?.classList.remove('bg-dark', 'navbar-dark');
  navbar?.classList.add('bg-body-tertiary');
  footer?.classList.remove('bg-dark', 'text-white');
  footer?.classList.add('bg-light', 'text-dark');
  if (toggleButton) {
    toggleButton.innerText = '🌙';
    toggleButton.classList.add('btn-outline-dark');
    toggleButton.classList.remove('btn-outline-light');
  }
  localStorage.setItem('theme', 'light');
} 