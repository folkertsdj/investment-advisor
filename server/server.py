import http.server
import socketserver
import json
import os
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import time
import sqlite3

PORT = 8000
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portfolio.db')
CACHE_TTL_SECONDS = 300  # 5 minutes
stock_cache = {
    "data": None,
    "timestamp": 0
}

def invalidate_cache():
    print("Cache invalidated due to portfolio change.")
    stock_cache["timestamp"] = 0
    stock_cache["data"] = None

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/stocks':
            # Check cache first
            if time.time() - stock_cache["timestamp"] < CACHE_TTL_SECONDS and stock_cache["data"] is not None:
                print("Returning cached stock data.")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(stock_cache["data"]).encode())
                return

            print("Fetching fresh stock data.")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*') # Allow CORS for development
            self.end_headers()
            
            stocks = []
            api_token = None
            
            api_token = os.environ.get('FINNHUB_API_TOKEN')

            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT symbol, name, quantity FROM stocks")
                rows = cursor.fetchall()
                conn.close()
                
                for row in rows:
                    stocks.append({
                        'symbol': row[0],
                        'name': row[1],
                        'quantity': row[2],
                        'price': 0.0
                    })
            except Exception as e:
                print(f"Error reading from database: {e}")

            if api_token and api_token != "YOUR_FINNHUB_TOKEN_HERE":
                import asyncio
                import aiohttp

                async def get_stock_data(session, stock):
                    try:
                        quote_url = f"https://finnhub.io/api/v1/quote?symbol={stock['symbol']}&token={api_token}"
                        profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={stock['symbol']}&token={api_token}"
                        
                        async with session.get(quote_url) as q_resp:
                            q_data = await q_resp.json()
                            if 'c' in q_data and q_data['c'] != 0:
                                stock['price'] = float(q_data['c'])
                                stock['change'] = float(q_data.get('dp', 0))
                        
                        async with session.get(profile_url) as p_resp:
                            p_data = await p_resp.json()
                            stock['logo'] = p_data.get('logo', '')
                            stock['industry'] = p_data.get('finnhubIndustry', 'N/A')
                    except Exception as e:
                        print(f"Error fetching {stock['symbol']}: {e}")

                async def fetch_all():
                    async with aiohttp.ClientSession() as session:
                        tasks = [get_stock_data(session, s) for s in stocks]
                        await asyncio.gather(*tasks)

                print("Fetching live prices in parallel from Finnhub...")
                asyncio.run(fetch_all())
            else:
                print("Skipping live data: No valid API token in config.json")
            
            print("Fetching analyst targets from yfinance...")
            def fetch_yf_data(stock):
                try:
                    ticker = yf.Ticker(stock['symbol'])
                    info = ticker.info
                    stock['targetMedianPrice'] = info.get('targetMedianPrice')
                    if stock['targetMedianPrice'] is None:
                        stock['targetMedianPrice'] = info.get('targetMeanPrice')
                except Exception as e:
                    print(f"Error fetching yfinance data for {stock['symbol']}: {e}")
                    stock['targetMedianPrice'] = None

            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(fetch_yf_data, stocks)
            
            stock_cache["data"] = stocks
            stock_cache["timestamp"] = time.time()

            self.wfile.write(json.dumps(stocks).encode())

        elif self.path.startswith('/api/search'):
            import urllib.parse
            import urllib.request
            import urllib.error
            
            api_token = os.environ.get('FINNHUB_API_TOKEN')
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            query = query_components.get('q', [''])[0]
            result = {"count": 0, "result": []}
            
            if api_token and query:
                try:
                    url = f"https://finnhub.io/api/v1/search?q={urllib.parse.quote(query)}&token={api_token}"
                    with urllib.request.urlopen(url) as response:
                        result = json.loads(response.read().decode())
                except Exception as e:
                    print(f"Search error: {e}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        else:
            if self.path == '/':
                self.path = '/index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/api/update-stock':
            invalidate_cache()
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                symbol_to_update = data.get('symbol')
                new_quantity = data.get('quantity')
                
                if symbol_to_update is not None and new_quantity is not None:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE stocks SET quantity = ? WHERE symbol = ?", (new_quantity, symbol_to_update))
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'status': 'success', 'message': 'Stock updated'}).encode())
                    else:
                        self.send_error(404, "Stock not found")
                    conn.close()
                else:
                    self.send_error(400, "Invalid data")
            except Exception as e:
                print(f"Error updating stock: {e}")
                self.send_error(500, str(e))

        elif self.path == '/api/add-stock':
            invalidate_cache()
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                symbol = data.get('symbol')
                name = data.get('name')
                
                if symbol and name:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR IGNORE INTO stocks (symbol, name, quantity) VALUES (?, ?, 0)", (symbol, name))
                    conn.commit()
                    conn.close()
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'success', 'message': 'Stock added'}).encode())
                else:
                    self.send_error(400, "Missing symbol or name")
            except Exception as e:
                print(f"Error adding stock: {e}")
                self.send_error(500, str(e))

        elif self.path == '/api/delete-stock':
            invalidate_cache()
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                symbol = data.get('symbol')
                
                if symbol:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM stocks WHERE symbol = ?", (symbol,))
                    conn.commit()
                    
                    if cursor.rowcount > 0:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'status': 'success', 'message': 'Stock deleted'}).encode())
                    else:
                        self.send_error(404, "Stock not found")
                    conn.close()
                else:
                    self.send_error(400, "Missing symbol")
            except Exception as e:
                print(f"Error deleting stock: {e}")
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

print(f"Server started at http://localhost:{PORT}")
with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
    httpd.serve_forever()
