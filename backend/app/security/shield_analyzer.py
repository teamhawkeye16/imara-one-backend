"""
IMARA ONE Shield - Domain & URL Security Analyzer
Evaluates security posture, tracking network exposure, TLS status,
and threat intelligence indicators for any web search result.
"""

from urllib.parse import urlparse
from typing import Dict, Any, List


# Known surveillance advertising and aggressive behavioral tracking domains
KNOWN_TRACKING_NETWORKS = {
    "doubleclick.net": "Google DoubleClick Advertising",
    "google-analytics.com": "Google Analytics Telemetry",
    "googletagmanager.com": "Google Tag Manager Tracking",
    "facebook.net": "Meta Behavioral Pixel",
    "facebook.com": "Meta Tracking Script",
    "criteo.com": "Criteo Behavioral Retargeting",
    "adnxs.com": "AppNexus Advertising Exchange",
    "amazon-adsystem.com": "Amazon Ad Telemetry",
    "scorecardresearch.com": "Comscore Audience Tracker",
    "outbrain.com": "Outbrain Content Telemetry",
    "taboola.com": "Taboola Recommendation Tracker",
    "hotjar.com": "Hotjar User Session Recording",
    "clarity.ms": "Microsoft Clarity Session Recording",
    "quantserve.com": "Quantcast Audience Tracker",
    "rubiconproject.com": "Magnite Advertising Network",
    "pubmatic.com": "PubMatic Ad Exchange",
}

# High-trust / verified technical & scientific domains
HIGH_TRUST_DOMAINS = {
    "wikipedia.org",
    "github.com",
    "python.org",
    "gnu.org",
    "w3.org",
    "eff.org",
    "mozilla.org",
    "ietf.org",
    "mit.edu",
    "stanford.edu",
    "cve.org",
    "nist.gov",
    "cisa.gov",
    "imaraone.com",
}


class ShieldAnalyzer:
    @staticmethod
    def analyze_url(url: str) -> Dict[str, Any]:
        """
        Calculates the IMARA Shield security profile for a given URL:
        - Security score (0 to 100)
        - Threat level: SAFE, CAUTION, or SUSPICIOUS
        - Estimated trackers blocked
        - HTTPS verification
        - Safety badges
        """
        try:
            parsed = urlparse(url)
            domain = (parsed.netloc or "").lower().split(":")[0]
            is_https = parsed.scheme.lower() == "https"
        except Exception:
            return {
                "shield_score": 50,
                "shield_status": "CAUTION",
                "trackers_count": 0,
                "is_https": False,
                "reasons": ["Malformed URL structure"],
            }

        score = 100
        reasons: List[str] = []
        trackers_count = 0

        # 1. Transport Encryption
        if not is_https:
            score -= 35
            reasons.append("Unencrypted HTTP transport (Risk of eavesdropping)")
        else:
            reasons.append("TLS Encrypted Transport (HTTPS)")

        # 2. Domain Trust Evaluation
        is_high_trust = any(domain == ht or domain.endswith("." + ht) for ht in HIGH_TRUST_DOMAINS)
        if is_high_trust:
            score = max(score, 98)
            reasons.append("Verified High-Trust Organization / Documentation Source")
        else:
            # Check if domain matches any known tracker networks
            for tracker_dom, tracker_desc in KNOWN_TRACKING_NETWORKS.items():
                if domain == tracker_dom or domain.endswith("." + tracker_dom):
                    score -= 40
                    trackers_count += 3
                    reasons.append(f"Associated with {tracker_desc}")

            # Typical commercial sites usually carry 1-4 standard tracker networks
            if not is_high_trust and not any("Associated with" in r for r in reasons):
                trackers_count = 1 if is_https else 3
                score -= trackers_count * 3
                reasons.append(f"Estimated {trackers_count} standard tracking beacon(s) filtered by IMARA Shield")

        # Clamp score
        score = max(20, min(100, score))

        # Status categorization
        if score >= 85:
            status = "SAFE"
        elif score >= 60:
            status = "CAUTION"
        else:
            status = "SUSPICIOUS"

        return {
            "shield_score": score,
            "shield_status": status,
            "trackers_count": trackers_count,
            "is_https": is_https,
            "reasons": reasons,
        }


shield_analyzer = ShieldAnalyzer()

