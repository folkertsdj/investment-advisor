# Investment Advisor - AI Agent Instructions

## Project Overview
**Purpose**: Portfolio management web app that displays stock holdings, live prices, and analyst targets.

**Architecture**: Frontend-backend split  
- **Frontend**: HTML/CSS/JavaScript with real-time price updates and currency conversion
- **Backend**: Python HTTP server (SimpleHTTPRequestHandler) with parallel API calls to Finnhub and yfinance

**Key Files**:
- [index.html](index.html) - UI structure  
- [script.js](script.js) - Client logic (portfolio operations, API calls, DOM rendering)
- [server/server.py](server/server.py) - REST API endpoints  
- [server/stocks.txt](server/stocks.txt) - Portfolio persistence (CSV-like format)  
- [server/config.json](server/config.json) - Finnhub API token configuration

---

## Data Flow

### Stock Portfolio Storage
Portfolio stored in [server/stocks.txt](server/stocks.txt) as CSV lines:  
```
SYMBOL,COMPANY_NAME,QUANTITY
AAPL,Apple,10
MSFT,Microsoft,5.5
```

Data loads from file → fetches live prices/analyst data in parallel → returns JSON to frontend.

### API Endpoints
| Endpoint | Method | Purpose | Data Persistence |
|----------|--------|---------|---|
| `/api/stocks` | GET | Fetch portfolio with live prices | Reads stocks.txt, enriches with live data |
| `/api/add-stock` | POST | Add stock (0 quantity) | Appends to stocks.txt |
| `/api/update-stock` | POST | Update quantity | Modifies stocks.txt in-place |
| `/api/delete-stock` | POST | Remove stock | Rewrites stocks.txt without deleted row |
| `/api/search` | GET | Search stocks (Finnhub) | No persistence, read-only |

---

## Critical Developer Patterns

### Backend: Parallel Data Enrichment (server.py)
Live prices fetched **asynchronously** via `aiohttp` for performance:
```python
# Each stock gets Quote + Profile from Finnhub in parallel
async def get_stock_data(session, stock):
    # Two concurrent requests per stock
    quote_url = f"https://finnhub.io/api/v1/quote?symbol=..."
    profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol=..."
    # Await both concurrently with asyncio.gather()
```

Analyst targets fetched via `ThreadPoolExecutor` (yfinance is blocking I/O):
```python
with ThreadPoolExecutor(max_workers=10) as executor:
    executor.map(fetch_yf_data, stocks)  # Parallel, not sequential
```

**When modifying stock fetching**: Preserve parallel patterns. Sequential loops will cause 30s+ delays.

### Frontend: Optimistic UI Updates (script.js)
Quantity changes update DOM immediately, server request in background:
```javascript
// Optimistic: update card total instantly
rowTotalEl.innerHTML = formatCurrency(newTotal);
recalculateSummaryFromDOM();  // Recalc portfolio summary from visible cards

// Background: persist to server
fetch(API_UPDATE_URL, {...}).catch(() => alert('Failed to save'));
```

If server update fails, UI stays updated (no automatic revert). This is acceptable for fast user experience.

### Frontend: Search with Debouncing
Search input debounces at **300ms** to reduce Finnhub API calls:
```javascript
let debounceTimer;
searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => performSearch(query), 300);
});
```

### Currency Conversion
Exchange rate fetched from **frankfurter.app** API (free, no key):
```javascript
USD_TO_EUR_RATE = 0.93;  // Default fallback
fetch('https://api.frankfurter.app/latest?from=USD&to=EUR')
    .then(r => r.json())
    .then(d => USD_TO_EUR_RATE = d.rates.EUR);
```

All monetary values displayed in USD + EUR (dual currency).

---

## File Handling and State Management

### Stocks.txt Mutation Logic
- **Add**: Append new line with 0 quantity  
- **Update**: Parse all lines, modify matching symbol, rewrite entire file  
- **Delete**: Rewrite file excluding target symbol  

No database—pure file I/O. Keep file format consistent: `SYMBOL,NAME,QTY`.

### Config Loading
API token loaded from [server/config.json](server/config.json) in every GET request. If token missing/invalid, falls back to yfinance-only (limited data).

```python
if api_token and api_token != "YOUR_FINNHUB_TOKEN_HERE":
    # Use async Finnhub calls
else:
    print("Skipping live data: No valid API token")
```

---

## UI/UX Conventions

- **Glass morphism design**: Semi-transparent backgrounds with blur (CSS variables in [style.css](style.css))  
- **Color scheme**: Dark mode (slate/indigo), accent cyan, success/danger indicators  
- **Loading states**: Spinner shown while fetching portfolio  
- **Search dropdown**: Closes on outside click, shows 10 results max  
- **Sector aggregation**: Sidebar showing industry distribution with counts

---

## Common Development Tasks

### Run Project
```bash
# Backend (port 8000)
python server/server.py

# Frontend (browser)
http://localhost:8000
```

### Add a New Stock Field
1. Update [server/stocks.txt](server/stocks.txt) line format  
2. Modify parsing in [server/server.py](server/server.py) (line splitting, indexing)  
3. Update card rendering in [script.js](script.js) (`renderStocks()`)

### Optimize API Calls
- Keep `ThreadPoolExecutor(max_workers=10)` for yfinance  
- Use `async/await` + `aiohttp` for Finnhub (not blocking)  
- Reduce yfinance fields requested (only `targetMedianPrice` needed)

### Debug Portfolio Persistence
Check [server/stocks.txt](server/stocks.txt) directly—it's the source of truth. Server always reads/writes here. UI state is ephemeral.

---

## External Dependencies
- **Finnhub API**: Stock quotes, profiles, search (requires API key in [server/config.json](server/config.json))  
- **yfinance**: Analyst targets (free, included)  
- **frankfurter.app**: Exchange rates (free, no key)  
- **Parqet/UI Avatars**: Stock logos with fallback

---

## Testing/Validation
- Portfolio changes: Verify [server/stocks.txt](server/stocks.txt) modified correctly  
- Price updates: Check console for Finnhub/yfinance fetch logs  
- Search: Confirm results limited to 10, sorted by Finnhub relevance  
- Currency: Verify EUR value updates when exchange rate fetched
