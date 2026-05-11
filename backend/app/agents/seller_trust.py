from backend.app.agents.state import AnalysisState


def seller_trust_agent(state: AnalysisState) -> AnalysisState:
    seller_name = state.get("seller_name")

    if seller_name:
        seller_score = 68
        seller_analysis = (
            f"{seller_name} satıcısı için orta seviyede güven skoru hesaplandı. "
            "Kargo süresi, iletişim ve iade süreçleri dikkatle incelenmelidir."
        )
    else:
        seller_score = 55
        seller_analysis = (
            "Satıcı adı belirtilmediği için güven analizi sınırlı yapılabildi."
        )

    state["seller_score"] = seller_score
    state["seller_analysis"] = seller_analysis

    return state