import itertools
import math
import random
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk
from typing import Dict, List, Optional, Set, Tuple, Any, cast

import networkx as nx
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg,
    NavigationToolbar2Tk
)
from matplotlib.figure import Figure

class BarraHerramientasEspanol(NavigationToolbar2Tk):
    toolitems = (
        ("Inicio", "Restablecer la vista inicial", "home", "home"),
        ("Anterior", "Volver a la vista anterior", "back", "back"),
        ("Siguiente", "Recuperar la vista siguiente", "forward", "forward"),
        (None, None, None, None),
        ("Mover", "Desplazar el gráfico con el ratón", "move", "pan"),
        ("Zoom", "Ampliar una región del gráfico", "zoom_to_rect", "zoom"),
        (None, None, None, None),
        ("Guardar", "Guardar el gráfico como imagen", "filesave", "save_figure"),
    )

    def apply_dark_style(self) -> None:
        try:
            self.config(
                background="#0d1117",
                bd=0,
                highlightthickness=0
            )
        except tk.TclError:
            pass

        for child in self.winfo_children():
            for opt, val in (
                ("background", "#0d1117"),
                ("fg", "#c9d1d9"),
                ("activebackground", "#161b22"),
                ("activeforeground", "#e6edf3"),
                ("selectcolor", "#161b22"),
                ("relief", "flat"),
                ("bd", 0),
                ("highlightthickness", 0),
            ):
                try:
                    child.configure(**{opt: val})
                except tk.TclError:
                    pass
            if hasattr(child, "_image_file") and hasattr(
                self, "_set_image_for_button"
            ):
                try:
                    self._set_image_for_button(child)
                except (tk.TclError, AttributeError, OSError):
                    pass

    def save_figure(self):
        filename = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Guardar gráfico",
            initialfile="grafo_camino_minimo.png",
            defaultextension=".png",
            filetypes=(
                ("Imagen PNG", "*.png"),
                ("Documento PDF", "*.pdf"),
                ("Imagen SVG", "*.svg"),
            ),
        )

        if not filename:
            return

        try:
            self.canvas.figure.savefig(
                filename,
                bbox_inches="tight",
                facecolor=self.canvas.figure.get_facecolor()
            )
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Error al guardar",
                f"No se pudo guardar el gráfico.\n{error}",
                parent=self.winfo_toplevel()
            )
            return

        messagebox.showinfo(
            "Gráfico guardado",
            f"El gráfico se guardó correctamente en:\n{filename}",
            parent=self.winfo_toplevel()
        )

class ProjectInfo:
    def __init__(self) -> None:
        self.course = "Matemática Computacional (1AMA0726)"
        self.theme = "Algoritmos de caminos mínimos"
        self.delivery = "Entrega final de la semana 11 (TB)"
        self.group = "3"

        self.integrants = [
            "Adriana Sofia Gamboa Coronado",
            "Edward Miguel Rodríguez Mamani",
            "Edwart Mathias Estrada Camus",
            "Ruben Alvaro Palpa Guimaray",
            "Tayra Valentina Espinoza Ramírez",
        ]

