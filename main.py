"""
Ticker Talker - Compare normalized stock price actions across multiple tickers
"""
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Tuple, Optional
import sys


def get_user_input() -> Tuple[List[str], datetime, datetime]:
    """Get ticker symbols and time window from user."""
    print("=" * 60)
    print("Ticker Talker - Stock Price Comparison Tool")
    print("=" * 60)
    
    # Get ticker symbols
    tickers_input = input("\nEnter ticker symbols (comma-separated, e.g., AAPL,MSFT,GOOGL): ").strip()
    tickers = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]
    
    if not tickers:
        print("Error: No ticker symbols provided!")
        sys.exit(1)
    
    print(f"\nSelected tickers: {', '.join(tickers)}")
    
    # Get time window
    print("\nTime window options:")
    print("1. Enter start and end dates (YYYY-MM-DD)")
    print("2. Enter period (e.g., '1y' for 1 year, '6m' for 6 months, '3mo' for 3 months)")
    
    choice = input("\nChoose option (1 or 2): ").strip()
    
    if choice == "1":
        start_str = input("Enter start date (YYYY-MM-DD): ").strip()
        end_str = input("Enter end date (YYYY-MM-DD): ").strip()
        
        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
        except ValueError as e:
            print(f"Error: Invalid date format. {e}")
            sys.exit(1)
    elif choice == "2":
        period = input("Enter period (e.g., '1y', '6m', '3mo', '1mo', '5d'): ").strip()
        end_date = datetime.now()
        
        # Calculate start date based on period
        period_map = {
            '1y': 365, '6m': 180, '3mo': 90, '1mo': 30,
            '5d': 5, '1d': 1
        }
        
        if period.lower() in period_map:
            days = period_map[period.lower()]
        else:
            # Try to parse period string
            try:
                if period.lower().endswith('y'):
                    days = int(period.lower().rstrip('y')) * 365
                elif period.lower().endswith('m'):
                    days = int(period.lower().rstrip('m')) * 30
                elif period.lower().endswith('mo'):
                    days = int(period.lower().rstrip('mo')) * 30
                elif period.lower().endswith('d'):
                    days = int(period.lower().rstrip('d'))
                else:
                    raise ValueError("Invalid period format")
            except:
                print(f"Error: Invalid period format: {period}")
                sys.exit(1)
        
        from datetime import timedelta
        start_date = end_date - timedelta(days=days)
    else:
        print("Error: Invalid choice!")
        sys.exit(1)
    
    return tickers, start_date, end_date


def download_price_data(tickers: List[str], start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Download price data for given tickers."""
    print(f"\nDownloading price data from {start_date.date()} to {end_date.date()}...")
    
    all_data = {}
    
    for ticker in tickers:
        try:
            print(f"  Fetching {ticker}...", end=" ")
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                print(f"⚠ No data found")
                continue
            
            # Use 'Close' price
            all_data[ticker] = hist['Close']
            print(f"✓ ({len(hist)} data points)")
            
        except Exception as e:
            print(f"✗ Error: {e}")
            continue
    
    if not all_data:
        print("\nError: No data could be downloaded for any ticker!")
        sys.exit(1)
    
    # Combine into a single DataFrame
    df = pd.DataFrame(all_data)
    
    # Remove rows where all values are NaN
    df = df.dropna(how='all')
    
    return df


def normalize_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize prices to starting point (100% at start)."""
    print("\nNormalizing prices to starting point (100% baseline)...")
    
    normalized_df = df.copy()
    
    for ticker in normalized_df.columns:
        # Get first non-null value
        first_valid_idx = normalized_df[ticker].first_valid_index()
        if first_valid_idx is not None:
            first_value = normalized_df.loc[first_valid_idx, ticker]
            if first_value != 0:
                # Normalize: (current_price / starting_price) * 100
                normalized_df[ticker] = (normalized_df[ticker] / first_value) * 100
    
    return normalized_df


def visualize_comparison(df: pd.DataFrame, start_date: datetime, end_date: datetime):
    """Create visualization of normalized price comparison."""
    print("\nGenerating visualization...")
    
    plt.figure(figsize=(14, 8))
    
    for ticker in df.columns:
        plt.plot(df.index, df[ticker], label=ticker, linewidth=2, alpha=0.8)
    
    plt.axhline(y=100, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Baseline (100%)')
    
    plt.title(
        f'Normalized Price Comparison\n{start_date.date()} to {end_date.date()}',
        fontsize=16,
        fontweight='bold',
        pad=20
    )
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Normalized Price (%)', fontsize=12)
    plt.legend(loc='best', fontsize=10, framealpha=0.9)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    # Rotate x-axis labels for better readability
    plt.xticks(rotation=45)
    
    # Save the plot
    filename = f"ticker_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"  Saved visualization to: {filename}")
    
    # Show the plot
    plt.show()


def print_summary(df: pd.DataFrame, normalized_df: pd.DataFrame):
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)
    
    for ticker in normalized_df.columns:
        if ticker in df.columns:
            start_price = df[ticker].iloc[0]
            end_price = df[ticker].iloc[-1]
            start_normalized = normalized_df[ticker].iloc[0]
            end_normalized = normalized_df[ticker].iloc[-1]
            change_pct = end_normalized - start_normalized
            
            print(f"\n{ticker}:")
            print(f"  Starting Price: ${start_price:.2f}")
            print(f"  Ending Price:   ${end_price:.2f}")
            print(f"  Normalized Start: {start_normalized:.2f}%")
            print(f"  Normalized End:   {end_normalized:.2f}%")
            print(f"  Change:          {change_pct:+.2f}%")
            
            # Calculate actual return
            actual_return = ((end_price - start_price) / start_price) * 100
            print(f"  Actual Return:   {actual_return:+.2f}%")


def main():
    """Main application entry point."""
    try:
        # Get user input
        tickers, start_date, end_date = get_user_input()
        
        # Download price data
        price_df = download_price_data(tickers, start_date, end_date)
        
        if price_df.empty:
            print("\nError: No price data available!")
            return
        
        # Normalize prices
        normalized_df = normalize_prices(price_df)
        
        # Print summary
        print_summary(price_df, normalized_df)
        
        # Visualize
        visualize_comparison(normalized_df, start_date, end_date)
        
        print("\n" + "=" * 60)
        print("Analysis complete!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
