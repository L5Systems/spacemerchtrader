# Starfall Space Merchandise Handling Co.

Interstellar merchandise handling platform with a FastAPI core and autonomous handling agents.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn starfall.main:app --reload
```

On Windows with corporate SSL interception, copy [`pip.ini.example`](pip.ini.example) to `.venv/pip.ini` after creating the venv. That file stays local and is ignored by git.

Open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive API.

Optional infrastructure:

```bash
cp .env.example .env
docker compose up -d   # PostgreSQL + Redis
```

## Architecture

```
starfall/          # Core API (FastAPI + SQLAlchemy)
agents/            # Handling agents (pricing, inventory, routing)
```

### Order pipeline

When you `POST /orders`, agents run automatically:

1. **Pricing Agent** — sets unit price, handling fee, total credits
2. **Inventory Agent** — reserves warehouse stock (sell orders)
3. **Routing Agent** — assigns route, carrier, ETA, and freight cost

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/markets/{system_id}/prices` | Market prices by star system |
| GET | `/routes/quote?origin=&dest=&qty=` | Freight quote |
| GET | `/warehouses/{id}/stock` | Warehouse inventory |
| POST | `/orders` | Place order (triggers agent pipeline) |
| GET | `/orders/{id}` | Order status |
| GET | `/orders/{id}/shipment` | Shipment details |
| GET | `/agents` | List available agents |
| POST | `/agents/{id}/run` | Manually trigger an agent |
| GET | `/agents/runs/{id}` | Agent run audit log |

### Demo data

Seeded on startup with three systems (`sol`, `vega`, `kepler`), products, warehouses, routes, and market prices.

## Example: place a sell order

```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "trader-aurora-7",
    "order_type": "sell",
    "product_id": "alloy",
    "quantity": 10,
    "origin_system_id": "sol",
    "destination_system_id": "vega"
  }'
```

Then check shipment:

```bash
curl http://localhost:8000/orders/<order_id>/shipment
```

## Agents

| Agent | Role |
|-------|------|
| `pricing` | Computes buy/sell price and handling fees |
| `inventory` | Reserves stock at origin warehouse |
| `routing` | Plans route and creates shipment |

Each run is logged in `agent_runs` with input, output, and reasoning.

## Next steps

- ~~Trader portal (Next.js)~~ → Svelte 5 demo client in `apps/demo-client`
- Procurement, clearance, and customer agents
- Webhooks (`order.routed`, `shipment.updated`)
- PostgreSQL + Redis job queue for async agent runs

## Demo client (Svelte 5)

```bash
# Terminal 1 — API
uvicorn starfall.main:app --reload

# Terminal 2 — client
cd apps/demo-client && npm install && npm run dev
```

See [apps/demo-client/README.md](apps/demo-client/README.md).
