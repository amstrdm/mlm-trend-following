# MLM Trend-Following Strategy with IBKR

This repository provides an automated system in Python that replicates a **trend-following approach** similar to the Mount Lucas Management (MLM) Index methodology.
The Mount Lucas Management Index works using a Moving average 200 Day Crossover Strategy and is a trend following strategy. It's obvious that trend following strategys work best in volatile environments so I built upon the strategy by introducing a function which checks the volatility of the futures contracts and only trades the strategy if volatility is above a certain (by the user specified) threshold.

**Since I'm currently busy with other bigger projects I wrote this up quickly in a few hours. I did want to do this project because I htought it was inetersting how a fund like MLM would use such a simplistic strategy. However this means the code is far from production ready. I listed the main features missing down below I may return to this when I have more time on my hands but for now if you'd like to contribute just send me a PR**

The script:

1. **Connects** to Interactive Brokers (IBKR)  
2. **Retrieves** historical data from **Continuous Futures** contracts (`ContFuture`) for computing signals (e.g., a 200-day Moving Average crossover)  
3. **Determines** the **front-month** (actual, dated) futures contract to place trades  
4. **Filters** trades based on a **volatility threshold**  
5. **Executes** buys/sells on IBKR’s **paper** or **live** environment

> **Disclaimer**: This code is intended for **educational purposes**. Use at your own risk. Thoroughly **paper trade** and understand the risks before using real funds.

---

## Table of Contents

