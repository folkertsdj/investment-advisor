# investment-advisor
App for managing investments and investment advice.

## Tech Stack
- HTML
- CSS
- JavaScript
- Python
- Flask
- Finnhub API

## Setup
1. **Set API Token**: Before running the server, you need to set your Finnhub API token as an environment variable.
   ```bash
   export FINNHUB_API_TOKEN="YOUR_FINNHUB_TOKEN_HERE"
   ```
2. **Create the Database**:
    ```bash
    python3 server/migrate_to_db.py
    ```
3. **Run Server**:
   ```bash
   python3 server/server.py
   ```

![Dashboard Screenshot](screenshot.png)
