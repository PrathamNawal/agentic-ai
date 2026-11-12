"""Builds an A2UI-style surface for a stock quote card.

The surface is a flat list of components plus a separate data model. Components
reference values by path (e.g. "/price"), so the numbers live in the data model,
not in the component tree. The message shapes follow the A2UI idea
(createSurface / updateComponents / updateDataModel) in simplified form; check
the official spec (https://a2ui.org/specification/) before depending on exact
field names.
"""

SURFACE_ID = "quote"


def quote_card(symbol: str, name: str, price: float, change: float, change_pct: float, currency: str) -> list[dict]:
    up = change >= 0
    components = [
        {"id": "root", "component": "Card", "child": "col"},
        {"id": "col", "component": "Column", "children": ["sym", "name", "price", "chg"]},
        {"id": "sym", "component": "Text", "variant": "h2", "text": {"path": "/symbol"}},
        {"id": "name", "component": "Text", "variant": "caption", "text": {"path": "/name"}},
        {"id": "price", "component": "Text", "variant": "h1", "text": {"path": "/priceLabel"}},
        {"id": "chg", "component": "Text", "variant": "up" if up else "down", "text": {"path": "/changeLabel"}},
    ]
    data = {
        "symbol": symbol,
        "name": name,
        "priceLabel": f"{price:,.2f} {currency}",
        "changeLabel": f"{'▲' if up else '▼'} {abs(change):,.2f} ({abs(change_pct):.2f}%)",
    }
    return [
        {"createSurface": {"surfaceId": SURFACE_ID}},
        {"updateComponents": {"surfaceId": SURFACE_ID, "components": components}},
        {"updateDataModel": {"surfaceId": SURFACE_ID, "value": data}},
    ]
