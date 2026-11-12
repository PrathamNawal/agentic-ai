"""Builds the A2UI messages for a stock quote card using the official a2ui-agent-sdk.

Protocol v0.9 is used because it is what the published renderers (@a2ui/lit,
@a2ui/react, @a2ui/angular 0.15) implement today.
"""

from a2ui.builder.v0_9 import Card, Column, DataBinding, Divider, Text
from a2ui.core.schema.v0_9 import (
    CreateSurface,
    CreateSurfaceMessage,
    UpdateComponents,
    UpdateComponentsMessage,
    UpdateDataModel,
    UpdateDataModelMessage,
)

BASIC_CATALOG = "https://a2ui.org/specification/v0_9/catalogs/basic/catalog.json"


def quote_card(surface_id: str, symbol: str, price: float, change: float, change_pct: float, currency: str) -> list[dict]:
    """Return the three A2UI messages that create and fill a quote card surface."""
    arrow = "▲" if change >= 0 else "▼"
    tree = Card(
        id="root",
        child=Column(
            children=[
                Text(text=DataBinding(path="/symbol"), variant="h2"),
                Text(text=DataBinding(path="/price"), variant="h1"),
                Divider(),
                Text(text=DataBinding(path="/change"), variant="body"),
            ]
        )
    )
    messages = [
        CreateSurfaceMessage(create_surface=CreateSurface(surface_id=surface_id, catalog_id=BASIC_CATALOG)),
        UpdateComponentsMessage(update_components=UpdateComponents(surface_id=surface_id, components=tree.flatten())),
        UpdateDataModelMessage(
            update_data_model=UpdateDataModel(
                surface_id=surface_id,
                value={
                    "symbol": symbol,
                    "price": f"{price:,.2f} {currency}",
                    "change": f"{arrow} {abs(change):,.2f} ({abs(change_pct):.2f}%)",
                },
            )
        ),
    ]
    return [m.model_dump(by_alias=True, exclude_none=True, mode="json") for m in messages]
