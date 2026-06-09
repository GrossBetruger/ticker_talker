"""
Flask web application for Ticker Talker
"""
import os
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""

from flask import Flask, render_template, request, jsonify
import yfinance as yf
from curl_cffi.requests import Session as CffiSession
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import traceback
import math

_session = CffiSession(verify=False, impersonate="chrome")

app = Flask(__name__)


def _resolve_tase_security(security_id: str) -> str:
    """Resolve a TASE security number to a yfinance ticker via ISIN lookup.

    1. Query the TASE market API for the security's ISIN.
    2. Search Yahoo Finance for that ISIN.
    3. Return the first matching yfinance ticker.
    """
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
        raise ValueError(f"TASE security {security_id} not found (HTTP {resp.status_code})")

    info = resp.json()
    isin = info.get("ISIN")
    if not isin:
        raise ValueError(f"No ISIN found for TASE security {security_id}")

    yf_resp = _requests.get(
        "https://query2.finance.yahoo.com/v1/finance/search",
        params={"q": isin, "quotesCount": 10, "newsCount": 0},
        headers={"User-Agent": "Mozilla/5.0"},
        verify=False,
        timeout=10,
    )
    quotes = yf_resp.json().get("quotes", [])
    if not quotes:
        raise ValueError(
            f"TASE security {security_id} (ISIN {isin}) not found on Yahoo Finance"
        )

    return quotes[0]["symbol"]


def resolve_tickers(raw_tickers: List[str]) -> tuple[List[str], Dict[str, str]]:
    """Resolve user-provided identifiers to yfinance ticker symbols.

    Purely numeric identifiers are treated as TASE security numbers and
    resolved via ISIN lookup through the TASE API + Yahoo Finance search.

    Returns (yf_tickers, display_map) where display_map maps
    yf_ticker -> original user input for chart labels / summaries.
    """
    yf_tickers = []
    display_map: Dict[str, str] = {}

    for raw in raw_tickers:
        if raw.isdigit():
            yf_ticker = _resolve_tase_security(raw)
        else:
            yf_ticker = raw
        yf_tickers.append(yf_ticker)
        display_map[yf_ticker] = raw

    return yf_tickers, display_map


def download_price_data(tickers: List[str], start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Download price data for given tickers."""
    df = yf.download(
        tickers,
        start=start_date,
        end=end_date,
        session=_session,
        progress=False,
        threads=False,
        auto_adjust=True,
    )

    if df is None or df.empty:
        raise ValueError("No data could be downloaded for any ticker!")

    if len(tickers) == 1:
        df = df[['Close']].rename(columns={'Close': tickers[0]})
    else:
        df = df['Close']

    df = df.dropna(how='all')

    if df.empty:
        raise ValueError("No data could be downloaded for any ticker!")

    # Forward-fill per-ticker gaps caused by different exchange calendars
    # (e.g. TASE is open Sun-Thu, NYSE Mon-Fri).
    df = df.ffill()
    # Drop any leading rows that still have NaN (before the first trade of a ticker)
    df = df.dropna()

    return df


def normalize_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize prices to starting point (100% at start)."""
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


def _safe_float(val) -> Optional[float]:
    """Convert to float, replacing NaN/Inf with None (JSON null)."""
    f = float(val)
    if math.isfinite(f):
        return f
    return None


def get_summary_stats(df: pd.DataFrame, normalized_df: pd.DataFrame) -> Dict:
    """Calculate summary statistics for each ticker."""
    summary = {}
    
    for ticker in normalized_df.columns:
        if ticker in df.columns:
            start_price = df[ticker].iloc[0]
            end_price = df[ticker].iloc[-1]
            start_normalized = normalized_df[ticker].iloc[0]
            end_normalized = normalized_df[ticker].iloc[-1]
            change_pct = end_normalized - start_normalized
            actual_return = ((end_price - start_price) / start_price) * 100
            
            summary[ticker] = {
                'start_price': _safe_float(start_price),
                'end_price': _safe_float(end_price),
                'start_normalized': _safe_float(start_normalized),
                'end_normalized': _safe_float(end_normalized),
                'change_pct': _safe_float(change_pct),
                'actual_return': _safe_float(actual_return)
            }
    
    return summary


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/api/compare', methods=['POST'])
def compare_tickers():
    """API endpoint to compare tickers."""
    try:
        data = request.get_json()
        raw_tickers = [t.strip().upper() for t in data.get('tickers', '').split(',') if t.strip()]
        
        if not raw_tickers:
            return jsonify({'error': 'No ticker symbols provided'}), 400
        
        tickers, display_map = resolve_tickers(raw_tickers)
        
        # Parse time window
        time_window_type = data.get('time_window_type', 'period')
        
        if time_window_type == 'dates':
            start_str = data.get('start_date')
            end_str = data.get('end_date')
            try:
                start_date = datetime.strptime(start_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_str, "%Y-%m-%d")
            except ValueError as e:
                return jsonify({'error': f'Invalid date format: {e}'}), 400
        else:  # period
            period = data.get('period', '1y')
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
                    return jsonify({'error': f'Invalid period format: {period}'}), 400
            
            start_date = end_date - timedelta(days=days)
        
        # Download and process data
        price_df = download_price_data(tickers, start_date, end_date)
        
        if price_df.empty:
            return jsonify({'error': 'No price data available'}), 400
        
        # Normalize prices
        normalized_df = normalize_prices(price_df)
        
        # Get summary statistics
        summary = get_summary_stats(price_df, normalized_df)
        
        # Prepare chart data
        chart_data = {
            'labels': [date.strftime('%Y-%m-%d') for date in normalized_df.index],
            'datasets': []
        }
        
        colors = [
            '#3B82F6', '#EF4444', '#10B981', '#F59E0B', 
            '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'
        ]
        
        for idx, ticker in enumerate(normalized_df.columns):
            chart_data['datasets'].append({
                'label': display_map.get(ticker, ticker),
                'data': [_safe_float(val) for val in normalized_df[ticker].values],
                'borderColor': colors[idx % len(colors)],
                'backgroundColor': colors[idx % len(colors)] + '20',
                'borderWidth': 2,
                'fill': False,
                'tension': 0.1
            })
        
        display_summary = {
            display_map.get(k, k): v for k, v in summary.items()
        }
        
        return jsonify({
            'success': True,
            'chart_data': chart_data,
            'summary': display_summary,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

