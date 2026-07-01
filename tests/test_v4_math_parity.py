import pytest
from decimal import Decimal
from domain.models import StrategyParams, CycleState, Position, OrderKind, Side, TickerType
from strategy.infinite_buying_v4 import InfiniteBuyingV4Strategy
import math

@pytest.fixture
def base_state():
    params = StrategyParams(
        symbol=TickerType.TQQQ,
        total_budget=Decimal('10000'),
        split_count=40,
        star_alpha=Decimal('0.10'),
        star_beta=Decimal('2.0')
    )
    return CycleState(
        params=params,
        cash_remaining=Decimal('10000')
    )

def test_t_value_and_star_calculation(base_state):
    strategy = InfiniteBuyingV4Strategy()
    
    # 예시: 시드 10000달러, 40분할 -> 1회 할당액 = 250달러
    # 평단가 25달러로 106.7주 보유 (약 2667.5달러 누적 투자)
    # T = 2667.5 / 250 = 10.67
    base_state.position = Position(quantity=Decimal('106.7'), avg_price=Decimal('25'))
    base_state.cash_remaining = Decimal('7332.5')
    
    strategy.calculate_daily_indicators(base_state)
    
    # 1. T값 검증
    assert math.isclose(base_state.T, 10.67, abs_tol=0.001)
    
    # 2. 별값 검증
    # TQQQ 40분할 기준 공식: 15% - (15/20)*T = 15 - 0.75*10.67 = 6.9975%
    # 코드는 비율값으로 나오므로 0.069975여야 함
    assert math.isclose(base_state.current_star_pct, 0.069975, abs_tol=0.0001)

def test_order_build_logic(base_state):
    strategy = InfiniteBuyingV4Strategy()
    
    # T = 1 인 상황 
    base_state.position = Position(quantity=Decimal('10'), avg_price=Decimal('25')) # 250불
    base_state.cash_remaining = Decimal('9750')
    
    orders = strategy.build_buy_orders(base_state, current_price=Decimal('25'))
    
    # orders should contain "절반 매수 (별지점)" and "절반 매수 (평단가)"
    tags = [o.tag for o in orders]
    assert "절반 매수 (별지점)" in tags
    assert "절반 매수 (평단가)" in tags

def test_t_value_with_zero_budget():
    params = StrategyParams(
        symbol=TickerType.TQQQ,
        total_budget=Decimal('0'),
        split_count=40
    )
    state = CycleState(params=params)
    state.position = Position(quantity=Decimal('10'), avg_price=Decimal('25'))
    
    strategy = InfiniteBuyingV4Strategy()
    # D가 0일 경우, division by zero가 발생하지 않아야 함
    strategy.calculate_daily_indicators(state)
    assert state.T == 0.0
