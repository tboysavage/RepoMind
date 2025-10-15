"""Base abstractions for Repo-Surgeon detectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, MutableMapping, Optional, Sequence, Tuple, Type, TypeVar

from ..tracing import Tracer


@dataclass(slots=True)
class Issue:
    """Represents a single finding emitted by a detector."""

    message: str
    path: str
    detector: str = ""
    severity: str = "warning"
    line: Optional[int] = None
    column: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a serialisable representation of the issue."""

        payload: Dict[str, Any] = {
            "detector": self.detector,
            "message": self.message,
            "path": self.path,
            "severity": self.severity,
        }
        if self.line is not None:
            payload["line"] = self.line
        if self.column is not None:
            payload["column"] = self.column
        if self.details:
            payload["details"] = dict(self.details)
        return payload


DetectorType = TypeVar("DetectorType", bound="Detector")


class Detector:
    """Base class for Repo-Surgeon detectors.

    Subclasses must override :meth:`detect` and provide ``name`` and
    ``description`` class attributes. Instances are callable and produce
    :class:`Issue` objects describing findings.
    """

    #: Unique identifier for the detector. Override in subclasses.
    name: str = ""
    #: Human readable description.
    description: str = ""
    #: Default severity for issues emitted by this detector.
    default_severity: str = "warning"
    #: Whether the detector should be enabled when no explicit selection is
    #: provided.
    enable_by_default: bool = True

    def __init__(self, *, tracer: Optional[Tracer] = None) -> None:
        self.tracer = tracer or Tracer()

    # Public API -----------------------------------------------------------
    def run(self, root: Path) -> Iterator[Issue]:
        """Run the detector against *root* yielding :class:`Issue` objects."""

        root = Path(root)
        if not root.exists():
            raise FileNotFoundError(root)
        with self.tracer.span("detector", name=self.name):
            for issue in self.detect(root):
                if not isinstance(issue, Issue):
                    raise TypeError(
                        f"Detector {self.name!r} yielded non-Issue value {issue!r}"
                    )
                if not issue.detector:
                    issue.detector = self.name
                if not issue.severity:
                    issue.severity = self.default_severity
                self.tracer.emit("issue", **issue.to_dict())
                yield issue

    # Internals ------------------------------------------------------------
    def detect(self, root: Path) -> Iterable[Issue]:  # pragma: no cover - abstract
        """Subclasses override to implement their analysis."""

        raise NotImplementedError


class DetectorRegistry(MutableMapping[str, Type[Detector]]):
    """Container that stores detector classes by name."""

    def __init__(self) -> None:
        self._registry: Dict[str, Type[Detector]] = {}

    # Mapping interface ----------------------------------------------------
    def __getitem__(self, key: str) -> Type[Detector]:
        return self._registry[key]

    def __setitem__(self, key: str, value: Type[Detector]) -> None:
        self.register(value, name=key)

    def __delitem__(self, key: str) -> None:
        del self._registry[key]

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self._registry))

    def __len__(self) -> int:
        return len(self._registry)

    # Registry operations --------------------------------------------------
    def register(
        self,
        detector_cls: Type[DetectorType],
        *,
        name: Optional[str] = None,
        overwrite: bool = False,
    ) -> Type[DetectorType]:
        """Register *detector_cls* under *name*.

        Parameters
        ----------
        detector_cls:
            Subclass of :class:`Detector` to register.
        name:
            Optional custom name. Defaults to ``detector_cls.name``.
        overwrite:
            Allow replacing an existing registration.
        """

        if not issubclass(detector_cls, Detector):
            raise TypeError("detector_cls must be a Detector subclass")
        detector_name = name or detector_cls.name
        if not detector_name:
            raise ValueError("detector name cannot be empty")
        if detector_name in self._registry and not overwrite:
            raise ValueError(f"detector {detector_name!r} already registered")
        self._registry[detector_name] = detector_cls
        return detector_cls

    def unregister(self, name: str) -> None:
        """Remove the detector associated with *name*."""

        self._registry.pop(name)

    def create(
        self,
        name: str,
        *,
        tracer_factory: Optional[Callable[[], Tracer]] = None,
    ) -> Detector:
        """Instantiate the detector named *name*."""

        detector_cls = self._registry[name]
        tracer = tracer_factory() if tracer_factory else None
        return detector_cls(tracer=tracer)

    def available(self) -> List[Tuple[str, Type[Detector]]]:
        """Return registered detectors sorted by name."""

        return sorted(self._registry.items(), key=lambda item: item[0])

    def instantiate_all(
        self,
        *,
        include: Optional[Sequence[str]] = None,
        exclude: Optional[Sequence[str]] = None,
        tracer_factory: Optional[Callable[[str], Tracer]] = None,
    ) -> List[Detector]:
        """Instantiate detectors respecting include/exclude filters."""

        include_set = set(include or [])
        exclude_set = set(exclude or [])
        detectors: List[Detector] = []
        for name, detector_cls in self.available():
            if include_set and name not in include_set:
                continue
            if name in exclude_set:
                continue
            tracer = tracer_factory(name) if tracer_factory else None
            detectors.append(detector_cls(tracer=tracer))
        return detectors


registry = DetectorRegistry()


def register(
    detector_cls: Type[DetectorType] | None = None, *, overwrite: bool = False
) -> Callable[[Type[DetectorType]], Type[DetectorType]] | Type[DetectorType]:
    """Decorator that registers a detector class with the global registry."""

    def decorator(cls: Type[DetectorType]) -> Type[DetectorType]:
        registry.register(cls, overwrite=overwrite)
        return cls

    if detector_cls is not None:
        return decorator(detector_cls)
    return decorator
