from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BaseWindowReader(ABC):
    @abstractmethod
    def get_active_window(self) -> Optional[Dict[str, Any]]:
        pass
