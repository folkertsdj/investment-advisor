const API_URL = 'http://localhost:8000/api/stocks';
const API_UPDATE_URL = 'http://localhost:8000/api/update-stock';
const API_SEARCH_URL = 'http://localhost:8000/api/search';

document.addEventListener('DOMContentLoaded', () => {
    fetchStocks();
    setupSearch();
});

function setupSearch() {
    const searchInput = document.getElementById('stock-search');
    const resultsContainer = document.getElementById('search-results');

    let debounceTimer;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(debounceTimer);

        if (query.length < 1) {
            resultsContainer.classList.add('hidden');
            return;
        }

        debounceTimer = setTimeout(() => {
            performSearch(query, resultsContainer);
        }, 300);
    });

    // Close on click outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !resultsContainer.contains(e.target)) {
            resultsContainer.classList.add('hidden');
        }
    });
}

async function performSearch(query, container) {
    try {
        const response = await fetch(`${API_SEARCH_URL}?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.result && data.result.length > 0) {
            renderSearchResults(data.result.slice(0, 10), container); // Limit to 10
        } else {
            container.innerHTML = '<div class="result-item" style="cursor: default;">No results found</div>';
            container.classList.remove('hidden');
        }
    } catch (error) {
        console.error('Search error:', error);
    }
}

function renderSearchResults(results, container) {
    container.innerHTML = '';

    results.forEach(stock => {
        if (!stock.symbol) return;

        const item = document.createElement('div');
        item.className = 'result-item';
        item.innerHTML = `
            <img 
                src="https://assets.parqet.com/logos/symbol/${stock.symbol}?format=png" 
                class="stock-logo" 
                style="width: 32px; height: 32px;"
                onerror="this.onerror=null; this.src='https://ui-avatars.com/api/?name=${stock.symbol}&background=random&color=fff&size=64';"
            >
            <div class="result-info">
                <span class="result-symbol">${stock.symbol}</span>
                <span class="result-name">${stock.description || stock.symbol}</span>
            </div>
        `;

        item.addEventListener('click', () => {
            addStockToPortfolio(stock.symbol, stock.description || stock.symbol);
            container.classList.add('hidden');
            document.getElementById('stock-search').value = '';
        });

        container.appendChild(item);
    });

    container.classList.remove('hidden');
}

async function addStockToPortfolio(symbol, name) {
    try {
        const response = await fetch('http://localhost:8000/api/add-stock', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, name })
        });

        if (response.ok) {
            fetchStocks(); // Refresh grid
        } else {
            const errorData = await response.json();
            console.error("Error adding stock:", errorData.message || response.statusText);
            alert(`Failed to add stock: ${errorData.message || 'Unknown error'}`);
        }
    } catch (e) {
        console.error("Error adding stock:", e);
        alert("Failed to add stock due to network error.");
    }
}

async function fetchStocks() {
    const container = document.getElementById('stocks-container');
    const totalValueEl = document.getElementById('total-value');
    const totalHoldingsEl = document.getElementById('total-holdings');

    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        renderStocks(data, container);
        updateSummary(data, totalValueEl, totalHoldingsEl);
    } catch (error) {
        console.error('Error fetching stocks:', error);
        container.innerHTML = `
            <div class="glass" style="grid-column: 1/-1; padding: 2rem; text-align: center; color: #ef4444;">
                <p>Failed to load stock data.</p>
                <p style="font-size: 0.8rem; margin-top: 0.5rem; color: var(--text-secondary);">Please ensure the server is running on port 8000.</p>
            </div>
        `;
    }
}



function renderStocks(stocks, container) {
    container.innerHTML = ''; // Clear loading state

    stocks.forEach(stock => {
        const totalValue = stock.quantity * stock.price;

        const card = document.createElement('div');
        card.className = 'glass stock-card';
        card.id = `stock-card-${stock.symbol}`;
        card.innerHTML = `
            <button class="remove-btn" onclick="deleteStock('${stock.symbol}')">REMOVE</button>
            <div class="stock-header">
                <div class="stock-info-wrapper">
                    <img 
                        src="${stock.logo || `https://assets.parqet.com/logos/symbol/${stock.symbol}?format=png`}" 
                        alt="${stock.symbol}" 
                        class="stock-logo"
                        onerror="this.onerror=null; this.src='https://ui-avatars.com/api/?name=${stock.symbol}&background=random&color=fff&size=128';"
                    >
                    <div class="stock-info">
                        <h4>${stock.symbol}</h4>
                        <span class="stock-name">${stock.name}</span>
                        <div class="stock-industry" style="font-size: 0.7rem; color: var(--text-secondary); opacity: 0.8; margin-top: 2px;">${stock.industry || ''}</div>
                    </div>
                </div>
                <div class="stock-price">
                    <span class="current-price">${formatCurrency(stock.price)} <span class="currency-sub">${formatEuro(stock.price)}</span></span>
                    <div class="trend ${stock.change >= 0 ? 'positive' : 'negative'}" style="font-size: 0.75rem; justify-content: flex-end; margin-top: 2px;">
                        ${stock.change >= 0 ? '▲' : '▼'} ${Math.abs(stock.change).toFixed(2)}%
                    </div>
                </div>
            </div>
            <div class="stock-holdings">
                <div class="holding-item">
                    <span class="label">Quantity</span>
                    <input 
                        type="number" 
                        class="quantity-input" 
                        value="${stock.quantity}" 
                        min="0"
                        step="0.000001"
                        onchange="updateStockQuantity('${stock.symbol}', this.value, ${stock.price})"
                    >
                </div>
                <div class="holding-item" style="text-align: right;">
                    <span class="label">Total Value</span>
                    <span class="value total-row-value" style="color: var(--accent-color);">${formatCurrency(totalValue)} <span class="currency-sub">${formatEuro(totalValue)}</span></span>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

async function deleteStock(symbol) {
    try {
        const response = await fetch('http://localhost:8000/api/delete-stock', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ symbol })
        });

        if (response.ok) {
            fetchStocks(); // Refresh UI
        } else {
            console.error('Failed to delete stock');
        }
    } catch (error) {
        console.error('Error deleting stock:', error);
    }
}

