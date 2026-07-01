import math
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN
from datetime import date
from typing import List

from domain.models import StrategyParams, CycleState, OrderIntent, Side, OrderKind, CycleStatus

class InfiniteBuyingV4Strategy:
    """
    Quantstack V4.0 오피셜 로직 기반 전략 엔진.
    """
    
    def calculate_daily_indicators(self, state: CycleState):
        """매일 바뀌는 1회매수금, 별%, 별지점을 계산하여 상태에 캐싱"""
        splits = state.params.split_count
        # 0. T값 동적 수학적 계산
        D = state.params.total_budget / Decimal(str(splits))
        total_invested = state.position.quantity * state.position.avg_price
        if D > 0:
            state.T = float(total_invested / D)
        T = state.T
        
        # 1. 1회 매수금 (변동형)
        if float(splits) - T > 0:
            state.current_one_lot_budget = state.cash_remaining / Decimal(str(float(splits) - T))
        else:
            state.current_one_lot_budget = Decimal('0')
            
        # 2. 별% 계산 (파라미터화된 alpha, beta 적용)
        # alpha가 0.10 (10%)이고 beta가 2.0일 때, 10 - T/2(%)를 표현하기 위해 100으로 나눔
        state.current_star_pct = float(state.params.star_alpha) - (T / (float(state.params.star_beta) * 100))
            
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
                    
        # 폭락 대비 다중 매수: 전일종가 / (1.25, 1.50, 1.75, 2.00) × 1주
        if state.params.sudden_drop_pct < 0 and current_price > 0:
            crash_levels = [
                (Decimal('1.25'), '-20%'),
                (Decimal('1.50'), '-30%'),
                (Decimal('1.75'), '-40%'),
                (Decimal('2.00'), '-50%'),
            ]
            # sudden_drop_pct에 따라 건수 결정: -20%=1건, -30%=2건, -40%=3건, -50%=4건
            max_levels = 1
            if state.params.sudden_drop_pct <= Decimal('-0.30'): max_levels = 2
            if state.params.sudden_drop_pct <= Decimal('-0.40'): max_levels = 3
            if state.params.sudden_drop_pct <= Decimal('-0.50'): max_levels = 4
            
            for i in range(max_levels):
                divisor, label = crash_levels[i]
                crash_price = (current_price / divisor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
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
            # LOC 매도 수량: 매수와 대칭 (전반전=평단 매수수량, 후반전=별값 매수수량)
            loc_sell_qty = Decimal('0')
            
            if state.T < state.params.split_count / 2:
                # 전반전: LOC 매도 수량 = 당일 평단 LOC 매수 수량
                if state.current_star_price > 0 and state.position.avg_price > 0:
                    half_budget = budget / Decimal('2')
                    qty_star = Decimal(str(math.floor(half_budget / state.current_star_price)))
                    total_buyable = Decimal(str(math.floor(budget / state.position.avg_price)))
                    loc_sell_qty = total_buyable - qty_star
            else:
                # 후반전: LOC 매도 수량 = 당일 별값 LOC 매수 수량 (1회 전체)
                if state.current_star_price > 0:
                    loc_sell_qty = Decimal(str(math.floor(budget / state.current_star_price)))
            
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

