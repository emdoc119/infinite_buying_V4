import sys
import os
sys.path.append(os.getcwd())

from decimal import Decimal
from domain.models import StrategyParams, CycleState, CycleStatus, Position, OrderKind, Side
from strategy.infinite_buying_v4 import InfiniteBuyingV4Strategy
from strategy.state_machine import CycleStateMachine

def print_orders(tag, orders):
    print(f"\n--- {tag} ---")
    if not orders:
        print("No orders generated.")
    for o in orders:
        print(f"[{o.kind.value}] {o.side.value} {o.quantity} shares @ ${o.price:.2f} ({o.tag})")

strategy = InfiniteBuyingV4Strategy()
machine = CycleStateMachine()

params = StrategyParams(
    symbol="TQQQ",
    total_budget=Decimal('20000'),
    split_count=40,
    initial_loc_pct=Decimal('0.15'),
    sudden_drop_pct=Decimal('-0.10')
)

state = CycleState(params=params)

print("=== 1. T=0 초기 진입 (보유량 0) ===")
# Current price 50.00
buy_orders = strategy.build_buy_orders(state, Decimal('50.00'))
print_orders("T=0 Buy Orders", buy_orders)

print("\n=== 2. T=1 전반전 ===")
state.T = 1.0
state.position = Position(quantity=Decimal('10'), avg_price=Decimal('55.00'))
state.cash_remaining = Decimal('19450')
strategy.calculate_daily_indicators(state)
print(f"Star Pct: {state.current_star_pct*100}% | Star Price: {state.current_star_price:.2f}")
buy_orders = strategy.build_buy_orders(state, Decimal('50.00'))
sell_orders = strategy.build_sell_orders(state)
print_orders("T=1 Buy Orders", buy_orders)
print_orders("T=1 Sell Orders", sell_orders)

print("\n=== 3. T=21 후반전 ===")
state.T = 21.0
state.position = Position(quantity=Decimal('200'), avg_price=Decimal('50.00'))
state.cash_remaining = Decimal('10000')
strategy.calculate_daily_indicators(state)
print(f"Star Pct: {state.current_star_pct*100}% | Star Price: {state.current_star_price:.2f}")
buy_orders = strategy.build_buy_orders(state, Decimal('50.00'))
sell_orders = strategy.build_sell_orders(state)
print_orders("T=21 Buy Orders", buy_orders)
print_orders("T=21 Sell Orders", sell_orders)

print("\n=== 4. 리버스 모드 ===")
state.T = 40.0
state.reverse_mode = True
state.status = CycleStatus.REVERSE_MODE
state.current_5d_avg = Decimal('45.00')
state.reverse_sell_qty_unit = Decimal('10')
state.position = Position(quantity=Decimal('400'), avg_price=Decimal('60.00'))
state.cash_remaining = Decimal('400') # 잔금
buy_orders = strategy.build_buy_orders(state, Decimal('45.00'))
sell_orders = strategy.build_sell_orders(state)
print_orders("Reverse Mode Buy Orders", buy_orders)
print_orders("Reverse Mode Sell Orders", sell_orders)
