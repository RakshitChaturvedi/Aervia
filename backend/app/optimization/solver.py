"""
Google OR-Tools vehicle routing with time windows (CVRPTW) solver.
Computes optimal inspector and drone dispatch paths.
"""
import math
from typing import Dict, Any, List
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from optimization.router import get_dispatch_details
from optimization.roi import calculate_inspection_roi

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes the great-circle distance between two points in kilometers.
    """
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_coords(loc: Dict[str, Any]) -> tuple:
    lat = loc.get("latitude") or loc.get("lat") or 0.0
    lon = loc.get("longitude") or loc.get("lon") or 0.0
    return float(lat), float(lon)

def format_eta(minutes: int) -> str:
    """
    Converts cumulative minutes from start of shift (9:00 AM) to HH:MM format.
    """
    start_hour = 9
    start_minute = 0
    total_minutes = start_hour * 60 + start_minute + minutes
    h = (total_minutes // 60) % 24
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"

class RouteSolver:
    def __init__(self, locations: List[Dict[str, Any]], depot_index: int = 0, threshold: float = 200.0):
        """
        Args:
            locations: List of dicts representing nodes. The depot is at depot_index.
                       Other nodes represent sources.
            depot_index: Index of the depot node in locations.
        """
        self.locations = locations
        self.depot_index = depot_index
        self.threshold = threshold
        
    def solve_vrp(self, time_matrix: List[List[int]] = None, demand: List[int] = None, vehicle_capacities: List[int] = [480, 480, 45]) -> Dict[str, Any]:
        """
        Runs the VRP solver using OR-Tools CVRPTW and returns a routing plan.
        We support a heterogeneous fleet of:
          - Inspector (vehicle index 0): capacity = 480 min, speed = 30 km/h, ground multiplier = 1.3, service_time = 30 min.
          - Van (vehicle index 1): capacity = 480 min, speed = 25 km/h, ground multiplier = 1.3, service_time = 30 min.
          - Drone (vehicle index 2): capacity = 45 min, speed = 50 km/h, straight line (no multiplier), service_time = 10 min.
        """
        num_locations = len(self.locations)
        num_vehicles = 3
        
        if num_locations <= 1:
            # Only depot or no locations
            return {
                "inspector_1": {"route_id": "inspector_1", "vehicle_type": "inspector", "vehicle_label": "Inspector Team Alpha", "total_time_min": 0, "stops": []},
                "van_1": {"route_id": "van_1", "vehicle_type": "van", "vehicle_label": "Enforcement Van Charlie", "total_time_min": 0, "stops": []},
                "drone_1": {"route_id": "drone_1", "vehicle_type": "drone", "vehicle_label": "Drone Unit Bravo", "total_time_min": 0, "stops": []}
            }

        # 1. Initialize Routing Manager and Model
        manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, self.depot_index)
        routing = pywrapcp.RoutingModel(manager)

        # 2. Define travel times and service times callbacks
        def get_travel_time(from_node: int, to_node: int, vehicle_idx: int) -> int:
            if from_node == to_node:
                return 0
            lat1, lon1 = get_coords(self.locations[from_node])
            lat2, lon2 = get_coords(self.locations[to_node])
            dist_km = haversine_distance(lat1, lon1, lat2, lon2)
            
            if vehicle_idx == 0:  # Inspector
                speed = 30.0
                multiplier = 1.3
            elif vehicle_idx == 1:  # Van
                speed = 25.0
                multiplier = 1.3
            else:  # Drone
                speed = 50.0
                multiplier = 1.0
                
            travel_time_min = (dist_km * multiplier) / (speed / 60.0)
            return int(round(travel_time_min))

        def get_service_time(node: int, vehicle_idx: int) -> int:
            if node == self.depot_index:
                return 0
            # Drone visits take 10 minutes, ground checks take 30 minutes
            return 10 if vehicle_idx == 2 else 30

        # We construct transit callbacks for each vehicle
        transit_callback_indices = []
        callbacks_ref = []
        for v in range(num_vehicles):
            def make_callback(v_idx=v):
                def callback(from_index, to_index):
                    from_node = manager.IndexToNode(from_index)
                    to_node = manager.IndexToNode(to_index)
                    return get_travel_time(from_node, to_node, v_idx) + get_service_time(from_node, v_idx)
                return callback
                
            cb = make_callback()
            callbacks_ref.append(cb)
            transit_idx = routing.RegisterTransitCallback(cb)
            transit_callback_indices.append(transit_idx)
            routing.SetArcCostEvaluatorOfVehicle(transit_idx, v)

        # 3. Add Time Dimension (cumulative time representing arrival times)
        # Shift capacities upper bound: max(vehicle_capacities) = 480
        max_capacity = max(vehicle_capacities)
        routing.AddDimensionWithVehicleTransits(
            transit_callback_indices,
            540,  # Max wait time (slack) allowed
            max_capacity,  # Shift time limit upper bound
            True,  # Cumulative start to zero
            "Time"
        )
        time_dimension = routing.GetDimensionOrDie("Time")

        # Set individual vehicle capacities on their End node variables
        for v in range(num_vehicles):
            end_index = routing.End(v)
            time_dimension.CumulVar(end_index).SetRange(0, vehicle_capacities[v])

        # 4. Restrict allowed vehicle for each node (Uncertainty-aware logic)
        for i in range(num_locations):
            if i == self.depot_index:
                continue
            
            loc = self.locations[i]
            severity = loc.get("severity", 0.0)
            set_size = loc.get("set_size", 0)
            
            details = get_dispatch_details(severity, set_size, self.threshold)
            allowed_idx = details["vehicle_index"]
            
            index = manager.NodeToIndex(i)
            # Sets values to -1 (can be unassigned) or the allowed vehicle index
            routing.VehicleVar(index).SetValues([-1, allowed_idx])

        # 5. Add Disjunction penalties for each source node to maximize reward
        # To ensure the solver visits as many nodes as possible (even in clean cities like Hyderabad),
        # the penalty for dropping a node must be much larger than the travel time cost.
        for i in range(num_locations):
            if i == self.depot_index:
                continue
            
            loc = self.locations[i]
            severity = loc.get("severity", 0.0)
            confidence = loc.get("confidence", 0.0)
            pop = loc.get("population_exposed", 0.0)
            
            reward = severity * confidence * pop
            # Massive penalty ensures nodes are only dropped if the vehicle runs out of 8-hour shift time
            penalty = 100000 + int(reward)
            
            index = manager.NodeToIndex(i)
            routing.AddDisjunction([index], penalty)

        # 6. Solve
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        # Limit solver CPU time to 5 seconds
        search_parameters.time_limit.seconds = 5
        
        solution = routing.SolveWithParameters(search_parameters)
        
        # 7. Format routing results
        routes = {}
        vehicle_names = {0: "inspector", 1: "van", 2: "drone"}
        vehicle_labels = {0: "Inspector Team Alpha", 1: "Enforcement Van Charlie", 2: "Drone Unit Bravo"}
        
        if not solution:
            # Fallback empty routes
            for v in range(num_vehicles):
                r_id = f"{vehicle_names[v]}_1"
                routes[r_id] = {
                    "route_id": r_id,
                    "vehicle_type": vehicle_names[v],
                    "vehicle_label": vehicle_labels[v],
                    "total_time_min": 0,
                    "stops": []
                }
            return routes

        for v in range(num_vehicles):
            v_name = vehicle_names[v]
            r_id = f"{v_name}_1"
            stops = []
            
            index = routing.Start(v)
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node != self.depot_index:
                    loc = self.locations[node]
                    
                    time_var = time_dimension.CumulVar(index)
                    arrival_time_min = solution.Value(time_var)
                    eta_str = format_eta(arrival_time_min)
                    
                    severity = loc.get("severity", 0.0)
                    pop = loc.get("population_exposed", 0.0)
                    set_size = loc.get("set_size", 0)
                    
                    details = get_dispatch_details(severity, set_size, self.threshold)
                    action = details["action"]
                    
                    # Compute ROI dynamically
                    aqi_reduction = severity * 0.05
                    sev_diff = max(0.0, severity - self.threshold)
                    if v == 0:
                        cost = 10000.0 + sev_diff * 36.0
                    elif v == 1:
                        cost = 9000.0 + sev_diff * 40.0
                    else:
                        cost = 5000.0 + sev_diff * 50.0
                        
                    roi_val = calculate_inspection_roi(pop, aqi_reduction, cost)
                    
                    stops.append({
                        "source_id": loc.get("source_id"),
                        "lat": get_coords(loc)[0],
                        "lon": get_coords(loc)[1],
                        "eta": eta_str,
                        "action": action,
                        "roi": round(roi_val, 1)
                    })
                    
                index = solution.Value(routing.NextVar(index))
                
            end_index = routing.End(v)
            total_time = solution.Value(time_dimension.CumulVar(end_index))
            
            routes[r_id] = {
                "route_id": r_id,
                "vehicle_type": v_name,
                "vehicle_label": vehicle_labels[v],
                "total_time_min": total_time,
                "stops": stops
            }
            
        return routes
