from langgraph.graph import END, StateGraph

from backend.app.agents.state import AnalysisState
from backend.app.agents.review_collector import review_collector_agent
from backend.app.agents.fake_review_detector import fake_review_detector_agent
from backend.app.agents.seller_trust import seller_trust_agent
from backend.app.agents.price_analysis import price_analysis_agent
from backend.app.agents.final_recommendation import final_recommendation_agent


def build_analysis_graph():
    graph = StateGraph(AnalysisState)

    graph.add_node("review_collector", review_collector_agent)
    graph.add_node("fake_review_detector", fake_review_detector_agent)
    graph.add_node("seller_trust", seller_trust_agent)
    graph.add_node("price_analysis", price_analysis_agent)
    graph.add_node("final_recommendation", final_recommendation_agent)

    graph.set_entry_point("review_collector")

    graph.add_edge("review_collector", "fake_review_detector")
    graph.add_edge("fake_review_detector", "seller_trust")
    graph.add_edge("seller_trust", "price_analysis")
    graph.add_edge("price_analysis", "final_recommendation")
    graph.add_edge("final_recommendation", END)

    return graph.compile()