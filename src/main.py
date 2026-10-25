import itertools
import math
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple, Any, cast

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
                bbox_inches="tight"
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
            base_x = (
                x_margin
                + (z_idx / max(1, num_zones - 1)) * usable_w
            )
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
            ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0))
            and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))
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
        self.decision_history.clear()
        self.processed_nodes.clear()

        self.iteration = 0
        self.source = None
        self.target = None
        self.current_node = None

        self.algorithm_finished = False

    def create_random_dag(self, node_count: int) -> None:
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
            u: str,
            v: str,
            allow_crossing: bool = False
        ) -> bool:
            if self.graph.has_edge(u, v):
                return False
            p1, p2 = pos[u], pos[v]
            if p2[0] < p1[0] - 0.35:
                return False
            for w in nodes:
                if w == u or w == v:
                    continue
                if self.point_to_segment_dist(pos[w], p1, p2) < 0.95:
                    return False
            if not allow_crossing:
                for eu, ev in self.graph.edges:
                    if eu in (u, v) or ev in (u, v):
                        continue
                    if self.segments_intersect(
                        p1,
                        p2,
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
                        weight=random.randint(1, 20)
                    )
                    added = True
                    break
            if not added and candidates:
                self.graph.add_edge(
                    candidates[0][1],
                    v,
                    weight=random.randint(1, 20)
                )

        for i in range(node_count - 1):
            u = nodes[i]
            if self.graph.out_degree(u) > 0:
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
                        weight=random.randint(1, 20)
                    )
                    added = True
                    break
            if not added and candidates:
                self.graph.add_edge(
                    u,
                    candidates[0][1],
                    weight=random.randint(1, 20)
                )

        for i in range(node_count - 1):
            u = nodes[i]
            zu = node_zone[u]
            target_out = (
                2 if i > 0 else min(3, max(2, node_count // 5))
            )
            if random.random() < 0.35 and i < node_count - 3:
                target_out = min(3, target_out + 1)

            if self.graph.out_degree(u) >= target_out:
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
                if self.graph.out_degree(u) >= target_out:
                    break
                if self.graph.in_degree(v) >= 3 and v != nodes[-1]:
                    continue
                if can_add_clean_edge(u, v, allow_crossing=False):
                    self.graph.add_edge(
                        u,
                        v,
                        weight=random.randint(1, 20)
                    )

    def create_manual_graph(
            self,
            node_count: int,
            edges: List[Tuple[str, str, int]]
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

        if not nx.is_directed_acyclic_graph(candidate_graph):
            raise ValueError(
                "El grafo contiene un ciclo. Debe ser acíclico."
            )

        self.graph = candidate_graph
        self.reset_algorithm_data()
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

        self.labels[source] = (0, None, 0)

        self.label_history[source].append(
            (0, None, 0, False)
        )

        self.decision_history = [
            f"Inicialización: el origen {source} recibe distancia 0.",
            "Inicialización: los demás vértices reciben distancia ∞."
        ]

        return self.labels.copy()

    def get_unprocessed_nodes(self) -> List[str]:
        return [
            node
            for node in self.graph.nodes
            if node not in self.processed_nodes
        ]

    def select_next_node(self) -> Optional[str]:
        available_nodes = self.get_unprocessed_nodes()

        if not available_nodes:
            return None

        return min(
            available_nodes,
            key=lambda node: self.labels[node][0]
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

            self.decision_history.append(
                "Finalización: no quedan vértices sin procesar."
            )

            return self.labels.copy()

        self.current_node = next_node
        self.iteration += 1
        self.processed_nodes.append(next_node)

        current_distance = self.labels[next_node][0]

        if current_distance == float("inf"):

            self.decision_history.append(
                f"\nIteración {self.iteration}: se selecciona "
                f"{next_node} con distancia ∞."
            )

            self.decision_history.append(
                f"{next_node} es inalcanzable desde el origen. "
                "Se revisa sin calcular distancias desde ∞."
            )

            neighbors = []

        else:

            self.decision_history.append(
                f"\nIteración {self.iteration}: se selecciona "
                f"{next_node} con distancia "
                f"{int(current_distance)}."
            )

            neighbors = self.get_successors(next_node)

        for neighbor in neighbors:

            if neighbor in self.processed_nodes:
                self.decision_history.append(
                    f"Arista {next_node} -> {neighbor}: "
                    "el vértice destino ya fue procesado."
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

                self.labels[neighbor] = (
                    candidate_distance,
                    next_node,
                    self.iteration
                )

                self.optimal_predecessors[neighbor] = [
                    next_node
                ]

                self.label_history[neighbor].append(
                    (
                        candidate_distance,
                        next_node,
                        self.iteration,
                        False
                    )
                )

                self.decision_history.append(
                    f"Arista {next_node} -> {neighbor}, "
                    f"peso {weight}: "
                    f"{int(current_distance)} + {weight} = "
                    f"{int(candidate_distance)}. "
                    f"Distancia anterior: {previous_distance_text}. "
                    "Se actualiza la etiqueta."
                )

            elif candidate_distance == current_distance_neighbor:

                if (
                        next_node
                        not in self.optimal_predecessors[neighbor]
                ):

                    self.optimal_predecessors[neighbor].append(
                        next_node
                    )

                    self.label_history[neighbor].append(
                        (
                            candidate_distance,
                            next_node,
                            self.iteration,
                            False
                        )
                    )

                    self.decision_history.append(
                        f"Arista {next_node} -> {neighbor}, "
                        f"peso {weight}: "
                        f"{int(current_distance)} + {weight} = "
                        f"{int(candidate_distance)}. "
                        "Se encuentra una ruta con igual distancia "
                        "mínima. Se registra el predecesor alternativo "
                        f"{next_node}."
                    )

                else:
                    self.decision_history.append(
                        f"Arista {next_node} -> {neighbor}: "
                        "la alternativa óptima ya está registrada."
                    )

            else:
                self.decision_history.append(
                    f"Arista {next_node} -> {neighbor}, "
                    f"peso {weight}: "
                    f"{int(current_distance)} + {weight} = "
                    f"{int(candidate_distance)}. "
                    f"La distancia conocida es "
                    f"{int(current_distance_neighbor)}. "
                    "Se conserva la etiqueta anterior."
                )

        remaining_nodes = [
            node
            for node in self.graph.nodes
            if node not in self.processed_nodes
        ]

        if not remaining_nodes:

            self.algorithm_finished = True

            self.decision_history.append(
                "Finalización: todos los vértices fueron revisados. "
                "Los que conservan distancia ∞ son inalcanzables "
                "desde el origen."
            )

        else:

            self.decision_history.append(
                f"Fin de la iteración {self.iteration}. "
                "Se continuará con el vértice pendiente "
                "de menor distancia."
            )

        return self.labels.copy()

    def is_valid_dag(self) -> bool:
        return nx.is_directed_acyclic_graph(self.graph)

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

        def build_paths(node: str) -> List[List[str]]:

            if node == self.source:

                return [[self.source]]

            paths = []

            predecessors = self.optimal_predecessors.get(
                node,
                []
            )

            for predecessor in predecessors:

                previous_paths = build_paths(predecessor)

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
            min(1000, window_width),
            min(600, window_height)
        )

        self.configure_style()

        self.node_count_var = tk.StringVar()
        self.source_var = tk.StringVar()
        self.target_var = tk.StringVar()

        self.mode_var = tk.StringVar(
            value="Aleatorio"
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

        self.graph_frame: Optional[
            ttk.Frame
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

        self.next_button: Optional[
            ttk.Button
        ] = None

        self.finish_button: Optional[
            ttk.Button
        ] = None

        self.create_menu()
        self.create_main_layout()

    def configure_style(self) -> None:
        style = ttk.Style(self.root)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 25, "bold")
        )

        style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 10)
        )

        style.configure(
            "Section.TLabelframe",
            font=("Segoe UI", 10, "bold")
        )

        style.configure(
            "Action.TButton",
            font=("Segoe UI", 9, "bold"),
            padding=(10, 6)
        )

    def create_menu(self) -> None:
        menu_bar = tk.Menu(self.root)

        project_menu = tk.Menu(
            menu_bar,
            tearoff=0
        )

        project_menu.add_command(
            label="Generar nuevo grafo",
            command=self.generate_graph
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
            tearoff=0
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
            tearoff=0
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
            padding=14
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
            pady=(0, 10)
        )

        ttk.Label(
            header_frame,
            text="PROBLEMA DEL CAMINO MÍNIMO",
            style="Title.TLabel"
        ).pack(
            anchor="center",
            pady=(4, 2)
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
            padding=10,
            style="Section.TLabelframe"
        )

        configuration_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            configuration_frame,
            text="Número de nodos (7-16):"
        ).grid(
            row=0,
            column=0,
            padx=(4, 6),
            pady=6
        )

        ttk.Entry(
            configuration_frame,
            textvariable=self.node_count_var,
            width=10
        ).grid(
            row=0,
            column=1,
            padx=4,
            pady=6
        )

        ttk.Label(
            configuration_frame,
            text="Tipo de grafo:"
        ).grid(
            row=0,
            column=2,
            padx=(14, 4),
            pady=6
        )

        self.mode_combo = ttk.Combobox(
            configuration_frame,
            textvariable=self.mode_var,
            values=[
                "Aleatorio",
                "Manual"
            ],
            state="readonly",
            width=12
        )

        self.mode_combo.grid(
            row=0,
            column=3,
            padx=4,
            pady=6
        )

        ttk.Button(
            configuration_frame,
            text="Generar grafo",
            command=self.generate_graph,
            style="Action.TButton"
        ).grid(
            row=0,
            column=4,
            padx=8,
            pady=6
        )

        ttk.Separator(
            configuration_frame,
            orient="vertical"
        ).grid(
            row=0,
            column=5,
            sticky="ns",
            padx=10
        )

        ttk.Label(
            configuration_frame,
            text="Origen:"
        ).grid(
            row=0,
            column=6,
            padx=4
        )

        self.source_combo = ttk.Combobox(
            configuration_frame,
            textvariable=self.source_var,
            state="readonly",
            width=8
        )

        self.source_combo.grid(
            row=0,
            column=7,
            padx=4
        )

        ttk.Label(
            configuration_frame,
            text="Destino:"
        ).grid(
            row=0,
            column=8,
            padx=(14, 4)
        )

        self.target_combo = ttk.Combobox(
            configuration_frame,
            textvariable=self.target_var,
            state="readonly",
            width=8
        )

        self.target_combo.grid(
            row=0,
            column=9,
            padx=4
        )

        ttk.Button(
            configuration_frame,
            text="Inicializar",
            command=self.initialize_algorithm,
            style="Action.TButton"
        ).grid(
            row=0,
            column=10,
            padx=(12, 4)
        )

        self.next_button = ttk.Button(
            configuration_frame,
            text="Siguiente paso",
            command=self.execute_next_step,
            style="Action.TButton"
        )

        self.next_button.grid(
            row=0,
            column=11,
            padx=4
        )

        self.finish_button = ttk.Button(
            configuration_frame,
            text="Ejecutar todo",
            command=self.execute_until_finished,
            style="Action.TButton"
        )

        self.finish_button.grid(
            row=0,
            column=12,
            padx=4
        )

        workspace = ttk.Frame(
            main_frame
        )

        workspace.pack(
            fill="both",
            expand=True
        )

        workspace.columnconfigure(
            0,
            weight=5
        )

        workspace.columnconfigure(
            1,
            weight=1
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

        side_frame = ttk.Frame(
            workspace
        )

        side_frame.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        self.create_labels_panel(
            side_frame
        )

        status_frame = ttk.Frame(
            main_frame
        )

        status_frame.pack(
            fill="x",
            pady=(8, 0)
        )

        ttk.Separator(
            status_frame,
            orient="horizontal"
        ).pack(
            fill="x",
            pady=(0, 5)
        )

        ttk.Label(
            status_frame,
            textvariable=self.status_var
        ).pack(
            anchor="w"
        )

    def create_labels_panel(
            self,
            parent: ttk.Frame
    ) -> None:

        labels_frame = ttk.LabelFrame(
            parent,
            text="Etiquetas y decisiones de Dijkstra",
            padding=8,
            style="Section.TLabelframe"
        )

        labels_frame.pack(
            fill="both",
            expand=True
        )

        ttk.Label(
            labels_frame,
            text=(
                "L = distancia acumulada | "
                "X = predecesor | k = iteración"
            ),
            font=("Segoe UI", 9)
        ).pack(
            anchor="w",
            pady=(0, 6)
        )

        notebook = ttk.Notebook(
            labels_frame
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
                state="disabled",
                font=("Consolas", 9),
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
            self.graph_model.create_random_dag(
                node_count
            )

        else:
            self.open_manual_graph_window(
                node_count
            )

            return

        self.finish_graph_generation()

    def finish_graph_generation(self) -> None:
        if not self.graph_model.is_valid_dag():

            messagebox.showerror(
                "Error",
                "El grafo debe ser dirigido y acíclico."
            )

            return

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

    def open_manual_graph_window(
        self,
        node_count: int
    ) -> None:

        window = tk.Toplevel(
            self.root
        )

        window.title(
            "Construcción manual del grafo"
        )

        window.geometry(
            "850x650"
        )

        window.minsize(
            760,
            560
        )

        window.transient(
            self.root
        )

        container = ttk.Frame(
            window,
            padding=14
        )

        container.pack(
            fill="both",
            expand=True
        )

        ttk.Label(
            container,
            text="Construcción manual del grafo",
            font=("Segoe UI", 18, "bold")
        ).pack(
            pady=(0, 5)
        )

        ttk.Label(
            container,
            text=(
                "Ingrese las conexiones como "
                "origen, destino y peso."
            )
        ).pack(
            pady=(0, 10)
        )

        form_frame = ttk.LabelFrame(
            container,
            text="Nueva arista",
            padding=10
        )

        form_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            form_frame,
            text="Desde:"
        ).grid(
            row=0,
            column=0,
            padx=5,
            pady=5
        )

        source_entry = ttk.Combobox(
            form_frame,
            values=[
                f"N{i}"
                for i in range(1, node_count + 1)
            ],
            state="readonly",
            width=10
        )

        source_entry.grid(
            row=0,
            column=1,
            padx=5,
            pady=5
        )

        ttk.Label(
            form_frame,
            text="Hacia:"
        ).grid(
            row=0,
            column=2,
            padx=5,
            pady=5
        )

        target_entry = ttk.Combobox(
            form_frame,
            values=[
                f"N{i}"
                for i in range(1, node_count + 1)
            ],
            state="readonly",
            width=10
        )

        target_entry.grid(
            row=0,
            column=3,
            padx=5,
            pady=5
        )

        ttk.Label(
            form_frame,
            text="Peso:"
        ).grid(
            row=0,
            column=4,
            padx=5,
            pady=5
        )

        weight_entry = ttk.Entry(
            form_frame,
            width=10
        )

        weight_entry.grid(
            row=0,
            column=5,
            padx=5,
            pady=5
        )

        edges: List[
            Tuple[str, str, int]
        ] = []

        list_frame = ttk.LabelFrame(
            container,
            text="Aristas ingresadas",
            padding=10
        )

        list_frame.pack(
            fill="both",
            expand=True
        )

        listbox = tk.Listbox(
            list_frame,
            font=("Consolas", 10)
        )

        listbox.pack(
            side="left",
            fill="both",
            expand=True
        )

        list_scroll = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=listbox.yview
        )

        list_scroll.pack(
            side="right",
            fill="y"
        )

        listbox.config(
            yscrollcommand=list_scroll.set
        )

        button_frame = ttk.Frame(
            container
        )

        button_frame.pack(
            fill="x",
            pady=(10, 0)
        )

        def add_edge() -> None:

            source = source_entry.get().strip()
            target = target_entry.get().strip()
            weight_text = weight_entry.get().strip()

            if not source or not target:

                messagebox.showwarning(
                    "Datos incompletos",
                    "Seleccione origen y destino.",
                    parent=window
                )
                return

            if source == target:

                messagebox.showerror(
                    "Arista inválida",
                    "El origen y destino deben ser distintos.",
                    parent=window
                )
                return

            try:
                weight = int(
                    weight_text
                )

            except ValueError:
                messagebox.showerror(
                    "Peso inválido",
                    "El peso debe ser un número entero.",
                    parent=window
                )
                return

            if weight <= 0:
                messagebox.showerror(
                    "Peso inválido",
                    "El peso debe ser positivo.",
                    parent=window
                )
                return

            if (
                source,
                target,
                weight
            ) in edges:

                messagebox.showwarning(
                    "Arista repetida",
                    "La arista ya fue ingresada.",
                    parent=window
                )
                return

            for old_source, old_target, _ in edges:

                if (
                    old_source == source
                    and old_target == target
                ):

                    messagebox.showwarning(
                        "Arista repetida",
                        "Ya existe esa conexión.",
                        parent=window
                    )
                    return

            test_graph = nx.DiGraph()

            test_graph.add_nodes_from(
                f"N{i}"
                for i in range(1, node_count + 1)
            )

            test_graph.add_edges_from(
                (u, v)
                for u, v, _ in edges
            )

            test_graph.add_edge(
                source,
                target
            )

            if not nx.is_directed_acyclic_graph(
                test_graph
            ):

                messagebox.showerror(
                    "Ciclo detectado",
                    "La conexión crearía un ciclo. "
                    "El grafo debe ser acíclico.",
                    parent=window
                )

                return

            edges.append(
                (
                    source,
                    target,
                    weight
                )
            )

            listbox.insert(
                tk.END,
                f"{source} -> {target}  peso={weight}"
            )

            source_entry.set("")
            target_entry.set("")
            weight_entry.delete(
                0,
                tk.END
            )

        def remove_edge() -> None:

            selection = listbox.curselection()

            if not selection:
                return

            index = selection[0]

            listbox.delete(
                index
            )

            edges.pop(index)

        def finish_manual_graph() -> None:

            if not edges:
                messagebox.showwarning(
                    "Grafo vacío",
                    "Ingrese al menos una arista.",
                    parent=window
                )
                return

            try:
                self.graph_model.create_manual_graph(
                    node_count,
                    edges
                )
            except ValueError as error:
                messagebox.showerror(
                    "Grafo inválido",
                    str(error),
                    parent=window
                )
                return

            window.destroy()
            self.finish_graph_generation()

        ttk.Button(
            button_frame,
            text="Agregar arista",
            command=add_edge,
            style="Action.TButton"
        ).pack(
            side="left",
            padx=4
        )

        ttk.Button(
            button_frame,
            text="Eliminar seleccionada",
            command=remove_edge,
            style="Action.TButton"
        ).pack(
            side="left",
            padx=4
        )

        ttk.Button(
            button_frame,
            text="Crear grafo",
            command=finish_manual_graph,
            style="Action.TButton"
        ).pack(
            side="right",
            padx=4
        )

        ttk.Button(
            button_frame,
            text="Cancelar",
            command=window.destroy
        ).pack(
            side="right",
            padx=4
        )

    def calculate_positions(
            self
    ) -> Dict[str, Tuple[float, float]]:

        graph = self.graph_model.graph
        nodes = list(graph.nodes)
        node_count = len(nodes)

        if node_count == 0:
            return {}

        if node_count == 1:
            return {nodes[0]: (8.0, 5.0)}

        rng = random.Random(self.graph_model.layout_seed)

        try:
            node_rank = {
                node: idx for idx, node in enumerate(nodes)
            }
            topo_nodes = list(
                nx.lexicographical_topological_sort(
                    graph,
                    key=lambda n: node_rank.get(n, 0)
                )
            )
        except nx.NetworkXUnfeasible:
            topo_nodes = list(nodes)

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
                        if p2[0] < p1[0] + 0.3:
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
                if dx < 1.1:
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
            x1: float,
            y1: float,
            x2: float,
            y2: float,
            rad: float,
            t: float
        ) -> Tuple[float, float]:
            dx = x2 - x1
            dy = y2 - y1
            cx = (x1 + x2) / 2.0 + rad * dy
            cy = (y1 + y2) / 2.0 - rad * dx
            rem = 1.0 - t
            bx = (
                rem * rem * x1
                + 2.0 * rem * t * cx
                + t * t * x2
            )
            by = (
                rem * rem * y1
                + 2.0 * rem * t * cy
                + t * t * y2
            )
            return bx, by

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
            x1, y1 = positions[u]
            x2, y2 = positions[v]
            best_rad = 0.0
            best_cost = float("inf")

            for rad in candidate_rads:
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
                dpi=100
            )

            self.graph_axis = self.figure.add_subplot(
                111
            )

            self.canvas = FigureCanvasTkAgg(
                self.figure,
                master=self.graph_frame
            )

            self.toolbar = BarraHerramientasEspanol(
                self.canvas,
                self.graph_frame,
                pack_toolbar=False
            )

            self.toolbar.update()
            self.toolbar.pack(
                side="top",
                fill="x"
            )

            self.canvas.get_tk_widget().pack(
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
            edge_width = 1.4
            arrow_size = 19
            weight_font_size = 8
        else:
            edge_width = 1.2
            arrow_size = 16
            weight_font_size = 8

        highlight_edge_width = (
            3.2 if edge_count <= 20 else 2.8
        )

        highlight_arrow_size = (
            22 if edge_count <= 20 else 19
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

        default_nodes = [
            node
            for node in nodes
            if node != source
            and node != target
            and node not in processed
        ]

        if default_nodes:

            nx.draw_networkx_nodes(
                graph,
                positions,
                ax=axis,
                nodelist=default_nodes,
                node_size=base_node_size,
                node_color="#DCE6F1",
                edgecolors="#2F3B52",
                linewidths=1.2
            )

        if source is not None:

            nx.draw_networkx_nodes(
                graph,
                positions,
                ax=axis,
                nodelist=[source],
                node_size=key_node_size,
                node_color="#B7E4C7",
                edgecolors="#1B4332",
                linewidths=2
            )

        if target is not None and target != source:

            nx.draw_networkx_nodes(
                graph,
                positions,
                ax=axis,
                nodelist=[target],
                node_size=key_node_size,
                node_color="#FFD6A5",
                edgecolors="#9C2C00",
                linewidths=2
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
                node_color="#CDE7F0",
                edgecolors="#16697A",
                linewidths=2
            )

        if (
                self.graph_model.current_node is not None
                and self.graph_model.current_node != source
                and self.graph_model.current_node != target
        ):

            nx.draw_networkx_nodes(
                graph,
                positions,
                ax=axis,
                nodelist=[
                    self.graph_model.current_node
                ],
                node_size=current_node_size,
                node_color="#FFF3BF",
                edgecolors="#8A6D1D",
                linewidths=3
            )

        nx.draw_networkx_labels(
            graph,
            positions,
            ax=axis,
            font_size=node_label_size,
            font_weight="bold"
        )

        edge_curvatures, label_coords = (
            self.compute_smart_curvatures_and_labels(
                graph,
                positions
            )
        )

        for edge in graph.edges:
            curvature = edge_curvatures[edge]

            nx.draw_networkx_edges(
                graph,
                positions,
                edgelist=[edge],
                ax=axis,
                arrows=True,
                arrowsize=arrow_size,
                width=edge_width,
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
                    edge_color="#D62828",
                    node_size=edge_node_sizes,
                    nodelist=nodes,
                    connectionstyle=f"arc3,rad={curvature:.3f}"
                )

        edge_labels = nx.get_edge_attributes(
            graph,
            "weight"
        )

        for edge, weight in edge_labels.items():
            label_x, label_y = label_coords[edge]

            axis.text(
                label_x,
                label_y,
                str(weight),
                fontsize=weight_font_size,
                horizontalalignment="center",
                verticalalignment="center",
                zorder=5,
                bbox={
                    "boxstyle": "round,pad=0.22",
                    "fc": "white",
                    "ec": "#D9DDE5",
                    "alpha": 0.95
                }
            )
        axis.set_title(
            "Grafo dirigido acíclico ponderado",
            fontsize=14,
            fontweight="bold",
            pad=12
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

        if not paths or distance is None:
            self.status_var.set(
                "No existe un camino desde el origen hasta el destino."
            )

            messagebox.showinfo(
                "Resultado",
                "No existe un camino alcanzable "
                "desde el origen hasta el destino."
            )
            return

        self.status_var.set(
            f"Algoritmo terminado | "
            f"Distancia mínima: {distance} | "
            f"Caminos mínimos: {len(paths)}"
        )

        result_window = tk.Toplevel(
            self.root
        )

        result_window.title(
            "Resultado de caminos mínimos"
        )

        result_window.geometry(
            "760x560"
        )

        result_window.minsize(
            620,
            420
        )

        result_window.transient(
            self.root
        )

        container = ttk.Frame(
            result_window,
            padding=14
        )

        container.pack(
            fill="both",
            expand=True
        )

        ttk.Label(
            container,
            text="Resultado del algoritmo de Dijkstra",
            font=("Segoe UI", 17, "bold")
        ).pack(
            anchor="w",
            pady=(0, 12)
        )

        ttk.Label(
            container,
            text=f"Distancia mínima: {distance}",
            font=("Segoe UI", 12, "bold")
        ).pack(
            anchor="w",
            pady=3
        )

        ttk.Label(
            container,
            text=f"Cantidad de caminos mínimos: {len(paths)}",
            font=("Segoe UI", 12, "bold")
        ).pack(
            anchor="w",
            pady=(3, 12)
        )

        result_frame = ttk.LabelFrame(
            container,
            text="Caminos mínimos encontrados",
            padding=8
        )

        result_frame.pack(
            fill="both",
            expand=True
        )

        text_frame = ttk.Frame(
            result_frame
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

        results_text = tk.Text(
            text_frame,
            wrap="word",
            font=("Consolas", 10),
            yscrollcommand=scrollbar.set,
            padx=8,
            pady=8
        )

        results_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.config(
            command=results_text.yview
        )

        for index, path in enumerate(
                paths,
                start=1
        ):
            path_text = " → ".join(path)

            results_text.insert(
                tk.END,
                f"Camino {index}: {path_text}\n\n"
            )

        results_text.config(
            state="disabled"
        )

        ttk.Button(
            container,
            text="Cerrar",
            command=result_window.destroy
        ).pack(
            anchor="e",
            pady=(12, 0)
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

        nodes = self.graph_model.get_nodes()

        processed = set(
            self.graph_model.processed_nodes
        )

        self.labels_text.insert(
            tk.END,
            "ETIQUETAS ACTUALES POR VÉRTICE\n"
            "================================\n\n"
        )

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

            if node == self.graph_model.source:
                status = "Origen"

            elif (
                    node == self.graph_model.target
                    and self.graph_model.algorithm_finished
                    and distance != float("inf")
            ):
                status = "Destino alcanzado"

            elif (
                    node == self.graph_model.current_node
                    and not self.graph_model.algorithm_finished
            ):
                status = "Vértice actual"


            elif (

                    distance == float("inf")

                    and node in processed

            ):

                status = "Inalcanzable desde el origen"


            elif node in processed:

                status = "Procesado"


            elif distance == float("inf"):

                status = "Distancia ∞ (pendiente)"

            elif node == self.graph_model.target:
                status = "Destino pendiente"

            else:
                status = "Pendiente"

            self.labels_text.insert(
                tk.END,
                f"{node}\n"
                f"  Etiqueta: [{distance_text}, "
                f"{predecessor_text}]_{iteration}\n"
                f"  Estado: {status}\n\n"
            )

        self.labels_text.insert(
            tk.END,
            "LEYENDA\n"
            "=======\n"
            "∞ = distancia infinita desde el origen\n"
            "Origen = vértice de partida\n"
            "Destino alcanzado = solución encontrada\n"
            "Procesado = vértice ya examinado\n"
            "Pendiente = vértice por examinar\n"
            "Inalcanzable = no existe ruta desde el origen\n"
        )

        self.history_text.insert(
            tk.END,
            "HISTORIAL DE ETIQUETAS\n"
            "=====================\n\n"
        )

        self.history_text.tag_config(
            "crossed",
            foreground="#A00000",
            overstrike=True
        )

        for node in nodes:

            self.history_text.insert(
                tk.END,
                f"{node}\n"
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
                    "(sin distancia finita registrada)\n\n"
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

                start = self.history_text.index(
                    tk.END
                )

                self.history_text.insert(
                    tk.END,
                    label_text + "\n"
                )

                end = self.history_text.index(
                    tk.END
                )

                if crossed:
                    self.history_text.tag_add(
                        "crossed",
                        start,
                        end
                    )

            self.history_text.insert(
                tk.END,
                "\n"
            )

        self.history_text.insert(
            tk.END,
            "Las etiquetas en rojo y tachadas "
            "fueron reemplazadas por una distancia menor."
        )

        self.decisions_text.insert(
            tk.END,
            "REGISTRO DE DECISIONES DEL ALGORITMO\n"
            "====================================\n\n"
        )

        if not self.graph_model.decision_history:

            self.decisions_text.insert(
                tk.END,
                "Todavía no hay decisiones registradas. "
                "Inicialice Dijkstra para comenzar.\n"
            )

        else:
            for index, decision in enumerate(
                    self.graph_model.decision_history,
                    start=1
            ):

                decision_text = decision.strip()

                if decision_text:
                    self.decisions_text.insert(
                        tk.END,
                        f"DECISIÓN {index}\n"
                        f"{decision_text}\n\n"
                    )

        for text_widget in (
                self.labels_text,
                self.history_text,
                self.decisions_text
        ):
            text_widget.config(
                state="disabled"
            )

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

        information_window.transient(
            self.root
        )

        container = ttk.Frame(
            information_window,
            padding=24
        )

        container.pack(
            fill="both",
            expand=True
        )

        style = ttk.Style(information_window)

        style.configure(
            "Project.Title.TLabel",
            font=("Segoe UI", 18, "bold")
        )

        style.configure(
            "Project.Subtitle.TLabel",
            font=("Segoe UI", 11)
        )

        style.configure(
            "Project.Body.TLabel",
            font=("Segoe UI", 10),
            foreground="#333333"
        )

        style.configure(
            "Project.Field.TLabel",
            font=("Segoe UI", 10, "bold")
        )

        style.configure(
            "Project.Value.TLabel",
            font=("Segoe UI", 10)
        )

        style.configure(
            "Project.Member.TLabel",
            font=("Segoe UI", 10)
        )

        style.configure(
            "Project.Close.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 6)
        )

        ttk.Label(
            container,
            text="Información del proyecto",
            style="Project.Title.TLabel"
        ).pack(
            pady=(0, 5)
        )

        ttk.Label(
            container,
            text=self.project_info.theme,
            style="Project.Subtitle.TLabel"
        ).pack(
            pady=(0, 18)
        )

        ttk.Label(
            container,
            text=(
                "Aplicación desarrollada en Python para construir grafos "
                "dirigidos, acíclicos y ponderados. Permite ejecutar el "
                "algoritmo de Dijkstra paso a paso, consultar las etiquetas "
                "y el registro de decisiones, y visualizar los caminos "
                "mínimos mediante una representación gráfica de red."
            ),
            style="Project.Body.TLabel",
            wraplength=560,
            justify="left"
        ).pack(
            fill="x",
            pady=(0, 18)
        )

        information_frame = ttk.LabelFrame(
            container,
            text="Datos académicos",
            padding=14
        )

        information_frame.pack(
            fill="x",
            pady=(0, 12)
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
                pady=4
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
                pady=4
            )

        integrants_frame = ttk.LabelFrame(
            container,
            text="Integrantes",
            padding=14
        )

        integrants_frame.pack(
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
                pady=3
            )

        ttk.Button(
            container,
            text="Cerrar",
            command=information_window.destroy,
            style="Project.Close.TButton"
        ).pack(
            pady=(14, 0)
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
            font=("Segoe UI", 18, "bold")
        ).pack(
            pady=(0, 4)
        )

        ttk.Label(
            container,
            text=(
                "Problema del camino mínimo | "
                "Algoritmo de Dijkstra"
            ),
            font=("Segoe UI", 10)
        ).pack(
            pady=(0, 12)
        )

        notebook = ttk.Notebook(
            container
        )

        notebook.pack(
            fill="both",
            expand=True
        )

        overview_tab = ttk.Frame(
            notebook,
            padding=16
        )

        usage_tab = ttk.Frame(
            notebook,
            padding=16
        )

        dijkstra_tab = ttk.Frame(
            notebook,
            padding=16
        )

        labels_tab = ttk.Frame(
            notebook,
            padding=16
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

        if initial_tab < 0 or initial_tab > 3:
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
                    "Permite trabajar el problema "
                    "del camino mínimo mediante "
                    "un grafo dirigido acíclico "
                    "con pesos positivos."
                ),
                (
                    "Generación",
                    "El usuario puede generar el "
                    "grafo aleatoriamente o construirlo "
                    "manualmente."
                ),
                (
                    "Algoritmo",
                    "Dijkstra puede ejecutarse paso "
                    "a paso o hasta completar el "
                    "camino mínimo."
                ),
            ]
        )

        self.create_help_text(
            usage_tab,
            "Cómo utilizar el sistema",
            [
                (
                    "1. Cantidad de nodos",
                    "Ingrese un número entre 7 y 16."
                ),
                (
                    "2. Tipo de grafo",
                    "Seleccione Aleatorio o Manual."
                ),
                (
                    "3. Crear grafo",
                    "En modo manual ingrese cada "
                    "conexión, destino y peso."
                ),
                (
                    "4. Origen y destino",
                    "Seleccione los vértices correspondientes."
                ),
                (
                    "5. Inicializar",
                    "Crea las etiquetas iniciales."
                ),
                (
                    "6. Siguiente paso",
                    "Ejecuta una iteración de Dijkstra."
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
                    "han sido revisados. Los que conservan distancia "
                    "infinita son inalcanzables desde el origen."
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

        ttk.Button(
            container,
            text="Cerrar",
            command=help_window.destroy
        ).pack(
            pady=(12, 0)
        )

    @staticmethod
    def create_help_text(
            parent: ttk.Frame,
            title: str,
            sections: List[Tuple[str, str]]
    ) -> None:

        ttk.Label(
            parent,
            text=title,
            font=("Segoe UI", 15, "bold")
        ).pack(
            anchor="w",
            pady=(0, 14)
        )

        for section_title, description in sections:
            ttk.Label(
                parent,
                text=section_title,
                font=("Segoe UI", 10, "bold")
            ).pack(
                anchor="w",
                pady=(4, 2)
            )

            ttk.Label(
                parent,
                text=description,
                wraplength=700,
                justify="left"
            ).pack(
                anchor="w",
                fill="x",
                pady=(0, 8)
            )

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