def calculate_overall_score(
    fake_review_score: int,
    seller_score: int,
    price_risk_score: int,
) -> int:
    review_score = 100 - fake_review_score
    price_score = 100 - price_risk_score

    overall_score = (
        review_score * 0.30
        + seller_score * 0.30
        + price_score * 0.40
    )

    return round(overall_score)


def recommendation_from_score(score: int) -> str:
    if score < 40:
        return "Riskli. Satın almadan önce dikkatli incelenmeli."
    if score < 70:
        return "Dikkatli satın alınmalı."
    return "Güvenilir görünüyor."