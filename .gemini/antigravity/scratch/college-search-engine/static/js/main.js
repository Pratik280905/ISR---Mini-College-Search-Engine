/**
 * Frontend JavaScript for Mini College Search Engine
 * Features:
 * - Real-time Autocomplete / Search Suggestions with keyboard navigation
 * - Relevance Feedback logging via AJAX
 * - Search Result Click Tracking
 * - Web Crawler AJAX progress streaming
 * - Bootstrap Tooltip Initialization
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Initialize Bootstrap Tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 2. Autocomplete Suggestions
    setupAutocomplete();
});

function setupAutocomplete() {
    const searchInput = document.getElementById('search-input');
    const suggestionsBox = document.getElementById('suggestions-box');
    if (!searchInput || !suggestionsBox) return;

    let debounceTimer = null;
    let currentFocus = -1;

    searchInput.addEventListener('input', function () {
        const query = this.value.trim();
        clearTimeout(debounceTimer);
        currentFocus = -1;

        if (query.length < 2) {
            suggestionsBox.innerHTML = '';
            suggestionsBox.classList.add('d-none');
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/api/suggest?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.suggestions && data.suggestions.length > 0) {
                        renderSuggestions(data.suggestions);
                    } else {
                        suggestionsBox.innerHTML = '';
                        suggestionsBox.classList.add('d-none');
                    }
                })
                .catch(() => {
                    suggestionsBox.classList.add('d-none');
                });
        }, 180);
    });

    // Keyboard navigation (Down, Up, Enter)
    searchInput.addEventListener('keydown', function (e) {
        const items = suggestionsBox.querySelectorAll('.list-group-item');
        if (!items || items.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            currentFocus++;
            addActive(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            currentFocus--;
            addActive(items);
        } else if (e.key === 'Enter') {
            if (currentFocus > -1 && items[currentFocus]) {
                e.preventDefault();
                items[currentFocus].click();
            }
        }
    });

    function addActive(items) {
        if (!items) return false;
        items.forEach(it => it.classList.remove('active'));
        if (currentFocus >= items.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = items.length - 1;
        items[currentFocus].classList.add('active');
        searchInput.value = items[currentFocus].dataset.value;
    }

    function renderSuggestions(suggestions) {
        suggestionsBox.innerHTML = '';
        suggestions.forEach(item => {
            const el = document.createElement('a');
            el.className = 'list-group-item list-group-item-action d-flex align-items-center gap-2';
            el.dataset.value = item;
            el.innerHTML = `<i class="fa-solid fa-magnifying-glass text-muted small"></i> <span>${escapeHtml(item)}</span>`;
            el.addEventListener('click', function (e) {
                e.preventDefault();
                searchInput.value = item;
                suggestionsBox.classList.add('d-none');
                searchInput.closest('form').submit();
            });
            suggestionsBox.appendChild(el);
        });
        suggestionsBox.classList.remove('d-none');
    }

    // Hide suggestions when clicking outside
    document.addEventListener('click', function (e) {
        if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
            suggestionsBox.classList.add('d-none');
        }
    });
}

// 3. Relevance Feedback Simulation
function toggleFeedback(button, query, docId) {
    fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, doc_id: docId, is_relevant: 1 })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            button.classList.remove('btn-outline-secondary', 'btn-outline-success');
            button.classList.add('btn-success', 'text-white');
            button.innerHTML = '<i class="fa-solid fa-check me-1"></i> <span>Marked Relevant</span>';
            // Show toast or slight animation
            button.setAttribute('disabled', 'true');
        }
    })
    .catch(err => console.error('Feedback error:', err));
}

// 4. Click Logging
function logClick(query, docId) {
    navigator.sendBeacon('/api/click', JSON.stringify({ query: query, doc_id: docId }));
}

// 5. Admin Live Web Crawler
function startCrawler(event) {
    event.preventDefault();

    const url = document.getElementById('crawl-url').value.trim();
    const maxPages = document.getElementById('crawl-max-pages').value;
    const depth = document.getElementById('crawl-depth').value;

    const submitBtn = document.getElementById('crawl-submit-btn');
    const spinner = document.getElementById('crawl-spinner');
    const statusText = document.getElementById('crawl-status-text');
    const terminal = document.getElementById('crawl-log-terminal');
    const countBadge = document.getElementById('crawl-count-badge');

    if (!url) return;

    submitBtn.disabled = true;
    spinner.classList.remove('d-none');
    statusText.innerText = 'Crawling in progress... please wait...';
    terminal.innerHTML = `<span class="text-info">// Initiating crawl on ${escapeHtml(url)}...</span><br>`;

    fetch('/admin/crawl', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, max_pages: parseInt(maxPages), depth: parseInt(depth) })
    })
    .then(res => res.json())
    .then(data => {
        submitBtn.disabled = false;
        spinner.classList.add('d-none');

        if (data.status === 'success') {
            statusText.innerText = `Crawling complete! ${data.crawled_count} pages indexed.`;
            statusText.className = 'text-success small fw-bold';
            countBadge.innerText = `${data.crawled_count} pages indexed`;

            // Display log lines
            terminal.innerHTML += data.logs.map(line => `<div>${escapeHtml(line)}</div>`).join('');
            terminal.scrollTop = terminal.scrollHeight;
        } else {
            statusText.innerText = `Crawl failed: ${data.message}`;
            statusText.className = 'text-danger small fw-bold';
            terminal.innerHTML += `<div class="text-danger">[Error] ${escapeHtml(data.message)}</div>`;
        }
    })
    .catch(err => {
        submitBtn.disabled = false;
        spinner.classList.add('d-none');
        statusText.innerText = 'Network error during crawling.';
        statusText.className = 'text-danger small fw-bold';
        terminal.innerHTML += `<div class="text-danger">[Error] ${escapeHtml(err.message)}</div>`;
    });
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}