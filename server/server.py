import http.server
import socketserver
import json
import os

PORT = 8000

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/stocks':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*') # Allow CORS for development
            self.end_headers()
            
            stocks = []
            api_token = None
            
            # Load API Token
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(script_dir, 'config.json')
                with open(config_path, 'r') as cf:
                    config = json.load(cf)
                    api_token = config.get('finnhub_api_token')
            except Exception as e:
                print(f"Error reading config.json: {e}")

            # Read stocks from file
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                file_path = os.path.join(script_dir, 'stocks.txt')
                
                with open(file_path, 'r') as f:
                    for line in f:
                        parts = line.strip().split(',')
                        if len(parts) >= 3:
                            stocks.append({
                                'symbol': parts[0],
                                'name': parts[1],
                                'quantity': int(parts[2]),
                                'price': 0.0 # Price not stored in file anymore
                            })
            except Exception as e:
                print(f"Error reading stocks.txt: {e}")

            # Fetch live prices if token exists
            if api_token and api_token != "YOUR_FINNHUB_TOKEN_HERE":
                import urllib.request
                import urllib.error
                
                print("Fetching live prices from Finnhub...")
                for stock in stocks:
                    try:
                        url = f"https://finnhub.io/api/v1/quote?symbol={stock['symbol']}&token={api_token}"
                        with urllib.request.urlopen(url) as response:
                            data = json.loads(response.read().decode())
                            if 'c' in data and data['c'] != 0:
                                stock['price'] = float(data['c'])
                    except urllib.error.URLError as e:
                         print(f"Network error fetching {stock['symbol']}: {e}")
                    except Exception as e:
                        print(f"Error fetching {stock['symbol']}: {e}")
            else:
                print("Skipping live data: No valid API token in config.json")
            
            self.wfile.write(json.dumps(stocks).encode())

        elif self.path.startswith('/api/search'):
            import urllib.parse
            import urllib.request
            import urllib.error
            
            # Load API Token (Duplicate logic for safety)
            api_token = None
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(script_dir, 'config.json')
                with open(config_path, 'r') as cf:
                    config = json.load(cf)
                    api_token = config.get('finnhub_api_token')
            except Exception:
                pass

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
            # Serve index.html for root path
            if self.path == '/':
                self.path = '/index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == '/api/update-stock':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                symbol_to_update = data.get('symbol')
                new_quantity = data.get('quantity')
                
                if symbol_to_update is not None and new_quantity is not None:
                    # Update file
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    file_path = os.path.join(script_dir, 'stocks.txt')
                    
                    updated_lines = []
                    found = False
                    
                    if os.path.exists(file_path):
                        with open(file_path, 'r') as f:
                            lines = f.readlines()
                            for line in lines:
                                parts = line.strip().split(',')
                                if len(parts) >= 3 and parts[0] == symbol_to_update:
                                    # Update quantity (index 2)
                                    parts[2] = str(new_quantity)
                                    updated_lines.append(','.join(parts) + '\n')
                                    found = True
                                else:
                                    updated_lines.append(line)
                    
                    if found:
                        with open(file_path, 'w') as f:
                            f.writelines(updated_lines)
                            
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({'status': 'success', 'message': 'Stock updated'}).encode())
                    else:
                        self.send_error(404, "Stock not found")
                else:
                    self.send_error(400, "Invalid data")
            except Exception as e:
                print(f"Error updating stock: {e}")
                self.send_error(500, str(e))

        elif self.path == '/api/add-stock':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                symbol = data.get('symbol')
                name = data.get('name')
                
                if symbol and name:
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    file_path = os.path.join(script_dir, 'stocks.txt')
                    
                    exists = False
                    if os.path.exists(file_path):
                        with open(file_path, 'r') as f:
                            for line in f:
                                parts = line.strip().split(',')
                                if len(parts) > 0 and parts[0] == symbol:
                                    exists = True
                                    break
                    
                    if not exists:
                        with open(file_path, 'a') as f:
                            # Append new stock with 0 quantity
                            f.write(f"{symbol},{name},0\n")
                            
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
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                symbol = data.get('symbol')
                
                if symbol:
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    file_path = os.path.join(script_dir, 'stocks.txt')
                    
                    if os.path.exists(file_path):
                        lines_to_keep = []
                        found = False
                        with open(file_path, 'r') as f:
                            lines = f.readlines()
                            for line in lines:
                                parts = line.strip().split(',')
                                if len(parts) > 0 and parts[0] == symbol:
                                    found = True
                                    continue # Skip this line
                                lines_to_keep.append(line)
                        
                        if found:
                            with open(file_path, 'w') as f:
                                f.writelines(lines_to_keep)
                                
                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps({'status': 'success', 'message': 'Stock deleted'}).encode())
                        else:
                            self.send_error(404, "Stock not found")
                    else:
                        self.send_error(404, "File not found")
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
