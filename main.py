"""
Ticker Talker - Compare normalized stock price actions across multiple tickers
"""
import os
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""

import yfinance as yf
from curl_cffi.requests import Session as CffiSession
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from typing import List, Tuple, Optional
import sys

_session = CffiSession(verify=False, impersonate="chrome")


def _resolve_tase_security(security_id: str) -> str:
    """Resolve a TASE security number to a yfinance ticker via ISIN lookup."""
    import requests as _requests

    tase_session = CffiSession(verify=False, impersonate="chrome")
    tase_session.get("https://api.tase.co.il/api/")
    tase_headers = {
        "Accept": "application/json",
        "Origin": "https://market.tase.co.il",
        "Referer": "https://market.tase.co.il/",
    }
    resp = tase_session.get(
        f"https://api.tase.co.il/api/company/securitydata?securityId={security_id}&lang=en",
        headers=tase_headers,
    )
    if resp.status_code != 200:
        print(f"  Error: TASE security {security_id} not found (HTTP {resp.status_code})")
        sys.exit(1)

    info = resp.json()
    isin = info.get("ISIN")
    if not isin:
        print(f"  Error: No ISIN found for TASE security {security_id}")
        sys.exit(1)

    name = info.get("SecurityLongName") or info.get("Name", "")
    print(f"  TASE {security_id}: {name} (ISIN {isin})")

    yf_resp = _requests.get(
        "https://query2.finance.yahoo.com/v1/finance/search",
        params={"q": isin, "quotesCount": 10, "newsCount": 0},
        headers={"User-Agent": "Mozilla/5.0"},
        verify=False,
        timeout=10,
    )
    quotes = yf_resp.json().get("quotes", [])
    if not quotes:
        print(f"  Error: TASE security {security_id} (ISIN {isin}) not found on Yahoo Finance")
        sys.exit(1)

    symbol = quotes[0]["symbol"]
    print(f"  Resolved to Yahoo Finance ticker: {symbol}")
    return symbol


def resolve_tickers(raw_tickers: List[str]) -> Tuple[List[str], dict]:
    """Resolve user-provided identifiers to yfinance ticker symbols.

    Purely numeric identifiers are treated as TASE security numbers and
    resolved via ISIN lookup through the TASE API + Yahoo Finance search.

    Returns (yf_tickers, display_map) where display_map maps
    yf_ticker -> original user input for chart labels / summaries.
    """
    yf_tickers = []
    display_map = {}

    for raw in raw_tickers:
        if raw.isdigit():
            yf_ticker = _resolve_tase_security(raw)
        else:
            yf_ticker = raw
        yf_tickers.append(yf_ticker)
        display_map[yf_ticker] = raw

    return yf_tickers, display_map


def get_user_input() -> Tuple[List[str], datetime, datetime, dict]:
    """Get ticker symbols and time window from user."""
    print("=" * 60)
    print("Ticker Talker - Stock Price Comparison Tool")
    print("=" * 60)
    
    tickers_input = input("\nEnter ticker symbols or TASE security numbers (comma-separated, e.g., AAPL,MSFT,1159250): ").strip()
    raw_tickers = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]
    
    if not raw_tickers:
        print("Error: No ticker symbols provided!")
        sys.exit(1)
    
    tickers, display_map = resolve_tickers(raw_tickers)
    
    resolved_info = [
        f"{display_map[t]} -> {t}" if display_map[t] != t else t
        for t in tickers
    ]
    print(f"\nSelected tickers: {', '.join(resolved_info)}")
    
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
    
    return tickers, start_date, end_date, display_map


def download_price_data(tickers: List[str], start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Download price data for given tickers."""
    import time

    print(f"\nDownloading price data from {start_date.date()} to {end_date.date()}...")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            df = yf.download(
                tickers,
                start=start_date,
                end=end_date,
                session=_session,
                progress=True,
                threads=False,
            )
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  Error: {e}. Retrying in {wait}s...")
                time.sleep(wait)
                continue
            print(f"\nError: {e}")
            sys.exit(1)

        if df is not None and not df.empty:
            break

        if attempt < max_retries - 1:
            wait = 2 ** (attempt + 1)
            print(f"  Empty response, retrying in {wait}s...")
            time.sleep(wait)
        else:
            print("\nError: No data could be downloaded for any ticker!")
            sys.exit(1)

    if len(tickers) == 1:
        df = df[['Close']].rename(columns={'Close': tickers[0]})
    else:
        df = df['Close']

    df = df.dropna(how='all')

    # Forward-fill per-ticker gaps caused by different exchange calendars
    # (e.g. TASE is open Sun-Thu, NYSE Mon-Fri).
    df = df.ffill()
    df = df.dropna()
    
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


def visualize_comparison(df: pd.DataFrame, start_date: datetime, end_date: datetime, display_map: Optional[dict] = None):
    """Create visualization of normalized price comparison."""
    print("\nGenerating visualization...")
    
    plt.figure(figsize=(14, 8))
    
    for ticker in df.columns:
        label = (display_map or {}).get(ticker, ticker)
        plt.plot(df.index, df[ticker], label=label, linewidth=2, alpha=0.8)
    
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


def print_summary(df: pd.DataFrame, normalized_df: pd.DataFrame, display_map: Optional[dict] = None):
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
            
            display_name = (display_map or {}).get(ticker, ticker)
            print(f"\n{display_name}:")
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
        tickers, start_date, end_date, display_map = get_user_input()
        
        # Download price data
        price_df = download_price_data(tickers, start_date, end_date)
        
        if price_df.empty:
            print("\nError: No price data available!")
            return
        
        # Normalize prices
        normalized_df = normalize_prices(price_df)
        
        # Print summary
        print_summary(price_df, normalized_df, display_map)
        
        # Visualize
        visualize_comparison(normalized_df, start_date, end_date, display_map)
        
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
