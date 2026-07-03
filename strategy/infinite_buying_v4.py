import math
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
from datetime import date
from typing import List

from domain.models import StrategyParams, CycleState, OrderIntent, Side, OrderKind, CycleStatus

class InfiniteBuyingV4Strategy:
    """
    Quantstack V4.0 오피셜 로직 기반 전략 엔진.
    """
    
    def calculate_crash_reserve(self, state: CycleState) -> Decimal:
        """폭락장 대비 예산 계산 (진입가 기준 -20%, -30%, -40%, -50% 등 각 단계별 1주 금액 합산)"""
        base_price = Decimal('0')
        if state.first_buy_price > Decimal('0'):
            base_price = state.first_buy_price
        elif state.position.avg_price > Decimal('0'):
            base_price = state.position.avg_price
        else:
            if state.current_5d_avg > Decimal('0'):
                base_price = state.current_5d_avg
            else:
                if state.params.symbol.value == "SOXL":
                    base_price = Decimal('50.00')
                else:
                    base_price = Decimal('80.00')
                    
        drop_pct = state.params.sudden_drop_pct
        if drop_pct >= 0:
            return Decimal('0')
            
        multipliers = []
        if drop_pct <= Decimal('-0.20'):
            multipliers.append(Decimal('0.80'))
        if drop_pct <= Decimal('-0.30'):
            multipliers.append(Decimal('0.70'))
        if drop_pct <= Decimal('-0.40'):
            multipliers.append(Decimal('0.60'))
        if drop_pct <= Decimal('-0.50'):
            multipliers.append(Decimal('0.50'))
            
        reserve = sum(base_price * m for m in multipliers)
        return reserve.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def calculate_daily_indicators(self, state: CycleState):
        """매일 바뀌는 1회매수금, 별%, 별지점을 계산하여 상태에 캐싱"""
        splits = state.params.split_count
        # T값은 상태머신(state_machine.py)에서 Action 기반으로 관리하므로 직접 재계산하지 않습니다.
        # 단, T가 0이고 보유량이 있는 비정상 상황이거나, 초기 동기화 시점에만 보조적으로 추정합니다.
        if state.T == 0.0 and state.position.quantity > 0:
            D = state.params.total_budget / Decimal(str(splits))
            if D > 0:
                total_invested = state.position.quantity * state.position.avg_price
                state.T = float(total_invested / D)
        T = state.T
        
        # 1. 1회 매수금 (변동형, 폭락 대비 금액을 차감한 후 계산)
        crash_reserve = self.calculate_crash_reserve(state)
        available_cash = max(Decimal('0'), state.cash_remaining - crash_reserve)
        
        if float(splits) - T > 0:
            state.current_one_lot_budget = available_cash / Decimal(str(float(splits) - T))
        else:
            state.current_one_lot_budget = Decimal('0')
            
        # 2. 별% 계산 (V4.0 공식: T가 splits / 2에 가까워질수록 별%가 0%로 선형 감소)
        star_alpha = state.params.star_alpha
        # 기본값 0.10(10%)인 경우 종목에 맞춰 TQQQ는 15%, SOXL은 20%로 자동 보정
        if star_alpha == Decimal('0.10'):
            if state.params.symbol.value == "SOXL":
                star_alpha = Decimal('0.20')
            elif state.params.symbol.value == "TQQQ":
                star_alpha = Decimal('0.15')
        
        half_splits = float(splits) / 2.0
        if half_splits > 0:
            state.current_star_pct = float(star_alpha) * (1.0 - T / half_splits)
        else:
            state.current_star_pct = float(star_alpha)
            
        # 3. 별지점 계산
        if state.reverse_mode:
            raw_star = state.current_5d_avg
        elif state.position.quantity > 0:
            raw_star = state.position.avg_price * Decimal(str(1 + state.current_star_pct))
        else:
            raw_star = Decimal('0')
            
        state.current_star_price = raw_star.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

    def build_buy_orders(self, state: CycleState, current_price: Decimal) -> List[OrderIntent]:
        if state.status != CycleStatus.RUNNING and state.status != CycleStatus.REVERSE_MODE:
            return []
            
        self.calculate_daily_indicators(state)
        orders = []
        budget = state.current_one_lot_budget
        
        if state.reverse_mode:
            if state.current_star_price > 0 and state.cash_remaining > 0:
                buy_budget = state.cash_remaining / Decimal('4')
                qty = math.floor(buy_budget / state.current_star_price)
                if qty > 0:
                    orders.append(OrderIntent(
                        symbol=state.params.symbol, side=Side.BUY, kind=OrderKind.LOC,
                        price=state.current_star_price - Decimal('0.01'), quantity=Decimal(qty), tag="리버스 쿼터매수 (별지점 아래)"
                    ))
            return orders
        orders = []
        budget = state.current_one_lot_budget
        
        if state.T == 0 and state.position.quantity == 0:
            # 첫날(T=0) 진입 매수 (LOC 큰수 매수)
            base_one_shot_budget = state.params.total_budget / Decimal(str(state.params.split_count))
            big_multiplier = Decimal('1') + state.params.initial_loc_pct
            first_loc_price = current_price * big_multiplier
            qty = math.floor(base_one_shot_budget / first_loc_price)
            
            if qty > 0:
                pct_str = int(state.params.initial_loc_pct * 100)
                orders.append(OrderIntent(
                    symbol=state.params.symbol, side=Side.BUY, kind=OrderKind.LOC,
                    price=first_loc_price, quantity=Decimal(str(qty)), tag=f"큰수 매수 (+{pct_str}%)"
                ))
        elif state.T < state.params.split_count / 2:
            # 전반전: 전체 매수 가능 수량에서 별지점 매수 수량을 뺀 나머지를 평단가 매수
            half_budget = budget / Decimal('2')
            
            qty_star = 0
            if state.current_star_price > 0:
                qty_star = math.floor(half_budget / state.current_star_price)
                if qty_star > 0:
                    orders.append(OrderIntent(
                        symbol=state.params.symbol, side=Side.BUY, kind=OrderKind.LOC, 
                        price=state.current_star_price - Decimal('0.01'), quantity=Decimal(qty_star), tag="절반 매수 (별지점)"
                    ))
            
            if state.position.avg_price > 0:
                total_buyable = math.floor(budget / state.position.avg_price)
                qty_avg = total_buyable - qty_star
                if qty_avg > 0:
                    orders.append(OrderIntent(
                        symbol=state.params.symbol, side=Side.BUY, kind=OrderKind.LOC, 
                        price=state.position.avg_price, quantity=Decimal(qty_avg), tag="절반 매수 (평단가)"
                    ))
        else:
            # 후반전: 1회 매수금 전체 별지점 매수
            if state.current_star_price > 0:
                qty = math.floor(budget / state.current_star_price)
                if qty > 0:
                    orders.append(OrderIntent(
                        symbol=state.params.symbol, side=Side.BUY, kind=OrderKind.LOC, 
                        price=state.current_star_price - Decimal('0.01'), quantity=Decimal(qty), tag="1회 매수 (별지점)"
                    ))
                    
        # 폭락 대비 다중 매수: 진입가 기준 -20%, -30%, -40%, -50% 지점에 1주씩
        if state.params.sudden_drop_pct < 0:
            base_price = Decimal('0')
            if state.first_buy_price > Decimal('0'):
                base_price = state.first_buy_price
            elif state.position.avg_price > Decimal('0'):
                base_price = state.position.avg_price
            else:
                if state.current_5d_avg > Decimal('0'):
                    base_price = state.current_5d_avg
                else:
                    if state.params.symbol.value == "SOXL":
                        base_price = Decimal('50.00')
                    else:
                        base_price = Decimal('80.00')

            levels = []
            if state.params.sudden_drop_pct <= Decimal('-0.20'):
                levels.append((Decimal('0.80'), '-20%'))
            if state.params.sudden_drop_pct <= Decimal('-0.30'):
                levels.append((Decimal('0.70'), '-30%'))
            if state.params.sudden_drop_pct <= Decimal('-0.40'):
                levels.append((Decimal('0.60'), '-40%'))
            if state.params.sudden_drop_pct <= Decimal('-0.50'):
                levels.append((Decimal('0.50'), '-50%'))

            for multiplier, label in levels:
                crash_price = (base_price * multiplier).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                orders.append(OrderIntent(
                    symbol=state.params.symbol, side=Side.BUY, kind=OrderKind.LOC,
                    price=crash_price, quantity=Decimal('1'), tag=f"폭락 대비 ({label})"
                ))
                    
        return orders

    def build_sell_orders(self, state: CycleState) -> List[OrderIntent]:
        if (state.status != CycleStatus.RUNNING and state.status != CycleStatus.REVERSE_MODE) or state.position.quantity <= 0:
            return []
            
        self.calculate_daily_indicators(state)
        orders = []
        budget = state.current_one_lot_budget
        
        if state.reverse_mode:
            sell_qty = state.reverse_sell_qty_unit
            if sell_qty > 0 and state.current_star_price > 0:
                orders.append(OrderIntent(
                    symbol=state.params.symbol, side=Side.SELL, kind=OrderKind.LOC,
                    price=state.current_star_price, quantity=Decimal(math.floor(sell_qty)), tag="리버스 무한매도 (별지점 위)"
                ))
            return orders
            
        total_qty = state.position.quantity
        if total_qty > 0:
            # LOC 매도 수량: 보유 수량의 25% (1/4)
            loc_sell_qty = (total_qty * Decimal('0.25')).quantize(Decimal('1'), rounding=ROUND_DOWN)
            if loc_sell_qty < Decimal('1') and total_qty > 0:
                loc_sell_qty = Decimal('1')
            
            # 안전장치: 매도 수량이 보유 수량 초과 방지
            loc_sell_qty = min(loc_sell_qty, total_qty)
            rest_qty = total_qty - loc_sell_qty
            
            # 1. LOC 매도 (별지점)
            if loc_sell_qty > 0 and state.current_star_price > 0:
                orders.append(OrderIntent(
                    symbol=state.params.symbol, side=Side.SELL, kind=OrderKind.LOC,
                    price=state.current_star_price, quantity=loc_sell_qty, tag=f"LOC 매도 (☆{(state.current_star_pct*100):.1f}%)"
                ))
                
            # 2. 지정가 익절 (나머지 전량)
            if rest_qty > 0:
                tp_target = Decimal('1.20') if state.params.symbol.upper() == "SOXL" else Decimal('1.15')
                take_profit_price = (state.position.avg_price * tp_target).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                pct_str = "+20%" if state.params.symbol.upper() == "SOXL" else "+15%"
                orders.append(OrderIntent(
                    symbol=state.params.symbol, side=Side.SELL, kind=OrderKind.LIMIT,
                    price=take_profit_price, quantity=rest_qty, tag=f"지정가 익절 ({pct_str})"
                ))
            
        return orders

