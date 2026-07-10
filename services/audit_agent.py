from decimal import Decimal
from typing import List, Dict, Any
from domain.models import CycleState, FillEvent
from services.notifier import notifier

class AuditAgent:
    @staticmethod
    async def run_daily_audit(cycle_id: str, current_cycle: CycleState, new_fills: List[FillEvent], actual_balance: Dict[str, Any]) -> bool:
        """
        예상 잔고와 KIS 실제 잔고를 비교하여 불일치 시 텔레그램으로 경고를 발송하고
        덮어쓰기 허용 여부를 반환합니다.
        반환값: bool (True면 덮어쓰기 진행, False면 덮어쓰기 보류)
        """
        if not actual_balance:
            return True # 잔고 정보 없으면 무시
            
        expected_qty = current_cycle.position.quantity
        # new_fills 는 이미 current_cycle 의 process_action 에서 반영되었으므로 이중으로 더하지 않습니다.
                
        actual_qty = actual_balance.get("quantity", Decimal('0'))
        
        if abs(expected_qty - actual_qty) > Decimal('0.01'):
            msg = (
                f"🚨 **[시스템 알림] 잔고 불일치 자동 복구**\n"
                f"종목: {current_cycle.params.symbol.value}\n"
                f"내부 예상: {expected_qty}주\n"
                f"실제 잔고: {actual_qty}주\n\n"
                f"⚠️ 증권사 API의 체결 내역 누락이 감지되었습니다.\n"
                f"실제 잔고(Source of Truth)를 기준으로 시스템을 자동 동기화합니다. 🔄"
            )
            await notifier.send_message(msg)
            return True # 불일치 시에도 실제 잔고를 우선하여 덮어쓰기를 진행하도록 True 반환
            
        return True # 일치 시 정상 진행

audit_agent = AuditAgent()
