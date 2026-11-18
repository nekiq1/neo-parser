"""Abstract source provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, Optional


@dataclass
class CompanyResult:
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    city: str = ""
    category: str = ""
    website: str = ""
    vk: str = ""
    telegram: str = ""
    whatsapp: str = ""
    source: str = ""
    source_id: str = ""
    card_url: str = ""
    raw: dict = field(default_factory=dict)


class SourceProvider(ABC):
    """Pluggable data source. Implement search() for new providers."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    def configuration_help(self) -> str:
        ...

    @abstractmethod
    def search(
        self,
        query: str,
        city: str,
        *,
        max_pages: int = 3,
        stop_flag: Optional[callable] = None,
    ) -> Iterator[CompanyResult]:
        """Yield company records. Respect stop_flag() if provided."""
        ...
