# VestBridge

**Let your agents trade on your terms.**

VestBridge is an open-source MCP server that connects AI agents to financial brokers — with built-in mandate enforcement and a complete audit trail.

Other MCP broker connectors let your agent trade with zero guardrails. VestBridge lets you define what your agent can and can't do, enforces it on every order, and logs everything.

- **Connect** — Unified tool schema for Robinhood, Interactive Brokers, Alpaca, and more
- **Authorize** — Define mandates: allowed assets, position limits, order size caps, time windows
- **Audit** — Append-only log of every action, agent-attributed, hash-chained, exportable
- **Local-first** — Broker credentials never leave your machine. No cloud dependency.

## Quick Start

```bash
pip install vestbridge
```

```json
// Claude Desktop — claude_desktop_config.json
{
  "mcpServers": {
    "vestbridge": {
      "command": "vestbridge",
      "args": ["--broker", "robinhood"]
    }
  }
}
```

## Mandate Example

```yaml
# ~/.vest/mandates/default.yaml
permissions:
  max_order_size_usd: 10000
  max_daily_notional_usd: 50000
  allowed_symbols: ["NVDA", "MSFT", "GOOG", "AAPL", "AMZN", "AVGO"]
  blocked_symbols: ["GME", "AMC"]
  max_concentration_pct: 20
  allowed_sides: ["buy", "sell"]
  allowed_order_types: ["market", "limit"]
  allowed_asset_types: ["equity"]
  trading_hours_only: true
```

Agent tries to put 40% in NVDA? Blocked. Tries to buy options when mandate says equities only? Blocked. Every check — pass or fail — is logged to an append-only audit trail.

## Audit Trail

Every action produces a structured log entry:

```json
{
  "event_id": "evt_a1b2c3",
  "timestamp": "2026-02-22T14:30:00.123Z",
  "agent_id": "agt_7f3a9b",
  "action": "place_order",
  "params": {"symbol": "NVDA", "qty": 70, "side": "buy"},
  "mandate_check": "FAIL",
  "mandate_reason": "would exceed 20% single-stock concentration",
  "prev_hash": "sha256:def456..."
}
```

Verify your audit trail integrity:

```bash
vest audit verify
```

## Supported Brokers

| Broker | Status |
|--------|--------|
| Robinhood | In Progress |
| Interactive Brokers | In Progress |
| Alpaca | Planned |
| Tradier | Planned |

## License

MIT
