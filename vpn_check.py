# Summary:
# Simple script to check public IP, location and whether the connection appears to
# be via a known VPN provider.
#
# Workflow:
# 1. Fetch IPv4 metadata from https://ipinfo.io/json.
# 2. Print full metadata plus IP and location fields.
# 3. Compare the reported organization string against known VPN provider keywords.
# 4. Query https://api6.ipify.org to detect a public IPv6 address.
# 5. Emit warnings if the organization is unrecognized or a public IPv6 address is present.
import json
from typing import Any, Dict, Optional
from urllib.request import urlopen
from urllib.error import URLError

VPN_ORG_KEYWORDS = [
    "packethub",
    "clouvider",
    "tefincom",
    "nordvpn",
]


# Fetch and parse JSON from a URL.
# url: endpoint to request (expects JSON response)
# timeout: timeout in seconds for the request
# returns: parsed JSON as a dict on success, otherwise None
def fetch_json(url: str, timeout: int = 5) -> Optional[Dict[str, Any]]:
    try:
        with urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        print(f"Error fetching {url}: {e}")
        return None


# Check whether an organization string matches known VPN keywords.
# org: organization string returned by IP metadata
# keywords: list of keywords associated with VPN providers
# returns: True if any keyword is found (case-insensitive), False otherwise
def is_vpn_org(org: str, keywords=VPN_ORG_KEYWORDS) -> bool:
    return any(k.lower() in org.lower() for k in keywords)


# Detect public IPv6 address by querying api6.ipify.org.
# timeout: timeout in seconds for the request
# returns: IPv6 address string if present, otherwise None
def detect_ipv6(timeout: int = 5) -> Optional[str]:
    try:
        with urlopen("https://api6.ipify.org", timeout=timeout) as resp:
            ip = resp.read().decode("utf-8").strip()
            return ip if ip else None
    except URLError:
        return None


# Main workflow orchestration.
# Steps:
# - Call fetch_json to get IPv4 metadata.
# - Print metadata and extract ip, city, region and org fields.
# - Use is_vpn_org to determine likely VPN usage and print status.
# - Call detect_ipv6 to check for public IPv6 and print warnings as needed.
def main() -> None:
    data = fetch_json("https://ipinfo.io/json")
    if not data:
        return

    print(f"IP address: {data.get('ip', 'Unknown')}")
    print(f"Location: {data.get('city', 'Unknown')}, {data.get('region', 'Unknown')}")

    organization = data.get("org", "Unknown")
    print(f"Organization: {organization}")

    if is_vpn_org(organization):
        print("VPN status: likely connected to NordVPN")
    else:
        print(f"WARNING: Organization is not recognized: {organization}")
        print("You may not be connected to NordVPN.")

    ipv6 = detect_ipv6()
    if ipv6:
        print(f"WARNING: Public IPv6 address detected: {ipv6}")
    else:
        print("IPv6 is unavailable.")


if __name__ == "__main__":
    main()