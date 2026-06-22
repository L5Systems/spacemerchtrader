# Starfall Demo Client (Svelte 5)

Interactive demo UI for exercising the Starfall API.

## Prerequisites

- Node.js 20+ (Vite 6 / Svelte 5 require Node 18+; system Node 12 will not work)
- Starfall API running on port 8000

If your system Node is old, use [nvm](https://github.com/nvm-sh/nvm):

```bash
nvm install    # reads .nvmrc → Node 20
```

## Run

Terminal 1 — API:

```bash
cd ../..
source .venv/bin/activate
uvicorn starfall.main:app --reload
```

Terminal 2 — demo client:

```bash
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

Vite proxies `/api/*` → `http://127.0.0.1:8000/*`, so the default API base URL `/api` works out of the box.

## Features

| Panel | Endpoint(s) |
|-------|-------------|
| Market Prices | `GET /markets/{system}/prices` |
| Route Quote | `GET /routes/quote` |
| Warehouse Stock | `GET /warehouses/{id}/stock` |
| Place Order | `POST /orders` (+ auto shipment fetch) |
| Order Lookup | `GET /orders/{id}`, `GET /orders/{id}/shipment` |
| Handling Agents | `GET /agents`, `POST /agents/{id}/run` |

Use **Run full demo** to hit health, market, route, stock, agents, and place a sample sell order in one click.

## Custom API URL

Change the **API base URL** field to point at a remote server (e.g. `http://192.168.1.10:8000`). CORS must allow your origin — the API permits `localhost:5173` by default.
