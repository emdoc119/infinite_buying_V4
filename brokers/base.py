from abc import ABC, abstractmethod
from typing import List
from datetime import date

from domain.models import OrderIntent, FillEvent

class BrokerAdapter(ABC):
    """
    브로커 통신을 위한 추상 인터페이스입니다.
    이 인터페이스를 상속하여 각 증권사별 어댑터를 구현합니다.
    """
    
    @abstractmethod
    def submit_order(self, intent: OrderIntent) -> str:
        """
        주문을 전송하고 브로커가 부여한 주문 ID(Order ID)를 반환합니다.
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        미체결 주문을 취소합니다. 성공 여부를 반환합니다.
        """
        pass

    @abstractmethod
    def get_open_orders(self, symbol: str) -> List[str]:
        """
        특정 종목의 미체결 주문 ID 목록을 반환합니다.
        """
        pass

    @abstractmethod
    def get_fills(self, symbol: str, target_date: date) -> List[FillEvent]:
        """
        특정 일자의 체결 내역을 조회하여 FillEvent 리스트로 반환합니다.
        """
        pass
