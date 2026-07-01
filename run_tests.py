import math
from decimal import Decimal
from domain.models import StrategyParams, CycleState, Position, OrderKind, Side, TickerType
from strategy.infinite_buying_v4 import InfiniteBuyingV4Strategy

def run_tests():
    params = StrategyParams(
        symbol=TickerType.TQQQ,
        total_budget=Decimal('10000'),
        split_count=40,
        star_alpha=Decimal('0.10'),
        star_beta=Decimal('2.0')
    )
    base_state = CycleState(
        params=params,
        cash_remaining=Decimal('10000')
    )
    
    strategy = InfiniteBuyingV4Strategy()
    
    # 1. T값 검증
    base_state.position = Position(quantity=Decimal('106.7'), avg_price=Decimal('25'))
    base_state.cash_remaining = Decimal('7332.5')
    strategy.calculate_daily_indicators(base_state)
    assert math.isclose(base_state.T, 10.67, abs_tol=0.001), f"T is {base_state.T}"
    assert math.isclose(base_state.current_star_pct, 0.04665, abs_tol=0.0001), f"Star is {base_state.current_star_pct}"
    
    # 2. T=0 예산
    params2 = StrategyParams(
        symbol=TickerType.TQQQ,
        total_budget=Decimal('0'),
        split_count=40
    )
    state2 = CycleState(params=params2)
    state2.position = Position(quantity=Decimal('10'), avg_price=Decimal('25'))
    strategy.calculate_daily_indicators(state2)
    assert state2.T == 0.0, f"T is {state2.T}"
    
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    run_tests()
