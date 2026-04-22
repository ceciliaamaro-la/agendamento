(function () {
    'use strict';

    /* ── Dark mode ────────────────────────────────────────────────── */
    if (localStorage.getItem('darkMode') === 'true') {
        document.documentElement.classList.add('dark-mode-pre');
    }
    document.addEventListener('DOMContentLoaded', function () {
        if (document.documentElement.classList.contains('dark-mode-pre')) {
            document.body.classList.add('dark-mode');
            document.documentElement.classList.remove('dark-mode-pre');
        }
    });

    window.toggleDarkMode = function () {
        var isDark = document.body.classList.toggle('dark-mode');
        localStorage.setItem('darkMode', isDark);
        var icon = document.querySelector('#fab-actions .bi-moon-stars, #fab-actions .bi-sun');
        if (icon) {
            icon.classList.toggle('bi-sun', isDark);
            icon.classList.toggle('bi-moon-stars', !isDark);
        }
    };

    /* ── Preloader inteligente ────────────────────────────────────── */
    var preloader = null;
    var navTimer = null;

    function getPreloader() {
        if (!preloader) preloader = document.getElementById('preloader');
        return preloader;
    }
    function hidePreloader() {
        var el = getPreloader();
        if (el) el.classList.remove('show');
        if (navTimer) { clearTimeout(navTimer); navTimer = null; }
    }
    function scheduleShowPreloader() {
        if (navTimer) clearTimeout(navTimer);
        navTimer = setTimeout(function () {
            var el = getPreloader();
            if (el) el.classList.add('show');
        }, 180);
    }

    document.addEventListener('DOMContentLoaded', hidePreloader);
    window.addEventListener('pageshow', hidePreloader);

    document.addEventListener('click', function (e) {
        var link = e.target.closest('a');
        if (!link || !link.href) return;
        if (link.target && link.target !== '_self') return;
        if (link.href.indexOf('#') !== -1) return;
        if (link.classList.contains('no-loader')) return;
        if (link.href.indexOf(window.location.origin) !== 0) return;
        if (e.defaultPrevented || e.button !== 0) return;
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        scheduleShowPreloader();
    });

    /* ── Service Worker (somente em produção/HTTPS) ───────────────── */
    if ('serviceWorker' in navigator &&
        (location.protocol === 'https:' || location.hostname === 'localhost')) {
        window.addEventListener('load', function () {
            navigator.serviceWorker.register('/static/sw.js').catch(function () { /* silencioso */ });
        });
    }
})();
