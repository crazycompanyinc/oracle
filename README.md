# Oracle

Oracle is an autonomous incident prediction and prevention system. It learns from project history, detects leading indicators, predicts likely incidents, recommends preventive actions, can execute safe actions automatically, and measures whether its predictions improve over time.

Oracle is intentionally lightweight: the prediction engine is pure Python and uses interpretable signal scoring instead of external ML frameworks.

## Install

```bash
pip install -e ".[dev]"
```

## CLI

```bash
oracle init
oracle train --incidents ./incidents
oracle predict
oracle predict --service payments
oracle watch
oracle prevent
oracle history
oracle accuracy
oracle dashboard
oracle serve --port 8000
oracle demo
```

## Demo

```bash
oracle demo
```

The demo simulates two weeks of a SaaS system. Week 1 trains Oracle on incidents caused by deploy risk, Redis saturation, DB migration failure, gateway saturation, and cache storms. Week 2 runs predictions, executes high-confidence prevention for Redis saturation, and prints an accuracy report.

## Architecture

- `oracle/core`: dataclass models and JSON storage
- `oracle/telemetry`: metric sources and collection
- `oracle/predictor`: leading indicators, causal projection, pattern matching, trend analysis, correlation scoring, deployment risk
- `oracle/prevention`: preventive action recommendation and execution
- `oracle/feedback`: prediction outcome tracking and accuracy metrics
- `oracle/causal`: CausalChain-style causal graph reasoning
- `oracle/dashboard`: API payload helpers
- `oracle/server`: FastAPI and WebSocket app
- `oracle/cli.py`: Click command line interface

## Development

```bash
pytest
```

