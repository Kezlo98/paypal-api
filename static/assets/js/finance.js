/**
 * Finance page - PayPal API integration
 * Fetches live balance and transactions from backend API
 */

const API_BASE = '/api/v1/paypal';

// State management
let currentPage = 1;
let currentDateRange = {
    startDate: null,
    endDate: null
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
        // Use USD value if available, otherwise use original value
        const totalBalance = data.balances?.[0]?.total_balance || {};
        const balance = totalBalance.value_usd ?? totalBalance.value ?? 0;

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
 * Update date range display
 */
function updateDateRangeDisplay() {
    const displayEl = document.getElementById('date-range-display');
    if (!displayEl) return;

    const start = new Date(currentDateRange.startDate);
    const end = new Date(currentDateRange.endDate);

    const formatDate = (date) => {
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    displayEl.textContent = `${formatDate(start)} - ${formatDate(end)}`;
}

/**
 * Update transaction count display
 */
function updateTransactionCount(count) {
    const countEl = document.getElementById('transaction-count');
    if (countEl) {
        countEl.textContent = count.toLocaleString();
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

    // Update transaction count
    updateTransactionCount(transactions?.length || 0);

    // Update date range display
    updateDateRangeDisplay();

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

    // Filter to only show completed/successful transactions
    const completedTransactions = transactions.filter(tx => {
        const status = (tx.transaction_info?.transaction_status || tx.status || '').toLowerCase();
        return status.includes('success') || status.includes('completed') || status === 's';
    });

    // Sort transactions by date in descending order (most recent first)
    const sortedTransactions = [...completedTransactions].sort((a, b) => {
        const dateA = new Date(a.transaction_info?.transaction_initiation_date || a.transaction_date || 0);
        const dateB = new Date(b.transaction_info?.transaction_initiation_date || b.transaction_date || 0);
        return dateB - dateA; // DESC order
    });

    sortedTransactions.forEach(tx => {
        const row = document.createElement('tr');
        row.className = 'border-b border-gray-200 hover:bg-gray-50';

        // Extract transaction details (defensive access)
        const date = tx.transaction_info?.transaction_initiation_date ||
                    tx.transaction_date ||
                    'N/A';
        const id = tx.transaction_info?.transaction_id || tx.transaction_id || 'N/A';
        const tx_amount = tx.transaction_info?.transaction_amount || {};
        const amount = tx_amount.value || tx.amount || 0;
        const status = tx.transaction_info?.transaction_status ||
                      tx.status ||
                      'Unknown';

        // Extract description (payer info or transaction subject)
        const payer_info = tx.payer_info || {};
        const payer_name = payer_info.payer_name?.alternate_full_name ||
                          payer_info.payer_name?.given_name ||
                          payer_info.email_address ||
                          tx.transaction_info?.transaction_subject ||
                          tx.transaction_info?.transaction_note ||
                          'N/A';

        // Use USD amount if available, otherwise use original amount
        const displayAmount = tx_amount.value_usd ?? amount;

        // Color code based on amount
        const amountClass = parseFloat(displayAmount) >= 0 ? 'text-green-600' : 'text-red-600';

        row.innerHTML = `
            <td class="px-6 py-4 text-sm text-gray-900">${formatDate(date)}</td>
            <td class="px-6 py-4 text-sm text-gray-600 font-mono text-xs">${id}</td>
            <td class="px-6 py-4 text-sm text-gray-600">${payer_name}</td>
            <td class="px-6 py-4 text-sm">
                <span class="px-2 py-1 text-xs rounded-full ${getStatusColor(status)}">
                    ${status}
                </span>
            </td>
            <td class="px-6 py-4 text-sm text-right font-semibold ${amountClass}">
                ${formatCurrency(displayAmount)}
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
        const tx_amount = tx.transaction_info?.transaction_amount || {};

        // Use USD amount if available, otherwise use original amount
        const amount = parseFloat(
            tx_amount.value_usd ??
            tx_amount.value ??
            tx.amount ??
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
 * Convert ISO 8601 string to datetime-local input format (YYYY-MM-DDTHH:mm)
 */
function toDatetimeLocal(isoString) {
    // Remove seconds and timezone from ISO string
    return isoString.slice(0, 16);
}

/**
 * Convert datetime-local input value to ISO 8601 string
 */
function toISO8601(datetimeLocal) {
    // Add seconds and timezone
    return new Date(datetimeLocal).toISOString();
}

/**
 * Set default date range (1 year ago to now)
 */
function setDefaultDateRange() {
    const now = new Date();
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(now.getFullYear() - 1);

    currentDateRange.startDate = oneYearAgo.toISOString();
    currentDateRange.endDate = now.toISOString();

    // Populate input fields
    const startDateInput = document.getElementById('filter-start-date');
    const endDateInput = document.getElementById('filter-end-date');

    if (startDateInput) {
        startDateInput.value = toDatetimeLocal(currentDateRange.startDate);
    }
    if (endDateInput) {
        endDateInput.value = toDatetimeLocal(currentDateRange.endDate);
    }
}

/**
 * Apply filters and reload transactions
 */
async function applyFilters() {
    const startDateInput = document.getElementById('filter-start-date');
    const endDateInput = document.getElementById('filter-end-date');

    if (!startDateInput?.value || !endDateInput?.value) {
        showError('Please select both start and end dates');
        return;
    }

    // Update state
    currentDateRange.startDate = toISO8601(startDateInput.value);
    currentDateRange.endDate = toISO8601(endDateInput.value);

    // Validate date range
    if (new Date(currentDateRange.startDate) > new Date(currentDateRange.endDate)) {
        showError('Start date must be before end date');
        return;
    }

    // Reload transactions
    await loadTransactions(currentDateRange.startDate, currentDateRange.endDate);
}

/**
 * Reset filters to default (1 year ago to now)
 */
async function resetFilters() {
    setDefaultDateRange();
    await loadTransactions(currentDateRange.startDate, currentDateRange.endDate);
}

/**
 * Initialize finance page on DOM ready
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Finance page loaded - initializing API integration');

    // Load balance immediately
    await loadBalance();

    // Set default date range (1 year ago to now)
    setDefaultDateRange();

    // Load transactions with default date range
    await loadTransactions(currentDateRange.startDate, currentDateRange.endDate);

    // Add event listeners
    const applyButton = document.getElementById('apply-filters');
    const resetButton = document.getElementById('reset-filters');

    if (applyButton) {
        applyButton.addEventListener('click', applyFilters);
    }
    if (resetButton) {
        resetButton.addEventListener('click', resetFilters);
    }
});
