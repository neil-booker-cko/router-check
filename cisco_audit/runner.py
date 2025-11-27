import logging
import yaml
from nornir import InitNornir
from nornir_netmiko.tasks import netmiko_send_command
from nornir_utils.plugins.functions import print_result

# --- 1. SETUP LOGGING ---
# We configure a logger to write to a file AND print to console
logger = logging.getLogger("ComplianceAudit")
logger.setLevel(logging.INFO)

# File Handler (The Audit Trail)
file_handler = logging.FileHandler("compliance.log")
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Stream Handler (Console Output - Optional if you use print_result)
stream_handler = logging.StreamHandler()
stream_formatter = logging.Formatter('%(levelname)s: %(message)s')
stream_handler.setFormatter(stream_formatter)
logger.addHandler(stream_handler)


# --- 2. LOAD RULES ---
def load_rules(filename='compliance_rules.yaml'):
    with open(filename, 'r') as f:
        return yaml.safe_load(f)

GLOBAL_RULES = load_rules()


# --- 3. THE COMPLIANCE TASK ---
def audit_device(task):
    """
    This function runs on every router in parallel.
    """
    device_name = task.host.name
    logger.info(f"Starting audit for {device_name}")
    
    compliance_report = []
    
    # ---------------------------
    # CHECK 1: ROUTING TABLE
    # ---------------------------
    # Nornir+Netmiko can auto-parse with Genie using use_genie=True
    route_output = task.run(
        task=netmiko_send_command, 
        command_string="show ip route", 
        use_genie=True,
        severity_level=logging.DEBUG
    )
    
    # Extract the parsed dictionary (route_output.result)
    routes = route_output.result
    # Handle cases where parsing fails or returns empty
    if not isinstance(routes, dict):
        routes = {} 

    vrf_routes = routes.get('vrf', {}).get('default', {}).get('address_family', {}).get('ipv4', {}).get('routes', {})

    for rule in GLOBAL_RULES['static_routes']:
        prefix = rule['prefix']
        expected_hop = rule['next_hop']
        
        if prefix in vrf_routes:
            # Extract actual hops
            actual_route = vrf_routes[prefix]
            hops = actual_route.get('next_hop', {}).get('next_hop_list', {})
            
            # Logic to match hop in dictionary list
            hop_found = any(h.get('next_hop') == expected_hop for h in hops.values())

            if hop_found:
                msg = f"{device_name}: [PASS] Route {prefix} correct."
                logger.info(msg)
                compliance_report.append(msg)
            else:
                msg = f"{device_name}: [FAIL] Route {prefix} next-hop mismatch."
                logger.error(msg)
                compliance_report.append(msg)
        else:
            msg = f"{device_name}: [FAIL] Route {prefix} missing."
            logger.error(msg)
            compliance_report.append(msg)

    # ---------------------------
    # CHECK 2: BGP
    # ---------------------------
    bgp_output = task.run(
        task=netmiko_send_command, 
        command_string="show ip bgp all summary", 
        use_genie=True
    )
    bgp_data = bgp_output.result
    
    if isinstance(bgp_data, dict):
        vrf_bgp = bgp_data.get('vrf', {}).get('default', {})
        
        # Check Neighbors
        neighbors_data = vrf_bgp.get('neighbor', {})
        target_neighbors = GLOBAL_RULES['bgp']['neighbors']

        for expected in target_neighbors:
            t_ip = expected['ip']
            if t_ip in neighbors_data:
                actual_state = str(neighbors_data[t_ip].get('state_pfxrcd'))
                # BGP state is often an integer (prefixes received) if established
                if actual_state == expected['state'] or actual_state.isdigit():
                    logger.info(f"{device_name}: [PASS] BGP Neighbor {t_ip} Established")
                else:
                    logger.error(f"{device_name}: [FAIL] BGP Neighbor {t_ip} is {actual_state}")
            else:
                logger.error(f"{device_name}: [FAIL] BGP Neighbor {t_ip} not found")

    # ---------------------------
    # CHECK 3: OSPF
    # ---------------------------
    ospf_output = task.run(
        task=netmiko_send_command, 
        command_string="show ip ospf neighbor", 
        use_genie=True
    )
    ospf_data = ospf_output.result

    if isinstance(ospf_data, dict):
        # Flatten OSPF structure for easier searching
        active_neighbors = {}
        try:
            inst = ospf_data['vrf']['default']['address_family']['ipv4']['instance']
            for proc in inst.values():
                for area in proc.get('areas', {}).values():
                    for intf in area.get('interfaces', {}).values():
                        for nid, ndata in intf.get('neighbors', {}).items():
                            active_neighbors[nid] = ndata.get('state')
        except KeyError:
            pass # OSPF structure might not exist if not configured

        for rule in GLOBAL_RULES['ospf']['neighbors']:
            n_id = rule['neighbor_id']
            if n_id in active_neighbors:
                if rule['state'].lower() in active_neighbors[n_id].lower():
                    logger.info(f"{device_name}: [PASS] OSPF Neighbor {n_id} {rule['state']}")
                else:
                    logger.error(f"{device_name}: [FAIL] OSPF Neighbor {n_id} state mismatch")
            else:
                logger.error(f"{device_name}: [FAIL] OSPF Neighbor {n_id} missing")

    return "\n".join(compliance_report)


# --- 4. EXECUTION ---
def main():
    # Initialize Nornir
    nr = InitNornir(config_file="config.yaml")
    
    print("--- Starting Nornir Compliance Audit ---")
    
    # Run the audit_device function on all hosts
    # Nornir handles the threading automatically based on config.yaml
    result = nr.run(task=audit_device)
    
    # Print a summary to screen (standard Nornir output)
    print_result(result)
    
    print("\nAudit Complete. Check 'compliance.log' for details.")

if __name__ == "__main__":
    main()