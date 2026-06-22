from sqlalchemy.orm import Session

from starfall.models import MarketPrice, Product, Route, StarSystem, StockItem, Warehouse


def seed_demo_data(db: Session) -> None:
    if db.query(StarSystem).first():
        return

    systems = [
        StarSystem(id="sol", name="Sol Expanse", risk_level=0.05),
        StarSystem(id="vega", name="Vega Reach", risk_level=0.12),
        StarSystem(id="kepler", name="Kepler Rim", risk_level=0.22),
    ]
    db.add_all(systems)

    products = [
        Product(id="hydro", sku="SF-H2O-01", name="Purified Ice Blocks", category="life-support", base_price=120.0),
        Product(id="alloy", sku="SF-ALY-02", name="Titanium Alloy Ingots", category="industrial", base_price=480.0),
        Product(id="spice", sku="SF-SPC-03", name="Nebula Spice Crates", category="luxury", base_price=920.0),
    ]
    db.add_all(products)

    warehouses = [
        Warehouse(id="wh-sol-dock", name="Sol Orbital Dock", system_id="sol", station="High Orbit Terminal"),
        Warehouse(id="wh-vega-hub", name="Vega Trade Hub", system_id="vega", station="Vega Station Alpha"),
        Warehouse(id="wh-kepler-yard", name="Kepler Rim Yard", system_id="kepler", station="Outer Rim Depot"),
    ]
    db.add_all(warehouses)

    stock = [
        StockItem(warehouse_id="wh-sol-dock", product_id="hydro", quantity=500, reserved=0),
        StockItem(warehouse_id="wh-sol-dock", product_id="alloy", quantity=200, reserved=0),
        StockItem(warehouse_id="wh-vega-hub", product_id="spice", quantity=80, reserved=0),
        StockItem(warehouse_id="wh-vega-hub", product_id="alloy", quantity=150, reserved=0),
        StockItem(warehouse_id="wh-kepler-yard", product_id="hydro", quantity=60, reserved=0),
    ]
    db.add_all(stock)

    routes = [
        Route(id="rt-sol-vega", origin_system_id="sol", destination_system_id="vega", jump_lanes="Sol → Altair → Vega", base_days=4, base_cost=180.0, risk_multiplier=1.0),
        Route(id="rt-vega-kepler", origin_system_id="vega", destination_system_id="kepler", jump_lanes="Vega → Deneb → Kepler", base_days=6, base_cost=260.0, risk_multiplier=1.3),
        Route(id="rt-sol-kepler", origin_system_id="sol", destination_system_id="kepler", jump_lanes="Sol → Sirius → Kepler", base_days=9, base_cost=410.0, risk_multiplier=1.6),
        Route(id="rt-kepler-sol", origin_system_id="kepler", destination_system_id="sol", jump_lanes="Kepler → Sirius → Sol", base_days=10, base_cost=430.0, risk_multiplier=1.7),
    ]
    db.add_all(routes)

    prices = [
        MarketPrice(product_id="hydro", system_id="sol", buy_price=118.0, sell_price=132.0),
        MarketPrice(product_id="alloy", system_id="sol", buy_price=470.0, sell_price=505.0),
        MarketPrice(product_id="spice", system_id="sol", buy_price=910.0, sell_price=980.0),
        MarketPrice(product_id="hydro", system_id="vega", buy_price=145.0, sell_price=160.0),
        MarketPrice(product_id="alloy", system_id="vega", buy_price=455.0, sell_price=490.0),
        MarketPrice(product_id="spice", system_id="vega", buy_price=880.0, sell_price=950.0),
        MarketPrice(product_id="hydro", system_id="kepler", buy_price=210.0, sell_price=235.0),
        MarketPrice(product_id="alloy", system_id="kepler", buy_price=620.0, sell_price=670.0),
        MarketPrice(product_id="spice", system_id="kepler", buy_price=1200.0, sell_price=1280.0),
    ]
    db.add_all(prices)
    db.commit()
