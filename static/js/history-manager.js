// static/js/history-manager.js
// WhatsApp-style history management for standalone pages

(function() {
    'use strict';

    // ===========================================
    // 1. DEFINE PAGE CATEGORIES
    // ===========================================
    const pageCategories = {
        'home': ['/', '/index', '/dashboard'],
        'pricing': ['/pricing'],
        'subject': ['/subject/'],
        'lesson': ['/lesson/'],
        'payment': ['/payment', '/payment-status', '/payment-success', '/payment-failed'],
        'profile': ['/profile', '/user-menu', '/settings'],
        'auth': ['/login', '/register', '/forgot-password', '/reset-password'],
        'admin': ['/admin']
    };

    // ===========================================
    // 2. HELPER FUNCTIONS
    // ===========================================

    // Get category of current page
    function getCurrentCategory() {
        const path = window.location.pathname;

        for (const [category, patterns] of Object.entries(pageCategories)) {
            if (patterns.some(pattern => path.includes(pattern))) {
                return category;
            }
        }
        return 'other';
    }

    // Get navigation history from session storage
    function getHistoryStack() {
        try {
            return JSON.parse(sessionStorage.getItem('navHistory') || '[]');
        } catch (e) {
            console.error('Error reading history:', e);
            return [];
        }
    }

    // Save navigation history
    function saveHistoryStack(stack) {
        try {
            sessionStorage.setItem('navHistory', JSON.stringify(stack));
        } catch (e) {
            console.error('Error saving history:', e);
        }
    }

    // Get last visited category
    function getLastCategory(stack) {
        return stack.length > 0 ? stack[stack.length - 1] : null;
    }

    // ===========================================
    // 3. MAIN HISTORY MANAGEMENT
    // ===========================================

    function initHistoryManager() {
        const currentCategory = getCurrentCategory();
        let historyStack = getHistoryStack();
        const lastCategory = getLastCategory(historyStack);

        console.log(`📍 Current: ${currentCategory}, Last: ${lastCategory}`);
        console.log('📚 History before:', historyStack);

        // CASE 1: Same category as last page - REPLACE (like WhatsApp)
        if (currentCategory === lastCategory && currentCategory !== 'other') {
            console.log('🔄 Same category - replacing history entry');
            history.replaceState({}, document.title, window.location.href);

            // Don't add to stack, keep as is
        }
        // CASE 2: Different category - PUSH new entry
        else {
            console.log('➕ New category - pushing to history');
            history.pushState({}, document.title, window.location.href);
            historyStack.push(currentCategory);
        }

        // Keep stack size reasonable (max 20)
        if (historyStack.length > 20) {
            historyStack = historyStack.slice(-20);
        }

        saveHistoryStack(historyStack);
        console.log('📚 History after:', historyStack);

        // ===========================================
        // 4. HANDLE BACK BUTTON
        // ===========================================

        window.addEventListener('popstate', function(event) {
            console.log('⬅️ Back button pressed');

            // Get current stack
            let currentStack = getHistoryStack();

            // If we're going back, remove the last category
            if (currentStack.length > 0) {
                currentStack.pop();
                saveHistoryStack(currentStack);

                // If stack is empty, allow normal back behavior
                if (currentStack.length === 0) {
                    console.log('🏁 End of history, allowing normal back');
                    return;
                }
            }

            console.log('📚 Updated history:', currentStack);
        });
    }

    // ===========================================
    // 5. SPECIAL HANDLING FOR PAYMENT PAGES
    // ===========================================

    // Prevent back navigation on payment pages
    if (window.location.pathname.includes('/payment-status')) {
        (function() {
            // Stack multiple states to trap user
            history.pushState(null, null, location.href);
            history.pushState(null, null, location.href);

            window.addEventListener('popstate', function() {
                history.go(1);
                if (typeof showToast === 'function') {
                    showToast('Please wait for payment confirmation', 'warning');
                }
            });
        })();
    }

    // ===========================================
    // 6. CLEAN UP ON PAGE UNLOAD
    // ===========================================

    window.addEventListener('beforeunload', function() {
        // Optional: Clean up if needed
        console.log('Leaving page');
    });

    // ===========================================
    // 7. START THE MANAGER
    // ===========================================

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initHistoryManager);
    } else {
        initHistoryManager();
    }
})();