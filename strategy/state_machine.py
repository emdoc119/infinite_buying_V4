from decimal import Decimal
from typing import Optional
from datetime import date
from domain.models import CycleState, CycleStatus

class CycleStateMachine:
    """
    무한매수법 V4 상태 머신 (Action-based).
    UI에서 버튼(1회 매수, 절반 매수, 쿼터 매도 등)을 클릭했을 때 상태를 변경합니다.
    """
    
    def process_action(self, state: CycleState, action: str, price: Decimal, quantity: Decimal, trade_date: Optional[date] = None, update_fills: bool = True) -> CycleState:
        from domain.models import Side, FillEvent
        if state.status != CycleStatus.RUNNING and state.status != CycleStatus.REVERSE_MODE:
            return state

        if update_fills:
            side = Side.BUY if action in ["full_buy", "half_buy", "first_buy", "reverse_buy"] else Side.SELL
            fill_evt = FillEvent(
                symbol=state.params.symbol.value,
                side=side,
                price=price,
                quantity=quantity,
                trade_date=trade_date or date.today(),
                action=action
            )
            state.fills.append(fill_evt)

        def add_position(p: Decimal, q: Decimal):
            total_value = state.position.value + (p * q)
            state.position.quantity += q
            if state.position.quantity > 0:
                state.position.avg_price = total_value / state.position.quantity
            state.cash_remaining -= (p * q)
            
        def reduce_position(p: Decimal, q: Decimal):
            state.position.quantity -= q
            state.cash_remaining += (p * q)
            if state.position.quantity <= 0:
                state.position.quantity = Decimal('0')
                state.position.avg_price = Decimal('0')
        
        # 첫 진입 매수 체결 처리 (T=0)
        if state.T == 0 and state.position.quantity == 0 and action in ["full_buy", "half_buy", "first_buy"]:
            notional = price * quantity
            state.position.quantity = quantity
            state.position.avg_price = price
            state.cash_remaining = state.params.total_budget - notional
            
            base_budget = state.params.total_budget / Decimal(str(state.params.split_count))
            if action == "half_buy":
                state.T = 0.5
            else:
                state.T = 1.0
            return state

        # 일반 모드 액션
        if not state.reverse_mode:
            if action == "full_buy":
                add_position(price, quantity)
                state.T += 1.0
            elif action == "half_buy":
                add_position(price, quantity)
                state.T += 0.5
            elif action == "take_profit":
                reduce_position(price, quantity)
                state.T = 0.0
                state.status = CycleStatus.WAITING_RESET
                return state
            elif action == "quarter_sell":
                reduce_position(price, quantity)
                state.T *= 0.75
                
            # 리버스 모드 진입 체크
            if state.T > state.params.split_count - 1:
                state.reverse_mode = True
                state.status = CycleStatus.REVERSE_MODE
                divisor = Decimal('10') if state.params.split_count == 20 else Decimal('20')
                state.reverse_sell_qty_unit = state.position.quantity / divisor
                
        # 리버스 모드 액션
        else:
            if action == "reverse_sell":
                reduce_position(price, quantity)
                if state.params.split_count == 20:
                    state.T *= 0.9
                else:
                    state.T *= 0.95
                    
            elif action == "reverse_buy":
                add_position(price, quantity)
                if state.params.split_count == 20:
                    state.T += (20 - state.T) * 0.25
                else:
                    state.T += (40 - state.T) * 0.25
                    
            # 일반 모드 복귀 체크 (평단가 이상 회복 시)
            if price > state.position.avg_price:
                state.reverse_mode = False
                state.status = CycleStatus.RUNNING
                
        return state

    def determine_fill_action(self, state: CycleState, fill) -> str:
        from domain.models import Side
        splits = state.params.split_count
        
        if fill.side == Side.SELL:
            if state.reverse_mode:
                return "reverse_sell"
                
            # 보유량이 0이 되거나, 판매 수량이 보유수량의 90% 이상인 경우 전량 익절 처리
            if state.position.quantity > 0 and fill.quantity >= state.position.quantity * Decimal('0.9'):
                return "take_profit"
            else:
                return "quarter_sell"
        else:
            # BUY fill
            if state.reverse_mode:
                return "reverse_buy"
                
            if state.position.quantity == 0 or state.T == 0.0:
                return "first_buy"
                
            from strategy.infinite_buying_v4 import InfiniteBuyingV4Strategy
            engine = InfiniteBuyingV4Strategy()
            engine.calculate_daily_indicators(state)
            
            # 전반전(T < splits/2)과 후반전 분기
            if state.T < splits / 2:
                # 오늘 시점의 1회 매수금 예산 계산
                if splits - state.T > 0:
                    expected_budget = state.cash_remaining / Decimal(str(float(splits) - state.T))
                else:
                    expected_budget = Decimal('0')
                
                star_pct = state.current_star_pct
                star_price = state.current_star_price
                
                # 각각 절반의 예산으로 매수 가능한 수량 계산
                half_budget = expected_budget / Decimal('2')
                qty_star = int(half_budget / star_price) if star_price > 0 else 0
                qty_avg = int(half_budget / state.position.avg_price) if state.position.avg_price > 0 else 0
                total_buyable = qty_star + qty_avg
                
                # 체결 수량이 예상 총 매수 수량의 70%를 넘으면 full_buy, 아니면 half_buy로 판단
                if total_buyable > 0 and fill.quantity > Decimal(str(total_buyable)) * Decimal('0.7'):
                    return "full_buy"
                else:
                    return "half_buy"
            else:
                # 후반전은 항상 1회 매수 전체를 별지점에 LOC 매수
                return "full_buy"
