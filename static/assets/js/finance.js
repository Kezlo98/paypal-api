/**
 * Finance page - PayPal API integration
 * Fetches live balance and transactions from backend API
 */

const API_BASE = '/api/v1/paypal';

// State management
let currentPage = 1;
let currentFilters = {
    type: 'all',
    category: 'all'
};

/**
 * Fetch PayPal balance from API
 */
async function loadBalance() {
    try {
        showLoading('balance');
        const response = await fetch(`${API_BASE}/balance`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // PayPal balance structure (snake_case from backend)
        // Expected fields: available_balance, total_balance, etc.
        const balance = data.balances?.[0]?.total_balance?.value ||
                       data.available_balance ||
                       0;

        document.getElementById('summary-balance').textContent = formatCurrency(balance);
        hideLoading('balance');

    } catch (error) {
        console.error('Error loading balance:', error);
        document.getElementById('summary-balance').textContent = 'Error';
        showError(`Failed to load balance: ${error.message}`);
        hideLoading('balance');
    }
}

/**
 * Fetch transactions with date range and pagination
 */
async function loadTransactions(startDate, endDate, page = 1) {
    try {
        showLoading('transactions');

        const params = new URLSearchParams({
            start_date: startDate,
            end_date: endDate,
            page: page.toString(),
            page_size: '20'
        });

        const response = await fetch(`${API_BASE}/transactions?${params}`);

        if (!response.ok) {
            if (response.status === 429) {
                throw new Error('Rate limit exceeded. Please wait a moment.');
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Expected structure: { transactions: [...], pagination: {...} }
        const transactions = data.transaction_details || data.transactions || [];

        // Render transactions table
        renderTransactions(transactions);

        // Update pagination controls
        if (data.pagination) {
            renderPagination(data.pagination);
        }

        // Calculate and display summaries
        calculateSummaries(transactions);

        hideLoading('transactions');

    } catch (error) {
        console.error('Error loading transactions:', error);
        showError(`Failed to load transactions: ${error.message}`);
        hideLoading('transactions');
    }
}

/**
 * Render transactions in table
 */
function renderTransactions(transactions) {
    const tbody = document.getElementById('transactions-tbody');

    if (!tbody) {
        console.error('Transactions tbody element not found');
        return;
    }

    tbody.innerHTML = '';

    if (!transactions || transactions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="px-6 py-4 text-center text-gray-500">
                    No transactions found for this period.
                </td>
            </tr>
        `;
        return;
    }

    transactions.forEach(tx => {
        const row = document.createElement('tr');
        row.className = 'border-b border-gray-200 hover:bg-gray-50';

        // Extract transaction details (defensive access)
        const date = tx.transaction_info?.transaction_initiation_date ||
                    tx.transaction_date ||
                    'N/A';
        const id = tx.transaction_info?.transaction_id || tx.transaction_id || 'N/A';
        const type = tx.transaction_info?.transaction_event_code ||
                    tx.transaction_type ||
                    'Unknown';
        const amount = tx.transaction_info?.transaction_amount?.value ||
                      tx.amount ||
                      0;
        const status = tx.transaction_info?.transaction_status ||
                      tx.status ||
                      'Unknown';

        // Color code based on amount
        const amountClass = parseFloat(amount) >= 0 ? 'text-green-600' : 'text-red-600';

        row.innerHTML = `
            <td class="px-6 py-4 text-sm text-gray-900">${formatDate(date)}</td>
            <td class="px-6 py-4 text-sm text-gray-600 font-mono">${id.substring(0, 12)}...</td>
            <td class="px-6 py-4 text-sm text-gray-600">${type}</td>
            <td class="px-6 py-4 text-sm font-semibold ${amountClass}">
                ${formatCurrency(amount)}
            </td>
            <td class="px-6 py-4 text-sm">
                <span class="px-2 py-1 text-xs rounded-full ${getStatusColor(status)}">
                    ${status}
                </span>
            </td>
        `;
        tbody.appendChild(row);
    });
}

/**
 * Calculate summary metrics from transactions
 */
function calculateSummaries(transactions) {
    if (!transactions || transactions.length === 0) {
        updateSummaryCards(0, 0, 0, 0);
        return;
    }

    let totalIncome = 0;
    let totalDonations = 0;
    let totalToolFees = 0;

    transactions.forEach(tx => {
        const amount = parseFloat(
            tx.transaction_info?.transaction_amount?.value ||
            tx.amount ||
            0
        );
        const type = (
            tx.transaction_info?.transaction_event_code ||
            tx.transaction_type ||
            ''
        ).toLowerCase();

        // Categorize transactions
        if (amount > 0) {
            if (type.includes('donation')) {
                totalDonations += amount;
            } else {
                totalIncome += amount;
            }
        } else {
            // Negative amounts are expenses (tool fees, etc.)
            totalToolFees += Math.abs(amount);
        }
    });

    const net = totalIncome + totalDonations - totalToolFees;

    updateSummaryCards(totalIncome, totalDonations, totalToolFees, net);
}

/**
 * Update summary card values
 */
function updateSummaryCards(income, donations, toolFees, net) {
    const incomeEl = document.getElementById('summary-income');
    const donationsEl = document.getElementById('summary-donations');
    const toolFeesEl = document.getElementById('summary-toolfees');
    const netEl = document.getElementById('summary-net');

    if (incomeEl) incomeEl.textContent = formatCurrency(income);
    if (donationsEl) donationsEl.textContent = formatCurrency(donations);
    if (toolFeesEl) toolFeesEl.textContent = formatCurrency(toolFees);
    if (netEl) netEl.textContent = formatCurrency(net);
}

/**
 * Render pagination controls
 */
function renderPagination(pagination) {
    // TODO: Implement pagination UI if needed
    // For MVP, showing first 20 transactions is sufficient
    console.log('Pagination:', pagination);
}

/**
 * Get status badge color classes
 */
function getStatusColor(status) {
    const statusLower = status.toLowerCase();
    if (statusLower.includes('success') || statusLower.includes('completed')) {
        return 'bg-green-100 text-green-800';
    }
    if (statusLower.includes('pending')) {
        return 'bg-yellow-100 text-yellow-800';
    }
    if (statusLower.includes('failed') || statusLower.includes('denied')) {
        return 'bg-red-100 text-red-800';
    }
    return 'bg-gray-100 text-gray-800';
}

/**
 * Show loading state
 */
function showLoading(section) {
    const loadingEl = document.getElementById(`loading-${section}`);
    if (loadingEl) loadingEl.classList.remove('hidden');
}

/**
 * Hide loading state
 */
function hideLoading(section) {
    const loadingEl = document.getElementById(`loading-${section}`);
    if (loadingEl) loadingEl.classList.add('hidden');
}

/**
 * Show error message
 */
function showError(message) {
    const errorEl = document.getElementById('error');
    const errorText = document.getElementById('error-text');

    if (errorEl && errorText) {
        errorText.textContent = message;
        errorEl.classList.remove('hidden');

        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorEl.classList.add('hidden');
        }, 5000);
    }
}

/**
 * Initialize finance page on DOM ready
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Finance page loaded - initializing API integration');

    // Load balance immediately
    await loadBalance();

    // Load last 30 days of transactions
    const endDate = new Date().toISOString().split('T')[0];
    const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0];

    await loadTransactions(startDate, endDate);

    // TODO: Add event listeners for filters if needed
    // const filterType = document.getElementById('filter-type');
    // const filterCategory = document.getElementById('filter-category');
    // if (filterType) filterType.addEventListener('change', applyFilters);
});
