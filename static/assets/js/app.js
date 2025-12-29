/**
 * Shared utilities for the static site
 */

// Load JSON data from a local file
async function loadJSON(path) {
    try {
        const response = await fetch(path);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Error loading JSON from ${path}:`, error);
        return null;
    }
}

// Format currency (USD)
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

// Format date
function formatDate(dateString, endDateString = null) {
    const date = new Date(dateString);
    const formatter = new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    if (endDateString) {
        const endDate = new Date(endDateString);
        const endFormatter = new Intl.DateTimeFormat('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        return `${formatter.format(date)} - ${endFormatter.format(endDate)}`;
    }

    return formatter.format(date);
}

// Set active navigation link
function setActiveNav() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (currentPath.endsWith(href) || (href === 'home.html' && (currentPath.endsWith('/') || currentPath.endsWith('index.html')))) {
            link.classList.add('text-blue-600', 'font-semibold');
            link.classList.remove('text-gray-600', 'hover:text-blue-600');
        } else {
            link.classList.remove('text-blue-600', 'font-semibold');
            link.classList.add('text-gray-600', 'hover:text-blue-600');
        }
    });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', setActiveNav);
