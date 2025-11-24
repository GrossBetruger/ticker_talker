# Ticker Talker

A Python application that downloads stock price data for multiple ticker symbols, normalizes them to a starting point (100% baseline), and compares their performance over a user-defined time window.

## Features

- 📊 Download price data for multiple tickers simultaneously
- 📅 Flexible time window selection (date range or period-based)
- 📈 Normalize prices to starting point for easy comparison
- 📉 Visualize normalized price actions in a single chart
- 📋 Display summary statistics for each ticker

## Installation

1. Install dependencies:
```bash
pip install -e .
```

Or install dependencies directly:
```bash
pip install yfinance matplotlib pandas flask
```

## Usage

### Web GUI (Recommended)

Start the web server:
```bash
python app.py
```

Then open your browser and navigate to:
```
http://localhost:5000
```

The web interface provides:
- 🎨 Modern, responsive UI
- 📊 Interactive charts with Chart.js
- 📱 Mobile-friendly design
- ⚡ Real-time data fetching
- 📈 Beautiful visualizations

### Command Line Interface

Run the command-line application:
```bash
python main.py
```

The application will prompt you for:
1. **Ticker symbols**: Enter comma-separated ticker symbols (e.g., `AAPL,MSFT,GOOGL`)
2. **Time window**: Choose between:
   - Option 1: Enter specific start and end dates (YYYY-MM-DD format)
   - Option 2: Enter a period (e.g., `1y` for 1 year, `6m` for 6 months, `3mo` for 3 months)

### Example

```
Enter ticker symbols (comma-separated, e.g., AAPL,MSFT,GOOGL): AAPL,MSFT,GOOGL,TSLA

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

## Dependencies

- `yfinance`: Download stock price data from Yahoo Finance
- `matplotlib`: Create visualizations (for CLI)
- `pandas`: Data manipulation and analysis
- `flask`: Web framework (for web GUI)

## License

MIT


