import os
from pathlib import Path
from typing import Any

from src.models.instance import PDPInstance
from src.models.node import Node, NodeType
from src.models.request import Request
from src.models.vehicle import Vehicle


ALLOW_INCOMPLETE_INSTANCE = (
    os.environ.get("PDP_ALLOW_INCOMPLETE_INSTANCE", "0").lower()
    in {"1", "true", "yes", "y"}
)


class PDPParser:
    """Parser for Li & Lim PDPTW/PDP files, ignoring time windows."""

    @staticmethod
    def read_li_lim_raw(file_path: str | os.PathLike[str]) -> dict[str, Any]:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        if not lines:
            raise ValueError(f"Empty instance file: {file_path}")

        first = lines[0].split()
        if len(first) == 3:
            K = int(first[0])
            C = int(float(first[1]))
            speed = float(first[2])
            data_start = 1
        else:
            K = int(first[0])
            C = int(float(lines[1].split()[0]))
            speed = float(lines[2].split()[0])
            data_start = 3

        nodes = []
        for line in lines[data_start:]:
            parts = line.split()
            if len(parts) < 9:
                raise ValueError(
                    f"Invalid task row in {file_path}: expected 9 columns, "
                    f"got {len(parts)}: {line}"
                )
            nodes.append(
                {
                    "id": int(parts[0]),
                    "x": float(parts[1]),
                    "y": float(parts[2]),
                    "demand": int(float(parts[3])),
                    "e": float(parts[4]),
                    "l": float(parts[5]),
                    "s": float(parts[6]),
                    "pickup": int(parts[7]),
                    "delivery": int(parts[8]),
                }
            )

        if len({node["id"] for node in nodes}) != len(nodes):
            raise ValueError(f"Duplicate task ids found in {file_path}.")
        if 0 not in {node["id"] for node in nodes}:
            raise ValueError(f"Missing depot task 0 in {file_path}.")

        raw_by_id = {node["id"]: node for node in nodes}
        depot = raw_by_id[0]
        if depot["demand"] != 0 or depot["pickup"] != 0 or depot["delivery"] != 0:
            raise ValueError("Depot task 0 must have demand=0, pickup=0, delivery=0.")

        n_requests = sum(
            1
            for node in nodes
            if (
                node["demand"] > 0
                and node["pickup"] == 0
                and node["delivery"] > 0
                and node["delivery"] in raw_by_id
                and raw_by_id[node["delivery"]]["demand"] < 0
                and raw_by_id[node["delivery"]]["pickup"] == node["id"]
                and raw_by_id[node["delivery"]]["delivery"] == 0
                and node["demand"] + raw_by_id[node["delivery"]]["demand"] == 0
            )
        )

        return {
            "n": n_requests,
            "K": K,
            "C": C,
            "speed": speed,
            "nodes": nodes,
        }

    @staticmethod
    def parse_li_lim_format(file_path: str | os.PathLike[str]) -> PDPInstance:
        raw_instance = PDPParser.read_li_lim_raw(file_path)
        instance_name = Path(file_path).stem
        instance = PDPInstance(
            name=instance_name,
            max_vehicles=int(raw_instance["K"]),
            vehicle_capacity=float(raw_instance["C"]),
            speed=float(raw_instance["speed"]),
            raw_nodes=[dict(node) for node in raw_instance["nodes"]],
        )

        for raw in raw_instance["nodes"]:
            node_type = PDPParser._infer_node_type(raw)
            instance.nodes[raw["id"]] = Node(
                id=raw["id"],
                original_id=raw["id"],
                x=raw["x"],
                y=raw["y"],
                demand=float(raw["demand"]),
                node_type=node_type,
                earliest=float(raw["e"]),
                latest=float(raw["l"]),
                service_time=float(raw["s"]),
                pickup_id=int(raw["pickup"]),
                delivery_id=int(raw["delivery"]),
            )

        depot_node = instance.nodes[0]
        depot_node.node_type = NodeType.START_DEPOT
        end_depot_node = Node(
            id=depot_node.id,
            original_id=depot_node.original_id,
            x=depot_node.x,
            y=depot_node.y,
            demand=0.0,
            node_type=NodeType.END_DEPOT,
            earliest=depot_node.earliest,
            latest=depot_node.latest,
            service_time=0.0,
        )

        for vehicle_id in range(1, instance.max_vehicles + 1):
            instance.vehicles.append(
                Vehicle(
                    id=vehicle_id,
                    capacity=instance.vehicle_capacity,
                    start_depot=depot_node,
                    end_depot=end_depot_node,
                )
            )

        PDPParser._build_requests(instance)
        instance.calculate_euclidean_distances()
        return instance

    @staticmethod
    def _infer_node_type(raw: dict[str, Any]) -> NodeType:
        if raw["id"] == 0:
            return NodeType.START_DEPOT
        if raw["demand"] > 0 and raw["pickup"] == 0 and raw["delivery"] > 0:
            return NodeType.PICKUP
        if raw["demand"] < 0 and raw["pickup"] > 0 and raw["delivery"] == 0:
            return NodeType.DELIVERY
        return NodeType.SERVICE

    @staticmethod
    def _build_requests(instance: PDPInstance) -> None:
        raw_by_id = {node["id"]: node for node in instance.raw_nodes}
        invalid_pairs = []
        request_id = 1

        for raw in instance.raw_nodes:
            pickup_id = raw["id"]
            if not (raw["demand"] > 0 and raw["pickup"] == 0 and raw["delivery"] > 0):
                continue

            delivery_id = raw["delivery"]
            delivery_raw = raw_by_id.get(delivery_id)
            reason = None
            if delivery_raw is None:
                reason = "missing delivery node"
            elif delivery_raw["demand"] >= 0:
                reason = "delivery has non-negative demand"
            elif delivery_raw["pickup"] != pickup_id:
                reason = "delivery does not point back to pickup"
            elif delivery_raw["delivery"] != 0:
                reason = "delivery row has non-zero delivery sibling"
            elif raw["demand"] + delivery_raw["demand"] != 0:
                reason = "pickup/delivery demands do not balance"

            if reason is not None:
                invalid_pairs.append((pickup_id, delivery_id, reason))
                continue

            pickup_node = instance.nodes[pickup_id]
            delivery_node = instance.nodes[delivery_id]
            instance.requests[request_id] = Request(
                id=request_id,
                pickup_node=pickup_node,
                delivery_node=delivery_node,
                demand=float(raw["demand"]),
            )
            request_id += 1

        if invalid_pairs and not ALLOW_INCOMPLETE_INSTANCE:
            shown = ", ".join(
                f"{pickup}->{delivery} ({reason})"
                for pickup, delivery, reason in invalid_pairs[:5]
            )
            suffix = "" if len(invalid_pairs) <= 5 else f", ... +{len(invalid_pairs) - 5} more"
            raise ValueError(
                f"Found {len(invalid_pairs)} invalid pickup-delivery pairs: "
                f"{shown}{suffix}. Set PDP_ALLOW_INCOMPLETE_INSTANCE=1 only if "
                "you intentionally want to solve the valid sub-instance."
            )

        if not instance.requests:
            raise ValueError("No valid pickup-delivery pairs found in instance.")
