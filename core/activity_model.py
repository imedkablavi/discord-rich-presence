from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

@dataclass
class ActivityState:
    type: str
    details: str = ""
    state: str = ""
    large_image: str = "app"
    large_text: str = ""
    small_image: Optional[str] = None
    small_text: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    url: Optional[str] = None
    buttons: List[Dict[str, str]] = field(default_factory=list)

    def to_discord_payload(self) -> Dict[str, Any]:
        payload = {
            "details": self.details[:128] if self.details else None,
            "state": self.state[:128] if self.state else None,
            "large_image": self.large_image,
            "large_text": self.large_text[:128] if self.large_text else None,
        }
        if self.small_image:
            payload["small_image"] = self.small_image
        if self.small_text:
            payload["small_text"] = self.small_text[:128]
        if self.start_time:
            payload["start"] = self.start_time
        if self.end_time:
            payload["end"] = self.end_time
        if self.buttons:
            payload["buttons"] = self.buttons[:2]
        return {k: v for k, v in payload.items() if v is not None}
