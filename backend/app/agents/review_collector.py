from backend.app.agents.state import AnalysisState
from backend.app.services.product_scraper_service import fetch_product_data


def review_collector_agent(state: AnalysisState) -> AnalysisState:
    product_data = fetch_product_data(
        product_url=state.get("product_url"),
        product_name=state.get("product_name"),
        seller_name=state.get("seller_name"),
    )

    state["product_name"] = product_data.get("product_name")
    state["product_url"] = product_data.get("product_url")
    state["seller_name"] = product_data.get("seller_name")
    state["reviews"] = product_data.get("reviews", [])

    return state