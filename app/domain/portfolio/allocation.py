def allocate_portfolio(
        scores: dict[str, float],
        seed_money: int,
        min_weight: float = 0.10,
        max_weight: float = 0.30,
) -> dict[str, dict[str, float | int]]:
    """
    점수 비례로 비중을 정하되 10~30% 범위를 벗어나면 고정하고
    나머지 종목끼리 점수 비례로 다시 나눈다 (수렴할 때까지 반복)
    5~7개 종목을 전재로 한다
    """

    fixed_weights: dict[str, float] = {}
    all_codes = set(scores)
    while True:
        flexible = {c: s for c, s in scores.items() if c not in fixed_weights}
        if not flexible:
            break
        flexible_score_total = sum(flexible.values())
        available_weight = 1.0 - sum(fixed_weights.values())
        proposed = {
            c: (s / flexible_score_total) * available_weight
            for c, s in flexible.items()
        }
        violated = False
        for c, w in proposed.items():
            if w > max_weight:
                fixed_weights[c] = max_weight
                violated = True
            elif w < min_weight:
                fixed_weights[c] = min_weight
                violated = True
        if not violated:
            fixed_weights.update(proposed)
            break

    # 반올림 오차 보정: 남는/모자란 원 단위를 가장 비중이 큰 종목에 몰아줌
    amounts = {c: round(seed_money * w) for c, w in fixed_weights.items()}
    diff = seed_money - sum(amounts.values())
    if diff:
        top_code = max(fixed_weights, key=fixed_weights.get)
        amounts[top_code] += diff
    return {
        c: {"ratio": round(fixed_weights[c] * 100, 2), "amount": amounts[c]}
        for c in all_codes
    }