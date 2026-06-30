from decimal import Decimal
from datetime import date
import pytest

from domain.models import StrategyParams, CycleState, FillEvent, Side, OrderKind, CycleStatus
from strategy.infinite_buying_v4 import InfiniteBuyingV4Strategy
from strategy.state_machine import CycleStateMachine

@pytest.fixture
def params():
    return StrategyParams(
        symbol="TQQQ",
        total_budget=Decimal("10000"),
        split_count=40,
        star_pct=Decimal("0.15"),
        loc_buffer_pct=Decimal("0.12"),
        take_profit_pct=Decimal("0.10"),
        max_loss_pct_for_reset=Decimal("-0.10"),
        loc_shares_per_line=1
    )

@pytest.fixture
def cycle(params):
    return CycleState(params=params)

@pytest.fixture
def strategy():
    return InfiniteBuyingV4Strategy()

@pytest.fixture
def machine():
    return CycleStateMachine()


def test_build_buy_orders_initial_and_subsequent(strategy, cycle):
    # 1. 첫 진입 시 (보유수량 없음)
    # T=0, 잔여예산=10000 -> 1회매수금=250.
    # avg_price=0 이므로 LOC평단은 안 나오고, 버퍼매수만 나옴 (기준가에 따라 다를 수 있으나, 일반적으로 첫 매수는 종가 또는 시장가 등으로 직접 처리함. V4앱 로직상으로는 avg_price 0일 때 예외처리됨)
    trade_date = date(2023, 10, 1)
    orders = strategy.build_buy_orders(cycle, trade_date, ref_price_for_buffer=Decimal("50"))
    
    assert len(orders) == 1
    assert orders[0].tag == "LOC_BUFFER_BUY"
    assert orders[0].price == Decimal("50") * (Decimal("1") + cycle.params.loc_buffer_pct)  # 56
    # half_budget = 125, price = 56, qty = floor(125/56) = 2
    assert orders[0].quantity == Decimal("2")

    # 2. 체결 후 진행 상황 임의 설정
    cycle.position.avg_price = Decimal("50")
    cycle.position.quantity = Decimal("5")
    cycle.T = 1
    cycle.cash_remaining = Decimal("9750") # 임의 잔금
    
    # 남은 분할 = 39, 잔금 = 9750 -> 1회 매수금 = 250, half_budget = 125
    orders2 = strategy.build_buy_orders(cycle, trade_date, ref_price_for_buffer=Decimal("52"))
    
    # 평단 50, 버퍼가 52*1.12 = 58.24
    assert len(orders2) == 2
    tags = [o.tag for o in orders2]
    assert "LOC_AVG_BUY" in tags
    assert "LOC_BUFFER_BUY" in tags

def test_apply_buy_fills(machine, cycle):
    # 매수 체결 적용 후 T증가 및 평단가 계산 확인
    fills = [
        FillEvent(symbol="TQQQ", side=Side.BUY, price=Decimal("50"), quantity=Decimal("2"), trade_date=date(2023, 10, 1)),
        FillEvent(symbol="TQQQ", side=Side.BUY, price=Decimal("40"), quantity=Decimal("3"), trade_date=date(2023, 10, 1)),
    ]
    
    updated_cycle = machine.apply_fills(cycle, fills)
    
    # 50*2 + 40*3 = 100 + 120 = 220
    # qty = 5
    # avg_price = 44
    assert updated_cycle.position.quantity == Decimal("5")
    assert updated_cycle.position.avg_price == Decimal("44")
    assert updated_cycle.T == 2
    assert updated_cycle.cash_remaining == Decimal("10000") - Decimal("220")

def test_apply_sell_fill_waiting_reset(machine, cycle):
    # 전량 매도 후 WAITING_RESET 전환
    cycle.position.quantity = Decimal("10")
    cycle.position.avg_price = Decimal("50")
    cycle.T = 10
    cycle.cash_remaining = Decimal("5000")
    
    fills = [
        FillEvent(symbol="TQQQ", side=Side.SELL, price=Decimal("55"), quantity=Decimal("10"), trade_date=date(2023, 10, 2))
    ]
    
    updated_cycle = machine.apply_fills(cycle, fills)
    
    assert updated_cycle.position.quantity == Decimal("0")
    assert updated_cycle.position.avg_price == Decimal("0")
    assert updated_cycle.T == 0
    assert updated_cycle.status == CycleStatus.WAITING_RESET
    assert updated_cycle.cash_remaining == Decimal("5000") + Decimal("550")

def test_evaluate_after_close_reverse_mode(machine, cycle):
    # 잔금 5% 이하, 손익 -10% 미만 -> 리버스 모드
    cycle.cash_remaining = Decimal("400") # 4%
    cycle.position.quantity = Decimal("100")
    cycle.position.avg_price = Decimal("100") # 매입금 10000, 이미 손실 상황
    
    # 종가 80 -> 평가금 = 8000 + 400 = 8400
    # 손실 = -1600 / 10000 = -16% -> max_loss_pct_for_reset(-10%) 보다 심함 -> 리버스
    last_close = Decimal("80")
    
    updated_cycle = machine.evaluate_after_close(cycle, last_close)
    
    assert updated_cycle.reverse_mode is True
    assert updated_cycle.status == CycleStatus.REVERSE

def test_evaluate_after_close_reset(machine, cycle):
    # 잔금 5% 이하, 손익 -5% (max_loss_pct_for_reset 이상) -> 리셋 후 RUNNING
    cycle.cash_remaining = Decimal("400") # 4%
    cycle.position.quantity = Decimal("100")
    cycle.position.avg_price = Decimal("100")
    
    # 종가 91 -> 평가금 = 9100 + 400 = 9500
    # 손실 = -500 / 10000 = -5% -> max_loss_pct 이상이므로 리셋
    last_close = Decimal("91")
    
    updated_cycle = machine.evaluate_after_close(cycle, last_close)
    
    assert updated_cycle.reverse_mode is False
    assert updated_cycle.status == CycleStatus.WAITING_RESET
    assert updated_cycle.position.quantity == Decimal("0")
    assert updated_cycle.position.avg_price == Decimal("0")
    assert updated_cycle.T == 0
