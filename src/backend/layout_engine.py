"""Motor de distribución espacial 2D y cálculo de curvaturas de aristas para el grafo."""

import itertools
import math
import random
from typing import Dict, List, Tuple
import networkx as nx


class LayoutEngine:
    """
    Calcula las posiciones 2D de los nodos simulando una topología realista
    de red informática (no elíptica) y determina las curvaturas óptimas de las
    aristas y las posiciones de las etiquetas de peso para minimizar cruces.
    """

    @staticmethod
    def build_base_2d_slots(
        node_count: int, rng: random.Random
    ) -> List[List[Tuple[float, float]]]:
        """
        Genera ranuras 2D escalonadas por zonas dentro de un lienzo [0..16] x [0..10],
        evitando formas elípticas o colineales y distribuyendo los servidores como una red real.
        """
        width = 16.0
        height = 10.0
        x_margin = 1.3
        y_margin = 1.1
        usable_w = width - 2 * x_margin
        usable_h = height - 2 * y_margin

        preset_zones: Dict[int, List[int]] = {
            7: [1, 2, 2, 2],
            8: [1, 2, 3, 2],
            9: [1, 3, 3, 2],
            10: [1, 3, 3, 2, 1],
            11: [1, 3, 3, 3, 1],
            12: [1, 3, 3, 3, 2],
            13: [2, 3, 3, 3, 2],
            14: [1, 3, 3, 3, 3, 1],
            15: [2, 3, 3, 3, 3, 1],
            16: [2, 3, 3, 3, 3, 2],
        }

        if node_count in preset_zones:
            zone_sizes = list(preset_zones[node_count])
        else:
            zone_sizes = []
            rem = node_count
            while rem > 0:
                take = min(3, rem)
                zone_sizes.append(take)
                rem -= take

        num_zones = len(zone_sizes)
        zones_coords: List[List[Tuple[float, float]]] = []

        for z_idx, k in enumerate(zone_sizes):
            base_x = x_margin + (z_idx / max(1, num_zones - 1)) * usable_w
            zone_pts: List[Tuple[float, float]] = []

            if k == 1:
                y_frac = (
                    0.48
                    + (0.08 if z_idx % 2 == 0 else -0.08)
                    + rng.uniform(-0.08, 0.08)
                )
                x_jit = (
                    0.0
                    if z_idx in (0, num_zones - 1)
                    else rng.uniform(-0.22, 0.22)
                )
                zone_pts.append((base_x + x_jit, y_margin + y_frac * usable_h))
            else:
                band_shift = 0.065 if (z_idx % 2 == 1) else -0.065
                stagger_dir = 1.0 if (z_idx % 2 == 0) else -1.0
                raw_pts: List[Tuple[float, float]] = []

                for slot_i in range(k):
                    frac = (slot_i + 0.5) / k + band_shift
                    frac = max(0.06, min(0.94, frac))
                    y_val = (
                        y_margin
                        + frac * usable_h
                        + rng.uniform(-0.14, 0.14)
                    )
                    x_off = (
                        (slot_i - (k - 1) / 2.0) * 0.52 * stagger_dir
                        + rng.uniform(-0.12, 0.12)
                    )
                    if z_idx == 0:
                        x_off = max(-0.15, x_off * 0.35)
                    elif z_idx == num_zones - 1:
                        x_off = min(0.15, x_off * 0.35)

                    raw_pts.append(
                        (
                            base_x + x_off,
                            max(y_margin, min(height - y_margin, y_val)),
                        )
                    )

                if k == 3:
                    order = [0, 2, 1] if (z_idx % 2 == 1) else [2, 0, 1]
                elif k == 2:
                    order = [1, 0] if (z_idx % 2 == 1) else [0, 1]
                else:
                    order = list(range(k))

                for idx_o in order:
                    zone_pts.append(raw_pts[idx_o])

            zones_coords.append(zone_pts)

        return zones_coords

    @staticmethod
    def segments_intersect(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        p4: Tuple[float, float],
    ) -> bool:
        """Verifica si el segmento p1-p2 se cruza propiamente con el segmento p3-p4."""
        def ccw(
            a: Tuple[float, float],
            b: Tuple[float, float],
            c: Tuple[float, float],
        ) -> float:
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

        d1 = ccw(p1, p2, p3)
        d2 = ccw(p1, p2, p4)
        d3 = ccw(p3, p4, p1)
        d4 = ccw(p3, p4, p2)

        return ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
            (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
        )

    @staticmethod
    def point_to_segment_dist(
        p: Tuple[float, float],
        a: Tuple[float, float],
        b: Tuple[float, float],
    ) -> float:
        """Calcula la distancia euclidiana mínima desde el punto p al interior del segmento a-b."""
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        l2 = dx * dx + dy * dy
        if l2 < 1e-6:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2
        if t <= 0.05 or t >= 0.95:
            return float("inf")
        proj_x = a[0] + t * dx
        proj_y = a[1] + t * dy
        return math.hypot(p[0] - proj_x, p[1] - proj_y)

    @classmethod
    def calculate_positions(
        cls, graph: nx.DiGraph, layout_seed: int = 101
    ) -> Dict[str, Tuple[float, float]]:
        """
        Calcula las posiciones 2D de todos los nodos combinando ranuras por zonas,
        permutación óptima intrazona contra cruces y relajación continua de fuerzas.
        """
        nodes = list(graph.nodes)
        node_count = len(nodes)

        if node_count == 0:
            return {}

        if node_count == 1:
            return {nodes[0]: (8.0, 5.0)}

        rng = random.Random(layout_seed)
        node_rank = {node: idx for idx, node in enumerate(nodes)}

        try:
            topo_nodes = list(
                nx.lexicographical_topological_sort(
                    graph, key=lambda n: node_rank.get(n, 0)
                )
            )
        except nx.NetworkXUnfeasible:
            topo_nodes = list(nodes)

        zones_coords = cls.build_base_2d_slots(node_count, rng)
        zones_nodes: List[List[str]] = []
        cursor = 0

        for zone_pts in zones_coords:
            k = len(zone_pts)
            zones_nodes.append(list(topo_nodes[cursor : cursor + k]))
            cursor += k

        positions: Dict[str, List[float]] = {}
        for z_idx, zone_pts in enumerate(zones_coords):
            for i, u in enumerate(zones_nodes[z_idx]):
                positions[u] = [zone_pts[i][0], zone_pts[i][1]]

        edges = list(graph.edges)

        for _sweep in range(4):
            for z_idx in range(len(zones_coords)):
                z_nodes = zones_nodes[z_idx]
                z_pts = zones_coords[z_idx]
                k = len(z_nodes)

                if k <= 1:
                    continue

                best_perm = tuple(range(k))
                best_cost = float("inf")

                for perm in itertools.permutations(range(k)):
                    for idx_in_zone, pt_idx in enumerate(perm):
                        u = z_nodes[idx_in_zone]
                        positions[u][0], positions[u][1] = z_pts[pt_idx]

                    cost = 0.0

                    for u, v in edges:
                        p1 = (positions[u][0], positions[u][1])
                        p2 = (positions[v][0], positions[v][1])
                        dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                        cost += dist * 1.2
                        if (
                            node_rank.get(u, 0) < node_rank.get(v, 0)
                            and p2[0] < p1[0] + 0.3
                        ):
                            cost += (p1[0] + 0.3 - p2[0]) * 8.0

                    for idx1 in range(len(edges)):
                        u1, v1 = edges[idx1]
                        if u1 not in z_nodes and v1 not in z_nodes:
                            continue
                        p1 = (positions[u1][0], positions[u1][1])
                        p2 = (positions[v1][0], positions[v1][1])
                        for idx2 in range(idx1 + 1, len(edges)):
                            u2, v2 = edges[idx2]
                            if u1 in (u2, v2) or v1 in (u2, v2):
                                continue
                            p3 = (positions[u2][0], positions[u2][1])
                            p4 = (positions[v2][0], positions[v2][1])
                            if cls.segments_intersect(p1, p2, p3, p4):
                                cost += 35.0

                    if cost < best_cost:
                        best_cost = cost
                        best_perm = perm

                for idx_in_zone, pt_idx in enumerate(best_perm):
                    u = z_nodes[idx_in_zone]
                    positions[u][0], positions[u][1] = z_pts[pt_idx]

        width = 16.0
        height = 10.0
        x_margin = 1.2
        y_margin = 1.0
        min_node_dist = 2.65 if node_count <= 12 else 2.30
        ideal_edge_len = 3.6

        for iteration in range(85):
            temp = 0.12 * (1.0 - iteration / 85.0)
            forces = {u: [0.0, 0.0] for u in nodes}

            for i in range(node_count):
                u = nodes[i]
                ux, uy = positions[u]
                for j in range(i + 1, node_count):
                    v = nodes[j]
                    vx, vy = positions[v]
                    dx = ux - vx
                    dy = uy - vy
                    dist = math.hypot(dx, dy)
                    if dist < 1e-4:
                        dx, dy, dist = 0.1, 0.1, 0.14
                    if dist < min_node_dist * 1.35:
                        rep = ((min_node_dist * 1.35 - dist) ** 2 * 1.9) / dist
                        forces[u][0] += dx * rep
                        forces[u][1] += dy * rep * 1.2
                        forces[v][0] -= dx * rep
                        forces[v][1] -= dy * rep * 1.2

            for u, v in edges:
                ux, uy = positions[u]
                vx, vy = positions[v]
                dx = vx - ux
                dy = vy - uy
                dist = math.hypot(dx, dy)
                if dist > 1e-4:
                    diff = (dist - ideal_edge_len) * 0.08
                    fx = (dx / dist) * diff
                    fy = (dy / dist) * diff
                    forces[u][0] += fx
                    forces[u][1] += fy
                    forces[v][0] -= fx
                    forces[v][1] -= fy
                if node_rank.get(u, 0) < node_rank.get(v, 0) and dx < 1.1:
                    push_x = (1.1 - dx) * 0.65
                    forces[u][0] -= push_x
                    forces[v][0] += push_x

            clearance_dist = 1.35
            for u, v in edges:
                x1, y1 = positions[u]
                x2, y2 = positions[v]
                seg_dx = x2 - x1
                seg_dy = y2 - y1
                seg_len_sq = seg_dx * seg_dx + seg_dy * seg_dy
                if seg_len_sq < 1e-4:
                    continue
                for w in nodes:
                    if w == u or w == v:
                        continue
                    wx, wy = positions[w]
                    t = ((wx - x1) * seg_dx + (wy - y1) * seg_dy) / seg_len_sq
                    if 0.08 < t < 0.92:
                        proj_x = x1 + t * seg_dx
                        proj_y = y1 + t * seg_dy
                        odx = wx - proj_x
                        ody = wy - proj_y
                        odist = math.hypot(odx, ody)
                        if odist < clearance_dist:
                            if odist < 1e-4:
                                seg_len = math.sqrt(seg_len_sq)
                                odx = -seg_dy / seg_len
                                ody = seg_dx / seg_len
                                odist = 0.01
                            push = ((clearance_dist - odist) * 2.4) / odist
                            forces[w][0] += odx * push
                            forces[w][1] += ody * push
                            forces[u][0] -= odx * push * 0.2
                            forces[u][1] -= ody * push * 0.2
                            forces[v][0] -= odx * push * 0.2
                            forces[v][1] -= ody * push * 0.2

            for u in nodes:
                fx, fy = forces[u]
                mag = math.hypot(fx, fy)
                if mag > 1.0:
                    fx /= mag
                    fy /= mag
                positions[u][0] = max(
                    x_margin, min(width - x_margin, positions[u][0] + fx * temp)
                )
                positions[u][1] = max(
                    y_margin, min(height - y_margin, positions[u][1] + fy * temp)
                )

        xs = [p[0] for p in positions.values()]
        ys = [p[1] for p in positions.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(1e-3, max_x - min_x)
        span_y = max(1e-3, max_y - min_y)

        final_positions: Dict[str, Tuple[float, float]] = {}
        for u, (px, py) in positions.items():
            nx_coord = ((px - min_x) / span_x) * 14.0 + 1.0
            ny_coord = ((py - min_y) / span_y) * 8.4 + 0.8
            final_positions[u] = (float(nx_coord), float(ny_coord))

        return final_positions

    @staticmethod
    def compute_smart_curvatures_and_labels(
        graph: nx.DiGraph,
        positions: Dict[str, Tuple[float, float]],
    ) -> Tuple[
        Dict[Tuple[str, str], float],
        Dict[Tuple[str, str], Tuple[float, float]],
    ]:
        """
        Determina la curvatura óptima de cada arista y la posición ideal de la
        etiqueta de peso sobre la trayectoria curva.
        """
        nodes = list(graph.nodes)
        edges = list(graph.edges)

        def bezier_point(
            x1: float,
            y1: float,
            x2: float,
            y2: float,
            rad: float,
            t: float,
        ) -> Tuple[float, float]:
            dx = x2 - x1
            dy = y2 - y1
            cx = (x1 + x2) / 2.0 + rad * dy
            cy = (y1 + y2) / 2.0 - rad * dx
            rem = 1.0 - t
            bx = rem * rem * x1 + 2.0 * rem * t * cx + t * t * x2
            by = rem * rem * y1 + 2.0 * rem * t * cy + t * t * y2
            return bx, by

        edge_curvatures: Dict[Tuple[str, str], float] = {}
        placed_midpoints: List[Tuple[float, float]] = []

        candidate_rads = [0.0, 0.10, -0.10, 0.18, -0.18, 0.26, -0.26]

        for u, v in edges:
            if (u, v) in edge_curvatures:
                continue

            has_reverse = graph.has_edge(v, u)
            same_weight = (
                has_reverse
                and graph[u][v].get("weight") == graph[v][u].get("weight")
            )

            x1, y1 = positions[u]
            x2, y2 = positions[v]
            best_rad = 0.0
            best_cost = float("inf")

            rads_to_try = (
                candidate_rads
                if (not has_reverse or same_weight)
                else [0.16, 0.24]
            )

            for rad in rads_to_try:
                cost = abs(rad) * 1.8

                for t in (0.25, 0.4, 0.5, 0.6, 0.75):
                    bx, by = bezier_point(x1, y1, x2, y2, rad, t)
                    for w in nodes:
                        if w == u or w == v:
                            continue
                        wx, wy = positions[w]
                        d = math.hypot(bx - wx, by - wy)
                        if d < 1.35:
                            cost += (1.35 - d) ** 2 * 30.0

                mx, my = bezier_point(x1, y1, x2, y2, rad, 0.5)
                for pmx, pmy in placed_midpoints:
                    md = math.hypot(mx - pmx, my - pmy)
                    if md < 0.75:
                        cost += (0.75 - md) ** 2 * 12.0

                if cost < best_cost:
                    best_cost = cost
                    best_rad = rad

            edge_curvatures[(u, v)] = best_rad
            placed_midpoints.append(bezier_point(x1, y1, x2, y2, best_rad, 0.5))

            if same_weight:
                edge_curvatures[(v, u)] = -best_rad

        label_coords: Dict[Tuple[str, str], Tuple[float, float]] = {}
        placed_labels: List[Tuple[float, float]] = []
        candidate_ts = [0.50, 0.40, 0.60, 0.33, 0.67, 0.27, 0.73]

        for u, v in edges:
            if (u, v) in label_coords:
                continue

            has_reverse = graph.has_edge(v, u)
            same_weight = (
                has_reverse
                and graph[u][v].get("weight") == graph[v][u].get("weight")
            )

            x1, y1 = positions[u]
            x2, y2 = positions[v]
            rad = edge_curvatures[(u, v)]
            best_pt = bezier_point(x1, y1, x2, y2, rad, 0.5)
            best_cost = float("inf")

            for t in candidate_ts:
                lx, ly = bezier_point(x1, y1, x2, y2, rad, t)
                cost = abs(t - 0.5) * 1.2

                for w in nodes:
                    wx, wy = positions[w]
                    d = math.hypot(lx - wx, ly - wy)
                    if d < 1.15:
                        cost += (1.15 - d) ** 2 * 40.0

                for plx, ply in placed_labels:
                    ld = math.hypot(lx - plx, ly - ply)
                    if ld < 0.85:
                        cost += (0.85 - ld) ** 2 * 35.0

                if cost < best_cost:
                    best_cost = cost
                    best_pt = (lx, ly)

            label_coords[(u, v)] = best_pt
            placed_labels.append(best_pt)

            if same_weight:
                label_coords[(v, u)] = best_pt

        return edge_curvatures, label_coords
