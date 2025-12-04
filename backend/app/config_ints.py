from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class IntDescriptor:
    key: str
    domain: str
    description: str


_INT_REGISTRY = {
    descriptor.key: descriptor
    for descriptor in [
        IntDescriptor(
            key="OSINT",
            domain="LEO/IC/Civilian",
            description="Open-source intelligence derived from public, commercial, and social data streams.",
        ),
        IntDescriptor(
            key="HUMINT",
            domain="LEO/DoD/IC",
            description="Human intelligence collected through interviews, debriefs, and source reporting.",
        ),
        IntDescriptor(
            key="SIGINT",
            domain="DoD/IC",
            description="Signals intelligence from RF, communications, and cyber telemetry.",
        ),
        IntDescriptor(
            key="GEOINT",
            domain="LEO/DoD/IC",
            description="Geospatial intelligence from imagery, maps, terrain, and geolocation data.",
        ),
        IntDescriptor(
            key="SOCMINT",
            domain="LEO",
            description="Social media intelligence focused on accounts, networks, and narratives.",
        ),
        IntDescriptor(
            key="DFINT",
            domain="LEO",
            description="Digital forensics intelligence sourced from device extractions and logs.",
        ),
        IntDescriptor(
            key="CrimeINT",
            domain="LEO",
            description="Crime-pattern intelligence supporting hotspot and repeat-offender analysis.",
        ),
        IntDescriptor(
            key="CaseINT",
            domain="LEO",
            description="Case-level intelligence encompassing timelines, leads, and corroboration.",
        ),
        IntDescriptor(
            key="CYBINT",
            domain="LEO/DoD",
            description="Cyber intelligence covering network intrusions, malware, and threat actors.",
        ),
        IntDescriptor(
            key="FININT",
            domain="LEO/IC",
            description="Financial intelligence over banking patterns, cryptocurrency, and illicit flows.",
        ),
        IntDescriptor(
            key="TargetingINT",
            domain="DoD",
            description="Targeting intelligence aligned to F3EAD (Find, Fix, Finish, Exploit, Analyze, Disseminate).",
        ),
        IntDescriptor(
            key="PredictiveINT",
            domain="LEO/DoD",
            description="Predictive analytics for forecasting threats, activity, or system failures.",
        ),
        IntDescriptor(
            key="TECHINT",
            domain="DoD/IC",
            description="Technical intelligence for exploited hardware, malware, and advanced sensors.",
        ),
        IntDescriptor(
            key="MASINT",
            domain="DoD/IC",
            description="Measurement and signature intelligence from specialized sensors and anomaly detection.",
        ),
    ]
}


def get_int_registry() -> Dict[str, IntDescriptor]:
    """Return the static INT registry."""

    return _INT_REGISTRY
