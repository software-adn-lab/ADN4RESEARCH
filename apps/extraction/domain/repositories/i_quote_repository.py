from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.quote import Quote

class IQuoteRepository(ABC):
    @abstractmethod
    def save(self, quote: Quote) -> Quote:
        pass

    @abstractmethod
    def get_by_id(self, quote_id: int) -> Optional[Quote]:
        pass

    @abstractmethod
    def get_by_tag(self, tag_id: int) -> List[Quote]:
        """Necesario para el TagMergeService"""
        pass

    @abstractmethod
    def delete(self, quote_id: int) -> None:
        pass