async function updateStockQuantity(symbol, newQuantity, price) {
    const qty = parseFloat(newQuantity);
    if (isNaN(qty) || qty < 0) return;

    // Optimistic UI update
    const card = document.getElementById(`stock-card-${symbol}`);
    const rowTotalEl = card.querySelector('.total-row-value');
    rowTotalEl.innerHTML = `${formatCurrency(qty * price)} <span class="currency-sub">${formatEuro(qty * price)}</span>`;

    // Update Global Summary locally first for snappiness
    recalculateSummaryFromDOM();

    try {
        const response = await fetch(API_UPDATE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                symbol: symbol,
                quantity: qty
            })
        });

        if (!response.ok) {
            throw new Error('Update failed');
        }

    } catch (error) {
        console.error('Error updating stock:', error);
        alert('Failed to save changes. Please try again.');
        // Optionally revert UI here
    }
}

function recalculateSummaryFromDOM() {
    const cards = document.querySelectorAll('.stock-card');
    let totalValue = 0;

    cards.forEach(card => {
        const priceText = card.querySelector('.current-price').textContent.replace(/[^0-9.-]+/g, "");
        const qty = card.querySelector('.quantity-input').value;
        const price = parseFloat(priceText);

        if (!isNaN(price) && !isNaN(qty)) {
            totalValue += price * qty;
        }
    });

    document.getElementById('total-value').innerHTML = `${formatCurrency(totalValue)} <span class="currency-sub">${formatEuro(totalValue)}</span>`;
}

function updateSummary(stocks, valueEl, holdingsEl) {
    let totalValue = 0;
    let totalCount = 0;

    stocks.forEach(stock => {
        totalValue += stock.quantity * stock.price;
        totalCount += 1; // Content count, or could be sum of quantities
    });

    // Animate value
    valueEl.innerHTML = `${formatCurrency(totalValue)} <span class="currency-sub">${formatEuro(totalValue)}</span>`;
    holdingsEl.textContent = totalCount;

    // Update Sectors
    updateSectors(stocks);
}

function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

function updateSectors(stocks) {
    const sectorEl = document.getElementById('sector-aggregation');
    if (!sectorEl) return;

    const sectors = {};
    stocks.forEach(stock => {
        const s = stock.industry || 'Other';
        sectors[s] = (sectors[s] || 0) + 1;
    });

    // Sort sectors by count
    const sortedSectors = Object.entries(sectors).sort((a, b) => b[1] - a[1]);

    sectorEl.innerHTML = sortedSectors.map(([name, count]) => `
        <span class="sector-tag">${name} (${count})</span>
    `).join('');
}

function formatEuro(usdValue) {
    const rate = 0.93; // Fixed conversion rate for prototype
    return new Intl.NumberFormat('en-DE', {
        style: 'currency',
        currency: 'EUR'
    }).format(usdValue * rate);
}
