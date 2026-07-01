import pytest
from decimal import Decimal
from datetime import date
from domain.models import StrategyParams, CycleState, FillEvent, Side, TickerType, Position
from strategy.state_machine import CycleStateMachine

def test_determine_fill_action_normal_buy():
    machine = CycleStateMachine()
    
    # 40분할 TQQQ 설정
    params = StrategyParams(
        symbol=TickerType.TQQQ,
        total_budget=Decimal('10000'),
        split_count=40,
        star_alpha=Decimal('0.10'),
        star_beta=Decimal('2.0')
    )
    state = CycleState(params=params)
    
    # 1. 첫 진입 (T=0, quantity=0)
    fill1 = FillEvent(symbol="TQQQ", side=Side.BUY, price=Decimal("50"), quantity=Decimal("5"), trade_date=date(2023, 10, 1))
    action1 = machine.determine_fill_action(state, fill1)
    assert action1 == "first_buy"
    
    # 첫 진입 액션 반영 (T = 1.0)
    state = machine.process_action(state, action1, fill1.price, fill1.quantity, update_fills=False)
    assert state.T == 1.0
    assert state.position.quantity == 5
    
    # 2. 전반전 진행 중 (T=1.0)
    # T=1일 때 1회매수 예산 = 9750 / 39 = 250
    # 별% = (15 - 0.75) % = 14.25%
    # 별지점 = 50 * 1.1425 = 57.125
    # 절반 예산 = 125.
    # qty_star = floor(125 / 57.125) = 2
    # qty_avg = floor(125 / 50) = 2
    # total_buyable = 4
    
    # 만약 2주만 매수했다면 (절반 매수)
    fill2 = FillEvent(symbol="TQQQ", side=Side.BUY, price=Decimal("50"), quantity=Decimal("2"), trade_date=date(2023, 10, 2))
    action2 = machine.determine_fill_action(state, fill2)
    assert action2 == "half_buy"
    
    state = machine.process_action(state, action2, fill2.price, fill2.quantity, update_fills=False)
    assert state.T == 1.5
    
    # 만약 4주를 매수했다면 (전체 매수)
    fill3 = FillEvent(symbol="TQQQ", side=Side.BUY, price=Decimal("50"), quantity=Decimal("4"), trade_date=date(2023, 10, 3))
    action3 = machine.determine_fill_action(state, fill3)
    assert action3 == "full_buy"

def test_determine_fill_action_sell():
    machine = CycleStateMachine()
    
    params = StrategyParams(
        symbol=TickerType.TQQQ,
        total_budget=Decimal('10000'),
        split_count=40
    )
    state = CycleState(params=params)
    state.position = Position(quantity=Decimal("100"), avg_price=Decimal("50"))
    state.T = 15.0
    
    # 1. 쿼터 매도 (25주)
    fill_sell1 = FillEvent(symbol="TQQQ", side=Side.SELL, price=Decimal("55"), quantity=Decimal("25"), trade_date=date(2023, 10, 4))
    action_sell1 = machine.determine_fill_action(state, fill_sell1)
    assert action_sell1 == "quarter_sell"
    
    # 2. 전량 익절 (95주 - 보유수량 100주 대비 90% 이상인 95주 판매)
    fill_sell2 = FillEvent(symbol="TQQQ", side=Side.SELL, price=Decimal("60"), quantity=Decimal("95"), trade_date=date(2023, 10, 5))
    action_sell2 = machine.determine_fill_action(state, fill_sell2)
    assert action_sell2 == "take_profit"
