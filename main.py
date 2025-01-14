"""
mlm_strategy.py

An example script for:
1) Connecting to IBKR (paper or live).
2) Fetching historical data from a continuous future (ContFuture) for signals.
3) Determining the actual front-month Future contract to place trades.
4) Computing realized volatility and 200-day MA signals for the MLM strategy.
5) Placing orders on the 25th of each month if volatility is above a threshold.
6) Paper trading or live trading based on config.
"""

import numpy as np
from datetime import datetime
from ib_insync import IB, Future, ContFuture, MarketOrder, util

# ---------------------------------
# 1. Define Universe & Parameters
# ---------------------------------

mlm_universe = [
    # NOTE: Some symbols might need to be adjusted (e.g., 6A vs. AUD).
    {
        "symbol": "ZC",          # Corn
        "exchange": "CBOT",
        "currency": "USD",
        "category": "Grains"
    },
    {
        "symbol": "ZW",          # Wheat
        "exchange": "CBOT",
        "currency": "USD",
        "category": "Grains"
    },
    {
        "symbol": "ZS",          # Soybeans
        "exchange": "CBOT",
        "currency": "USD",
        "category": "Grains"
    },
    {
        "symbol": "ZM",          # Soybean Meal
        "exchange": "CBOT",
        "currency": "USD",
        "category": "Grains"
    },
    {
        "symbol": "ZL",          # Soybean Oil
        "exchange": "CBOT",
        "currency": "USD",
        "category": "Grains"
    },
    {
        "symbol": "LE",          # Live Cattle
        "exchange": "CME",
        "currency": "USD",
        "category": "Cattle"
    },
    {
        "symbol": "CL",          # Crude Oil
        "exchange": "NYMEX",
        "currency": "USD",
        "category": "Energy"
    },
    {
        "symbol": "HO",          # Heating Oil
        "exchange": "NYMEX",
        "currency": "USD",
        "category": "Energy"
    },
    {
        "symbol": "RB",          # Gasoline
        "exchange": "NYMEX",
        "currency": "USD",
        "category": "Energy"
    },
    {
        "symbol": "NG",          # Natural Gas
        "exchange": "NYMEX",
        "currency": "USD",
        "category": "Energy"
    },
    {
        "symbol": "GC",          # Gold
        "exchange": "COMEX",
        "currency": "USD",
        "category": "Metals"
    },
    {
        "symbol": "SI",          # Silver
        "exchange": "COMEX",
        "currency": "USD",
        "category": "Metals"
    },
    {
        "symbol": "HG",          # Copper
        "exchange": "COMEX",
        "currency": "USD",
        "category": "Metals"
    },
    {
        "symbol": "SB",          # Sugar #11
        "exchange": "NYBOT",
        "currency": "USD",
        "category": "Softs"
    },
    {
        "symbol": "KC",          # Coffee
        "exchange": "NYBOT",
        "currency": "USD",
        "category": "Softs"
    },
    {
        "symbol": "CT",          # Cotton
        "exchange": "NYBOT",
        "currency": "USD",
        "category": "Softs"
    },
    {
        "symbol": "ZF",          # 5yr Treasury Note
        "exchange": "CBOT",
        "currency": "USD",
        "category": "Softs"
    },
    {
        "symbol": "ZN",          # 10yr Treasury Note
        "exchange": "CBOT",
        "currency": "USD",
        "category": "Treasurys"
    },
    {
        "symbol": "ZB",          # 30yr Treasury Bond
        "exchange": "CBOT",
        "currency": "USD",
        "category": "Treasurys"
    },
    {
        "symbol": "AUD",         # Australian Dollar (might need '6A')
        "exchange": "CME",
        "currency": "USD",
        "category": "Currencys"
    },
    {
        "symbol": "GBP",         # British Pound (might need '6B')
        "exchange": "CME",
        "currency": "USD",
        "category": "Currencys"
    },
    {
        "symbol": "CAD",         # Canadian Dollar (might need '6C')
        "exchange": "CME",
        "currency": "USD",
        "category": "Currencys"
    },
    {
        "symbol": "EUR",         # Euro (might need '6E')
        "exchange": "CME",
        "currency": "USD",
        "category": "Currencys"
    },
    {
        "symbol": "CHF",         # Swiss Franc (might need '6S')
        "exchange": "CME",
        "currency": "USD",
        "category": "Currencys"
    },
    {
        "symbol": "JPY",         # Japanese Yen (might need '6J')
        "exchange": "CME",
        "currency": "USD",
        "category": "Currencys"
    },
]