class GraphModel:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

        self.labels: Dict[
            str, Tuple[float, Optional[str], int]
        ] = {}

        self.label_history: Dict[
            str, List[Tuple[float, Optional[str], int, bool]]
        ] = {}

        self.optimal_predecessors: Dict[str, List[str]] = {}
        self.last_tie_iteration: Dict[str, int] = {}

        self.decision_history: List[str] = []

        self.processed_nodes: List[str] = []

        self.iteration = 0

        self.source: Optional[str] = None
        self.target: Optional[str] = None

        self.current_node: Optional[str] = None

        self.algorithm_finished = False

        self.layout_seed = 101

    @staticmethod
    def build_base_2d_slots(
        node_count: int,
        rng: random.Random
    ) -> List[List[Tuple[float, float]]]:
        width = 16.0
        height = 10.0
        x_margin = 1.3
        y_margin = 1.1
        usable_w = width - 2 * x_margin
        usable_h = height - 2 * y_margin

        preset_zones: Dict[int, List[int]] = {
            7: [1, 2, 3, 1],
            8: [1, 2, 2, 2, 1],
            9: [1, 2, 3, 2, 1],
            10: [1, 3, 3, 2, 1],
            11: [1, 3, 3, 3, 1],
            12: [1, 2, 3, 3, 2, 1],
            13: [1, 3, 3, 3, 2, 1],
            14: [1, 3, 3, 3, 3, 1],
            15: [1, 2, 3, 3, 3, 2, 1],
            16: [1, 2, 3, 3, 3, 3, 1],
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
            base_x = (
                x_margin
                + (z_idx / max(1, num_zones - 1)) * usable_w
            )
            zone_pts: List[Tuple[float, float]] = []

            if z_idx in (0, num_zones - 1) and k == 1:
                zone_pts.append(
                    (
                        base_x,
                        height / 2.0
                    )
                )
            elif k == 1:
                y_frac = (
                    0.48
                    + (0.08 if z_idx % 2 == 0 else -0.08)
                    + rng.uniform(-0.08, 0.08)
                )
                x_jit = rng.uniform(-0.22, 0.22)
                zone_pts.append(
                    (
                        base_x + x_jit,
                        y_margin + y_frac * usable_h
                    )
                )
            else:
                band_shift = (
                    0.065 if (z_idx % 2 == 1) else -0.065
                )
                stagger_dir = (
                    1.0 if (z_idx % 2 == 0) else -1.0
                )
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
                        (slot_i - (k - 1) / 2.0)
                        * 0.52
                        * stagger_dir
                        + rng.uniform(-0.12, 0.12)
                    )
                    if z_idx == 0:
                        x_off = max(-0.15, x_off * 0.35)
                    elif z_idx == num_zones - 1:
                        x_off = min(0.15, x_off * 0.35)

                    raw_pts.append(
                        (
                            base_x + x_off,
                            max(
                                y_margin,
                                min(height - y_margin, y_val)
                            ),
                        )
                    )

                if k == 3:
                    order = (
                        [0, 2, 1]
                        if (z_idx % 2 == 1)
                        else [2, 0, 1]
                    )
                elif k == 2:
                    order = (
                        [1, 0]
                        if (z_idx % 2 == 1)
                        else [0, 1]
                    )
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
        def ccw(
            a: Tuple[float, float],
            b: Tuple[float, float],
            c: Tuple[float, float],
        ) -> float:
            return (
                (b[0] - a[0]) * (c[1] - a[1])
                - (b[1] - a[1]) * (c[0] - a[0])
            )

        d1 = ccw(p1, p2, p3)
        d2 = ccw(p1, p2, p4)
        d3 = ccw(p3, p4, p1)
        d4 = ccw(p3, p4, p2)

        return (
            (d2 < 0 < d1 or d1 < 0 < d2)
            and (d4 < 0 < d3 or d3 < 0 < d4)
        )

    @staticmethod
    def point_to_segment_dist(
        p: Tuple[float, float],
        a: Tuple[float, float],
        b: Tuple[float, float],
    ) -> float:
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

    def reset_algorithm_data(self) -> None:
        self.labels.clear()
        self.label_history.clear()
        self.optimal_predecessors.clear()
        self.last_tie_iteration.clear()
        self.decision_history.clear()
        self.processed_nodes.clear()

        self.iteration = 0
        self.source = None
        self.target = None
        self.current_node = None

        self.algorithm_finished = False

    def initialize_empty_graph(self, node_count: int) -> None:
        if (
            not isinstance(node_count, int)
            or isinstance(node_count, bool)
            or not 7 <= node_count <= 16
        ):
            raise ValueError(
                "El número de nodos debe estar entre 7 y 16."
            )
        self.graph.clear()
        self.reset_algorithm_data()
        self.layout_seed = random.randint(1, 1_000_000)
        nodes = [f"N{i}" for i in range(1, node_count + 1)]
        self.graph.add_nodes_from(nodes)

    def create_random_graph(
        self,
        node_count: int,
        allow_bidirectional: bool = False,
        allow_cycles: bool = False,
    ) -> None:
        if (
            not isinstance(node_count, int)
            or isinstance(node_count, bool)
            or not 7 <= node_count <= 16
        ):
            raise ValueError(
                "El número de nodos debe estar entre 7 y 16."
            )
        self.graph.clear()
        self.reset_algorithm_data()

        self.layout_seed = random.randint(1, 1_000_000)

        nodes = [f"N{i}" for i in range(1, node_count + 1)]

        self.graph.add_nodes_from(nodes)

        slot_rng = random.Random(self.layout_seed)
        zones_coords = self.build_base_2d_slots(
            node_count,
            slot_rng
        )

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
            if self.graph.has_edge(edge_u, edge_v):
                return False
            pt_a, pt_b = pos[edge_u], pos[edge_v]
            if require_forward_x and pt_b[0] < pt_a[0] - 0.35:
                return False
            for w in nodes:
                if w == edge_u or w == edge_v:
                    continue
                if self.point_to_segment_dist(pos[w], pt_a, pt_b) < 0.95:
                    return False
            if not allow_crossing:
                for eu, ev in self.graph.edges:
                    if eu in (edge_u, edge_v) or ev in (edge_u, edge_v):
                        continue
                    if self.segments_intersect(
                        pt_a,
                        pt_b,
                        pos[eu],
                        pos[ev]
                    ):
                        return False
            return True

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
                        pos[u][0] - pos[v][0],
                        pos[u][1] - pos[v][1]
                    )
                    zone_penalty = (
                        0.0
                        if zone_diff == 1
                        else (1.4 if zone_diff == 0 else 3.2)
                    )
                    candidates.append(
                        (
                            dist + zone_penalty + random.uniform(0, 0.45),
                            u
                        )
                    )
            candidates.sort(key=lambda item: item[0])

            added = False
            for _, u in candidates:
                if can_add_clean_edge(u, v, allow_crossing=False):
                    self.graph.add_edge(
                        u,
                        v,
                        weight=random.randint(10, 30)
                    )
                    added = True
                    break
            if not added and candidates:
                self.graph.add_edge(
                    candidates[0][1],
                    v,
                    weight=random.randint(10, 30)
                )

        for i in range(node_count - 1):
            u = nodes[i]
            if len(list(self.graph.successors(u))) > 0:
                continue
            zu = node_zone[u]
            candidates = []
            for j in range(i + 1, node_count):
                v = nodes[j]
                zv = node_zone[v]
                zone_diff = zv - zu
                if 0 <= zone_diff <= 2:
                    dist = math.hypot(
                        pos[u][0] - pos[v][0],
                        pos[u][1] - pos[v][1]
                    )
                    zone_penalty = (
                        0.0
                        if zone_diff == 1
                        else (1.4 if zone_diff == 0 else 3.2)
                    )
                    candidates.append(
                        (
                            dist + zone_penalty + random.uniform(0, 0.45),
                            v
                        )
                    )
            candidates.sort(key=lambda item: item[0])

            added = False
            for _, v in candidates:
                if can_add_clean_edge(u, v, allow_crossing=False):
                    self.graph.add_edge(
                        u,
                        v,
                        weight=random.randint(10, 30)
                    )
                    added = True
                    break
            if not added and candidates:
                self.graph.add_edge(
                    u,
                    candidates[0][1],
                    weight=random.randint(10, 30)
                )

        for i in range(node_count - 1):
            u = nodes[i]
            zu = node_zone[u]
            target_out = (
                2 if i > 0 else min(3, max(2, node_count // 5))
            )
            if random.random() < 0.35 and i < node_count - 3:
                target_out = min(3, target_out + 1)

            if len(list(self.graph.successors(u))) >= target_out:
                continue

            candidates = []
            for j in range(i + 1, node_count):
                v = nodes[j]
                zv = node_zone[v]
                zone_diff = zv - zu
                if (
                    0 <= zone_diff <= 2
                    and not self.graph.has_edge(u, v)
                ):
                    dist = math.hypot(
                        pos[u][0] - pos[v][0],
                        pos[u][1] - pos[v][1]
                    )
                    zone_penalty = (
                        0.0
                        if zone_diff == 1
                        else (1.2 if zone_diff == 0 else 3.5)
                    )
                    candidates.append(
                        (
                            dist + zone_penalty + random.uniform(0, 0.6),
                            v
                        )
                    )
            candidates.sort(key=lambda item: item[0])

            for _, v in candidates:
                if len(list(self.graph.successors(u))) >= target_out:
                    break
                if len(list(self.graph.predecessors(v))) >= 3 and v != nodes[-1]:
                    continue
                if can_add_clean_edge(u, v, allow_crossing=False):
                    self.graph.add_edge(
                        u,
                        v,
                        weight=random.randint(10, 30)
                    )

        base_edges = list(self.graph.edges)

        if allow_bidirectional and base_edges:
            bidir_candidates = list(base_edges)
            random.shuffle(bidir_candidates)
            if not allow_cycles:
                def _shared_neighbors(edge: Tuple[str, str]) -> int:
                    eu, ev = edge
                    nu = set(self.graph.predecessors(eu)) | set(
                        self.graph.successors(eu)
                    )
                    nv = set(self.graph.predecessors(ev)) | set(
                        self.graph.successors(ev)
                    )
                    return len((nu & nv) - {eu, ev})

                bidir_candidates.sort(key=_shared_neighbors)

            bidir_count = max(
                2,
                min(
                    len(bidir_candidates) // 2,
                    int(
                        round(
                            len(bidir_candidates)
                            * random.uniform(0.22, 0.35)
                        )
                    )
                )
            )
            added_bidir = 0
            for u, v in bidir_candidates:
                if added_bidir >= bidir_count:
                    break
                if self.graph.has_edge(v, u):
                    continue
                existing_weight = self.get_edge_weight(u, v)
                if not allow_cycles:
                    self.graph.remove_edge(u, v)
                    creates_cycle = (
                        nx.has_path(self.graph, u, v)
                        or nx.has_path(self.graph, v, u)
                    )
                    self.graph.add_edge(
                        u,
                        v,
                        weight=existing_weight
                    )
                    if creates_cycle:
                        continue
                self.graph.add_edge(
                    v,
                    u,
                    weight=existing_weight
                )
                added_bidir += 1

            if not allow_cycles and added_bidir < 2:
                for u, v in bidir_candidates:
                    if added_bidir >= 2:
                        break
                    if self.graph.has_edge(v, u):
                        continue
                    existing_weight = self.get_edge_weight(u, v)
                    self.graph.remove_edge(u, v)
                    removed_chords: List[Tuple[str, str, int]] = []
                    while (
                        nx.has_path(self.graph, u, v)
                        or nx.has_path(self.graph, v, u)
                    ):
                        alt_path = (
                            nx.shortest_path(self.graph, u, v)
                            if nx.has_path(self.graph, u, v)
                            else nx.shortest_path(self.graph, v, u)
                        )
                        chord_removed = False
                        for idx in range(len(alt_path) - 1):
                            ca, cb = alt_path[idx], alt_path[idx + 1]
                            if (
                                not self.graph.has_edge(cb, ca)
                                and len(list(self.graph.successors(ca))) > 1
                                and len(list(self.graph.predecessors(cb))) > 1
                            ):
                                cw = self.get_edge_weight(ca, cb)
                                self.graph.remove_edge(ca, cb)
                                if nx.has_path(self.graph, nodes[0], cb):
                                    removed_chords.append((ca, cb, cw))
                                    chord_removed = True
                                    break
                                self.graph.add_edge(ca, cb, weight=cw)
                        if not chord_removed:
                            break
                    if (
                        not nx.has_path(self.graph, u, v)
                        and not nx.has_path(self.graph, v, u)
                    ):
                        self.graph.add_edge(
                            u,
                            v,
                            weight=existing_weight
                        )
                        self.graph.add_edge(
                            v,
                            u,
                            weight=existing_weight
                        )
                        added_bidir += 1
                    else:
                        for ca, cb, cw in removed_chords:
                            self.graph.add_edge(ca, cb, weight=cw)
                        self.graph.add_edge(
                            u,
                            v,
                            weight=existing_weight
                        )

        if allow_cycles:
            cycle_candidates: List[Tuple[float, str, str]] = []
            for i in range(node_count):
                for j in range(i + 1, node_count):
                    u = nodes[i]
                    v = nodes[j]
                    if self.graph.has_edge(u, v) or self.graph.has_edge(v, u):
                        continue
                    zone_diff = node_zone[v] - node_zone[u]
                    if 1 <= zone_diff <= 3 and nx.has_path(self.graph, u, v):
                        dist = math.hypot(
                            pos[v][0] - pos[u][0],
                            pos[v][1] - pos[u][1]
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
                    self.graph.add_edge(
                        src_back,
                        dst_back,
                        weight=random.randint(10, 30),
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
                        self.graph.add_edge(
                            src_back,
                            dst_back,
                            weight=random.randint(10, 30),
                        )
                        added_cycles += 1
                        break

            if added_cycles == 0:
                fallback_candidates: List[Tuple[float, str, str]] = []
                for i in range(node_count):
                    for j in range(i + 1, node_count):
                        u = nodes[i]
                        v = nodes[j]
                        if self.graph.has_edge(u, v) or self.graph.has_edge(v, u):
                            continue
                        if nx.has_path(self.graph, u, v):
                            p1, p2 = pos[v], pos[u]
                            min_clearance = min(
                                (
                                    self.point_to_segment_dist(pos[w], p1, p2)
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
                    self.graph.add_edge(
                        best_src,
                        best_dst,
                        weight=random.randint(10, 30),
                    )
                    added_cycles += 1
                else:
                    for u in nodes:
                        for mid in self.graph.successors(u):
                            for v in self.graph.successors(mid):
                                if u != v and not self.graph.has_edge(v, u):
                                    self.graph.add_edge(
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

    def create_manual_graph(
            self,
            node_count: int,
            edges: List[Tuple[str, str, int]],
            preserve_seed: Optional[int] = None
    ) -> None:

        if (
                not isinstance(node_count, int)
                or isinstance(node_count, bool)
                or not 7 <= node_count <= 16
        ):
            raise ValueError(
                "El número de nodos debe estar entre 7 y 16."
            )

        if not edges:
            raise ValueError(
                "El grafo debe tener al menos una arista."
            )

        nodes = [f"N{i}" for i in range(1, node_count + 1)]

        candidate_graph = nx.DiGraph()
        candidate_graph.add_nodes_from(nodes)

        seen_edges = set()

        for source, target, weight in edges:

            if source not in candidate_graph or target not in candidate_graph:
                raise ValueError(
                    f"La arista {source} -> {target} "
                    "contiene un vértice inexistente."
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

            candidate_graph.add_edge(
                source,
                target,
                weight=weight
            )

        self.graph = candidate_graph
        self.reset_algorithm_data()
        if preserve_seed is not None:
            self.layout_seed = preserve_seed
        else:
            self.layout_seed = (
                sum(
                    (idx + 1) * ord(ch)
                    for idx, ch in enumerate(repr(edges))
                )
                % 1_000_000
                + 1
            )

    def get_nodes(self) -> List[str]:
        return list(self.graph.nodes)

    def get_successors(self, node: str) -> List[str]:
        return list(self.graph.successors(node))

    def get_edge_weight(
        self,
        source: str,
        target: str
    ) -> int:

        edge_data: Dict[str, Any] = self.graph[source][target]

        weight = cast(int, edge_data["weight"])

        return int(weight)

    def initialize_dijkstra(
            self,
            source: str,
            target: str
    ) -> Dict[str, Tuple[float, Optional[str], int]]:
        if source not in self.graph or target not in self.graph:
            raise ValueError(
                "El vértice de origen y el de destino deben existir en el grafo."
            )
        if source == target:
            raise ValueError(
                "El vértice de origen y el de destino deben ser diferentes."
            )
        for u, v, edge_data in self.graph.edges(data=True):
            weight = edge_data.get("weight")
            if (
                not isinstance(weight, int)
                or isinstance(weight, bool)
                or weight <= 0
            ):
                raise ValueError(
                    f"La arista {u} -> {v} tiene un peso inválido ({weight}). "
                    "Todos los pesos deben ser enteros positivos."
                )

        self.source = source
        self.target = target

        self.iteration = 0

        self.processed_nodes.clear()
        self.current_node = None

        self.algorithm_finished = False

        self.labels = {
            node: (float("inf"), None, 0)
            for node in self.graph.nodes
        }

        self.label_history = {
            node: []
            for node in self.graph.nodes
        }

        self.optimal_predecessors = {
            node: []
            for node in self.graph.nodes
        }
        self.last_tie_iteration.clear()

        self.labels[source] = (0, None, 0)

        self.label_history[source].append(
            (0, None, 0, False)
        )

        self.decision_history = [
            (
                f"Inicialización: el origen {source} recibe distancia 0 ([0, -]_0).\n"
                "Inicialización: los demás vértices reciben distancia ∞ ([∞, -]_0).\n"
                f"Objetivo: hallar el camino mínimo desde {source} hasta {target}."
            )
        ]

        return self.labels.copy()

    def get_unprocessed_nodes(self) -> List[str]:
        return [
            node
            for node in self.graph.nodes
            if node not in self.processed_nodes
        ]

    def select_next_node(self) -> Optional[str]:
        available_nodes = [
            node
            for node in self.get_unprocessed_nodes()
            if self.labels.get(node, (float("inf"), None, 0))[0] != float("inf")
        ]

        if not available_nodes:
            return None

        return min(
            available_nodes,
            key=lambda node: (
                self.labels[node][0],
                int(node[1:]) if node[1:].isdigit() else 999
            )
        )

    def execute_next_step(
            self
    ) -> Dict[str, Tuple[float, Optional[str], int]]:

        if self.source is None:
            raise ValueError(
                "Primero debe inicializar Dijkstra."
            )

        if self.algorithm_finished:
            return self.labels.copy()

        next_node = self.select_next_node()

        if next_node is None:
            self.algorithm_finished = True
            unreachable_nodes = [
                n
                for n in self.get_unprocessed_nodes()
                if self.labels.get(n, (float("inf"), None, 0))[0] == float("inf")
            ]
            if unreachable_nodes:
                self.decision_history.append(
                    "Finalización: no existen caminos hacia los vértices restantes. "
                    f"Inalcanzables (distancia ∞): {', '.join(unreachable_nodes)}."
                )
            else:
                self.decision_history.append(
                    "Finalización: no quedan vértices sin procesar."
                )

            return self.labels.copy()

        self.current_node = next_node
        self.iteration += 1
        self.processed_nodes.append(next_node)

        current_distance = self.labels[next_node][0]

        step_lines: List[str] = [
            f"Iteración {self.iteration}: se selecciona "
            f"{next_node} con distancia acumulada {int(current_distance)}."
        ]

        neighbors = self.get_successors(next_node)
        if not neighbors:
            step_lines.append(
                f"El vértice {next_node} no tiene aristas salientes para evaluar."
            )

        for neighbor in neighbors:

            if neighbor in self.processed_nodes:
                step_lines.append(
                    f"Arista {next_node} -> {neighbor}: "
                    f"el vértice adyacente {neighbor} ya fue procesado (se conserva su etiqueta permanente)."
                )

                continue

            weight = self.get_edge_weight(
                next_node,
                neighbor
            )

            candidate_distance = current_distance + weight

            current_distance_neighbor = self.labels[neighbor][0]

            if candidate_distance < current_distance_neighbor:

                if current_distance_neighbor != float("inf"):

                    history = self.label_history[neighbor]

                    for history_index, old_label in enumerate(history):
                        if (
                                old_label[0] == current_distance_neighbor
                                and not old_label[3]
                        ):
                            history[history_index] = (
                                old_label[0],
                                old_label[1],
                                old_label[2],
                                True
                            )

                previous_distance_text = (
                    "∞"
                    if current_distance_neighbor == float("inf")
                    else str(int(current_distance_neighbor))
                )

                self.optimal_predecessors[neighbor] = [
                    next_node
                ]
                self.last_tie_iteration.pop(neighbor, None)

                self.labels[neighbor] = (
                    candidate_distance,
                    next_node,
                    self.iteration
                )

                self.label_history[neighbor].append(
                    (
                        candidate_distance,
                        next_node,
                        self.iteration,
                        False
                    )
                )

                step_lines.append(
                    f"Arista {next_node} -> {neighbor}, "
                    f"peso {weight}: "
                    f"{int(current_distance)} + {weight} = "
                    f"{int(candidate_distance)} < {previous_distance_text}. "
                    f"Actualización: se asigna [{int(candidate_distance)}, {next_node}]_{self.iteration}."
                )

            elif candidate_distance == current_distance_neighbor:

                if (
                        next_node
                        not in self.optimal_predecessors[neighbor]
                ):

                    self.optimal_predecessors[neighbor].append(
                        next_node
                    )

                    combined_preds = "/".join(self.optimal_predecessors[neighbor])
                    original_iteration = self.labels[neighbor][2]

                    self.labels[neighbor] = (
                        candidate_distance,
                        combined_preds,
                        original_iteration
                    )
                    self.last_tie_iteration[neighbor] = self.iteration

                    self.label_history[neighbor].append(
                        (
                            candidate_distance,
                            next_node,
                            self.iteration,
                            False
                        )
                    )

                    step_lines.append(
                        f"Arista {next_node} -> {neighbor}, "
                        f"peso {weight}: "
                        f"{int(current_distance)} + {weight} = "
                        f"{int(candidate_distance)}. "
                        "Empate en distancia mínima: se registra el predecesor alternativo "
                        f"{next_node} (predecesores óptimos: {combined_preds})."
                    )

                else:
                    step_lines.append(
                        f"Arista {next_node} -> {neighbor}: "
                        "la alternativa óptima ya está registrada."
                    )

            else:
                step_lines.append(
                    f"Arista {next_node} -> {neighbor}, "
                    f"peso {weight}: "
                    f"{int(current_distance)} + {weight} = "
                    f"{int(candidate_distance)} > {int(current_distance_neighbor)}. "
                    "Sin mejora: se conserva la etiqueta anterior."
                )

        next_reachable = self.select_next_node()

        if next_reachable is None:

            self.algorithm_finished = True

            unreachable_nodes = [
                node
                for node in self.get_unprocessed_nodes()
                if self.labels.get(node, (float("inf"), None, 0))[0] == float("inf")
            ]

            if unreachable_nodes:
                step_lines.append(
                    "Finalización: no quedan vértices alcanzables por procesar. "
                    f"Vértices inalcanzables (distancia ∞): {', '.join(unreachable_nodes)}."
                )
            else:
                step_lines.append(
                    "Finalización: todos los vértices fueron procesados óptimamente."
                )

        else:

            step_lines.append(
                f"Fin de la iteración {self.iteration}. "
                f"Siguiente candidato de menor distancia acumulada: {next_reachable}."
            )

        self.decision_history.append("\n".join(step_lines))

        return self.labels.copy()

    def get_shortest_path(self) -> List[str]:

        paths = self.get_shortest_paths()

        if not paths:
            return []

        return paths[0]

    def get_shortest_paths(self) -> List[List[str]]:

        if self.source is None or self.target is None:
            return []

        if self.labels[self.target][0] == float("inf"):
            return []

        def build_paths(
            node: str,
            visited: Optional[set] = None
        ) -> List[List[str]]:

            if visited is None:
                visited = {node}

            if node == self.source:

                return [[self.source]]

            paths = []

            predecessors = self.optimal_predecessors.get(
                node,
                []
            )

            for predecessor in predecessors:

                if predecessor in visited:
                    continue

                previous_paths = build_paths(
                    predecessor,
                    visited | {predecessor}
                )

                for path in previous_paths:

                    paths.append(
                        path + [node]
                    )

            return paths

        return build_paths(self.target)

    def get_shortest_distance(self) -> Optional[int]:
        if self.target is None:
            return None

        distance = self.labels[self.target][0]

        if distance == float("inf"):
            return None

        return int(distance)

class MainApplication:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root

        self.project_info = ProjectInfo()
        self.graph_model = GraphModel()

        self.root.title(
            "Problema del Camino Mínimo"
        )

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(1450, screen_width - 40)
        window_height = min(900, screen_height - 100)
        window_x = max(0, (screen_width - window_width) // 2)
        window_y = max(0, (screen_height - window_height) // 2)
        self.root.geometry(
            f"{window_width}x{window_height}+{window_x}+{window_y}"
        )
        self.root.minsize(
            min(940, window_width),
            min(620, window_height)
        )

        self.configure_style()

        self.node_count_var = tk.StringVar()
        self.source_var = tk.StringVar()
        self.target_var = tk.StringVar()

        self.mode_var = tk.StringVar(
            value="Aleatorio"
        )
        self.bidirectional_var = tk.BooleanVar(
            value=True
        )
        self.cycles_var = tk.BooleanVar(
            value=True
        )

        self.status_var = tk.StringVar(
            value=(
                "Ingrese la cantidad de nodos "
                "y seleccione el tipo de grafo."
            )
        )

        self.source_combo: Optional[
            ttk.Combobox
        ] = None

        self.target_combo: Optional[
            ttk.Combobox
        ] = None

        self.mode_combo: Optional[
            ttk.Combobox
        ] = None

        self.bidirectional_check: Optional[
            ttk.Checkbutton
        ] = None

        self.cycles_check: Optional[
            ttk.Checkbutton
        ] = None

        self.graph_frame: Optional[
            ttk.Frame
        ] = None

        self.side_frame: Optional[
            ttk.Frame
        ] = None

        self.labels_panel_frame: Optional[
            ttk.LabelFrame
        ] = None

        self.result_frame: Optional[
            tk.Frame
        ] = None

        self.result_header_label: Optional[
            tk.Label
        ] = None

        self.result_body_frame: Optional[
            tk.Frame
        ] = None

        self.result_badges_frame: Optional[
            tk.Frame
        ] = None

        self.result_summary_label: Optional[
            tk.Label
        ] = None

        self.result_count_label: Optional[
            tk.Label
        ] = None

        self.result_text: Optional[
            tk.Text
        ] = None

        self.manual_panel_frame: Optional[
            ttk.LabelFrame
        ] = None

        self.manual_rows_container: Optional[
            ttk.Frame
        ] = None

        self.manual_scroll_canvas: Optional[
            tk.Canvas
        ] = None

        self.manual_hint_var = tk.StringVar(
            value=""
        )

        self.manual_form_node1_var = tk.StringVar(
            value=""
        )
        self.manual_form_node2_var = tk.StringVar(
            value=""
        )
        self.manual_form_weight_var = tk.StringVar(
            value=""
        )
        self.manual_form_bi_var = tk.BooleanVar(
            value=False
        )

        self.manual_form_node1_combo: Optional[
            ttk.Combobox
        ] = None

        self.manual_form_node2_combo: Optional[
            ttk.Combobox
        ] = None

        self.manual_form_weight_entry: Optional[
            ttk.Entry
        ] = None

        self.manual_build_mode = False
        self.is_manual_graph_created = False
        self.manual_node_count = 0
        self.manual_selected_node: Optional[str] = None
        self.manual_highlighted_nodes: Set[str] = set()
        self.manual_connections: List[Dict[str, Any]] = []

        self.edit_manual_button: Optional[
            ttk.Button
        ] = None
        self.edit_manual_panel_button: Optional[
            ttk.Button
        ] = None
        self.legend_info_label: Optional[
            ttk.Label
        ] = None

        self.cached_positions: Dict[
            str,
            Tuple[float, float]
        ] = {}
        self._cached_layout_signature: Optional[
            Tuple[Any, ...]
        ] = None

        self.labels_text: Optional[
            tk.Text
        ] = None

        self.history_text: Optional[tk.Text] = None

        self.decisions_text: Optional[tk.Text] = None

        self.canvas: Optional[
            FigureCanvasTkAgg
        ] = None

        self.figure: Optional[
            Figure
        ] = None

        self.graph_axis: Optional[Any] = None

        self.toolbar: Optional[
            NavigationToolbar2Tk
        ] = None

        self.reset_graph_view = False

        self.init_button: Optional[
            ttk.Button
        ] = None

        self.next_button: Optional[
            ttk.Button
        ] = None

        self.finish_button: Optional[
            ttk.Button
        ] = None

        self.configuration_frame: Optional[
            ttk.LabelFrame
        ] = None
        self.left_config_group: Optional[
            ttk.Frame
        ] = None
        self.right_config_group: Optional[
            ttk.Frame
        ] = None
        self.config_separator: Optional[
            ttk.Separator
        ] = None
        self._config_bar_rows: int = 1

        self.create_menu()
        self.create_main_layout()

    @staticmethod
    def _make_rounded_image(
        width: int,
        height: int,
        radius: int,
        bg_out: str,
        border_col: str,
        fill_col: str
    ) -> tk.PhotoImage:
        def hex_rgb(h: str) -> Tuple[int, int, int]:
            c = h.lstrip("#")
            return (
                int(c[0:2], 16),
                int(c[2:4], 16),
                int(c[4:6], 16)
            )

        def blend_hex(
            c1: Tuple[int, int, int],
            c2: Tuple[int, int, int],
            t: float
        ) -> str:
            t_clamped = max(0.0, min(1.0, t))
            r = int(round(c1[0] + (c2[0] - c1[0]) * t_clamped))
            g = int(round(c1[1] + (c2[1] - c1[1]) * t_clamped))
            b = int(round(c1[2] + (c2[2] - c1[2]) * t_clamped))
            return f"#{r:02x}{g:02x}{b:02x}"

        rgb_out = hex_rgb(bg_out)
        rgb_border = hex_rgb(border_col)
        rgb_fill = hex_rgb(fill_col)

        img = tk.PhotoImage(width=width, height=height)
        top_rows: List[str] = []
        mid_w = width - 2 * radius

        for y in range(radius):
            left_px: List[str] = []
            for x in range(radius):
                dist = math.hypot(x - radius, y - radius)
                if dist >= radius + 0.5:
                    col = bg_out
                elif dist >= radius - 0.5:
                    col = blend_hex(
                        rgb_out,
                        rgb_border,
                        (radius + 0.5) - dist
                    )
                elif dist >= radius - 1.5:
                    col = blend_hex(
                        rgb_border,
                        rgb_fill,
                        (radius - 0.5) - dist
                    )
                else:
                    col = fill_col
                left_px.append(col)
            right_px = list(reversed(left_px))
            mid_col = border_col if y == 0 else fill_col
            row_str = (
                "{"
                + " ".join(left_px + [mid_col] * mid_w + right_px)
                + "}"
            )
            top_rows.append(row_str)

        mid_row = (
            "{"
            + " ".join(
                [border_col] + [fill_col] * (width - 2) + [border_col]
            )
            + "}"
        )
        bot_rows = list(reversed(top_rows))
        all_rows = (
            top_rows
            + [mid_row] * (height - 2 * radius)
            + bot_rows
        )
        img.put(" ".join(all_rows))
        return img

    def configure_style(self) -> None:
        bg_main = "#0d1117"
        bg_surface = "#161b22"
        bg_hover = "#21262d"
        border_subtle = "#21262d"
        border_input = "#30363d"
        border_focus = "#388bfd"
        text_primary = "#e6edf3"
        text_secondary = "#8b949e"
        text_disabled = "#484f58"

        self.root.configure(bg=bg_main)
        self.root.option_add(
            "*TCombobox*Listbox.background",
            bg_surface
        )
        self.root.option_add(
            "*TCombobox*Listbox.foreground",
            text_primary
        )
        self.root.option_add(
            "*TCombobox*Listbox.selectBackground",
            "#1f6feb"
        )
        self.root.option_add(
            "*TCombobox*Listbox.selectForeground",
            "#ffffff"
        )
        self.root.option_add(
            "*TCombobox*Listbox.font",
            ("Segoe UI", 9)
        )

        style = ttk.Style(self.root)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        if not hasattr(self.root, "_dark_theme_images"):
            btn_normal = self._make_rounded_image(
                110, 34, 5, bg_main, border_input, bg_surface
            )
            btn_hover = self._make_rounded_image(
                110, 34, 5, bg_main, border_focus, bg_hover
            )
            btn_pressed = self._make_rounded_image(
                110, 34, 5, bg_main, "#58a6ff", "#1f6feb"
            )
            btn_disabled = self._make_rounded_image(
                110, 34, 5, bg_main, "#21262d", "#0d1117"
            )
            tab_normal = self._make_rounded_image(
                110, 28, 5, bg_main, border_subtle, "#0d1117"
            )
            tab_selected = self._make_rounded_image(
                110, 28, 5, bg_main, border_input, bg_surface
            )
            setattr(
                self.root,
                "_dark_theme_images",
                {
                    "btn_normal": btn_normal,
                    "btn_hover": btn_hover,
                    "btn_pressed": btn_pressed,
                    "btn_disabled": btn_disabled,
                    "tab_normal": tab_normal,
                    "tab_selected": tab_selected,
                }
            )

        imgs = getattr(self.root, "_dark_theme_images")

        try:
            style.element_create(
                "DarkBtn.border",
                "image",
                imgs["btn_normal"],
                ("disabled", imgs["btn_disabled"]),
                ("pressed", imgs["btn_pressed"]),
                ("active", imgs["btn_hover"]),
                border=5,
                width=0,
                height=0,
                sticky="nsew"
            )
        except tk.TclError:
            pass

        try:
            btn_layout = [
                (
                    "DarkBtn.border",
                    {
                        "sticky": "nswe",
                        "children": [
                            (
                                "Button.padding",
                                {
                                    "sticky": "nswe",
                                    "children": [
                                        (
                                            "Button.label",
                                            {"sticky": "nswe"}
                                        )
                                    ]
                                }
                            )
                        ]
                    }
                )
            ]
            style.layout("TButton", btn_layout)
            style.layout("Action.TButton", btn_layout)
        except tk.TclError:
            pass

        try:
            style.element_create(
                "DarkTab.tab",
                "image",
                imgs["tab_normal"],
                ("selected", imgs["tab_selected"]),
                ("active", imgs["tab_selected"]),
                border=5,
                width=0,
                height=0,
                sticky="nsew"
            )
        except tk.TclError:
            pass

        try:
            style.layout(
                "TNotebook.Tab",
                [
                    (
                        "DarkTab.tab",
                        {
                            "sticky": "nswe",
                            "children": [
                                (
                                    "Notebook.padding",
                                    {
                                        "sticky": "nswe",
                                        "children": [
                                            (
                                                "Notebook.label",
                                                {"sticky": "nswe"}
                                            )
                                        ]
                                    }
                                )
                            ]
                        }
                    )
                ]
            )
        except tk.TclError:
            pass

        style.configure(
            ".",
            background=bg_main,
            foreground=text_primary,
            fieldbackground=bg_surface,
            troughcolor=bg_main,
            bordercolor=border_subtle,
            darkcolor=bg_main,
            lightcolor=bg_main,
            focuscolor=bg_main,
            font=("Segoe UI", 9)
        )
        style.map(
            ".",
            background=[
                ("disabled", bg_main),
                ("active", bg_surface)
            ],
            foreground=[
                ("disabled", text_disabled)
            ]
        )

        style.configure(
            "TFrame",
            background=bg_main
        )

        style.configure(
            "TLabel",
            background=bg_main,
            foreground=text_primary
        )

        style.configure(
            "Title.TLabel",
            background=bg_main,
            foreground="#f0f6fc",
            font=("Segoe UI", 22, "bold")
        )

        style.configure(
            "Subtitle.TLabel",
            background=bg_main,
            foreground=text_secondary,
            font=("Segoe UI", 10)
        )

        style.configure(
            "TLabelframe",
            background=bg_main,
            foreground=text_secondary,
            bordercolor=border_subtle,
            lightcolor=border_subtle,
            darkcolor=border_subtle,
            borderwidth=1,
            relief="solid"
        )
        style.configure(
            "TLabelframe.Label",
            background=bg_main,
            foreground=text_secondary,
            font=("Segoe UI", 9, "bold")
        )

        style.configure(
            "Section.TLabelframe",
            background=bg_main,
            foreground=text_secondary,
            bordercolor=border_subtle,
            lightcolor=border_subtle,
            darkcolor=border_subtle,
            borderwidth=1,
            relief="solid"
        )
        style.configure(
            "Section.TLabelframe.Label",
            background=bg_main,
            foreground=text_secondary,
            font=("Segoe UI", 9, "bold")
        )

        style.configure(
            "TButton",
            background=bg_surface,
            foreground=text_primary,
            font=("Segoe UI", 9),
            padding=(10, 5),
            borderwidth=0,
            relief="flat"
        )
        style.map(
            "TButton",
            background=[
                ("disabled", bg_main),
                ("pressed", "#1f6feb"),
                ("active", bg_hover)
            ],
            foreground=[
                ("disabled", text_disabled),
                ("pressed", "#ffffff"),
                ("active", "#ffffff")
            ]
        )

        style.configure(
            "Action.TButton",
            background=bg_surface,
            foreground=text_primary,
            font=("Segoe UI", 9, "bold"),
            padding=(10, 6),
            borderwidth=0,
            relief="flat"
        )
        style.map(
            "Action.TButton",
            background=[
                ("disabled", bg_main),
                ("pressed", "#1f6feb"),
                ("active", bg_hover)
            ],
            foreground=[
                ("disabled", text_disabled),
                ("pressed", "#ffffff"),
                ("active", "#ffffff")
            ]
        )

        style.configure(
            "TEntry",
            fieldbackground=bg_surface,
            background=bg_surface,
            foreground=text_primary,
            insertcolor=text_primary,
            bordercolor=border_input,
            lightcolor=bg_surface,
            darkcolor=bg_surface,
            borderwidth=1,
            padding=(6, 4),
            relief="flat"
        )
        style.map(
            "TEntry",
            fieldbackground=[
                ("disabled", bg_main),
                ("readonly", bg_surface)
            ],
            foreground=[("disabled", text_disabled)],
            bordercolor=[("focus", border_focus)]
        )

        style.configure(
            "TCombobox",
            fieldbackground=bg_surface,
            background=bg_surface,
            foreground=text_primary,
            arrowcolor=text_secondary,
            bordercolor=border_input,
            lightcolor=bg_surface,
            darkcolor=bg_surface,
            borderwidth=1,
            padding=(6, 4),
            relief="flat"
        )
        style.map(
            "TCombobox",
            fieldbackground=[
                ("readonly", bg_surface),
                ("disabled", bg_main)
            ],
            background=[
                ("readonly", bg_surface),
                ("active", bg_hover),
                ("disabled", bg_main)
            ],
            foreground=[
                ("readonly", text_primary),
                ("disabled", text_disabled)
            ],
            arrowcolor=[
                ("disabled", text_disabled),
                ("active", text_primary)
            ],
            bordercolor=[("focus", border_focus)]
        )

        style.configure(
            "TCheckbutton",
            background=bg_main,
            foreground=text_primary,
            indicatorbackground=bg_surface,
            indicatorforeground="#58a6ff",
            upperbordercolor=border_input,
            lowerbordercolor=border_input,
            font=("Segoe UI", 9)
        )
        style.map(
            "TCheckbutton",
            background=[("active", bg_main)],
            foreground=[
                ("disabled", text_disabled),
                ("active", "#ffffff")
            ],
            indicatorbackground=[
                ("selected", "#1f6feb"),
                ("disabled", bg_main)
            ]
        )

        style.configure(
            "TNotebook",
            background=bg_main,
            bordercolor=border_subtle,
            lightcolor=bg_main,
            darkcolor=bg_main,
            tabmargins=(0, 2, 0, 0),
            borderwidth=0
        )
        style.configure(
            "TNotebook.Tab",
            background=bg_main,
            foreground=text_secondary,
            padding=(12, 5),
            font=("Segoe UI", 9),
            borderwidth=0
        )
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", bg_surface),
                ("active", bg_surface)
            ],
            foreground=[
                ("selected", text_primary),
                ("active", text_primary)
            ]
        )

        style.configure(
            "Vertical.TScrollbar",
            background="#30363d",
            troughcolor=bg_main,
            bordercolor=bg_main,
            lightcolor=bg_main,
            darkcolor=bg_main,
            arrowcolor=text_secondary,
            gripcount=0,
            borderwidth=0,
            relief="flat"
        )
        style.map(
            "Vertical.TScrollbar",
            background=[
                ("pressed", "#58a6ff"),
                ("active", "#484f58"),
                ("disabled", bg_main)
            ]
        )

        style.configure(
            "TSeparator",
            background=border_subtle
        )

    def create_menu(self) -> None:
        menu_cfg = {
            "bg": "#0d1117",
            "fg": "#e6edf3",
            "activebackground": "#21262d",
            "activeforeground": "#ffffff",
            "bd": 0,
            "relief": "flat",
        }
        menu_bar = tk.Menu(self.root, **menu_cfg)

        project_menu = tk.Menu(
            menu_bar,
            tearoff=0,
            **menu_cfg
        )

        project_menu.add_command(
            label="Generar nuevo grafo",
            command=self.generate_graph
        )

        project_menu.add_command(
            label="Modificar grafo manual",
            command=self.edit_manual_graph
        )

        project_menu.add_command(
            label="Reiniciar Dijkstra",
            command=self.initialize_algorithm
        )

        project_menu.add_command(
            label="Ejecutar siguiente paso",
            command=self.execute_next_step
        )

        project_menu.add_command(
            label="Ejecutar algoritmo completo",
            command=self.execute_until_finished
        )

        project_menu.add_separator()

        project_menu.add_command(
            label="Salir",
            command=self.root.destroy
        )

        menu_bar.add_cascade(
            label="Proyecto",
            menu=project_menu
        )

        menu_bar.add_command(
            label="Información del proyecto",
            command=self.show_project_information
        )

        view_menu = tk.Menu(
            menu_bar,
            tearoff=0,
            **menu_cfg
        )

        view_menu.add_command(
            label="Restablecer vista del grafo",
            command=self.reset_graph_zoom
        )

        menu_bar.add_cascade(
            label="Vista",
            menu=view_menu
        )

        help_menu = tk.Menu(
            menu_bar,
            tearoff=0,
            **menu_cfg
        )

        help_menu.add_command(
            label="Descripción del sistema",
            command=lambda: self.show_help(0)
        )

        help_menu.add_command(
            label="Guía de uso",
            command=lambda: self.show_help(1)
        )

        help_menu.add_command(
            label="Dijkstra paso a paso",
            command=lambda: self.show_help(2)
        )

        help_menu.add_command(
            label="Etiquetas y conceptos de Dijkstra",
            command=lambda: self.show_help(3)
        )

        menu_bar.add_cascade(
            label="Ayuda",
            menu=help_menu
        )

        self.root.config(
            menu=menu_bar
        )

    def create_main_layout(self) -> None:
        main_frame = ttk.Frame(
            self.root,
            padding=(14, 10)
        )

        main_frame.pack(
            fill="both",
            expand=True
        )

        header_frame = ttk.Frame(
            main_frame
        )

        header_frame.pack(
            fill="x",
            pady=(0, 6)
        )

        ttk.Label(
            header_frame,
            text="PROBLEMA DEL CAMINO MÍNIMO",
            style="Title.TLabel"
        ).pack(
            anchor="center",
            pady=(0, 1)
        )

        ttk.Label(
            header_frame,
            text=(
                "Algoritmo de Dijkstra "
                "con ejecución paso a paso"
            ),
            style="Subtitle.TLabel"
        ).pack(
            anchor="center"
        )

        configuration_frame = ttk.LabelFrame(
            main_frame,
            text="Configuración del problema",
            padding=(10, 6),
            style="Section.TLabelframe"
        )
        self.configuration_frame = configuration_frame

        configuration_frame.pack(
            fill="x",
            pady=(0, 6)
        )

        left_group = ttk.Frame(configuration_frame)
        self.left_config_group = left_group

        ttk.Label(
            left_group,
            text="Número de nodos (7-16):"
        ).grid(
            row=0,
            column=0,
            padx=(2, 4),
            pady=2
        )

        ttk.Entry(
            left_group,
            textvariable=self.node_count_var,
            width=7
        ).grid(
            row=0,
            column=1,
            padx=3,
            pady=2
        )

        ttk.Label(
            left_group,
            text="Tipo de grafo:"
        ).grid(
            row=0,
            column=2,
            padx=(6, 3),
            pady=2
        )

        self.mode_combo = ttk.Combobox(
            left_group,
            textvariable=self.mode_var,
            values=[
                "Aleatorio",
                "Manual"
            ],
            state="readonly",
            width=9
        )

        self.mode_combo.grid(
            row=0,
            column=3,
            padx=3,
            pady=2
        )
        self.mode_combo.bind(
            "<<ComboboxSelected>>",
            self.on_mode_changed
        )

        ttk.Button(
            left_group,
            text="Generar grafo",
            command=self.generate_graph,
            style="Action.TButton"
        ).grid(
            row=0,
            column=4,
            padx=4,
            pady=2
        )

        options_subframe = ttk.Frame(
            left_group
        )
        options_subframe.grid(
            row=0,
            column=5,
            padx=(2, 2),
            pady=2
        )

        self.bidirectional_check = ttk.Checkbutton(
            options_subframe,
            text="Bidireccional",
            variable=self.bidirectional_var
        )
        self.bidirectional_check.pack(
            side="left",
            padx=(2, 4)
        )

        self.cycles_check = ttk.Checkbutton(
            options_subframe,
            text="Ciclos",
            variable=self.cycles_var
        )
        self.cycles_check.pack(
            side="left",
            padx=(2, 2)
        )

        self.edit_manual_button = ttk.Button(
            options_subframe,
            text="Modificar grafo",
            command=self.edit_manual_graph,
            style="Action.TButton",
            state="disabled"
        )

        self.config_separator = ttk.Separator(
            configuration_frame,
            orient="vertical"
        )

        right_group = ttk.Frame(configuration_frame)
        self.right_config_group = right_group

        ttk.Label(
            right_group,
            text="Origen:"
        ).grid(
            row=0,
            column=0,
            padx=(2, 3),
            pady=2
        )

        self.source_combo = ttk.Combobox(
            right_group,
            textvariable=self.source_var,
            state="readonly",
            width=6
        )

        self.source_combo.grid(
            row=0,
            column=1,
            padx=3,
            pady=2
        )
        self.source_combo.bind(
            "<<ComboboxSelected>>",
            self.on_endpoint_changed
        )

        ttk.Label(
            right_group,
            text="Destino:"
        ).grid(
            row=0,
            column=2,
            padx=(6, 3),
            pady=2
        )

        self.target_combo = ttk.Combobox(
            right_group,
            textvariable=self.target_var,
            state="readonly",
            width=6
        )

        self.target_combo.grid(
            row=0,
            column=3,
            padx=3,
            pady=2
        )
        self.target_combo.bind(
            "<<ComboboxSelected>>",
            self.on_endpoint_changed
        )

        self.init_button = ttk.Button(
            right_group,
            text="Inicializar",
            command=self.initialize_algorithm,
            style="Action.TButton"
        )
        self.init_button.grid(
            row=0,
            column=4,
            padx=(6, 3),
            pady=2
        )

        self.next_button = ttk.Button(
            right_group,
            text="Siguiente paso",
            command=self.execute_next_step,
            style="Action.TButton"
        )

        self.next_button.grid(
            row=0,
            column=5,
            padx=3,
            pady=2
        )

        self.finish_button = ttk.Button(
            right_group,
            text="Ejecutar todo",
            command=self.execute_until_finished,
            style="Action.TButton"
        )

        self.finish_button.grid(
            row=0,
            column=6,
            padx=(3, 2),
            pady=2
        )

        left_group.grid(row=0, column=0, sticky="w")
        self.config_separator.grid(
            row=0,
            column=1,
            sticky="ns",
            padx=6,
            pady=2
        )
        right_group.grid(row=0, column=2, sticky="w")
        self._config_bar_rows = 1

        configuration_frame.bind(
            "<Configure>",
            self._on_configuration_frame_configure
        )

        status_frame = ttk.Frame(
            main_frame
        )

        status_frame.pack(
            side="bottom",
            fill="x",
            pady=(4, 0)
        )

        ttk.Separator(
            status_frame,
            orient="horizontal"
        ).pack(
            fill="x",
            pady=(0, 3)
        )

        ttk.Label(
            status_frame,
            textvariable=self.status_var
        ).pack(
            anchor="w"
        )

        workspace = ttk.Frame(
            main_frame
        )

        workspace.pack(
            side="top",
            fill="both",
            expand=True
        )

        workspace.columnconfigure(
            0,
            weight=4,
            minsize=540
        )

        workspace.columnconfigure(
            1,
            weight=1,
            minsize=380
        )

        workspace.rowconfigure(
            0,
            weight=1
        )

        self.graph_frame = ttk.LabelFrame(
            workspace,
            text="Visualización del grafo",
            padding=6,
            style="Section.TLabelframe"
        )

        self.graph_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 8)
        )

        self.side_frame = ttk.Frame(
            workspace
        )

        self.side_frame.grid(
            row=0,
            column=1,
            sticky="nsew"
        )
        self.side_frame.bind(
            "<Configure>",
            self._on_side_frame_configure
        )

        self.create_labels_panel(
            self.side_frame
        )
        self.create_result_panel(
            self.side_frame
        )
        self.create_manual_panel(
            self.side_frame
        )

    def _on_side_frame_configure(
        self,
        event: Optional[Any] = None
    ) -> None:
        if self.side_frame is None or self.result_frame is None:
            return
        side_h = (
            event.height
            if event is not None and getattr(event, "height", 0) > 1
            else self.side_frame.winfo_height()
        )
        if side_h <= 1:
            return
        target_h = 185 if side_h >= 420 else max(140, min(185, int(side_h * 0.44)))
        if self.result_frame.cget("height") != target_h:
            self.result_frame.configure(height=target_h)

    def on_mode_changed(
        self,
        _event: Optional[Any] = None
    ) -> None:
        self.update_manual_edit_controls()

    def update_manual_edit_controls(self) -> None:
        is_random = self.mode_var.get() == "Aleatorio"
        can_edit_manual = (
            self.is_manual_graph_created
            and not self.manual_build_mode
        )
        if is_random:
            if self.edit_manual_button is not None:
                self.edit_manual_button.pack_forget()
            if self.bidirectional_check is not None:
                self.bidirectional_check.config(state="normal")
                if not self.bidirectional_check.winfo_manager():
                    self.bidirectional_check.pack(
                        side="left",
                        padx=(2, 6)
                    )
            if self.cycles_check is not None:
                self.cycles_check.config(state="normal")
                if not self.cycles_check.winfo_manager():
                    self.cycles_check.pack(
                        side="left",
                        padx=(2, 2)
                    )
        else:
            if self.bidirectional_check is not None:
                self.bidirectional_check.pack_forget()
            if self.cycles_check is not None:
                self.cycles_check.pack_forget()
            if self.edit_manual_button is not None:
                self.edit_manual_button.config(
                    state="normal" if can_edit_manual else "disabled"
                )
                if not self.edit_manual_button.winfo_manager():
                    self.edit_manual_button.pack(
                        side="left",
                        padx=(2, 2)
                    )

        if self.edit_manual_panel_button is not None:
            if can_edit_manual:
                self.edit_manual_panel_button.config(state="normal")
                if not self.edit_manual_panel_button.winfo_manager():
                    if self.legend_info_label is not None:
                        self.edit_manual_panel_button.pack(
                            side="right",
                            padx=(4, 0),
                            before=self.legend_info_label
                        )
                    else:
                        self.edit_manual_panel_button.pack(
                            side="right",
                            padx=(4, 0)
                        )
            else:
                self.edit_manual_panel_button.pack_forget()

        self._on_configuration_frame_configure()

    def _on_configuration_frame_configure(
        self,
        event: Optional[Any] = None
    ) -> None:
        if (
            self.configuration_frame is None
            or self.left_config_group is None
            or self.right_config_group is None
            or self.config_separator is None
        ):
            return

        avail_w = (
            event.width
            if event is not None and getattr(event, "width", 0) > 1
            else self.configuration_frame.winfo_width()
        )
        if avail_w <= 1:
            return

        req_left = self.left_config_group.winfo_reqwidth()
        req_right = self.right_config_group.winfo_reqwidth()
        needed_single_row = req_left + req_right + 30

        target_rows = 2 if avail_w < needed_single_row else 1
        if target_rows == self._config_bar_rows:
            return

        self._config_bar_rows = target_rows
        if target_rows == 1:
            self.left_config_group.grid_configure(
                row=0,
                column=0,
                sticky="w",
                pady=0
            )
            self.config_separator.grid(
                row=0,
                column=1,
                sticky="ns",
                padx=8,
                pady=2
            )
            self.right_config_group.grid_configure(
                row=0,
                column=2,
                sticky="w",
                pady=0
            )
        else:
            self.config_separator.grid_forget()
            self.left_config_group.grid_configure(
                row=0,
                column=0,
                sticky="w",
                pady=(0, 3)
            )
            self.right_config_group.grid_configure(
                row=1,
                column=0,
                sticky="w",
                pady=(2, 0)
            )

    def create_labels_panel(
            self,
            parent: ttk.Frame
    ) -> None:

        self.labels_panel_frame = ttk.LabelFrame(
            parent,
            text="Etiquetas y decisiones de Dijkstra",
            padding=8,
            style="Section.TLabelframe"
        )

        self.labels_panel_frame.pack(
            side="top",
            fill="both",
            expand=True
        )

        top_info_row = ttk.Frame(
            self.labels_panel_frame
        )
        top_info_row.pack(
            fill="x",
            pady=(0, 6)
        )

        self.edit_manual_panel_button = ttk.Button(
            top_info_row,
            text="Modificar grafo",
            command=self.edit_manual_graph,
            style="TButton"
        )

        self.legend_info_label = ttk.Label(
            top_info_row,
            text=(
                "L = distancia acumulada | "
                "X = predecesor | k = iteración"
            ),
            font=("Segoe UI", 9),
            foreground="#8b949e",
            justify="left"
        )
        self.legend_info_label.pack(
            side="left",
            anchor="w",
            fill="x",
            expand=True
        )

        def _on_top_info_configure(event: Any) -> None:
            if self.legend_info_label is None:
                return
            btn_w = (
                self.edit_manual_panel_button.winfo_reqwidth() + 8
                if (
                    self.edit_manual_panel_button is not None
                    and self.edit_manual_panel_button.winfo_manager()
                )
                else 0
            )
            avail = max(140, event.width - btn_w - 4)
            self.legend_info_label.configure(wraplength=avail)

        top_info_row.bind("<Configure>", _on_top_info_configure)

        notebook = ttk.Notebook(
            self.labels_panel_frame
        )

        notebook.pack(
            fill="both",
            expand=True
        )

        current_tab = ttk.Frame(
            notebook,
            padding=4
        )

        history_tab = ttk.Frame(
            notebook,
            padding=4
        )

        decisions_tab = ttk.Frame(
            notebook,
            padding=4
        )

        notebook.add(
            current_tab,
            text="Etiquetas actuales"
        )

        notebook.add(
            history_tab,
            text="Historial"
        )

        notebook.add(
            decisions_tab,
            text="Decisiones"
        )

        def create_text_area(
                tab: ttk.Frame
        ) -> tk.Text:
            text_frame = ttk.Frame(
                tab
            )

            text_frame.pack(
                fill="both",
                expand=True
            )

            scrollbar = ttk.Scrollbar(
                text_frame,
                orient="vertical"
            )

            scrollbar.pack(
                side="right",
                fill="y"
            )

            text_widget = tk.Text(
                text_frame,
                wrap="word",
                width=1,
                height=1,
                state="disabled",
                font=("Consolas", 9),
                bg="#0d1117",
                fg="#c9d1d9",
                insertbackground="#e6edf3",
                selectbackground="#1f6feb",
                selectforeground="#ffffff",
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground="#21262d",
                highlightcolor="#30363d",
                yscrollcommand=scrollbar.set,
                padx=8,
                pady=8
            )

            text_widget.pack(
                side="left",
                fill="both",
                expand=True
            )

            scrollbar.config(
                command=text_widget.yview
            )

            return text_widget

        self.labels_text = create_text_area(
            current_tab
        )

        self.history_text = create_text_area(
            history_tab
        )

        self.decisions_text = create_text_area(
            decisions_tab
        )

        self.configure_text_color_tags()
        self.clear_labels()

    def create_result_panel(
        self,
        parent: ttk.Frame
    ) -> None:
        self.result_frame = tk.Frame(
            parent,
            bg="#0d1117",
            highlightbackground="#238636",
            highlightthickness=1,
            bd=0,
            height=185
        )
        self.result_frame.pack_propagate(False)

        self.result_header_label = tk.Label(
            self.result_frame,
            text="RESULTADO FINAL · CAMINO MÍNIMO",
            font=("Segoe UI", 9, "bold"),
            bg="#121d2f",
            fg="#58a6ff",
            pady=5
        )
        self.result_header_label.pack(
            fill="x"
        )

        self.result_body_frame = tk.Frame(
            self.result_frame,
            bg="#0d1117",
            padx=8,
            pady=6
        )
        self.result_body_frame.pack(
            fill="both",
            expand=True
        )

        self.result_badges_frame = tk.Frame(
            self.result_body_frame,
            bg="#0d1117"
        )
        self.result_badges_frame.pack(
            fill="x",
            pady=(0, 6)
        )

        self.result_summary_label = tk.Label(
            self.result_badges_frame,
            text="Distancia mínima: -",
            font=("Segoe UI", 10, "bold"),
            bg="#122117",
            fg="#3fb950",
            bd=0,
            relief="flat",
            highlightbackground="#1f4429",
            highlightthickness=1,
            padx=8,
            pady=4
        )
        self.result_summary_label.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 4)
        )

        self.result_count_label = tk.Label(
            self.result_badges_frame,
            text="Caminos mínimos: 0",
            font=("Segoe UI", 10, "bold"),
            bg="#121d2f",
            fg="#58a6ff",
            bd=0,
            relief="flat",
            highlightbackground="#1f3a60",
            highlightthickness=1,
            padx=8,
            pady=4
        )
        self.result_count_label.pack(
            side="right",
            fill="x",
            expand=True,
            padx=(4, 0)
        )

        text_container = tk.Frame(
            self.result_body_frame,
            bg="#0d1117",
            highlightbackground="#21262d",
            highlightthickness=1,
            bd=0
        )
        text_container.pack(
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            text_container,
            orient="vertical"
        )
        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.result_text = tk.Text(
            text_container,
            wrap="word",
            width=1,
            height=4,
            state="disabled",
            font=("Consolas", 11, "bold"),
            bg="#0d1117",
            fg="#e6edf3",
            relief="flat",
            bd=0,
            highlightthickness=0,
            spacing1=2,
            spacing3=2,
            yscrollcommand=scrollbar.set,
            padx=8,
            pady=6
        )
        self.result_text.pack(
            side="left",
            fill="both",
            expand=True
        )
        scrollbar.config(
            command=self.result_text.yview
        )

    def hide_result_panel(self) -> None:
        if self.result_frame is not None:
            self.result_frame.pack_forget()

    @staticmethod
    def _bind_mousewheel_to_canvas(
        widget: tk.Widget,
        canvas: tk.Canvas
    ) -> None:
        def _on_mousewheel(event: Any) -> str:
            bbox = canvas.bbox("all")
            if bbox is None:
                return "break"
            content_h = bbox[3] - bbox[1]
            canvas_h = canvas.winfo_height()
            if content_h <= canvas_h:
                return "break"
            if getattr(event, "num", None) == 4:
                step = -1
            elif getattr(event, "num", None) == 5:
                step = 1
            else:
                delta = getattr(event, "delta", 0)
                if delta == 0:
                    return "break"
                step = (
                    -int(delta / 120)
                    if abs(delta) >= 120
                    else (-1 if delta > 0 else 1)
                )
            canvas.yview_scroll(step, "units")
            return "break"

        widget.bind("<MouseWheel>", _on_mousewheel)
        widget.bind("<Button-4>", _on_mousewheel)
        widget.bind("<Button-5>", _on_mousewheel)

    def _update_manual_scrollregion(
        self,
        _event: Optional[Any] = None
    ) -> None:
        if self.manual_scroll_canvas is None:
            return
        bbox = self.manual_scroll_canvas.bbox("all")
        canvas_w = max(1, self.manual_scroll_canvas.winfo_width())
        canvas_h = max(1, self.manual_scroll_canvas.winfo_height())
        if bbox is not None:
            content_h = max(0, bbox[3] - bbox[1])
            region_h = max(content_h, canvas_h)
            self.manual_scroll_canvas.configure(
                scrollregion=(0, 0, canvas_w, region_h)
            )
            if content_h <= canvas_h:
                self.manual_scroll_canvas.yview_moveto(0.0)
        else:
            self.manual_scroll_canvas.configure(
                scrollregion=(0, 0, canvas_w, canvas_h)
            )
            self.manual_scroll_canvas.yview_moveto(0.0)

    def create_manual_panel(
        self,
        parent: ttk.Frame
    ) -> None:
        self.manual_panel_frame = ttk.LabelFrame(
            parent,
            text="Construcción manual del grafo",
            padding=(8, 6),
            style="Section.TLabelframe"
        )

        info_box = tk.Frame(
            self.manual_panel_frame,
            bg="#161b22",
            bd=0,
            relief="flat",
            highlightbackground="#21262d",
            highlightthickness=1,
            padx=8,
            pady=4
        )
        info_box.pack(
            fill="x",
            pady=(0, 5)
        )

        tk.Label(
            info_box,
            text=(
                "Puede conectar nodos dando clic sobre ellos "
                "en el grafo o usando el cuadro de abajo:"
            ),
            font=("Segoe UI", 8, "bold"),
            bg="#161b22",
            fg="#c9d1d9",
            justify="left",
            wraplength=330
        ).pack(
            anchor="w"
        )

        tk.Label(
            info_box,
            textvariable=self.manual_hint_var,
            font=("Segoe UI", 8),
            bg="#161b22",
            fg="#58a6ff",
            justify="left",
            wraplength=330
        ).pack(
            anchor="w",
            pady=(2, 0)
        )

        conventional_box = ttk.LabelFrame(
            self.manual_panel_frame,
            text="Agregar conexión manual",
            padding=(6, 4),
            style="Section.TLabelframe"
        )
        conventional_box.pack(
            fill="x",
            pady=(0, 6)
        )

        row_top = ttk.Frame(conventional_box)
        row_top.pack(fill="x", pady=(0, 3))

        ttk.Label(
            row_top,
            text="Nodo 1:",
            font=("Segoe UI", 8, "bold")
        ).pack(side="left", padx=(0, 3))

        self.manual_form_node1_combo = ttk.Combobox(
            row_top,
            textvariable=self.manual_form_node1_var,
            state="readonly",
            width=5
        )
        self.manual_form_node1_combo.pack(
            side="left",
            padx=(0, 8)
        )

        ttk.Label(
            row_top,
            text="Nodo 2:",
            font=("Segoe UI", 8, "bold")
        ).pack(side="left", padx=(0, 3))

        self.manual_form_node2_combo = ttk.Combobox(
            row_top,
            textvariable=self.manual_form_node2_var,
            state="readonly",
            width=5
        )
        self.manual_form_node2_combo.pack(
            side="left",
            padx=(0, 8)
        )

        ttk.Label(
            row_top,
            text="Peso:",
            font=("Segoe UI", 8, "bold")
        ).pack(side="left", padx=(0, 3))

        self.manual_form_weight_entry = ttk.Entry(
            row_top,
            textvariable=self.manual_form_weight_var,
            width=6
        )
        self.manual_form_weight_entry.pack(
            side="left",
            fill="x",
            expand=True
        )

        row_bottom = ttk.Frame(conventional_box)
        row_bottom.pack(fill="x", pady=(1, 0))

        ttk.Checkbutton(
            row_bottom,
            text="Bidireccional",
            variable=self.manual_form_bi_var
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            row_bottom,
            text="Agregar conexión",
            command=self.add_connection_from_form,
            style="Action.TButton"
        ).pack(
            side="right",
            fill="x",
            expand=True
        )

        header_row = ttk.Frame(
            self.manual_panel_frame
        )
        header_row.pack(
            fill="x",
            pady=(0, 3)
        )

        ttk.Label(
            header_row,
            text="Conexión",
            font=("Segoe UI", 9, "bold"),
            width=12
        ).pack(
            side="left",
            padx=(4, 2)
        )

        ttk.Label(
            header_row,
            text="Peso",
            font=("Segoe UI", 9, "bold"),
            width=8
        ).pack(
            side="left",
            padx=4
        )

        ttk.Label(
            header_row,
            text="Sentido",
            font=("Segoe UI", 9, "bold")
        ).pack(
            side="left",
            padx=4
        )

        bottom_frame = ttk.Frame(
            self.manual_panel_frame
        )
        bottom_frame.pack(
            side="bottom",
            fill="x",
            pady=(6, 0)
        )

        ttk.Button(
            bottom_frame,
            text="Confirmar grafo",
            command=self.confirm_manual_graph,
            style="Action.TButton"
        ).pack(
            fill="x"
        )

        list_container = ttk.Frame(
            self.manual_panel_frame
        )
        list_container.pack(
            side="top",
            fill="both",
            expand=True
        )

        self.manual_scroll_canvas = tk.Canvas(
            list_container,
            bg="#0d1117",
            bd=0,
            highlightthickness=0,
            width=1,
            height=1
        )
        scrollbar = ttk.Scrollbar(
            list_container,
            orient="vertical",
            command=self.manual_scroll_canvas.yview
        )
        self.manual_rows_container = ttk.Frame(
            self.manual_scroll_canvas
        )

        self.manual_rows_container.bind(
            "<Configure>",
            self._update_manual_scrollregion
        )

        canvas_win = self.manual_scroll_canvas.create_window(
            (0, 0),
            window=self.manual_rows_container,
            anchor="nw"
        )

        def _on_canvas_configure(event: Any) -> None:
            if self.manual_scroll_canvas is not None:
                self.manual_scroll_canvas.itemconfig(
                    canvas_win,
                    width=event.width
                )
                self._update_manual_scrollregion()

        self.manual_scroll_canvas.bind(
            "<Configure>",
            _on_canvas_configure
        )

        self.manual_scroll_canvas.configure(
            yscrollcommand=scrollbar.set
        )

        self._bind_mousewheel_to_canvas(
            self.manual_scroll_canvas,
            self.manual_scroll_canvas
        )
        self._bind_mousewheel_to_canvas(
            self.manual_rows_container,
            self.manual_scroll_canvas
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )
        self.manual_scroll_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

    def validate_node_count(self) -> Optional[int]:
        node_count_text = (
            self.node_count_var.get().strip()
        )

        if not node_count_text:

            messagebox.showwarning(
                "Dato requerido",
                "Ingrese primero el número de nodos."
            )

            return None

        try:

            node_count = int(
                node_count_text
            )

        except ValueError:

            messagebox.showerror(
                "Valor inválido",
                "Ingrese un número entero."
            )

            return None

        if not 7 <= node_count <= 16:

            messagebox.showerror(
                "Rango inválido",
                "El número de nodos debe estar entre 7 y 16."
            )

            return None

        return node_count

    def generate_graph(self) -> None:
        node_count = self.validate_node_count()

        if node_count is None:

            return

        mode = self.mode_var.get()

        if mode == "Aleatorio":
            self.is_manual_graph_created = False
            self.exit_manual_build_mode()
            self.graph_model.create_random_graph(
                node_count,
                allow_bidirectional=self.bidirectional_var.get(),
                allow_cycles=self.cycles_var.get()
            )
            self.cached_positions = {}
            self.finish_graph_generation()

        else:
            self.start_manual_build_mode(
                node_count
            )

    def start_manual_build_mode(
        self,
        node_count: int
    ) -> None:
        self.manual_build_mode = True
        self.is_manual_graph_created = False
        self.manual_node_count = node_count
        self.manual_selected_node = None
        self.manual_highlighted_nodes = set()

        for conn in self.manual_connections:
            row_frame = conn.get("row_frame")
            if row_frame is not None:
                row_frame.destroy()
        self.manual_connections = []
        self._update_manual_scrollregion()

        node_names = [
            f"N{i}" for i in range(1, node_count + 1)
        ]
        if self.manual_form_node1_combo is not None:
            self.manual_form_node1_combo["values"] = node_names
        if self.manual_form_node2_combo is not None:
            self.manual_form_node2_combo["values"] = node_names
        self.manual_form_node1_var.set("")
        self.manual_form_node2_var.set("")
        self.manual_form_weight_var.set("")
        self.manual_form_bi_var.set(False)

        self.hide_result_panel()
        if self.labels_panel_frame is not None:
            self.labels_panel_frame.pack_forget()
        if self.manual_panel_frame is not None:
            self.manual_panel_frame.pack(
                side="top",
                fill="both",
                expand=True
            )

        self.set_dijkstra_controls_state("disabled")
        self.update_manual_edit_controls()

        self.graph_model.initialize_empty_graph(
            node_count
        )
        self.cached_positions = {}
        self.cached_positions = self.calculate_positions(
            force_recalculate=True
        )

        self.reset_graph_view = True
        self.manual_hint_var.set(
            "Paso: Seleccione nodos en el grafo o use el formulario..."
        )
        self.display_graph()
        self.clear_labels()

        self.status_var.set(
            f"Modo manual activo ({node_count} nodos). "
            "Agregue conexiones dando clic en los nodos o "
            "usando el cuadro superior."
        )

    def edit_manual_graph(self) -> None:
        if self.manual_build_mode:
            return
        if not self.is_manual_graph_created or self.manual_node_count <= 0:
            messagebox.showinfo(
                "Modificar grafo manual",
                "Primero debe generar y confirmar un grafo "
                "en modo Manual para poder modificarlo."
            )
            return

        self.mode_var.set("Manual")
        self.node_count_var.set(str(self.manual_node_count))

        self.graph_model.reset_algorithm_data()
        self.hide_result_panel()
        self.clear_labels()

        self.manual_build_mode = True
        self.manual_selected_node = None
        self.manual_highlighted_nodes = set()

        node_names = [
            f"N{i}" for i in range(1, self.manual_node_count + 1)
        ]
        if self.manual_form_node1_combo is not None:
            self.manual_form_node1_combo["values"] = node_names
        if self.manual_form_node2_combo is not None:
            self.manual_form_node2_combo["values"] = node_names
        self.manual_form_node1_var.set("")
        self.manual_form_node2_var.set("")
        self.manual_form_weight_var.set("")
        self.manual_form_bi_var.set(False)

        if self.labels_panel_frame is not None:
            self.labels_panel_frame.pack_forget()
        if self.manual_panel_frame is not None:
            self.manual_panel_frame.pack(
                side="top",
                fill="both",
                expand=True
            )

        self.set_dijkstra_controls_state("disabled")
        self.update_manual_edit_controls()

        self.manual_hint_var.set(
            "Edición activa: modifique pesos, elimine o "
            "agregue conexiones y confirme."
        )
        self.sync_manual_graph_edges()

        self.status_var.set(
            f"Editando grafo manual ({self.manual_node_count} nodos). "
            "Se ha reiniciado Dijkstra para evitar inconsistencias."
        )

    def exit_manual_build_mode(self) -> None:
        self.manual_build_mode = False
        self.manual_selected_node = None
        self.manual_highlighted_nodes = set()

        if self.manual_panel_frame is not None:
            self.manual_panel_frame.pack_forget()

        if self.labels_panel_frame is not None:
            self.labels_panel_frame.pack(
                side="top",
                fill="both",
                expand=True
            )

        self.set_dijkstra_controls_state("normal")
        self.update_manual_edit_controls()

    def set_dijkstra_controls_state(
        self,
        state: str
    ) -> None:
        combo_state = (
            "readonly" if state == "normal" else "disabled"
        )
        if self.source_combo is not None:
            self.source_combo.config(state=combo_state)
        if self.target_combo is not None:
            self.target_combo.config(state=combo_state)
        if self.init_button is not None:
            self.init_button.config(state=state)
        if self.next_button is not None:
            self.next_button.config(state=state)
        if self.finish_button is not None:
            self.finish_button.config(state=state)

    def add_connection_from_form(self) -> None:
        if not self.manual_build_mode:
            return

        u = self.manual_form_node1_var.get().strip()
        v = self.manual_form_node2_var.get().strip()
        w_str = self.manual_form_weight_var.get().strip()
        is_bi = self.manual_form_bi_var.get()

        if not u or not v:
            messagebox.showwarning(
                "Datos incompletos",
                "Seleccione el Nodo 1 y el Nodo 2."
            )
            return

        if u == v:
            messagebox.showerror(
                "Conexión inválida",
                "El Nodo 1 y el Nodo 2 deben ser distintos."
            )
            return

        if w_str:
            try:
                weight_val = int(w_str)
            except ValueError:
                messagebox.showerror(
                    "Peso inválido",
                    "El peso debe ser un número entero."
                )
                if self.manual_form_weight_entry is not None:
                    self.manual_form_weight_entry.focus_set()
                return

            if weight_val <= 0:
                messagebox.showerror(
                    "Peso inválido",
                    "El peso debe ser mayor que cero."
                )
                if self.manual_form_weight_entry is not None:
                    self.manual_form_weight_entry.focus_set()
                return

        self.manual_selected_node = None
        self.manual_highlighted_nodes = {u, v}

        applied = self.handle_manual_connection_creation(
            u,
            v,
            weight_str=w_str,
            is_bi=is_bi,
            from_form=True
        )
        if applied:
            self.manual_form_node1_var.set("")
            self.manual_form_node2_var.set("")
            self.manual_form_weight_var.set("")
            self.manual_form_bi_var.set(False)

    def handle_manual_connection_creation(
        self,
        first_node: str,
        second_node: str,
        weight_str: str = "",
        is_bi: bool = False,
        from_form: bool = False
    ) -> bool:
        existing_same = self.find_manual_connection(
            first_node,
            second_node
        )
        if existing_same is not None:
            arrow_txt = (
                "↔"
                if existing_same["bidirectional_var"].get()
                else "→"
            )
            cur_u = existing_same["u"]
            cur_v = existing_same["v"]
            cur_w = (
                existing_same["weight_var"].get().strip()
                or "sin asignar"
            )
            overwrite = messagebox.askyesno(
                "Conexión existente",
                f"Ya existe la conexión {cur_u} {arrow_txt} {cur_v} "
                f"(peso: {cur_w}).\n"
                "¿Desea sobrescribirla?"
            )
            if overwrite:
                existing_same["u"] = first_node
                existing_same["v"] = second_node
                existing_same["bidirectional_var"].set(is_bi)
                existing_same["weight_var"].set(weight_str)
                self.update_manual_connection_label(
                    existing_same
                )
                self.sync_manual_graph_edges()
                self.manual_hint_var.set(
                    f"Conexión {first_node} "
                    f"{'↔' if is_bi else '→'} {second_node} "
                    "sobrescrita."
                )
                entry_widget = existing_same.get("weight_entry")
                if not from_form and entry_widget is not None:
                    entry_widget.focus_set()
                return True

            self.display_graph()
            return False

        existing_reverse = self.find_manual_connection(
            second_node,
            first_node
        )
        if existing_reverse is not None:
            make_bi = messagebox.askyesno(
                "Conexión inversa detectada",
                f"Ya existe la conexión {second_node} -> {first_node}.\n"
                "¿Desea volverla bidireccional?"
            )
            if make_bi:
                existing_reverse["bidirectional_var"].set(True)
                if weight_str:
                    existing_reverse["weight_var"].set(weight_str)
                self.update_manual_connection_label(
                    existing_reverse
                )
                self.sync_manual_graph_edges()
                self.manual_hint_var.set(
                    f"Conexión {second_node} ↔ {first_node} "
                    "convertida en bidireccional."
                )
                return True

            self.display_graph()
            return False

        self.add_manual_connection_row(
            first_node,
            second_node,
            initial_weight=weight_str,
            initial_bi=is_bi,
            focus_weight=not from_form
        )
        self.manual_hint_var.set(
            f"Conexión {first_node} "
            f"{'↔' if is_bi else '→'} {second_node} agregada."
        )
        self.sync_manual_graph_edges()
        return True

    def on_canvas_click(
        self,
        event: Any
    ) -> None:
        if not self.manual_build_mode:
            return
        if (
            self.graph_axis is None
            or event.inaxes != self.graph_axis
        ):
            return
        if (
            self.toolbar is not None
            and getattr(self.toolbar, "mode", "") != ""
        ):
            return
        if event.xdata is None or event.ydata is None:
            return

        positions = self.cached_positions
        if not positions:
            return

        clicked_node: Optional[str] = None
        best_dist_px = float("inf")

        for node, (nx_coord, ny_coord) in positions.items():
            px, py = self.graph_axis.transData.transform(
                (nx_coord, ny_coord)
            )
            dist_px = math.hypot(
                event.x - px,
                event.y - py
            )
            if dist_px < 28.0 and dist_px < best_dist_px:
                best_dist_px = dist_px
                clicked_node = node

        if clicked_node is None:
            return

        if self.manual_selected_node is None:
            self.manual_selected_node = clicked_node
            self.manual_highlighted_nodes = {clicked_node}
            self.manual_hint_var.set(
                f"Nodo {clicked_node} seleccionado. "
                "Haga clic en otro nodo para conectar."
            )
            self.status_var.set(
                f"Nodo origen seleccionado: {clicked_node}. "
                "Seleccione el nodo destino."
            )
            self.display_graph()
            return

        first_node = self.manual_selected_node
        second_node = clicked_node

        if first_node == second_node:
            self.manual_selected_node = None
            self.manual_highlighted_nodes = set()
            self.manual_hint_var.set(
                "Selección cancelada. Haga clic en un nodo..."
            )
            self.display_graph()
            return

        self.manual_highlighted_nodes = {
            first_node,
            second_node
        }
        self.manual_selected_node = None

        self.handle_manual_connection_creation(
            first_node,
            second_node,
            weight_str="",
            is_bi=False,
            from_form=False
        )

    def find_manual_connection(
        self,
        u: str,
        v: str
    ) -> Optional[Dict[str, Any]]:
        for conn in self.manual_connections:
            if conn["u"] == u and conn["v"] == v:
                return conn
            if (
                conn["u"] == v
                and conn["v"] == u
                and conn["bidirectional_var"].get()
            ):
                return conn
        return None

    @staticmethod
    def update_manual_connection_label(
        conn: Dict[str, Any]
    ) -> None:
        lbl = conn.get("label_widget")
        if lbl is None:
            return
        arrow = (
            "↔"
            if conn["bidirectional_var"].get()
            else "→"
        )
        lbl.config(
            text=f"{conn['u']} {arrow} {conn['v']}"
        )

    def add_manual_connection_row(
        self,
        u: str,
        v: str,
        initial_weight: str = "",
        initial_bi: bool = False,
        focus_weight: bool = True
    ) -> None:
        if self.manual_rows_container is None:
            return

        row_frame = ttk.Frame(
            self.manual_rows_container,
            padding=(2, 3)
        )
        row_frame.pack(
            fill="x",
            pady=2
        )

        weight_var = tk.StringVar(value=initial_weight)
        bidirectional_var = tk.BooleanVar(value=initial_bi)

        conn_data: Dict[str, Any] = {
            "u": u,
            "v": v,
            "weight_var": weight_var,
            "bidirectional_var": bidirectional_var,
            "row_frame": row_frame,
            "label_widget": None,
            "weight_entry": None
        }

        arrow_char = "↔" if initial_bi else "→"
        lbl = ttk.Label(
            row_frame,
            text=f"{u} {arrow_char} {v}",
            font=("Consolas", 10, "bold"),
            width=11
        )
        lbl.pack(
            side="left",
            padx=(2, 4)
        )
        conn_data["label_widget"] = lbl

        weight_entry = ttk.Entry(
            row_frame,
            textvariable=weight_var,
            width=7
        )
        weight_entry.pack(
            side="left",
            padx=4
        )
        conn_data["weight_entry"] = weight_entry

        def _on_weight_change(*_args: Any) -> None:
            self.sync_manual_graph_edges()

        def _on_bi_toggle() -> None:
            self.update_manual_connection_label(conn_data)
            self.sync_manual_graph_edges()

        def _on_remove() -> None:
            if conn_data in self.manual_connections:
                self.manual_connections.remove(conn_data)
            row_frame.destroy()
            if self.manual_scroll_canvas is not None:
                self.manual_scroll_canvas.update_idletasks()
                self._update_manual_scrollregion()
            self.sync_manual_graph_edges()

        weight_var.trace_add("write", _on_weight_change)

        bi_check = ttk.Checkbutton(
            row_frame,
            text="Bidireccional",
            variable=bidirectional_var,
            command=_on_bi_toggle
        )
        bi_check.pack(
            side="left",
            padx=4
        )

        remove_btn = tk.Button(
            row_frame,
            text="✕",
            command=_on_remove,
            font=("Segoe UI", 8, "bold"),
            fg="#f85149",
            bg="#161b22",
            activebackground="#2d1519",
            activeforeground="#ff7b72",
            bd=0,
            highlightthickness=1,
            highlightbackground="#30363d",
            relief="flat",
            padx=5,
            pady=1
        )
        remove_btn.pack(
            side="right",
            padx=2
        )

        if self.manual_scroll_canvas is not None:
            for row_widget in (
                row_frame,
                lbl,
                weight_entry,
                bi_check,
                remove_btn
            ):
                self._bind_mousewheel_to_canvas(
                    row_widget,
                    self.manual_scroll_canvas
                )

        self.manual_connections.append(conn_data)
        if focus_weight:
            weight_entry.focus_set()

        if self.manual_scroll_canvas is not None:
            self.manual_scroll_canvas.update_idletasks()
            self._update_manual_scrollregion()
            bbox = self.manual_scroll_canvas.bbox("all")
            canvas_h = self.manual_scroll_canvas.winfo_height()
            if (
                bbox is not None
                and 1 < canvas_h < (bbox[3] - bbox[1])
            ):
                self.manual_scroll_canvas.yview_moveto(1.0)
            else:
                self.manual_scroll_canvas.yview_moveto(0.0)

    def sync_manual_graph_edges(self) -> None:
        if not self.manual_build_mode:
            return

        graph = nx.DiGraph()
        for index in range(1, self.manual_node_count + 1):
            graph.add_node(f"N{index}")

        for conn in self.manual_connections:
            u = conn["u"]
            v = conn["v"]
            w_str = conn["weight_var"].get().strip()
            try:
                w_val = int(w_str)
                if w_val <= 0:
                    w_val = 0
            except ValueError:
                w_val = 0

            graph.add_edge(u, v, weight=w_val)
            if conn["bidirectional_var"].get():
                graph.add_edge(v, u, weight=w_val)

        self.graph_model.graph = graph
        self.display_graph()

    def confirm_manual_graph(self) -> None:
        if not self.manual_connections:
            messagebox.showwarning(
                "Sin conexiones",
                "Debe crear al menos una conexión dando clic "
                "sobre los nodos del grafo."
            )
            return

        edges: List[Tuple[str, str, int]] = []

        for conn in self.manual_connections:
            u = conn["u"]
            v = conn["v"]
            w_str = conn["weight_var"].get().strip()
            if not w_str:
                messagebox.showerror(
                    "Peso faltante",
                    f"Ingrese un peso para la conexión {u} -> {v}."
                )
                entry_widget = conn.get("weight_entry")
                if entry_widget is not None:
                    entry_widget.focus_set()
                return

            try:
                weight = int(w_str)
            except ValueError:
                messagebox.showerror(
                    "Peso inválido",
                    f"El peso de la conexión {u} -> {v} "
                    "debe ser un número entero."
                )
                entry_widget = conn.get("weight_entry")
                if entry_widget is not None:
                    entry_widget.focus_set()
                return

            if weight <= 0:
                messagebox.showerror(
                    "Peso inválido",
                    f"El peso de la conexión {u} -> {v} "
                    "debe ser mayor que cero."
                )
                entry_widget = conn.get("weight_entry")
                if entry_widget is not None:
                    entry_widget.focus_set()
                return

            edges.append((u, v, weight))
            if conn["bidirectional_var"].get():
                edges.append((v, u, weight))

        try:
            self.graph_model.create_manual_graph(
                self.manual_node_count,
                edges,
                preserve_seed=self.graph_model.layout_seed
            )
        except ValueError as error:
            messagebox.showerror(
                "Grafo inválido",
                str(error)
            )
            return

        self.is_manual_graph_created = True
        self.exit_manual_build_mode()
        self.finish_graph_generation(
            preserve_positions=True
        )

    def finish_graph_generation(
        self,
        preserve_positions: bool = False
    ) -> None:
        self.hide_result_panel()

        if not preserve_positions:
            self.cached_positions = {}

        nodes = self.graph_model.get_nodes()

        if self.source_combo is not None:
            self.source_combo["values"] = nodes

        if self.target_combo is not None:
            self.target_combo["values"] = nodes

        if nodes:

            self.source_var.set(
                nodes[0]
            )

            self.target_var.set(
                nodes[-1]
            )

        self.reset_graph_view = True

        self.display_graph()
        self.clear_labels()

        edge_count = (
            self.graph_model.graph.number_of_edges()
        )

        self.status_var.set(
            f"Grafo creado: {len(nodes)} nodos y "
            f"{edge_count} aristas. "
            f"Seleccione origen y destino."
        )

    def calculate_positions(
            self,
            force_recalculate: bool = False
    ) -> Dict[str, Tuple[float, float]]:

        graph = self.graph_model.graph
        nodes = list(graph.nodes)
        node_count = len(nodes)

        if node_count == 0:
            return {}

        is_manual = (
            self.manual_build_mode
            or self.is_manual_graph_created
        )
        layout_signature = (
            tuple(nodes),
            self.graph_model.layout_seed,
            () if is_manual else tuple(sorted(graph.edges))
        )

        if (
            not force_recalculate
            and self.cached_positions
            and self._cached_layout_signature == layout_signature
        ):
            return self.cached_positions

        if node_count == 1:
            self.cached_positions = {nodes[0]: (8.0, 5.0)}
            self._cached_layout_signature = layout_signature
            return self.cached_positions

        rng = random.Random(self.graph_model.layout_seed)
        node_rank = {
            node: idx for idx, node in enumerate(nodes)
        }

        try:
            topo_nodes = list(
                nx.lexicographical_topological_sort(
                    graph,
                    key=lambda n: node_rank.get(n, 0)
                )
            )
        except nx.NetworkXUnfeasible:
            topo_nodes = list(nodes)

        first_node = nodes[0]
        last_node = nodes[-1]
        middle_topo = [
            n for n in topo_nodes if n not in (first_node, last_node)
        ]
        topo_nodes = [first_node] + middle_topo + [last_node]

        zones_coords = self.graph_model.build_base_2d_slots(
            node_count,
            rng
        )
        zones_nodes: List[List[str]] = []
        cursor = 0

        for zone_pts in zones_coords:
            k = len(zone_pts)
            zones_nodes.append(
                list(topo_nodes[cursor : cursor + k])
            )
            cursor += k

        positions: Dict[str, List[float]] = {}
        for z_idx, zone_pts in enumerate(zones_coords):
            for i, u in enumerate(zones_nodes[z_idx]):
                positions[u] = [
                    zone_pts[i][0],
                    zone_pts[i][1]
                ]

        edges = list(graph.edges)
        if not edges and len(zones_nodes) > 2:
            for z_idx in range(1, len(zones_nodes) - 1):
                rng.shuffle(zones_nodes[z_idx])
            for z_idx in range(1, len(zones_nodes) - 2):
                if (
                    zones_nodes[z_idx]
                    and zones_nodes[z_idx + 1]
                    and rng.random() < 0.5
                ):
                    i_a = rng.randrange(len(zones_nodes[z_idx]))
                    i_b = rng.randrange(len(zones_nodes[z_idx + 1]))
                    (
                        zones_nodes[z_idx][i_a],
                        zones_nodes[z_idx + 1][i_b],
                    ) = (
                        zones_nodes[z_idx + 1][i_b],
                        zones_nodes[z_idx][i_a],
                    )
            for z_idx, zone_pts in enumerate(zones_coords):
                if 0 < z_idx < len(zones_coords) - 1:
                    shifted_pts: List[Tuple[float, float]] = []
                    for px, py in zone_pts:
                        nx_p = max(
                            2.1,
                            min(13.9, px + rng.uniform(-0.55, 0.55))
                        )
                        ny_p = max(
                            1.1,
                            min(8.9, py + rng.uniform(-0.75, 0.75))
                        )
                        shifted_pts.append((nx_p, ny_p))
                    rng.shuffle(shifted_pts)
                    zones_coords[z_idx] = shifted_pts
                for i, u in enumerate(zones_nodes[z_idx]):
                    positions[u] = [
                        zones_coords[z_idx][i][0],
                        zones_coords[z_idx][i][1]
                    ]
            for z_idx in range(len(zones_nodes) - 1):
                curr_z = zones_nodes[z_idx]
                next_z = zones_nodes[z_idx + 1]
                for u in curr_z:
                    v = rng.choice(next_z)
                    edges.append((u, v))
                for v in next_z:
                    if not any(dst == v for _, dst in edges):
                        u = rng.choice(curr_z)
                        edges.append((u, v))

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
                        positions[u][0], positions[u][1] = (
                            z_pts[pt_idx]
                        )

                    cost = 0.0

                    for u, v in edges:
                        p1 = (positions[u][0], positions[u][1])
                        p2 = (positions[v][0], positions[v][1])
                        dist = math.hypot(
                            p2[0] - p1[0],
                            p2[1] - p1[1]
                        )
                        cost += dist * 1.2
                        if (
                            node_rank.get(u, 0) < node_rank.get(v, 0)
                            and p2[0] < p1[0] + 0.3
                        ):
                            cost += (p1[0] + 0.3 - p2[0]) * 8.0

                    for idx1 in range(len(edges)):
                        u1, v1 = edges[idx1]
                        if (
                            u1 not in z_nodes
                            and v1 not in z_nodes
                        ):
                            continue
                        p1 = (
                            positions[u1][0],
                            positions[u1][1]
                        )
                        p2 = (
                            positions[v1][0],
                            positions[v1][1]
                        )
                        for idx2 in range(idx1 + 1, len(edges)):
                            u2, v2 = edges[idx2]
                            if u1 in (u2, v2) or v1 in (u2, v2):
                                continue
                            p3 = (
                                positions[u2][0],
                                positions[u2][1]
                            )
                            p4 = (
                                positions[v2][0],
                                positions[v2][1]
                            )
                            if self.graph_model.segments_intersect(
                                p1,
                                p2,
                                p3,
                                p4
                            ):
                                cost += 35.0

                    if cost < best_cost:
                        best_cost = cost
                        best_perm = perm

                for idx_in_zone, pt_idx in enumerate(best_perm):
                    u = z_nodes[idx_in_zone]
                    positions[u][0], positions[u][1] = (
                        z_pts[pt_idx]
                    )

        width = 16.0
        height = 10.0
        x_margin = 1.2
        y_margin = 1.0
        positions[first_node] = [x_margin, height / 2.0]
        positions[last_node] = [width - x_margin, height / 2.0]
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
                        rep = (
                            (min_node_dist * 1.35 - dist) ** 2
                            * 1.9
                            / dist
                        )
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
                if (
                    node_rank.get(u, 0) < node_rank.get(v, 0)
                    and dx < 1.1
                ):
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
                    t = (
                        (wx - x1) * seg_dx + (wy - y1) * seg_dy
                    ) / seg_len_sq
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
                            push = (
                                (clearance_dist - odist)
                                * 2.4
                                / odist
                            )
                            forces[w][0] += odx * push
                            forces[w][1] += ody * push
                            forces[u][0] -= odx * push * 0.2
                            forces[u][1] -= ody * push * 0.2
                            forces[v][0] -= odx * push * 0.2
                            forces[v][1] -= ody * push * 0.2

            for u in nodes:
                if u in (first_node, last_node):
                    continue
                fx, fy = forces[u]
                mag = math.hypot(fx, fy)
                if mag > 1.0:
                    fx /= mag
                    fy /= mag
                positions[u][0] = max(
                    x_margin,
                    min(
                        width - x_margin,
                        positions[u][0] + fx * temp
                    )
                )
                positions[u][1] = max(
                    y_margin,
                    min(
                        height - y_margin,
                        positions[u][1] + fy * temp
                    )
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
            final_positions[u] = (
                float(nx_coord),
                float(ny_coord)
            )

        final_positions[first_node] = (1.0, 5.0)
        final_positions[last_node] = (15.0, 5.0)

        self.cached_positions = final_positions
        self._cached_layout_signature = layout_signature
        return final_positions

    @staticmethod
    def compute_smart_curvatures_and_labels(
        graph: nx.DiGraph,
        positions: Dict[str, Tuple[float, float]]
    ) -> Tuple[
        Dict[Tuple[str, str], float],
        Dict[Tuple[str, str], Tuple[float, float]]
    ]:
        nodes = list(graph.nodes)
        edges = list(graph.edges)

        def bezier_point(
            bx1: float,
            by1: float,
            bx2: float,
            by2: float,
            b_rad: float,
            b_t: float
        ) -> Tuple[float, float]:
            dx = bx2 - bx1
            dy = by2 - by1
            cx = (bx1 + bx2) / 2.0 + b_rad * dy
            cy = (by1 + by2) / 2.0 - b_rad * dx
            rem = 1.0 - b_t
            out_x = (
                rem * rem * bx1
                + 2.0 * rem * b_t * cx
                + b_t * b_t * bx2
            )
            out_y = (
                rem * rem * by1
                + 2.0 * rem * b_t * cy
                + b_t * b_t * by2
            )
            return out_x, out_y

        edge_curvatures: Dict[Tuple[str, str], float] = {}
        placed_midpoints: List[Tuple[float, float]] = []

        candidate_rads = [
            0.0,
            0.10,
            -0.10,
            0.18,
            -0.18,
            0.26,
            -0.26
        ]

        for u, v in edges:
            if (u, v) in edge_curvatures:
                continue

            has_reverse = graph.has_edge(v, u)
            same_weight = (
                has_reverse
                and graph[u][v].get("weight")
                == graph[v][u].get("weight")
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
                    bx, by = bezier_point(
                        x1, y1, x2, y2, rad, t
                    )
                    for w in nodes:
                        if w == u or w == v:
                            continue
                        wx, wy = positions[w]
                        d = math.hypot(bx - wx, by - wy)
                        if d < 1.35:
                            cost += (1.35 - d) ** 2 * 30.0

                mx, my = bezier_point(
                    x1, y1, x2, y2, rad, 0.5
                )
                for pmx, pmy in placed_midpoints:
                    md = math.hypot(mx - pmx, my - pmy)
                    if md < 0.75:
                        cost += (0.75 - md) ** 2 * 12.0

                if cost < best_cost:
                    best_cost = cost
                    best_rad = rad

            edge_curvatures[(u, v)] = best_rad
            placed_midpoints.append(
                bezier_point(x1, y1, x2, y2, best_rad, 0.5)
            )

            if same_weight:
                edge_curvatures[(v, u)] = -best_rad

        label_coords: Dict[
            Tuple[str, str],
            Tuple[float, float]
        ] = {}
        placed_labels: List[Tuple[float, float]] = []
        candidate_ts = [
            0.50,
            0.40,
            0.60,
            0.33,
            0.67,
            0.27,
            0.73
        ]

        for u, v in edges:
            if (u, v) in label_coords:
                continue

            has_reverse = graph.has_edge(v, u)
            same_weight = (
                has_reverse
                and graph[u][v].get("weight")
                == graph[v][u].get("weight")
            )

            x1, y1 = positions[u]
            x2, y2 = positions[v]
            rad = edge_curvatures[(u, v)]
            best_pt = bezier_point(
                x1, y1, x2, y2, rad, 0.5
            )
            best_cost = float("inf")

            for t in candidate_ts:
                lx, ly = bezier_point(
                    x1, y1, x2, y2, rad, t
                )
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

    def display_graph(self) -> None:

        if self.graph_frame is None:
            return

        preserved_xlim = None
        preserved_ylim = None

        if (
                self.figure is None
                or self.canvas is None
                or self.graph_axis is None
        ):

            self.figure = Figure(
                figsize=(11, 7),
                dpi=100,
                facecolor="#0d1117"
            )
            self.figure.subplots_adjust(
                left=0.02,
                right=0.98,
                bottom=0.04,
                top=0.91
            )

            self.graph_axis = self.figure.add_subplot(
                111
            )
            self.graph_axis.set_facecolor("#0d1117")

            self.canvas = FigureCanvasTkAgg(
                self.figure,
                master=self.graph_frame
            )

            self.canvas.mpl_connect(
                "button_press_event",
                self.on_canvas_click
            )

            self.toolbar = BarraHerramientasEspanol(
                self.canvas,
                self.graph_frame,
                pack_toolbar=False
            )

            self.toolbar.update()
            self.toolbar.apply_dark_style()
            self.toolbar.pack(
                side="top",
                fill="x"
            )

            tk_canvas_widget = self.canvas.get_tk_widget()
            try:
                tk_canvas_widget.configure(
                    bg="#0d1117",
                    bd=0,
                    highlightthickness=0
                )
            except tk.TclError:
                pass

            tk_canvas_widget.pack(
                side="top",
                fill="both",
                expand=True
            )

        else:

            if not self.reset_graph_view:
                preserved_xlim = (
                    self.graph_axis.get_xlim()
                )

                preserved_ylim = (
                    self.graph_axis.get_ylim()
                )

            self.graph_axis.clear()

        axis = self.graph_axis
        axis.set_facecolor("#0d1117")
        if self.figure is not None:
            self.figure.patch.set_facecolor("#0d1117")

        graph = self.graph_model.graph

        positions = self.calculate_positions()

        nodes = self.graph_model.get_nodes()

        source = self.graph_model.source
        target = self.graph_model.target

        node_count = len(nodes)
        edge_count = graph.number_of_edges()

        if node_count <= 10:
            base_node_size = 1000
            key_node_size = 1100
            current_node_size = 1200
            node_label_size = 10

        elif node_count <= 13:
            base_node_size = 850
            key_node_size = 950
            current_node_size = 1000
            node_label_size = 9

        else:
            base_node_size = 750
            key_node_size = 850
            current_node_size = 950
            node_label_size = 9

        if edge_count <= 20:
            edge_width = 1.3
            arrow_size = 18
            weight_font_size: float = 8
        elif edge_count <= 32:
            edge_width = 1.1
            arrow_size = 15
            weight_font_size = 7.5
        else:
            edge_width = 0.95
            arrow_size = 13
            weight_font_size = 7

        highlight_edge_width = (
            2.5 if edge_count <= 20 else 2.2
        )

        highlight_arrow_size = (
            20 if edge_count <= 20 else 18
        )

        edge_node_sizes = []

        for node in nodes:

            if node == source or node == target:
                size = key_node_size

            elif (
                    node == self.graph_model.current_node
                    and not self.graph_model.algorithm_finished
            ):
                size = current_node_size

            elif (
                    self.manual_build_mode
                    and node in self.manual_highlighted_nodes
            ):
                size = key_node_size

            else:
                size = base_node_size

            edge_node_sizes.append(size)

        processed = set(
            self.graph_model.processed_nodes
        )

        optimal_edges = set()

        if self.graph_model.algorithm_finished:

            shortest_paths = (
                self.graph_model.get_shortest_paths()
            )

            for path in shortest_paths:

                for index in range(len(path) - 1):

                    optimal_edges.add(
                        (
                            path[index],
                            path[index + 1]
                        )
                    )

        manual_blue_nodes = (
            set(self.manual_highlighted_nodes)
            if self.manual_build_mode
            else set()
        )

        default_nodes = [
            node
            for node in nodes
            if node != source
            and node != target
            and node not in processed
            and node not in manual_blue_nodes
        ]

        if default_nodes:

            nx.draw_networkx_nodes(
                graph,
                positions,
                ax=axis,
                nodelist=default_nodes,
                node_size=base_node_size,
                node_color="#161b22",
                edgecolors="#30363d",
                linewidths=1.2
            )

        if manual_blue_nodes:
            nx.draw_networkx_nodes(
                graph,
                positions,
                ax=axis,
                nodelist=list(manual_blue_nodes),
                node_size=key_node_size,
                node_color="#121d2f",
                edgecolors="#58a6ff",
                linewidths=1.6
            )

        if source is not None:

            nx.draw_networkx_nodes(
                graph,
                positions,
                ax=axis,
                nodelist=[source],
                node_size=key_node_size,
                node_color="#122117",
                edgecolors="#3fb950",
                linewidths=1.5
            )

        if target is not None and target != source:

            nx.draw_networkx_nodes(
                graph,
                positions,
                ax=axis,
                nodelist=[target],
                node_size=key_node_size,
                node_color="#2a1912",
                edgecolors="#ffa657",
                linewidths=1.5
            )

        processed_only = [
            node
            for node in processed
            if node != source
            and node != target
        ]

        if processed_only:

            nx.draw_networkx_nodes(
                graph,
                positions,
                ax=axis,
                nodelist=processed_only,
                node_size=base_node_size,
                node_color="#111b27",
                edgecolors="#388bfd",
                linewidths=1.4
            )

        if (
                self.graph_model.current_node is not None
                and not self.graph_model.algorithm_finished
        ):
            curr = self.graph_model.current_node
            if curr == source:
                curr_fill = "#122117"
            elif curr == target:
                curr_fill = "#2a1912"
            else:
                curr_fill = "#272115"

            nx.draw_networkx_nodes(
                graph,
                positions,
                ax=axis,
                nodelist=[curr],
                node_size=current_node_size,
                node_color=curr_fill,
                edgecolors="#e3b341",
                linewidths=2.0
            )

        nx.draw_networkx_labels(
            graph,
            positions,
            ax=axis,
            font_size=node_label_size,
            font_color="#e6edf3",
            font_weight="bold"
        )

        edge_curvatures, label_coords = (
            self.compute_smart_curvatures_and_labels(
                graph,
                positions
            )
        )

        for edge in graph.edges:
            u, v = edge
            curvature = edge_curvatures[edge]
            weight_val = graph[u][v].get("weight", 0)
            is_bi = (
                graph.has_edge(v, u)
                and graph[v][u].get("weight") == weight_val
            )
            edge_color = (
                "#484f58"
                if (self.manual_build_mode and weight_val <= 0)
                else ("#7c8896" if is_bi else "#6e7681")
            )
            edge_style = (
                "dashed"
                if (self.manual_build_mode and weight_val <= 0)
                else "solid"
            )

            nx.draw_networkx_edges(
                graph,
                positions,
                edgelist=[edge],
                ax=axis,
                arrows=True,
                arrowsize=arrow_size,
                width=edge_width,
                edge_color=edge_color,
                style=edge_style,
                node_size=edge_node_sizes,
                nodelist=nodes,
                connectionstyle=f"arc3,rad={curvature:.3f}"
            )

        if optimal_edges:
            for edge in optimal_edges:
                curvature = edge_curvatures[edge]

                nx.draw_networkx_edges(
                    graph,
                    positions,
                    edgelist=[edge],
                    ax=axis,
                    arrows=True,
                    arrowstyle="-|>",
                    arrowsize=highlight_arrow_size,
                    width=highlight_edge_width,
                    edge_color="#f85149",
                    node_size=edge_node_sizes,
                    nodelist=nodes,
                    connectionstyle=f"arc3,rad={curvature:.3f}"
                )

        edge_labels = nx.get_edge_attributes(
            graph,
            "weight"
        )
        drawn_shared_labels: Set[Tuple[str, str]] = set()

        for edge, weight in edge_labels.items():
            u, v = edge
            if (v, u) in drawn_shared_labels and (
                edge_labels.get((v, u)) == weight
            ):
                continue

            drawn_shared_labels.add((u, v))
            label_x, label_y = label_coords[edge]
            weight_str = (
                str(weight) if weight > 0 else "?"
            )
            box_ec = (
                "#3d4652"
                if (
                    graph.has_edge(v, u)
                    and edge_labels.get((v, u)) == weight
                )
                else "#30363d"
            )

            axis.text(
                label_x,
                label_y,
                weight_str,
                fontsize=weight_font_size,
                color="#e6edf3",
                horizontalalignment="center",
                verticalalignment="center",
                zorder=5,
                bbox={
                    "boxstyle": "round,pad=0.22,rounding_size=0.35",
                    "fc": "#161b22",
                    "ec": box_ec,
                    "lw": 0.8,
                    "alpha": 0.96
                }
            )

        if self.manual_build_mode:
            title_text = (
                "Construcción manual: haga clic en dos nodos "
                "para conectarlos"
            )
        else:
            title_text = "Red de nodos ponderada (Dijkstra)"

        axis.set_title(
            title_text,
            fontsize=12,
            color="#e6edf3",
            fontweight="bold",
            pad=10
        )

        axis.axis("off")
        axis.set_aspect("equal", adjustable="box")
        axis.margins(0.06)

        if (
                preserved_xlim is not None
                and preserved_ylim is not None
        ):
            axis.set_xlim(preserved_xlim)
            axis.set_ylim(preserved_ylim)

        self.reset_graph_view = False

        if self.canvas is not None:
            self.canvas.draw()

    def reset_graph_zoom(self):
        if self.graph_model.graph.number_of_nodes() == 0:
            return

        self.reset_graph_view = True
        self.display_graph()

        self.status_var.set(
            "Vista completa del grafo restablecida."
        )

    def initialize_algorithm(self) -> None:
        if self.manual_build_mode:
            messagebox.showwarning(
                "Modo manual activo",
                "Primero confirme la construcción manual del grafo."
            )
            return

        source = self.source_var.get()
        target = self.target_var.get()

        if not self.graph_model.graph.nodes:

            messagebox.showwarning(
                "Grafo inexistente",
                "Primero debe generar un grafo."
            )

            return

        if not source or not target:

            messagebox.showwarning(
                "Selección incompleta",
                "Seleccione un origen y un destino."
            )

            return

        if source == target:

            messagebox.showwarning(
                "Selección inválida",
                "El origen y el destino deben ser distintos."
            )

            return

        self.hide_result_panel()

        self.graph_model.initialize_dijkstra(
            source,
            target
        )

        self.update_labels_view()
        self.display_graph()

        self.status_var.set(
            f"Dijkstra inicializado | "
            f"Origen: {source} | "
            f"Destino: {target} | "
            f"Iteración: 0"
        )

    def on_endpoint_changed(self, _event: Optional[tk.Event] = None) -> None:
        if self.manual_build_mode or not self.graph_model.labels:
            return

        source = self.source_var.get()
        target = self.target_var.get()
        if not source or not target:
            return

        if source == target:
            self.hide_result_panel()
            self.graph_model.reset_algorithm_data()
            self.clear_labels()
            self.display_graph()
            self.status_var.set(
                "Se reinició Dijkstra al cambiar los extremos. El origen y el destino deben ser distintos."
            )
            return

        self.initialize_algorithm()

    def execute_next_step(self) -> None:

        if self.graph_model.source is None:

            messagebox.showwarning(
                "Algoritmo no inicializado",
                "Primero inicialice Dijkstra."
            )

            return

        if self.graph_model.algorithm_finished:

            return

        self.graph_model.execute_next_step()

        self.update_labels_view()
        self.display_graph()

        current_node = (
            self.graph_model.current_node
        )

        iteration = (
            self.graph_model.iteration
        )

        if self.graph_model.algorithm_finished:

            self.show_final_result()

        else:
            self.status_var.set(
                f"Iteración {iteration} | "
                f"Vértice seleccionado: {current_node}"
            )

    def execute_until_finished(self) -> None:

        if self.graph_model.source is None:

            messagebox.showwarning(
                "Algoritmo no inicializado",
                "Primero inicialice Dijkstra."
            )
            return

        if self.graph_model.algorithm_finished:
            return

        while not self.graph_model.algorithm_finished:

            self.graph_model.execute_next_step()

        self.update_labels_view()
        self.display_graph()

        self.show_final_result()

    def show_final_result(self) -> None:

        paths = self.graph_model.get_shortest_paths()
        distance = self.graph_model.get_shortest_distance()

        if self.result_frame is not None:
            self.result_frame.pack_forget()
            if (
                self.labels_panel_frame is not None
                and str(self.labels_panel_frame.winfo_manager())
                == "pack"
            ):
                self.result_frame.pack(
                    side="top",
                    fill="x",
                    pady=(0, 10),
                    before=self.labels_panel_frame
                )
            else:
                self.result_frame.pack(
                    side="top",
                    fill="x",
                    pady=(0, 10)
                )

        if not paths or distance is None:
            self.status_var.set(
                "No existe un camino desde el origen hasta el destino."
            )
            if self.result_frame is not None:
                self.result_frame.config(
                    bg="#0d1117",
                    highlightbackground="#da3633"
                )
            if self.result_header_label is not None:
                self.result_header_label.config(
                    text="RESULTADO FINAL · SIN RUTA ALCANZABLE",
                    bg="#281417",
                    fg="#f85149"
                )
            if self.result_body_frame is not None:
                self.result_body_frame.config(bg="#0d1117")
            if self.result_badges_frame is not None:
                self.result_badges_frame.config(bg="#0d1117")
            if self.result_summary_label is not None:
                self.result_summary_label.config(
                    text="Distancia mínima: ∞",
                    bg="#281417",
                    fg="#f85149",
                    highlightbackground="#5a1e23"
                )
            if self.result_count_label is not None:
                self.result_count_label.config(
                    text="Caminos mínimos: 0",
                    bg="#281417",
                    fg="#f85149",
                    highlightbackground="#5a1e23"
                )
            if self.result_text is not None:
                self.result_text.config(
                    state="normal",
                    bg="#0d1117",
                    fg="#f85149"
                )
                self.result_text.delete("1.0", tk.END)
                self.result_text.insert(
                    tk.END,
                    "No existe un camino alcanzable desde el "
                    "origen hasta el destino."
                )
                self.result_text.config(state="disabled")
            return

        self.status_var.set(
            f"Algoritmo terminado | "
            f"Distancia mínima: {distance} | "
            f"Caminos mínimos: {len(paths)}"
        )

        if self.result_frame is not None:
            self.result_frame.config(
                bg="#0d1117",
                highlightbackground="#238636"
            )
        if self.result_header_label is not None:
            self.result_header_label.config(
                text=(
                    f"RESULTADO FINAL  ·  {self.graph_model.source} "
                    f"→ {self.graph_model.target}"
                ),
                bg="#121d2f",
                fg="#58a6ff"
            )
        if self.result_body_frame is not None:
            self.result_body_frame.config(bg="#0d1117")
        if self.result_badges_frame is not None:
            self.result_badges_frame.config(bg="#0d1117")

        if self.result_summary_label is not None:
            self.result_summary_label.config(
                text=f"Distancia mínima: {distance}",
                bg="#122117",
                fg="#3fb950",
                highlightbackground="#1f4429"
            )

        if self.result_count_label is not None:
            self.result_count_label.config(
                text=f"Caminos mínimos: {len(paths)}",
                bg="#121d2f",
                fg="#58a6ff",
                highlightbackground="#1f3a60"
            )

        if self.result_text is not None:
            self.result_text.config(
                state="normal",
                bg="#0d1117",
                fg="#e6edf3"
            )
            self.result_text.delete("1.0", tk.END)
            self.result_text.tag_config(
                "path_title",
                foreground="#58a6ff",
                background="#121d2f",
                font=("Consolas", 11, "bold"),
                spacing1=2,
                spacing3=2
            )
            self.result_text.tag_config(
                "path_route",
                foreground="#e6edf3",
                font=("Consolas", 11, "bold"),
                spacing1=2,
                spacing3=2
            )

            for index, path in enumerate(paths, start=1):
                path_text = " → ".join(path)
                self.result_text.insert(
                    tk.END,
                    f" Camino {index} ",
                    "path_title"
                )
                self.result_text.insert(
                    tk.END,
                    f"  {path_text}\n",
                    "path_route"
                )

            self.result_text.config(state="disabled")
            self.result_text.see("1.0")

    def configure_text_color_tags(self) -> None:
        if self.labels_text is not None:
            self.labels_text.tag_config(
                "header",
                foreground="#f0f6fc",
                font=("Consolas", 9, "bold")
            )
            self.labels_text.tag_config(
                "current_block",
                background="#272115",
                foreground="#e3b341",
                font=("Consolas", 9, "bold")
            )
            self.labels_text.tag_config(
                "updated_now_block",
                background="#121d2f",
                foreground="#58a6ff",
                font=("Consolas", 9, "bold")
            )
            self.labels_text.tag_config(
                "tie_now_block",
                background="#102326",
                foreground="#39c5bb",
                font=("Consolas", 9, "bold")
            )
            self.labels_text.tag_config(
                "source_block",
                background="#122117",
                foreground="#3fb950",
                font=("Consolas", 9, "bold")
            )
            self.labels_text.tag_config(
                "target_reached_block",
                background="#2a1912",
                foreground="#ffa657",
                font=("Consolas", 9, "bold")
            )
            self.labels_text.tag_config(
                "target_pending_block",
                background="#1f1612",
                foreground="#d29922"
            )
            self.labels_text.tag_config(
                "processed_block",
                background="#111b27",
                foreground="#79c0ff"
            )
            self.labels_text.tag_config(
                "reachable_pending_block",
                background="#1e162b",
                foreground="#d2a8ff"
            )
            self.labels_text.tag_config(
                "unreachable_block",
                background="#281417",
                foreground="#f85149"
            )
            self.labels_text.tag_config(
                "pending_inf_block",
                foreground="#6e7681"
            )

        if self.history_text is not None:
            self.history_text.tag_config(
                "header",
                foreground="#f0f6fc",
                font=("Consolas", 9, "bold")
            )
            self.history_text.tag_config(
                "node_title",
                foreground="#e6edf3",
                font=("Consolas", 9, "bold")
            )
            self.history_text.tag_config(
                "node_current",
                background="#272115",
                foreground="#e3b341",
                font=("Consolas", 9, "bold")
            )
            self.history_text.tag_config(
                "crossed",
                foreground="#f85149",
                overstrike=True
            )
            self.history_text.tag_config(
                "active_now",
                background="#121d2f",
                foreground="#58a6ff",
                font=("Consolas", 9, "bold")
            )
            self.history_text.tag_config(
                "active_valid",
                foreground="#3fb950",
                font=("Consolas", 9, "bold")
            )
            self.history_text.tag_config(
                "inf_muted",
                foreground="#6e7681"
            )

        if self.decisions_text is not None:
            self.decisions_text.tag_config(
                "header",
                foreground="#f0f6fc",
                font=("Consolas", 9, "bold")
            )
            self.decisions_text.tag_config(
                "latest_header",
                background="#272115",
                foreground="#e3b341",
                font=("Consolas", 9, "bold")
            )
            self.decisions_text.tag_config(
                "past_header",
                background="#161b22",
                foreground="#8b949e",
                font=("Consolas", 9, "bold")
            )
            self.decisions_text.tag_config(
                "improved_line",
                background="#122117",
                foreground="#3fb950",
                font=("Consolas", 9, "bold")
            )
            self.decisions_text.tag_config(
                "no_improve_line",
                foreground="#6e7681"
            )
            self.decisions_text.tag_config(
                "selected_line",
                foreground="#58a6ff",
                font=("Consolas", 9, "bold")
            )
            self.decisions_text.tag_config(
                "finished_line",
                background="#2a1912",
                foreground="#ffa657",
                font=("Consolas", 9, "bold")
            )

    def update_labels_view(self) -> None:

        if (
                self.labels_text is None
                or self.history_text is None
                or self.decisions_text is None
        ):
            return

        for text_widget in (
                self.labels_text,
                self.history_text,
                self.decisions_text
        ):
            text_widget.config(
                state="normal"
            )

            text_widget.delete(
                "1.0",
                tk.END
            )

        self.configure_text_color_tags()

        nodes = self.graph_model.get_nodes()

        processed = set(
            self.graph_model.processed_nodes
        )
        current_iter = self.graph_model.iteration

        self.labels_text.insert(
            tk.END,
            "ETIQUETAS ACTUALES POR VÉRTICE\n"
            "================================\n\n",
            "header"
        )

        current_node_pos_index: Optional[str] = None

        for node in nodes:

            distance, predecessor, iteration = (
                self.graph_model.labels.get(
                    node,
                    (float("inf"), None, 0)
                )
            )

            distance_text = (
                "∞"
                if distance == float("inf")
                else str(int(distance))
            )

            predecessor_text = (
                predecessor
                if predecessor is not None
                else "-"
            )

            is_target = node == self.graph_model.target
            is_source = node == self.graph_model.source
            is_curr = (
                node == self.graph_model.current_node
                and not self.graph_model.algorithm_finished
            )
            tied_in_current_iter = (
                self.graph_model.last_tie_iteration.get(node) == current_iter
                and current_iter > 0
                and distance != float("inf")
            )

            if is_curr:
                if is_target:
                    status = "▶★ VÉRTICE ACTUAL — Destino alcanzado (evaluando)"
                elif is_source:
                    status = "▶● VÉRTICE ACTUAL — Origen (evaluando)"
                else:
                    status = "▶ VÉRTICE ACTUAL (evaluando)"
                block_tag = "current_block"
                badge = "▶"
            elif is_target:
                if (
                    node in processed
                    or self.graph_model.algorithm_finished
                ) and distance != float("inf"):
                    status = "★ Destino alcanzado (óptimo)"
                    block_tag = "target_reached_block"
                    badge = "★"
                elif (
                    self.graph_model.algorithm_finished
                    and distance == float("inf")
                ):
                    status = "✕ Destino inalcanzable desde el origen"
                    block_tag = "unreachable_block"
                    badge = "✕"
                elif (
                    iteration == current_iter
                    and current_iter > 0
                    and distance != float("inf")
                ):
                    status = f"◎✦ Destino actualizado en iteración {current_iter}"
                    block_tag = "target_pending_block"
                    badge = "◎"
                elif tied_in_current_iter:
                    status = f"◎≡ Destino: empate en iteración {current_iter} (nuevo predecesor óptimo)"
                    block_tag = "target_pending_block"
                    badge = "◎"
                elif distance != float("inf"):
                    status = "◎ Destino alcanzado (en frontera, pendiente)"
                    block_tag = "target_pending_block"
                    badge = "◎"
                else:
                    status = "◎ Destino pendiente (distancia ∞)"
                    block_tag = "target_pending_block"
                    badge = "◎"
            elif (
                    iteration == current_iter
                    and current_iter > 0
                    and distance != float("inf")
            ):
                status = f"✦ Actualizado en iteración {current_iter}"
                block_tag = "updated_now_block"
                badge = "✦"
            elif tied_in_current_iter:
                status = f"≡ Empate en iteración {current_iter} (nuevo predecesor óptimo)"
                block_tag = "tie_now_block"
                badge = "≡"
            elif is_source:
                status = "● Origen"
                block_tag = "source_block"
                badge = "●"
            elif (
                    distance == float("inf")
                    and (node in processed or self.graph_model.algorithm_finished)
            ):
                status = "✕ Inalcanzable desde el origen"
                block_tag = "unreachable_block"
                badge = "✕"
            elif node in processed:
                status = "✓ Procesado (etiqueta fija)"
                block_tag = "processed_block"
                badge = "✓"
            elif distance != float("inf"):
                status = "◆ Alcanzado (en frontera)"
                block_tag = "reachable_pending_block"
                badge = "◆"
            else:
                status = "○ Distancia ∞ (pendiente)"
                block_tag = "pending_inf_block"
                badge = "○"

            start_idx = self.labels_text.index(tk.END)
            if node == self.graph_model.current_node:
                current_node_pos_index = start_idx

            self.labels_text.insert(
                tk.END,
                f"{badge} {node}  [{distance_text}, "
                f"{predecessor_text}]_{iteration}\n"
                f"   Estado: {status}\n",
                block_tag
            )
            self.labels_text.insert(tk.END, "\n")

        self.labels_text.insert(
            tk.END,
            "GUÍA DE COLORES\n"
            "===============\n",
            "header"
        )
        self.labels_text.insert(
            tk.END,
            "▶ Amarillo : Vértice actual en evaluación\n",
            "current_block"
        )
        self.labels_text.insert(
            tk.END,
            "✦ Azul     : Etiqueta mejorada en este paso\n",
            "updated_now_block"
        )
        self.labels_text.insert(
            tk.END,
            "≡ Turquesa : Empate en distancia mínima (nuevo predecesor)\n",
            "tie_now_block"
        )
        self.labels_text.insert(
            tk.END,
            "● Verde    : Vértice de origen\n",
            "source_block"
        )
        self.labels_text.insert(
            tk.END,
            "✓ Celeste  : Vértice ya procesado\n",
            "processed_block"
        )
        self.labels_text.insert(
            tk.END,
            "◆ Violeta  : Vértice alcanzado pendiente\n",
            "reachable_pending_block"
        )
        self.labels_text.insert(
            tk.END,
            "★ Naranja  : Destino alcanzado\n",
            "target_reached_block"
        )

        self.history_text.insert(
            tk.END,
            "HISTORIAL DE ETIQUETAS\n"
            "=====================\n\n",
            "header"
        )

        for node in nodes:
            title_tag = (
                "node_current"
                if (
                    node == self.graph_model.current_node
                    and not self.graph_model.algorithm_finished
                )
                else "node_title"
            )
            self.history_text.insert(
                tk.END,
                f"Vértice {node}\n",
                title_tag
            )

            history = (
                self.graph_model.label_history.get(
                    node,
                    []
                )
            )

            if not history:
                self.history_text.insert(
                    tk.END,
                    "  [∞, -]_0 "
                    "(sin distancia finita registrada)\n\n",
                    "inf_muted"
                )
                continue

            for (
                    distance,
                    predecessor,
                    iteration,
                    crossed
            ) in history:

                distance_text = (
                    "∞"
                    if distance == float("inf")
                    else str(int(distance))
                )

                predecessor_text = (
                    predecessor
                    if predecessor is not None
                    else "-"
                )

                label_text = (
                    f"  [{distance_text}, "
                    f"{predecessor_text}]_{iteration}"
                )

                if crossed:
                    label_text += " (reemplazada)"
                    line_tag = "crossed"
                elif (
                    iteration == current_iter
                    and current_iter > 0
                ):
                    label_text += " ◀ nueva"
                    line_tag = "active_now"
                else:
                    label_text += " ✓ vigente"
                    line_tag = "active_valid"

                self.history_text.insert(
                    tk.END,
                    label_text + "\n",
                    line_tag
                )

            self.history_text.insert(
                tk.END,
                "\n"
            )

        self.decisions_text.insert(
            tk.END,
            "REGISTRO DE DECISIONES DEL ALGORITMO\n"
            "====================================\n\n",
            "header"
        )

        if not self.graph_model.decision_history:

            self.decisions_text.insert(
                tk.END,
                "Todavía no hay decisiones registradas. "
                "Inicialice Dijkstra para comenzar.\n",
                "no_improve_line"
            )

        else:
            total_decisions = len(
                self.graph_model.decision_history
            )
            for index, decision in enumerate(
                    self.graph_model.decision_history,
                    start=1
            ):

                decision_text = decision.strip()

                if not decision_text:
                    continue

                is_latest = index == total_decisions
                hdr_tag = (
                    "latest_header"
                    if is_latest
                    else "past_header"
                )
                hdr_prefix = "▶ " if is_latest else ""

                header_title = (
                    "INICIALIZACIÓN"
                    if index == 1
                    else f"ITERACIÓN {index - 1}"
                )
                self.decisions_text.insert(
                    tk.END,
                    f"{hdr_prefix}DECISIÓN {index} — {header_title}\n",
                    hdr_tag
                )

                for line in decision_text.splitlines():
                    if (
                        "Actualización:" in line
                        or "Se actualiza" in line
                        or "Empate" in line
                        or "igual distancia" in line
                    ):
                        line_tag = "improved_line"
                    elif (
                        "Sin mejora:" in line
                        or "Se conserva" in line
                        or "ya fue procesado" in line
                        or "ya está registrada" in line
                        or "no tiene aristas salientes" in line
                    ):
                        line_tag = "no_improve_line"
                    elif (
                        "se selecciona" in line
                        or "Se selecciona" in line
                        or "Inicialización:" in line
                        or "Objetivo:" in line
                        or "Fin de la iteración" in line
                        or "Siguiente candidato" in line
                        or "Candidatos" in line
                    ):
                        line_tag = "selected_line"
                    elif (
                        "Finalización:" in line
                        or "Inalcanzables" in line
                        or "procesados óptimamente" in line
                        or "Alcanzado" in line
                        or "Finalizado" in line
                        or "termina" in line
                    ):
                        line_tag = "finished_line"
                    else:
                        line_tag = ""

                    if line_tag:
                        self.decisions_text.insert(
                            tk.END,
                            line + "\n",
                            line_tag
                        )
                    else:
                        self.decisions_text.insert(
                            tk.END,
                            line + "\n"
                        )

                self.decisions_text.insert(tk.END, "\n")

        for text_widget in (
                self.labels_text,
                self.history_text,
                self.decisions_text
        ):
            text_widget.config(
                state="disabled"
            )

        if current_node_pos_index is not None:
            self.labels_text.see(current_node_pos_index)
        else:
            self.labels_text.see("1.0")
        self.history_text.see("1.0")
        self.decisions_text.see(tk.END)

    def clear_labels(self) -> None:

        for text_widget in (
                self.labels_text,
                self.history_text,
                self.decisions_text
        ):

            if text_widget is None:
                continue

            text_widget.config(
                state="normal"
            )

            text_widget.delete(
                "1.0",
                tk.END
            )

            text_widget.config(
                state="disabled"
            )

        if self.labels_text is not None:
            self.labels_text.config(
                state="normal"
            )

            self.labels_text.insert(
                tk.END,
                "Genere el grafo, seleccione el origen "
                "y el destino, e inicialice Dijkstra."
            )

            self.labels_text.config(
                state="disabled"
            )

        if self.history_text is not None:
            self.history_text.config(
                state="normal"
            )

            self.history_text.insert(
                tk.END,
                "El historial se mostrará cuando "
                "se inicialice Dijkstra."
            )

            self.history_text.config(
                state="disabled"
            )

        if self.decisions_text is not None:
            self.decisions_text.config(
                state="normal"
            )

            self.decisions_text.insert(
                tk.END,
                "El registro de decisiones aparecerá "
                "al inicializar el algoritmo."
            )

            self.decisions_text.config(
                state="disabled"
            )

    def show_project_information(self) -> None:

        information_window = tk.Toplevel(
            self.root
        )

        information_window.title(
            "Información del proyecto"
        )

        information_window.geometry(
            "720x680"
        )

        information_window.minsize(
            680,
            620
        )

        information_window.configure(
            bg="#0d1117"
        )

        information_window.transient(
            self.root
        )

        container = ttk.Frame(
            information_window,
            padding=(24, 16)
        )

        container.pack(
            fill="both",
            expand=True
        )

        style = ttk.Style(information_window)

        style.configure(
            "Project.Title.TLabel",
            font=("Segoe UI", 18, "bold"),
            foreground="#e6edf3"
        )

        style.configure(
            "Project.Subtitle.TLabel",
            font=("Segoe UI", 11),
            foreground="#58a6ff"
        )

        style.configure(
            "Project.Body.TLabel",
            font=("Segoe UI", 10),
            foreground="#8b949e"
        )

        style.configure(
            "Project.Field.TLabel",
            font=("Segoe UI", 10, "bold"),
            foreground="#c9d1d9",
            background="#0d1117"
        )

        style.configure(
            "Project.Value.TLabel",
            font=("Segoe UI", 10),
            foreground="#e6edf3",
            background="#0d1117"
        )

        style.configure(
            "Project.Member.TLabel",
            font=("Segoe UI", 10),
            foreground="#e6edf3",
            background="#0d1117"
        )

        style.configure(
            "Project.Close.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 6),
            background="#161b22",
            foreground="#e6edf3"
        )

        ttk.Label(
            container,
            text="Información del proyecto",
            style="Project.Title.TLabel"
        ).pack(
            pady=(0, 4)
        )

        ttk.Label(
            container,
            text=self.project_info.theme,
            style="Project.Subtitle.TLabel"
        ).pack(
            pady=(0, 12)
        )

        description_text = (
            "Aplicación desarrollada en Python para construir grafos "
            "dirigidos y ponderados con pesos positivos, soportando "
            "conexiones unidireccionales, bidireccionales y ciclos "
            "dirigidos. Permite ejecutar el algoritmo de Dijkstra paso "
            "a paso, consultar las etiquetas y el registro de decisiones, "
            "y visualizar los caminos mínimos mediante una representación "
            "gráfica de red."
        )
        body_font = tkfont.Font(
            root=information_window,
            family="Segoe UI",
            size=10
        )
        description_canvas = tk.Canvas(
            container,
            bg="#0d1117",
            bd=0,
            highlightthickness=0,
            width=1,
            height=80
        )
        description_canvas.pack(
            fill="x",
            pady=(0, 14)
        )

        def _render_justified_description(
            event: Optional[Any] = None
        ) -> None:
            avail_w = (
                event.width
                if event is not None and getattr(event, "width", 0) > 1
                else description_canvas.winfo_width()
            )
            if avail_w <= 40:
                avail_w = 632
            description_canvas.delete("all")
            words = description_text.split()
            space_w = body_font.measure(" ")
            lines: List[List[str]] = []
            curr_line: List[str] = []
            curr_w = 0
            for word in words:
                word_w = body_font.measure(word)
                if curr_line and curr_w + space_w + word_w > avail_w:
                    lines.append(curr_line)
                    curr_line = [word]
                    curr_w = word_w
                else:
                    curr_w = (
                        word_w
                        if not curr_line
                        else curr_w + space_w + word_w
                    )
                    curr_line.append(word)
            if curr_line:
                lines.append(curr_line)

            line_h = body_font.metrics("linespace") + 3
            for line_idx, line_words in enumerate(lines):
                y_pos = line_idx * line_h
                is_last_line = line_idx == len(lines) - 1
                if is_last_line or len(line_words) == 1:
                    description_canvas.create_text(
                        0,
                        y_pos,
                        text=" ".join(line_words),
                        anchor="nw",
                        font=body_font,
                        fill="#8b949e"
                    )
                else:
                    total_words_w = sum(
                        body_font.measure(w) for w in line_words
                    )
                    gap = (avail_w - total_words_w) / (len(line_words) - 1)
                    x_pos = 0.0
                    for w_idx, w in enumerate(line_words):
                        if w_idx == len(line_words) - 1:
                            description_canvas.create_text(
                                avail_w,
                                y_pos,
                                text=w,
                                anchor="ne",
                                font=body_font,
                                fill="#8b949e"
                            )
                        else:
                            description_canvas.create_text(
                                round(x_pos),
                                y_pos,
                                text=w,
                                anchor="nw",
                                font=body_font,
                                fill="#8b949e"
                            )
                            x_pos += body_font.measure(w) + gap

            total_h = max(1, len(lines) * line_h)
            if int(description_canvas.cget("height")) != total_h:
                description_canvas.configure(height=total_h)

        description_canvas.bind(
            "<Configure>",
            _render_justified_description
        )
        _render_justified_description()

        information_frame = ttk.LabelFrame(
            container,
            text="Datos académicos",
            padding=12
        )

        information_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        academic_data = (
            ("Curso", self.project_info.course),
            ("Tema", self.project_info.theme),
            ("Entrega", self.project_info.delivery),
            ("Grupo", self.project_info.group),
        )

        for index, (label, value) in enumerate(
                academic_data
        ):
            ttk.Label(
                information_frame,
                text=f"{label}:",
                style="Project.Field.TLabel"
            ).grid(
                row=index,
                column=0,
                sticky="w",
                padx=5,
                pady=3
            )

            ttk.Label(
                information_frame,
                text=value,
                style="Project.Value.TLabel",
                wraplength=470
            ).grid(
                row=index,
                column=1,
                sticky="w",
                padx=10,
                pady=3
            )

        ttk.Button(
            container,
            text="Cerrar",
            command=information_window.destroy,
            style="Project.Close.TButton"
        ).pack(
            side="bottom",
            pady=(10, 0)
        )

        integrants_frame = ttk.LabelFrame(
            container,
            text="Integrantes",
            padding=12
        )

        integrants_frame.pack(
            side="top",
            fill="both",
            expand=True
        )

        for index, name in enumerate(
                self.project_info.integrants,
                start=1
        ):
            ttk.Label(
                integrants_frame,
                text=f"{index}. {name}",
                style="Project.Member.TLabel"
            ).pack(
                anchor="w",
                pady=2
            )

    def show_help(
            self,
            initial_tab: int = 0
    ) -> None:

        help_window = tk.Toplevel(
            self.root
        )

        help_window.title(
            "Ayuda - Guía del sistema"
        )

        help_window.geometry(
            "820x680"
        )

        help_window.minsize(
            720,
            560
        )

        help_window.configure(
            bg="#0d1117"
        )

        help_window.transient(
            self.root
        )

        container = ttk.Frame(
            help_window,
            padding=14
        )

        container.pack(
            fill="both",
            expand=True
        )

        ttk.Label(
            container,
            text="Guía del sistema",
            font=("Segoe UI", 18, "bold"),
            foreground="#e6edf3"
        ).pack(
            pady=(0, 4)
        )

        ttk.Label(
            container,
            text=(
                "Problema del camino mínimo | "
                "Algoritmo de Dijkstra"
            ),
            font=("Segoe UI", 10),
            foreground="#8b949e"
        ).pack(
            pady=(0, 10)
        )

        ttk.Button(
            container,
            text="Cerrar",
            command=help_window.destroy
        ).pack(
            side="bottom",
            pady=(10, 0)
        )

        notebook = ttk.Notebook(
            container
        )

        notebook.pack(
            side="top",
            fill="both",
            expand=True
        )

        overview_tab = ttk.Frame(
            notebook,
            padding=12
        )

        usage_tab = ttk.Frame(
            notebook,
            padding=12
        )

        dijkstra_tab = ttk.Frame(
            notebook,
            padding=12
        )

        labels_tab = ttk.Frame(
            notebook,
            padding=12
        )

        notebook.add(
            overview_tab,
            text="¿Qué hace?"
        )

        notebook.add(
            usage_tab,
            text="Cómo usar"
        )

        notebook.add(
            dijkstra_tab,
            text="Dijkstra"
        )

        notebook.add(
            labels_tab,
            text="Etiquetas"
        )

        if not 0 <= initial_tab <= 3:
            initial_tab = 0

        notebook.select(
            initial_tab
        )

        self.create_help_text(
            overview_tab,
            "¿Qué hace esta aplicación?",
            [
                (
                    "Objetivo",
                    "Permite modelar y resolver el problema "
                    "del camino mínimo sobre grafos dirigidos "
                    "y ponderados con pesos positivos, admitiendo "
                    "conexiones unidireccionales, bidireccionales "
                    "y ciclos dirigidos."
                ),
                (
                    "Generación",
                    "El usuario puede generar el grafo "
                    "aleatoriamente (configurando las opciones "
                    "Bidireccional y Ciclos) o construirlo y "
                    "modificarlo manualmente de forma interactiva."
                ),
                (
                    "Algoritmo",
                    "Dijkstra puede ejecutarse paso "
                    "a paso o hasta completar todos "
                    "los caminos mínimos."
                ),
            ]
        )

        self.create_help_text(
            usage_tab,
            "Cómo utilizar el sistema",
            [
                (
                    "1. Cantidad de nodos",
                    "Ingrese un número entero entre 7 y 16."
                ),
                (
                    "2. Tipo de grafo y preferencias",
                    "Seleccione Aleatorio (pudiendo activar o desactivar "
                    "las casillas Bidireccional y Ciclos) o Manual."
                ),
                (
                    "3. Crear o modificar grafo",
                    "En modo Aleatorio presione Generar grafo. En modo "
                    "Manual, construya las conexiones haciendo clic "
                    "directamente sobre los nodos del lienzo gráfico "
                    "(origen y luego destino) o mediante el formulario "
                    "superior (Nodo 1, Nodo 2, Peso y casilla Bidireccional). "
                    "Presione Confirmar grafo al terminar, o use el botón "
                    "Modificar grafo para editar un grafo manual ya "
                    "confirmado (reiniciando Dijkstra automáticamente)."
                ),
                (
                    "4. Origen y destino",
                    "Seleccione los vértices correspondientes. Si los "
                    "cambia tras una ejecución previa, Dijkstra se "
                    "reinicializa automáticamente."
                ),
                (
                    "5. Inicializar",
                    "Crea las etiquetas iniciales ([0, -]_0 para el "
                    "origen y [∞, -]_0 para los demás vértices)."
                ),
                (
                    "6. Ejecución de Dijkstra",
                    "Use Siguiente paso para avanzar iteración por "
                    "iteración o Ejecutar hasta el final para completar "
                    "la búsqueda y desplegar el recuadro integrado con "
                    "todos los caminos mínimos."
                ),
                (
                    "Herramientas de visualización",
                    "Inicio restablece la vista; Anterior y Siguiente "
                    "permiten recuperar vistas previas; Mover desplaza "
                    "el gráfico; Zoom amplía una región seleccionada "
                    "con el ratón; Guardar permite exportar el gráfico "
                    "como PNG, PDF o SVG. También puede usar "
                    "Vista > Restablecer vista del grafo."
                ),
            ]
        )

        self.create_help_text(
            dijkstra_tab,
            "Dijkstra paso a paso",
            [
                (
                    "Inicio",
                    "El vértice origen recibe distancia "
                    "0. Los demás comienzan en ∞."
                ),
                (
                    "Selección",
                    "Se selecciona el vértice no "
                    "procesado con menor acumulado."
                ),
                (
                    "Relajación",
                    "Para u → v con peso w se calcula "
                    "L(v) = L(u) + w."
                ),
                (
                    "Comparación",
                    "Si la nueva distancia es menor, se actualiza "
                    "la etiqueta. Si es igual, se registra otro "
                    "predecesor óptimo; si es mayor, se conserva "
                    "la etiqueta anterior."
                ),
                (
                    "Finalización",
                    "El proceso termina cuando todos los vértices "
                    "alcanzables desde el origen han sido procesados. "
                    "Los que conservan distancia infinita (∞) son "
                    "inalcanzables desde el origen."
                ),
            ]
        )

        self.create_help_text(
            labels_tab,
            "Etiquetas y conceptos",
            [
                (
                    "[L, X]_k",
                    "L representa la distancia acumulada, X es el "
                    "predecesor de la etiqueta mostrada y k es la "
                    "iteración en la que se generó."
                ),
                (
                    "[0, -]_0",
                    "Etiqueta inicial del origen."
                ),
                (
                    "[∞, -]_0",
                    "Nodo cuya distancia todavía no ha sido determinada."
                ),
                (
                    "Predecesores alternativos",
                    "Cuando dos rutas alcanzan un vértice con la misma "
                    "distancia mínima, el sistema conserva los "
                    "predecesores que permiten reconstruir ambas rutas."
                ),
                (
                    "Caminos mínimos",
                    "Al finalizar, se muestra la distancia mínima, "
                    "la cantidad de caminos óptimos y la secuencia "
                    "de vértices de cada uno."
                ),
                (
                    "Etiqueta tachada",
                    "Representa una etiqueta que fue reemplazada "
                    "por otra de menor distancia."
                ),
                (
                    "Registro de decisiones",
                    "Muestra las distancias candidatas, las "
                    "comparaciones y las decisiones tomadas en "
                    "cada iteración."
                ),
            ]
        )

    @staticmethod
    def create_help_text(
            parent: ttk.Frame,
            title: str,
            sections: List[Tuple[str, str]]
    ) -> None:
        scroll_canvas = tk.Canvas(
            parent,
            bg="#0d1117",
            bd=0,
            highlightthickness=0,
            width=1,
            height=1
        )
        scrollbar = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=scroll_canvas.yview
        )
        content_frame = ttk.Frame(scroll_canvas)

        canvas_win = scroll_canvas.create_window(
            (0, 0),
            window=content_frame,
            anchor="nw"
        )
        scroll_canvas.configure(yscrollcommand=scrollbar.set)

        scroll_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        MainApplication._bind_mousewheel_to_canvas(
            scroll_canvas,
            scroll_canvas
        )
        MainApplication._bind_mousewheel_to_canvas(
            content_frame,
            scroll_canvas
        )

        desc_labels: List[ttk.Label] = []

        title_lbl = ttk.Label(
            content_frame,
            text=title,
            font=("Segoe UI", 14, "bold"),
            foreground="#e6edf3"
        )
        title_lbl.pack(
            anchor="w",
            pady=(0, 8)
        )
        MainApplication._bind_mousewheel_to_canvas(
            title_lbl,
            scroll_canvas
        )

        for section_title, description in sections:
            sec_lbl = ttk.Label(
                content_frame,
                text=section_title,
                font=("Segoe UI", 10, "bold"),
                foreground="#58a6ff"
            )
            sec_lbl.pack(
                anchor="w",
                pady=(2, 1)
            )
            MainApplication._bind_mousewheel_to_canvas(
                sec_lbl,
                scroll_canvas
            )

            desc_lbl = ttk.Label(
                content_frame,
                text=description,
                foreground="#8b949e",
                wraplength=700,
                justify="left"
            )
            desc_lbl.pack(
                anchor="w",
                fill="x",
                pady=(0, 5)
            )
            MainApplication._bind_mousewheel_to_canvas(
                desc_lbl,
                scroll_canvas
            )
            desc_labels.append(desc_lbl)

        def _update_scroll_state(_event: Optional[Any] = None) -> None:
            bbox = scroll_canvas.bbox("all")
            if bbox is None:
                return
            scroll_canvas.configure(scrollregion=bbox)
            content_h = bbox[3] - bbox[1]
            canvas_h = scroll_canvas.winfo_height()
            if canvas_h > 1 and content_h > canvas_h + 2:
                if not scrollbar.winfo_manager():
                    scrollbar.pack(
                        side="right",
                        fill="y",
                        before=scroll_canvas
                    )
            else:
                if scrollbar.winfo_manager():
                    scrollbar.pack_forget()

        def _on_canvas_configure(event: Any) -> None:
            new_w = max(200, event.width - 8)
            scroll_canvas.itemconfig(canvas_win, width=event.width)
            for lbl in desc_labels:
                lbl.configure(wraplength=new_w)
            _update_scroll_state()
        content_frame.bind("<Configure>", _update_scroll_state)
        scroll_canvas.bind("<Configure>", _on_canvas_configure)

    def run(self) -> None:
        self.root.mainloop()

class ApplicationLauncher:
    @staticmethod
    def start() -> None:
        root = tk.Tk()

        application = MainApplication(
            root
        )
        application.run()

if __name__ == "__main__":
    ApplicationLauncher.start()