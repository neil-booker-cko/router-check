import pytest

# --- MOCK DATA: PASSING SCENARIOS ---


@pytest.fixture
def mock_route_pass():
    """Simulates: 'show ip route' where the route exists and next-hop is correct."""
    return {
        "vrf": {
            "default": {
                "address_family": {
                    "ipv4": {
                        "routes": {
                            "192.168.10.0/24": {
                                "next_hop": {
                                    "next_hop_list": {1: {"next_hop": "10.1.1.2"}}
                                }
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_bgp_pass():
    """Simulates: 'show ip bgp all summary' where neighbor is established."""
    return {
        "vrf": {
            "default": {
                "neighbor": {
                    "10.2.2.2": {
                        "state_pfxrcd": "5"  # Established usually shows a number
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_ospf_pass():
    """Simulates: 'show ip ospf neighbor' with FULL state."""
    return {
        "vrf": {
            "default": {
                "address_family": {
                    "ipv4": {
                        "instance": {
                            "1": {
                                "areas": {
                                    "0.0.0.0": {
                                        "interfaces": {
                                            "GigabitEthernet1": {
                                                "neighbors": {
                                                    "2.2.2.2": {"state": "FULL/DR"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }


# --- MOCK DATA: FAILING SCENARIOS ---


@pytest.fixture
def mock_route_fail():
    """Simulates: Route exists but wrong next-hop."""
    return {
        "vrf": {
            "default": {
                "address_family": {
                    "ipv4": {
                        "routes": {
                            "192.168.10.0/24": {
                                "next_hop": {
                                    "next_hop_list": {1: {"next_hop": "99.99.99.99"}}
                                }
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_bgp_fail():
    """Simulates: BGP neighbor in Active (down) state."""
    return {"vrf": {"default": {"neighbor": {"10.2.2.2": {"state_pfxrcd": "Active"}}}}}
