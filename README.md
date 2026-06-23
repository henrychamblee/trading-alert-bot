# Trading Alert Bot

A Python project skeleton for an NQ and ES futures signal assistant.

This project is intentionally alert-only. It does not place trades, connect to a broker, or manage real-money execution. The first goal is to organize the model logic cleanly so live market data, GitHub workflows, and alert delivery can be added later.

## Planned Model Ideas

- NQ vs ES SMT divergence
- Asia, London, and New York sessions
- Midnight open
- Previous day high and low
- Swing highs and swing lows
- Standard deviation levels from manipulation legs
- OTE retracements
- Loss of momentum at deviation levels
- Trade setup forming alerts
- Entry alerts
- Stop loss levels
- Take profit levels
- Invalidations and exit alerts

## Project Structure

```text
trading-alert-bot/
├── README.md
├── requirements.txt
├── .gitignore
├── config/
│   └── settings.yaml
├── data/
│   └── sample_candles.csv
├── src/
│   ├── main.py
│   ├── data_loader.py
│   ├── sessions.py
│   ├── swings.py
│   ├── smt.py
│   ├── deviations.py
│   ├── ote.py
│   ├── momentum.py
│   ├── strategy.py
│   ├── risk.py
│   ├── alerts.py
│   └── logger.py
├── tests/
│   ├── test_sessions.py
│   ├── test_swings.py
│   └── test_smt.py
└── docs/
    └── model_notes.md
```

## Setup

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run Locally

```bash
python src/main.py
```

The app loads `data/sample_candles.csv`, checks placeholder model components, and prints any generated alerts.

## Run Tests

```bash
pytest
```

## GitHub Setup

Initialize Git:

```bash
git init
git add .
git commit -m "Initial trading alert bot skeleton"
```

Create a new empty repository on GitHub, then connect and push:

```bash
git remote add origin https://github.com/YOUR_USERNAME/trading-alert-bot.git
git branch -M main
git push -u origin main
```

## Next Development Step

The next step should be defining the candle timeframe and session timezone rules precisely. Once those are locked, build a reliable market structure layer: previous day high/low, midnight open, swing detection, and session tagging. That gives the strategy layer a stable foundation before adding real-time data or alert delivery.