- [Features](#features)  
- [Installation & Setup](#installation--setup)  
- [Usage](#usage)  
- [Strategy Overview](#strategy-overview)  
- [File Structure](#file-structure)  
- [Potential Customizations](#potential-customizations)  
- [FAQ](#faq)  
- [License](#license)

---

## Features

1. **Continuous Futures Data**: Fetches historical data from IBKR’s continuous futures (`ContFuture`), which allows for a longer historical series (useful for 200-day MAs).  
2. **Automatic Front-Month Selection**: Automatically identifies the nearest expiry month for each symbol when placing orders, ensuring you trade a valid, real contract.  
3. **Volatility Filter**: Calculates a 20-day realized volatility for each instrument and averages them. Trades are only placed if the overall average is above a threshold.  
4. **Crossover Signals**: Computes a simple rule: *Go Long if `close > 200-day MA`; Go Short if `close < 200-day MA`*.  
5. **Monthly Rebalance**: By default, checks date == 25. If conditions meet, places Market Orders.  
6. **Paper or Live**: Easily switch between IBKR **paper** and **live** accounts (be sure to confirm your account and port settings).

---

## Installation & Setup

1. **Clone this repo**:
   ```bash
   git clone https://github.com/yourusername/mlm-trend-following.git
   cd mlm-trend-following
   ```
2. **Install Python dependencies** (preferably in a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```
   Where `requirements.txt` should contain:
   ```text
   ib_insync
   numpy
   pandas
   ```
3. **Configure IBKR**  
   - Run **Trader Workstation (TWS)** or **IB Gateway**.  
   - **Enable API** in TWS:  
     ```
     Edit -> Global Configuration -> API -> Settings -> Enable ActiveX and Socket Clients
     ```
   - **Paper Account** typically uses port **7497**; **Live** uses **7496**.  

---

## Usage

1. **Edit `mlm_strategy.py`**  
   - Review and confirm the symbols in `mlm_universe`. Adjust them if needed (some might require different ticker symbols like `6E` for Euro).  
   - Modify thresholds (e.g., `VOL_THRESHOLD`, `MA_WINDOW`) to your preference.

2. **Run the script**:
   ```bash
   python mlm_strategy.py
   ```
   - By default, it connects to your IBKR **paper** environment (`paper_trading=True`).  
   - If you want to attempt **live** trading (not recommended until fully tested), change:
     ```python
     run_mlm_strategy(paper_trading=False)
     ```

3. **Observe the output**:
   - You should see log messages about connecting to IBKR, fetching data, computing signals, volatility, and (if conditions are met) placing orders.

---

## Strategy Overview

1. **Continuous Data**:  
   - We request daily historical bars from IBKR’s “CONTFUT” for each symbol. This helps maintain a seamless price series for calculating a **200-day MA**.

2. **Volatility Filter**:  
   - For each symbol, we calculate a **20-day standard deviation** of daily returns.  
   - We then **average** the last known vol across all symbols.  
   - If this average is **above** `VOL_THRESHOLD`, the market is considered “volatile,” and the strategy is “on.”

3. **200-day Moving Average Crossover**:  
   - If the **continuous** contract’s latest `close` is **above** the 200-day MA, signal = **+1** (long).  
   - If it’s **below**, signal = **-1** (short).

4. **Monthly Rebalance**:  
   - On the **25th** of each month, if volatility is above the threshold, the script places a **market order** for each symbol’s **front-month** (dated) `Future` contract.  
   - The order is either **BUY** (if signal = +1) or **SELL** (if signal = -1).  

---

## File Structure

```
mlm-trend-following/
├── main.py        # Main script with the logic
├── requirements.txt       # Dependencies (ib_insync, numpy, pandas)
└── README.md              # This file (overview & usage instructions)
```

---

## Potential Customizations

1. **Rollover Logic**: Instead of always picking the nearest contract, implement a rule to roll ~1 week before expiry.  
2. **Position Sizing**: Adjust how many contracts to trade based on volatility or account size.  
3. **Risk Management**: Include stop-losses, maximum drawdown limits, or Value-at-Risk approaches.  
4. **Symbol Mappings**: For currencies, you may need “6E” (Euro) instead of “EUR,” “6B” for GBP, etc. Confirm with TWS.  
5. **Trade Frequency**: Rebalance on a different schedule (weekly, daily) if desired, or only when signals change.

---

## FAQ

**Q**: *Why should anyone use this strategy?*  
**A**: Hedging. Jensen et al. (2002) found that the MLM Index performs better when US monetary policy is restrictive. US Equities tend to perform better when monetary policy is expansionary meaning the MLM Index is a good hedge for a stock concentrated portfolio. It also has no correlation to the S&P 500 Index as seen [here](https://imgur.com/a/iInUOJR). Another possible reason for using it is that, as shown in "Evidence-Based Technical Analysis" the MLM Index's Risk adjusted Return shines [when compared to stocks](https://imgur.com/a/A3wQcfn) (It is worth noting that risk here is defined as volatility by example of Milton. It is worth discussing if volatility is really a good proxy for risk in a trend following strategy which depends on volatility to function.)

**Q**: *Why do I see “No bars returned” for some symbols?*  
**A**: IBKR may not support continuous data for every symbol/exchange, or your data subscriptions might be insufficient. Test in TWS first.

**Q**: *Why does TWS show a longer chart than the data returned by the script?*  
**A**: TWS charting for a contract might be partially continuous or back-adjusted in ways the API does not replicate. Using a `ContFuture` is the closest approximation for the API.

**Q**: *Can I get live, streaming data from `ContFuture`?*  
**A**: No. IBKR only provides historical bars for continuous futures. To get real-time data, you must subscribe to an actual, dated contract.

**Q**: *How do I handle partial fills or open positions?*  
**A**: This example code is simplistic. In production, you’d track open positions, partial fills, margin usage, etc. Consider using the `ib_insync` event-driven approach for advanced logic.

**Q**: *Can I use this with stocks?*
**A**: Technically yes. However I do not recommend it. The MLM Index works far worse with stocks than it does with futures. This is pretty logical since there is no real risk transfer in stocks like there is with futures. As you can see [here](https://imgur.com/a/o6glNzK) this is further shown by the sharpe ratio of the strategy being terrible when applied to stocks compared to when it's applied to Futures.

**Q**: *What should I set the Volatilityd threshold to?*
**A**: That depends on your needs/portfolio and what you're hedging against. I recommend running a historical analysis (Something like calculating thr average real volatility of daily returns of all 25 contracts combined over the last 2 years and then taking the number above something like the bottom 70th percentile of that distribution) to find the average volatility over a given period and therefore setting the threshold to a number that singlas volatility falling out of line. In case you do decide to do this with stocks (which I don't recommend as explained in the previous question) you could of course also just plot a moving average over the VIX. 

---

## License

This project is licensed under the [MIT License](LICENSE). See the [LICENSE](LICENSE) file for details.

---

**Happy Trading!**  
If you find this project useful, feel free to star the repo and contribute improvements or clarifications.  

*Remember: Always test in IBKR’s paper environment before going live.*