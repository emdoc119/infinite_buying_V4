from decimal import Decimal
from domain.models import CycleState, CycleStatus

class CycleStateMachine:
    """
    무한매수법 V4 상태 머신 (Action-based).
    UI에서 버튼(1회 매수, 절반 매수, 쿼터 매도 등)을 클릭했을 때 상태를 변경합니다.
    """
    
    def process_action(self, state: CycleState, action: str, price: Decimal, quantity: Decimal) -> CycleState:
        if state.status != CycleStatus.RUNNING and state.status != CycleStatus.REVERSE_MODE:
            return state

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
            state.T = float(notional / base_budget)
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
                    
            # 일반 모드 복귀 체크
            threshold = Decimal('-0.15') if state.params.symbol == "TQQQ" else Decimal('-0.20')
            if price > state.position.avg_price * (Decimal('1') + threshold):
                state.reverse_mode = False
                state.status = CycleStatus.RUNNING
                
        return state
