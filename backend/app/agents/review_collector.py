from backend.app.agents.state import AnalysisState
from backend.app.services.scrape_orchestrator_service import collect_all_product_data


def review_collector_agent(state: AnalysisState) -> AnalysisState:
    product_data = collect_all_product_data(
        product_url=state.get("product_url"),
        product_name=state.get("product_name"),
        seller_name=state.get("seller_name"),
        search_mode=state.get("search_mode", "fast"),
    )

    state["analysis_scope"] = product_data.get("analysis_scope")
    state["product_name"] = product_data.get("product_name")
    state["product_url"] = product_data.get("product_url")
    state["seller_name"] = product_data.get("seller_name")
    state["price"] = product_data.get("price")

    state["reviews"] = product_data.get("reviews", [])
    state["review_count"] = product_data.get("review_count", 0)
    state["review_sources"] = product_data.get("review_sources", [])
    state["source_review_counts"] = product_data.get("source_review_counts", {})
    state["source_links"] = product_data.get("source_links", {})
    state["review_sample_target"] = product_data.get("review_sample_target", 0)
    state["review_sample_minimum"] = product_data.get("review_sample_minimum", 0)

    state["complaints"] = product_data.get("complaints", [])
    state["complaint_count"] = product_data.get("complaint_count", 0)
    state["complaint_sources"] = product_data.get("complaint_sources", [])
    state["complaint_scope"] = product_data.get("complaint_scope")
    state["complaint_query"] = product_data.get("complaint_query")
    state["price_history"] = product_data.get("price_history", [])
    state["price_sources"] = product_data.get("price_sources", [])
    state["price_history_source"] = product_data.get("price_history_source")
    state["price_history_days"] = product_data.get("price_history_days", 0)
    state["price_history_is_estimated"] = product_data.get("price_history_is_estimated", False)
    state["current_market_prices"] = product_data.get("current_market_prices", [])
    state["price_search_url"] = product_data.get("price_search_url")
    state["price_search_urls"] = product_data.get("price_search_urls", {})
    state["seller_info"] = product_data.get("seller_info", {})

    return state