# How many days of data do we want? (e.g., 1.5+ years to get 200-day MA)
HISTORY_DURATION = "2 Y"
BAR_SIZE = "1 day"

# Volatility threshold. Adjust based on preference/backtests.
VOL_THRESHOLD = 0.015

# The rolling window for realized volatility (e.g., 20 days)
VOL_WINDOW = 20

# The MA window for the MLM strategy (200 days).
MA_WINDOW = 200

# Position size for each contract.
# In practice, change this to more sophisticated position sizing or risk controls.
CONTRACT_SIZE = 1

# ---------------------------------
# 2. IBKR Connection
# ---------------------------------

def connect_ibkr(paper_trading=True, client_id=9999):
    ib = IB()
    # Usually paper is port 7497, live is 7496
    port = 7497 if paper_trading else 7496

    ib.connect(host='127.0.0.1', port=port, clientId=client_id)
    if ib.isConnected():
        print(f"[INFO] Connected to IBKR ({'paper' if paper_trading else 'live'}) on port {port}.")
    else:
        raise ConnectionError("Failed to connect to IBKR.")
    return ib

# ---------------------------------
# 3. Fetch Historical Data from Continuous Future
# ---------------------------------

def get_continuous_data(ib, symbol_info):
    """
    1) Create a ContFuture for the given symbol/exchange/currency.
    2) Request historical data (daily bars) for the desired duration.
    3) Return the DataFrame or None if unsuccessful.
    """
    cont_fut = ContFuture(
        symbol=symbol_info['symbol'],
        exchange=symbol_info['exchange'],
        currency=symbol_info['currency']
    )
    try:
        bars = ib.reqHistoricalData(
            contract=cont_fut,
            endDateTime='',
            durationStr=HISTORY_DURATION,
            barSizeSetting=BAR_SIZE,
            whatToShow='TRADES',
            useRTH=False,
            formatDate=1
        )
    except Exception as e:
        print(f"[ERROR] Failed to fetch continuous data for {symbol_info['symbol']}: {e}")
        return None

    if not bars:
        print(f"[WARNING] No continuous bars returned for {symbol_info['symbol']}.")
        return None

    df = util.df(bars)
    if df.empty:
        print(f"[WARNING] Continuous DataFrame empty for {symbol_info['symbol']}.")
        return None

    # Attach symbol
    df['symbol'] = symbol_info['symbol']
    return df

# ---------------------------------
# 4. Determine Actual Front-Month Contract (for Trading)
# ---------------------------------

def get_front_month_contract(ib, symbol_info):
    """
    Query IB for all available (dated) contracts for a given symbol_info,
    then pick the earliest valid one (front-month).
    Returns a Future contract object or None if not found.
    """
    # Create an 'undated' Future to get contract details
    undated = Future(
        symbol=symbol_info['symbol'],
        exchange=symbol_info['exchange'],
        currency=symbol_info['currency']
    )
    details = ib.reqContractDetails(undated)
    if not details:
        print(f"[WARNING] No contract details returned for {symbol_info['symbol']}")
        return None

    # Filter out only real futures with a valid lastTradeDateOrContractMonth
    valid_contracts = []
    for d in details:
        c = d.contract
        # Must have something like 'YYYYMM' in c.lastTradeDateOrContractMonth
        if c.lastTradeDateOrContractMonth and len(c.lastTradeDateOrContractMonth) >= 6:
            valid_contracts.append(c)

    if not valid_contracts:
        print(f"[WARNING] No valid (non-expired) contracts found for {symbol_info['symbol']}")
        return None

    # Sort by lastTradeDateOrContractMonth (earliest first)
    valid_contracts.sort(key=lambda x: x.lastTradeDateOrContractMonth)

    # Return the earliest contract (front-month)
    front = valid_contracts[0]
    return front

# ---------------------------------
# 5. Volatility & MLM Signal Calculation
# ---------------------------------

