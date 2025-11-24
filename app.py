"""
Flask web application for Ticker Talker
"""
from flask import Flask, render_template, request, jsonify
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import traceback

app = Flask(__name__)


def download_price_data(tickers: List[str], start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Download price data for given tickers."""
    all_data = {}
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                continue
            
            # Use 'Close' price
            all_data[ticker] = hist['Close']
            
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            continue
    
    if not all_data:
        raise ValueError("No data could be downloaded for any ticker!")
    
    # Combine into a single DataFrame
    df = pd.DataFrame(all_data)
    
    # Remove rows where all values are NaN
    df = df.dropna(how='all')
    
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
                'start_price': float(start_price),
                'end_price': float(end_price),
                'start_normalized': float(start_normalized),
                'end_normalized': float(end_normalized),
                'change_pct': float(change_pct),
                'actual_return': float(actual_return)
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
        tickers = [t.strip().upper() for t in data.get('tickers', '').split(',') if t.strip()]
        
        if not tickers:
            return jsonify({'error': 'No ticker symbols provided'}), 400
        
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
                'label': ticker,
                'data': [float(val) for val in normalized_df[ticker].values],
                'borderColor': colors[idx % len(colors)],
                'backgroundColor': colors[idx % len(colors)] + '20',
                'borderWidth': 2,
                'fill': False,
                'tension': 0.1
            })
        
        return jsonify({
            'success': True,
            'chart_data': chart_data,
            'summary': summary,
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

