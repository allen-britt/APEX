from __future__ import annotations

import itertools
from datetime import datetime
from typing import Any, Dict, Iterable, List, Sequence, Tuple


class CoverageService:
    """Builds heuristic coverage metadata for a mission context."""

    _SOCIAL_MEDIA_KEYWORDS: Tuple[str, ...] = (
        "social media",
        "facebook",
        "instagram",
        "tiktok",
        "twitter",
        "hashtag",
        "telegram",
    )
    _FINANCE_KEYWORDS: Tuple[str, ...] = (
        "bank",
        "account",
        "wire",
        "crypto",
        "wallet",
        "transaction",
        "invoice",
    )
    _GEO_KEYWORDS: Tuple[str, ...] = (
        "latitude",
        "longitude",
        "aoi",
        "geospatial",
        "map",
        "terrain",
        "imagery",
    )
    _CYBER_KEYWORDS: Tuple[str, ...] = (
        "c2",
        "malware",
        "packet",
        "pcap",
        "cve",
        "attack",
        "ransomware",
    )
    _FORENSICS_KEYWORDS: Tuple[str, ...] = (
        "cellebrite",
        "extraction",
        "forensic",
        "device dump",
        "dfir",
    )

    def build_coverage_map(self, context: Dict[str, Any]) -> Dict[str, Any]:
        documents: List[Dict[str, Any]] = context.get("documents", []) or []
        datasets: List[Dict[str, Any]] = context.get("datasets", []) or []
        events: List[Dict[str, Any]] = context.get("events", []) or []

        text_samples = self._collect_text(documents, datasets)
        ints_present = set()

        if self._contains(text_samples, self._SOCIAL_MEDIA_KEYWORDS):
            ints_present.add("SOCMINT")
        if self._contains(text_samples, self._FINANCE_KEYWORDS):
            ints_present.add("FININT")
        if self._contains(text_samples, self._GEO_KEYWORDS) or self._datasets_have_geo(datasets):
            ints_present.add("GEOINT")
        if self._contains(text_samples, self._CYBER_KEYWORDS):
            ints_present.add("CYBINT")
        if self._contains(text_samples, self._FORENSICS_KEYWORDS):
            ints_present.add("DFINT")
        if documents:
            ints_present.add("CaseINT")

        has_geospatial = ("GEOINT" in ints_present) or any(event.get("location") for event in events)
        has_financial = "FININT" in ints_present
        has_social_media = "SOCMINT" in ints_present

        time_range = self._compute_time_range(events)
        sources_summary = {
            "documents": len(documents),
            "entities": len(context.get("entities", []) or []),
            "events": len(events),
            "datasets": len(datasets),
        }

        return {
            "ints_present": sorted(ints_present),
            "has_geospatial": has_geospatial,
            "has_social_media": has_social_media,
            "has_financial": has_financial,
            "time_range": time_range,
            "source_counts": sources_summary,
        }

    def _collect_text(
        self,
        documents: Sequence[Dict[str, Any]],
        datasets: Sequence[Dict[str, Any]],
    ) -> List[str]:
        texts: List[str] = []
        for doc in documents:
            title = doc.get("title") or ""
            content = doc.get("content") or ""
            if title:
                texts.append(str(title))
            if content:
                texts.append(str(content))
        for dataset in datasets:
            profile = dataset.get("profile") or {}
            semantic = dataset.get("semantic_profile") or {}
            texts.extend(self._flatten_profile(profile))
            texts.extend(self._flatten_profile(semantic))
        return texts

    def _flatten_profile(self, payload: Any) -> List[str]:
        if isinstance(payload, dict):
            parts = []
            for value in payload.values():
                parts.extend(self._flatten_profile(value))
            return parts
        if isinstance(payload, list):
            return list(itertools.chain.from_iterable(self._flatten_profile(item) for item in payload))
        if isinstance(payload, (str, int, float)):
            return [str(payload)]
        return []

    def _contains(self, haystacks: Iterable[str], keywords: Sequence[str]) -> bool:
        lowered = " ".join(haystacks).lower()
        return any(keyword in lowered for keyword in keywords)

    def _datasets_have_geo(self, datasets: Sequence[Dict[str, Any]]) -> bool:
        for dataset in datasets:
            semantic = dataset.get("semantic_profile") or {}
            flattened = " ".join(self._flatten_profile(semantic)).lower()
            if "lat" in flattened and "lon" in flattened:
                return True
        return False

    def _compute_time_range(self, events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        timestamps: List[datetime] = []
        for event in events:
            ts = event.get("timestamp")
            if not ts:
                continue
            if isinstance(ts, datetime):
                timestamps.append(ts)
                continue
            if isinstance(ts, str):
                try:
                    timestamps.append(datetime.fromisoformat(ts))
                except ValueError:
                    continue
        if not timestamps:
            return {"start": None, "end": None}
        timestamps.sort()
        return {"start": timestamps[0].isoformat(), "end": timestamps[-1].isoformat()}