def compute_indicators(df):
    """
    Compute 20-day realized vol, 200-day MA, and signal (+1 or -1).
    """
    df = df.copy()
    df['return'] = df['close'].pct_change()
    # Realized vol
    df['rolling_std_20'] = df['return'].rolling(VOL_WINDOW).std()

    # 200-day MA
    df['MA200'] = df['close'].rolling(MA_WINDOW).mean()

    # Signal: +1 if price > MA, -1 otherwise
    df['signal'] = np.where(df['close'] > df['MA200'], 1, -1)

    # Drop rows where we don't have enough data (especially for first 200 days)
    df.dropna(inplace=True)
    return df

# ---------------------------------
# 6. Main Strategy Logic
# ---------------------------------

def run_mlm_strategy(paper_trading=True):
    """
    Main function:
     1. Connect to IBKR (paper or live).
     2. For each symbol in mlm_universe, pull historical data from the ContFuture.
     3. Compute indicators (vol, 200-day MA) from that continuous data.
     4. Collect the latest volatility from each symbol and average them.
     5. If today's day == 25 and avg vol > threshold, place trades.
        - Trades are placed on the actual front-month (dated) Future contract,
          based on the final signal from the continuous data.
    """
    ib = connect_ibkr(paper_trading=paper_trading, client_id=9999)

    symbol_data_map = {}

    # 1) Fetch continuous data & compute signals
    for info in mlm_universe:
        df_cont = get_continuous_data(ib, info)
        if df_cont is None or df_cont.empty:
            continue  # No data => skip

        # Compute indicators on the continuous series
        df_ind = compute_indicators(df_cont)
        if df_ind.empty:
            print(f"[WARNING] Not enough data for 200-day MA => {info['symbol']}")
            continue

        # We'll store the entire DF plus the *latest* signal
        symbol_data_map[info['symbol']] = {
            'df': df_ind,
            'signal': df_ind['signal'].iloc[-1],  # the most recent signal
            'vol': df_ind['rolling_std_20'].iloc[-1]  # the latest realized vol
        }

    if not symbol_data_map:
        print("[ERROR] No data for any symbols!")
        ib.disconnect()
        return

    # 2) Compute the average volatility across all instruments
    all_vols = [symbol_data_map[sym]['vol'] for sym in symbol_data_map]
    avg_vol = np.mean(all_vols)
    print(f"[INFO] Average realized vol across instruments = {avg_vol:.4f}")

    # 3) Decide if environment is 'volatile'
    is_volatile = (avg_vol > VOL_THRESHOLD)
    print(f"[INFO] Volatility check => {is_volatile} (threshold={VOL_THRESHOLD:.4f})")

    # 4) Check if today is the 25th
    today = datetime.today()
    is_rebalance_day = (today.day == 25)

    if is_rebalance_day and is_volatile:
        print("[INFO] Rebalance day & environment is volatile => placing orders.")
        # For each symbol, place an order on the front-month contract
        for sym, data in symbol_data_map.items():
            latest_signal = data['signal']
            # Grab the actual front-month Future to trade
            # (If not found, skip)
            symbol_info = next((x for x in mlm_universe if x['symbol'] == sym), None)
            if not symbol_info:
                continue

            front_contract = get_front_month_contract(ib, symbol_info)
            if front_contract is None:
                print(f"[WARNING] No front-month for {sym}")
                continue

            # Construct the IB MarketOrder
            pos_size = CONTRACT_SIZE
            action = 'BUY' if latest_signal == 1 else 'SELL'
            order = MarketOrder(action, pos_size)

            trade = ib.placeOrder(front_contract, order)
            print(f"[TRADE] {sym}: Placed {action} {pos_size} contract(s). "
                  f"Signal={latest_signal}, "
                  f"Front={front_contract.lastTradeDateOrContractMonth}")

        # Let the event loop run briefly to ensure orders process
        ib.sleep(5)
    else:
        print("[INFO] Not a rebalance day OR volatility is below threshold. No trades.")

    ib.disconnect()

# ---------------------------------
# 7. Execution
# ---------------------------------

if __name__ == "__main__":
    run_mlm_strategy(paper_trading=True)
