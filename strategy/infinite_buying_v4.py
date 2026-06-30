import math
from decimal import Decimal, ROUND_HALF_UP
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
        T = state.T
        
        # 1. 1회 매수금 (변동형)
        if splits - T > 0:
            state.current_one_lot_budget = state.cash_remaining / Decimal(str(splits - T))
        else:
            state.current_one_lot_budget = Decimal('0')
            
        # 2. 별% 계산 (TQQQ vs SOXL)
        symbol = state.params.symbol.upper()
        
        if symbol == "SOXL":
            tp_base = Decimal('0.20')
            if splits == 40:
                state.current_star_pct = tp_base - (Decimal('0.01') * Decimal(str(T)))
            else: # 20분할
                state.current_star_pct = tp_base - (Decimal('0.02') * Decimal(str(T)))
        else: # Default TQQQ
            tp_base = Decimal('0.15')
            if splits == 40:
                state.current_star_pct = tp_base - (Decimal('0.0075') * Decimal(str(T)))
            else: # 20분할
                state.current_star_pct = tp_base - (Decimal('0.015') * Decimal(str(T)))
            
        # 3. 별지점 계산
        if state.reverse_mode:
            raw_star = state.current_5d_avg
        elif state.position.quantity > 0:
            raw_star = state.position.avg_price * Decimal(str(1 + state.current_star_pct))
        else:
            raw_star = Decimal('0')
            
        state.current_star_price = raw_star.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

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
                    
        # 폭락 대비 다중 매수 (영혼법) - 1회 매수금 / N
        if state.params.sudden_drop_pct < 0:
            budget_per_day = state.params.total_budget / Decimal(str(state.params.split_count))
            
            crash_count = 0
            for n in range(1, 100):
                if crash_count >= 6:
                    break
                    
                crash_price = budget_per_day / Decimal(str(n))
                
                # 계산된 가격이 전일 종가보다 낮을 때만 유효한 '폭락 대비' 매수임
                if crash_price < current_price:
                    drop_pct = ((crash_price - current_price) / current_price) * 100
                    # 반올림하여 정수 퍼센트로 태그 생성
                    drop_pct_int = int(round(float(drop_pct)))
                    orders.append(OrderIntent(
                        symbol=state.params.symbol, side=Side.BUY, kind=OrderKind.LOC,
                        price=crash_price, quantity=Decimal('1'), tag=f"폭락 대비 매수 ({drop_pct_int}%)"
                    ))
                    crash_count += 1
                    
        return orders

    def build_sell_orders(self, state: CycleState) -> List[OrderIntent]:
        if (state.status != CycleStatus.RUNNING and state.status != CycleStatus.REVERSE_MODE) or state.position.quantity <= 0:
            return []
            
        self.calculate_daily_indicators(state)
        orders = []
        
        if state.reverse_mode:
            sell_qty = state.reverse_sell_qty_unit
            if sell_qty > 0 and state.current_star_price > 0:
                orders.append(OrderIntent(
                    symbol=state.params.symbol, side=Side.SELL, kind=OrderKind.LOC,
                    price=state.current_star_price, quantity=Decimal(math.floor(sell_qty)), tag="리버스 무한매도 (별지점 위)"
                ))
            return orders
            
        # 쿼터 매도 및 지정가 익절
        total_qty = state.position.quantity
        if total_qty > 0:
            quarter_qty = Decimal(str(math.floor(total_qty / Decimal('4'))))
            rest_qty = total_qty - quarter_qty
            
            # 1. 쿼터 매도 (1/4 별지점 LOC)
            if quarter_qty > 0 and state.current_star_price > 0:
                orders.append(OrderIntent(
                    symbol=state.params.symbol, side=Side.SELL, kind=OrderKind.LOC,
                    price=state.current_star_price, quantity=quarter_qty, tag="쿼터 매도 (별지점)"
                ))
                
            # 2. 지정가 익절 (나머지 3/4)
            if rest_qty > 0:
                tp_target = Decimal('1.20') if state.params.symbol.upper() == "SOXL" else Decimal('1.15')
                take_profit_price = state.position.avg_price * tp_target
                pct_str = "+20%" if state.params.symbol.upper() == "SOXL" else "+15%"
                orders.append(OrderIntent(
                    symbol=state.params.symbol, side=Side.SELL, kind=OrderKind.LIMIT,
                    price=take_profit_price, quantity=rest_qty, tag=f"지정가 익절 ({pct_str})"
                ))
            
        return orders

