"""Generador de grafos dirigidos ponderados (modo aleatorio y modo manual)."""

import math
import random
from typing import Any, Dict, List, Tuple, cast
import networkx as nx
from backend.layout_engine import LayoutEngine


class GraphGenerator:
    """
    Se encarga de la creación y validación de grafos dirigidos ponderados:
    - Generación aleatoria con topología realista de red, pesos en [10..30],
      y configuración independiente de conexiones bidireccionales y ciclos.
    - Construcción y validación de grafos manuales.
    """

    @staticmethod
    def validate_node_count(node_count: int) -> None:
        """Valida que la cantidad de nodos sea un entero entre 7 y 16."""
        if (
            not isinstance(node_count, int)
            or isinstance(node_count, bool)
            or not 7 <= node_count <= 16
        ):
            raise ValueError("El número de nodos debe estar entre 7 y 16.")

    @classmethod
    def create_empty_graph(
        cls, node_count: int
    ) -> Tuple[nx.DiGraph, int]:
        """Crea un grafo con los nodos N1..Nn sin aristas para el modo de construcción manual."""
        cls.validate_node_count(node_count)
        graph = nx.DiGraph()
        layout_seed = random.randint(1, 1_000_000)
        nodes = [f"N{i}" for i in range(1, node_count + 1)]
        graph.add_nodes_from(nodes)
        return graph, layout_seed

    @classmethod
    def create_random_graph(
        cls,
        node_count: int,
        allow_bidirectional: bool = False,
        allow_cycles: bool = False,
    ) -> Tuple[nx.DiGraph, int]:
        """
        Genera un grafo dirigido ponderado aleatorio con pesos entre 10 y 30.
        - Si allow_bidirectional=True y allow_cycles=False, añade conexiones
          bidireccionales garantizando que no se formen ciclos de longitud >= 3.
        - Si allow_cycles=True, permite la formación aleatoria de algunos ciclos dirigidos.
        """
        cls.validate_node_count(node_count)

        graph = nx.DiGraph()
        layout_seed = random.randint(1, 1_000_000)

        nodes = [f"N{i}" for i in range(1, node_count + 1)]
        graph.add_nodes_from(nodes)

        slot_rng = random.Random(layout_seed)
        zones_coords = LayoutEngine.build_base_2d_slots(node_count, slot_rng)

        pos: Dict[str, Tuple[float, float]] = {}
        cursor = 0
        node_zone: Dict[str, int] = {}

        for z_idx, zone_pts in enumerate(zones_coords):
            for pt in zone_pts:
                u = nodes[cursor]
                pos[u] = pt
                node_zone[u] = z_idx
                cursor += 1

        def can_add_clean_edge(
            edge_u: str,
            edge_v: str,
            allow_crossing: bool = False,
            require_forward_x: bool = True,
        ) -> bool:
            if graph.has_edge(edge_u, edge_v):
                return False
            pt_a, pt_b = pos[edge_u], pos[edge_v]
            if require_forward_x and pt_b[0] < pt_a[0] - 0.35:
                return False
            for w in nodes:
                if w == edge_u or w == edge_v:
                    continue
                if LayoutEngine.point_to_segment_dist(pos[w], pt_a, pt_b) < 0.95:
                    return False
            if not allow_crossing:
                for eu, ev in graph.edges:
                    if eu in (edge_u, edge_v) or ev in (edge_u, edge_v):
                        continue
                    if LayoutEngine.segments_intersect(
                        pt_a, pt_b, pos[eu], pos[ev]
                    ):
                        return False
            return True

        # 1. Garantizar que cada nodo (excepto N1) tenga al menos una entrada
        for j in range(1, node_count):
            v = nodes[j]
            zv = node_zone[v]
            candidates = []
            for i in range(j):
                u = nodes[i]
                zu = node_zone[u]
                zone_diff = zv - zu
                if 0 <= zone_diff <= 2:
                    dist = math.hypot(
                        pos[u][0] - pos[v][0], pos[u][1] - pos[v][1]
                    )
                    zone_penalty = (
                        0.0
                        if zone_diff == 1
                        else (1.4 if zone_diff == 0 else 3.2)
                    )
                    candidates.append(
                        (dist + zone_penalty + random.uniform(0, 0.45), u)
                    )
            candidates.sort(key=lambda item: item[0])

            added = False
            for _, u in candidates:
                if can_add_clean_edge(u, v, allow_crossing=False):
                    graph.add_edge(u, v, weight=random.randint(10, 30))
                    added = True
                    break
            if not added and candidates:
                graph.add_edge(
                    candidates[0][1], v, weight=random.randint(10, 30)
                )

        # 2. Garantizar que cada nodo (excepto el último) tenga al menos una salida
        for i in range(node_count - 1):
            u = nodes[i]
            if len(list(graph.successors(u))) > 0:
                continue
            zu = node_zone[u]
            candidates = []
            for j in range(i + 1, node_count):
                v = nodes[j]
                zv = node_zone[v]
                zone_diff = zv - zu
                if 0 <= zone_diff <= 2:
                    dist = math.hypot(
                        pos[u][0] - pos[v][0], pos[u][1] - pos[v][1]
                    )
                    zone_penalty = (
                        0.0
                        if zone_diff == 1
                        else (1.4 if zone_diff == 0 else 3.2)
                    )
                    candidates.append(
                        (dist + zone_penalty + random.uniform(0, 0.45), v)
                    )
            candidates.sort(key=lambda item: item[0])

            added = False
            for _, v in candidates:
                if can_add_clean_edge(u, v, allow_crossing=False):
                    graph.add_edge(u, v, weight=random.randint(10, 30))
                    added = True
                    break
            if not added and candidates:
                graph.add_edge(
                    u, candidates[0][1], weight=random.randint(10, 30)
                )

        # 3. Añadir conexiones adicionales de red sin saturar ni cruzar aristas
        for i in range(node_count - 1):
            u = nodes[i]
            zu = node_zone[u]
            target_out = 2 if i > 0 else min(3, max(2, node_count // 5))
            if random.random() < 0.35 and i < node_count - 3:
                target_out = min(3, target_out + 1)

            if len(list(graph.successors(u))) >= target_out:
                continue

            candidates = []
            for j in range(i + 1, node_count):
                v = nodes[j]
                zv = node_zone[v]
                zone_diff = zv - zu
                if 0 <= zone_diff <= 2 and not graph.has_edge(u, v):
                    dist = math.hypot(
                        pos[u][0] - pos[v][0], pos[u][1] - pos[v][1]
                    )
                    zone_penalty = (
                        0.0
                        if zone_diff == 1
                        else (1.2 if zone_diff == 0 else 3.5)
                    )
                    candidates.append(
                        (dist + zone_penalty + random.uniform(0, 0.6), v)
                    )
            candidates.sort(key=lambda item: item[0])

            for _, v in candidates:
                if len(list(graph.successors(u))) >= target_out:
                    break
                if len(list(graph.predecessors(v))) >= 3 and v != nodes[-1]:
                    continue
                if can_add_clean_edge(u, v, allow_crossing=False):
                    graph.add_edge(u, v, weight=random.randint(10, 30))

        # 4. Conexiones bidireccionales aleatorias (evitando ciclos de longitud >= 3 si allow_cycles=False)
        base_edges = list(graph.edges)

        if allow_bidirectional and base_edges:
            bidir_candidates = list(base_edges)
            random.shuffle(bidir_candidates)
            if not allow_cycles:
                def _shared_neighbors(edge: Tuple[str, str]) -> int:
                    eu, ev = edge
                    nu = set(graph.predecessors(eu)) | set(graph.successors(eu))
                    nv = set(graph.predecessors(ev)) | set(graph.successors(ev))
                    return len((nu & nv) - {eu, ev})

                bidir_candidates.sort(key=_shared_neighbors)

            bidir_count = max(
                2,
                min(
                    len(bidir_candidates) // 2,
                    int(
                        round(
                            len(bidir_candidates) * random.uniform(0.22, 0.35)
                        )
                    ),
                ),
            )
            added_bidir = 0
            for u, v in bidir_candidates:
                if added_bidir >= bidir_count:
                    break
                if graph.has_edge(v, u):
                    continue
                existing_weight = int(cast(Any, graph[u][v]["weight"]))
                if not allow_cycles:
                    graph.remove_edge(u, v)
                    creates_cycle = nx.has_path(graph, u, v) or nx.has_path(
                        graph, v, u
                    )
                    graph.add_edge(u, v, weight=existing_weight)
                    if creates_cycle:
                        continue
                graph.add_edge(v, u, weight=existing_weight)
                added_bidir += 1

            # Si las cuerdas transitivas impidieron crear al menos 2 aristas bidireccionales,
            # podar cuerdas redundantes de forma segura para permitir bidireccionalidad sin ciclos
            if not allow_cycles and added_bidir < 2:
                for u, v in bidir_candidates:
                    if added_bidir >= 2:
                        break
                    if graph.has_edge(v, u):
                        continue
                    existing_weight = int(cast(Any, graph[u][v]["weight"]))
                    graph.remove_edge(u, v)
                    removed_chords: List[Tuple[str, str, int]] = []
                    while nx.has_path(graph, u, v) or nx.has_path(graph, v, u):
                        alt_path = (
                            nx.shortest_path(graph, u, v)
                            if nx.has_path(graph, u, v)
                            else nx.shortest_path(graph, v, u)
                        )
                        chord_removed = False
                        for idx in range(len(alt_path) - 1):
                            ca, cb = alt_path[idx], alt_path[idx + 1]
                            if (
                                not graph.has_edge(cb, ca)
                                and len(list(graph.successors(ca))) > 1
                                and len(list(graph.predecessors(cb))) > 1
                            ):
                                cw = int(cast(Any, graph[ca][cb]["weight"]))
                                graph.remove_edge(ca, cb)
                                if nx.has_path(graph, nodes[0], cb):
                                    removed_chords.append((ca, cb, cw))
                                    chord_removed = True
                                    break
                                graph.add_edge(ca, cb, weight=cw)
                        if not chord_removed:
                            break
                    if not nx.has_path(graph, u, v) and not nx.has_path(
                        graph, v, u
                    ):
                        graph.add_edge(u, v, weight=existing_weight)
                        graph.add_edge(v, u, weight=existing_weight)
                        added_bidir += 1
                    else:
                        for ca, cb, cw in removed_chords:
                            graph.add_edge(ca, cb, weight=cw)
                        graph.add_edge(u, v, weight=existing_weight)

        # 5. Ciclos dirigidos aleatorios (si allow_cycles=True)
        if allow_cycles:
            cycle_candidates: List[Tuple[float, str, str]] = []
            for i in range(node_count):
                for j in range(i + 1, node_count):
                    u = nodes[i]
                    v = nodes[j]
                    if graph.has_edge(u, v) or graph.has_edge(v, u):
                        continue
                    zone_diff = node_zone[v] - node_zone[u]
                    if 1 <= zone_diff <= 3 and nx.has_path(graph, u, v):
                        dist = math.hypot(
                            pos[v][0] - pos[u][0], pos[v][1] - pos[u][1]
                        )
                        zone_penalty = 0.0 if zone_diff <= 2 else 1.5
                        cycle_candidates.append(
                            (dist + zone_penalty + random.uniform(0, 0.8), v, u)
                        )

            cycle_candidates.sort(key=lambda item: item[0])
            target_cycles = random.randint(1, min(3, max(1, node_count // 5)))
            added_cycles = 0

            for _, src_back, dst_back in cycle_candidates:
                if added_cycles >= target_cycles:
                    break
                if can_add_clean_edge(
                    src_back,
                    dst_back,
                    allow_crossing=False,
                    require_forward_x=False,
                ):
                    graph.add_edge(
                        src_back, dst_back, weight=random.randint(10, 30)
                    )
                    added_cycles += 1

            if added_cycles == 0:
                for _, src_back, dst_back in cycle_candidates:
                    if can_add_clean_edge(
                        src_back,
                        dst_back,
                        allow_crossing=True,
                        require_forward_x=False,
                    ):
                        graph.add_edge(
                            src_back, dst_back, weight=random.randint(10, 30)
                        )
                        added_cycles += 1
                        break

            if added_cycles == 0:
                fallback_candidates: List[Tuple[float, str, str]] = []
                for i in range(node_count):
                    for j in range(i + 1, node_count):
                        u = nodes[i]
                        v = nodes[j]
                        if graph.has_edge(u, v) or graph.has_edge(v, u):
                            continue
                        if nx.has_path(graph, u, v):
                            p1, p2 = pos[v], pos[u]
                            min_clearance = min(
                                (
                                    LayoutEngine.point_to_segment_dist(
                                        pos[w], p1, p2
                                    )
                                    for w in nodes
                                    if w != u and w != v
                                ),
                                default=float("inf"),
                            )
                            dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
                            fallback_candidates.append(
                                (-min_clearance + dist * 0.05, v, u)
                            )
                if fallback_candidates:
                    fallback_candidates.sort(key=lambda item: item[0])
                    _, best_src, best_dst = fallback_candidates[0]
                    graph.add_edge(
                        best_src,
                        best_dst,
                        weight=random.randint(10, 30),
                    )
                    added_cycles += 1
                else:
                    for u in nodes:
                        for mid in graph.successors(u):
                            for v in graph.successors(mid):
                                if u != v and not graph.has_edge(v, u):
                                    graph.add_edge(
                                        v,
                                        u,
                                        weight=random.randint(10, 30),
                                    )
                                    added_cycles += 1
                                    break
                            if added_cycles > 0:
                                break
                        if added_cycles > 0:
                            break

        return graph, layout_seed

    @classmethod
    def create_manual_graph(
        cls,
        node_count: int,
        edges: List[Tuple[str, str, int]],
        preserve_seed: int = 0,
    ) -> Tuple[nx.DiGraph, int]:
        """Valida las conexiones manuales y construye el grafo dirigido ponderado."""
        cls.validate_node_count(node_count)

        if not edges:
            raise ValueError("El grafo debe tener al menos una arista.")

        nodes = [f"N{i}" for i in range(1, node_count + 1)]
        candidate_graph = nx.DiGraph()
        candidate_graph.add_nodes_from(nodes)

        seen_edges = set()

        for source, target, weight in edges:
            if source not in candidate_graph or target not in candidate_graph:
                raise ValueError(
                    f"La arista {source} -> {target} contiene un vértice inexistente."
                )

            if source == target:
                raise ValueError(
                    "No se permiten aristas de un vértice a sí mismo."
                )

            if (
                not isinstance(weight, int)
                or isinstance(weight, bool)
                or weight <= 0
            ):
                raise ValueError(
                    "Todos los pesos deben ser enteros positivos."
                )

            edge = (source, target)
            if edge in seen_edges:
                raise ValueError(
                    f"La conexión {source} -> {target} está repetida."
                )

            seen_edges.add(edge)
            candidate_graph.add_edge(source, target, weight=weight)

        layout_seed = (
            preserve_seed
            if preserve_seed > 0
            else (
                sum((idx + 1) * ord(ch) for idx, ch in enumerate(repr(edges)))
                % 1_000_000
                + 1
            )
        )

        return candidate_graph, layout_seed
