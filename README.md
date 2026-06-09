# Ticker Talker

A Python application that downloads stock price data for multiple ticker symbols, normalizes them to a starting point (100% baseline), and compares their performance over a user-defined time window.

## Features

- 📊 Download price data for multiple tickers simultaneously
- 📅 Flexible time window selection (date range or period-based)
- 📈 Normalize prices to starting point for easy comparison
- 📉 Visualize normalized price actions in a single chart
- 📋 Display summary statistics for each ticker
- 🇮🇱 **TASE security number support** — enter numeric TASE identifiers (e.g., `1159250`) and they are automatically resolved to Yahoo Finance tickers via ISIN lookup through the TASE API
- 🌍 **Cross-exchange comparison** — compare tickers from different exchanges (e.g., NYSE + TASE) with automatic forward-fill for non-overlapping trading calendars

## Usage

### Web GUI (Recommended)

```bash
uv run app.py
```

Then open http://localhost:5000.

### Command Line Interface

```bash
uv run main.py
```

The application will prompt you for:
1. **Ticker symbols**: Enter comma-separated ticker symbols or TASE security numbers (e.g., `AAPL,MSFT,1159250`)
2. **Time window**: Choose between:
   - Option 1: Enter specific start and end dates (YYYY-MM-DD format)
   - Option 2: Enter a period (e.g., `1y` for 1 year, `6m` for 6 months, `3mo` for 3 months)

### Example

```
Enter ticker symbols or TASE security numbers (comma-separated, e.g., AAPL,MSFT,1159250): AAPL,1159250

Selected tickers: AAPL, 1159250 -> CSSPX.MI

Time window options:
1. Enter start and end dates (YYYY-MM-DD)
2. Enter period (e.g., '1y' for 1 year, '6m' for 6 months, '3mo' for 3 months)

Choose option (1 or 2): 2
Enter period (e.g., '1y', '6m', '3mo', '1mo', '5d'): 1y
```

## Output

The application will:
1. Download price data for all specified tickers
2. Normalize prices to 100% at the starting point
3. Display summary statistics (starting price, ending price, normalized values, returns)
4. Generate a visualization chart showing normalized price comparisons
5. Save the chart as a PNG file with timestamp

## How Normalization Works

Prices are normalized using the formula:
```
normalized_price = (current_price / starting_price) * 100
```

This means all tickers start at 100% at the beginning of the time window, making it easy to compare relative performance regardless of their actual price levels.

## TASE Security Numbers

You can enter TASE (Tel Aviv Stock Exchange) security numbers directly instead of ticker symbols. The app will:

1. Query the TASE market API to look up the security's ISIN
2. Search Yahoo Finance for a matching listing (typically on another exchange carrying the same instrument)
3. Download price data from that listing and display results using the original TASE security number

For example, entering `1159250` (iShares Core S&P 500 UCITS ETF on TASE) resolves to `CSSPX.MI` (same fund on Milan exchange).

## Dependencies

- `yfinance`: Download stock price data from Yahoo Finance
- `matplotlib`: Create visualizations (for CLI)
- `pandas`: Data manipulation and analysis
- `flask`: Web framework (for web GUI)
- `curl-cffi`: HTTP client with browser impersonation (used for TASE API access)

## License

MIT


