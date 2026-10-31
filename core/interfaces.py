"""
SOLID Interface definitions for SyncPulse core modules.
Implements Dependency Inversion Principle (DIP) and Interface Segregation (ISP).
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IEscalationEngine(ABC):
    """Interface for clinical emergency escalation detection."""
    @abstractmethod
    def check(self, query: str) -> Any:
        """Check query for clinical emergency flags."""
        ...


class IScopeClassifier(ABC):
    """Interface for paramedical scope guard classification."""
    @abstractmethod
    def classify(self, query: str) -> Any:
        """Classify whether query is within frontline scope."""
        ...


class IProtocolRetriever(ABC):
    """Interface for protocol chunk retrieval engine."""
    @abstractmethod
    def search(self, query: str, top_k: int = 3) -> List[Any]:
        """Retrieve top-k relevant protocol chunks."""
        ...

    @abstractmethod
    def should_abstain(self, chunks: List[Any]) -> bool:
        """Determine if retrieval confidence is too low to answer."""
        ...


class IAnswerComposer(ABC):
    """Interface for extractive grounded answer composition."""
    @abstractmethod
    def compose(self, query: str, retrieved_chunks: List[Any], abstain: bool = False) -> Any:
        """Compose a grounded clinical answer from retrieved chunks."""
        ...


class IReadableRepository(ABC):
    """Interface for read-only data access."""
    @abstractmethod
    def find_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def find_all(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        ...


class IWritableRepository(ABC):
    """Interface for write operations."""
    @abstractmethod
    def save(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        ...

    @abstractmethod
    def update(self, entity_id: str, patch: Dict[str, Any]) -> bool:
        ...

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        ...


class ISyncableRepository(ABC):
    """Interface for offline sync outbox management."""
    @abstractmethod
    def get_pending_sync_items(self) -> List[Dict[str, Any]]:
        ...

    @abstractmethod
    def mark_synced(self, event_ids: List[str]) -> None:
        ...

