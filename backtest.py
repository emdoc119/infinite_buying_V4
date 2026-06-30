import argparse
import yfinance as yf
from decimal import Decimal
import pandas as pd
from datetime import datetime
import warnings

from domain.models import StrategyParams
from engine.simulator import BacktestSimulator

# Suppress warnings from yfinance/pandas
warnings.filterwarnings('ignore')

def run_backtest(symbol: str, start_date: str, end_date: str):
    print(f"Downloading data for {symbol} from {start_date} to {end_date}...")
    df = yf.download(symbol, start=start_date, end=end_date, progress=False)
    
    if df.empty:
        print("No data found!")
        return

    # Handle multi-index columns in recent yfinance
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
        
    df = df.dropna()

    params = StrategyParams(
        symbol=symbol,
        total_budget=Decimal("10000"),
        split_count=40,
        star_pct=Decimal("0.15"),
        loc_buffer_pct=Decimal("0.12"),
        take_profit_pct=Decimal("0.10"),
        max_loss_pct_for_reset=Decimal("-0.10"),
        loc_shares_per_line=1
    )
    
    print(f"Starting V4 simulation for {symbol}...")
    print(f"Initial Budget: $10,000")
    
    simulator = BacktestSimulator(params, df)
    results = simulator.run()
    
    print("-" * 30)
    print("=== Backtest Results ===")
    print(f"Symbol: {symbol}")
    print(f"Period: {df.index[0].date()} ~ {df.index[-1].date()}")
    print(f"Completed Cycles: {results['completed_cycles']}")
    print(f"Final Equity: ${results['final_equity']:,.2f}")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Max Drawdown (MDD): {results['max_drawdown_pct']:.2f}%")
    print("-" * 30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Infinite Buying V4 Backtest")
    parser.add_argument("--symbol", type=str, default="TQQQ", choices=["TQQQ", "SOXL"], help="Ticker symbol")
    parser.add_argument("--start", type=str, default="2020-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=datetime.today().strftime('%Y-%m-%d'), help="End date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    run_backtest(args.symbol, args.start, args.end)
