"""API puente entre el núcleo en Python y la interfaz web de escritorio (pywebview)."""

import base64
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
import webview

from backend.project_info import ProjectInfo
from backend.graph_generator import GraphGenerator
from backend.layout_engine import LayoutEngine
from backend.dijkstra_engine import DijkstraEngine


class DesktopAPI:
    """
    Expone los métodos del núcleo en Python a la capa de interfaz JavaScript
    a través de `window.pywebview.api`.
    """

    def __init__(self) -> None:
        self.project_info = ProjectInfo()
        self.dijkstra = DijkstraEngine()

        self.cached_positions: Dict[str, Tuple[float, float]] = {}
        self.manual_build_mode: bool = False
        self.is_manual_graph: bool = False
        self.manual_connections: List[Dict[str, Any]] = []
        self.manual_highlighted_nodes: List[str] = []

        # Generar un grafo aleatorio inicial de 7 nodos al arrancar
        graph, seed = GraphGenerator.create_random_graph(
            7, allow_bidirectional=False, allow_cycles=False
        )
        self.dijkstra.set_graph(graph, seed)
        self.cached_positions = LayoutEngine.calculate_positions(graph, seed)

    def _build_graph_payload(self) -> Dict[str, Any]:
        """
        Construye la representación geométrica y visual completa del grafo
        (nodos, aristas curvas Bezier, etiquetas de peso y estados de Dijkstra)
        para ser renderizada en SVG por el frontend.
        """
        graph = self.dijkstra.graph
        nodes = self.dijkstra.get_nodes()
        node_count = len(nodes)
        edge_count = graph.number_of_edges()

        if not self.cached_positions or set(self.cached_positions.keys()) != set(nodes):
            self.cached_positions = LayoutEngine.calculate_positions(
                graph, self.dijkstra.layout_seed
            )

        positions = self.cached_positions
        edge_curvatures, label_coords = (
            LayoutEngine.compute_smart_curvatures_and_labels(graph, positions)
        )

        source = self.dijkstra.source
        target = self.dijkstra.target
        current_node = self.dijkstra.current_node
        algorithm_finished = self.dijkstra.algorithm_finished
        processed = set(self.dijkstra.processed_nodes)
        manual_blue = (
            set(self.manual_highlighted_nodes)
            if self.manual_build_mode
            else set()
        )

        optimal_edges: Set[Tuple[str, str]] = set()
        if algorithm_finished:
            for path in self.dijkstra.get_shortest_paths():
                for idx in range(len(path) - 1):
                    optimal_edges.add((path[idx], path[idx + 1]))

        if node_count <= 10:
            base_r, key_r, curr_r, font_sz = 30.0, 32.5, 34.5, 15
        elif node_count <= 13:
            base_r, key_r, curr_r, font_sz = 27.5, 30.0, 32.0, 14
        else:
            base_r, key_r, curr_r, font_sz = 25.5, 28.0, 30.0, 13

        # Transformar coordenadas de [0..16]x[0..10] (Y hacia arriba) a SVG [0..1600]x[0..1000] (Y hacia abajo)
        def to_svg(px: float, py: float) -> Tuple[float, float]:
            return round(px * 100.0, 2), round((10.0 - py) * 100.0, 2)

        nodes_payload: List[Dict[str, Any]] = []
        node_radii: Dict[str, float] = {}

        for node in nodes:
            px, py = positions.get(node, (8.0, 5.0))
            sx, sy = to_svg(px, py)

            # Prioridad de color exacta a la versión original
            fill_color = "#161b22"
            stroke_color = "#30363d"
            stroke_width = 1.6
            radius = base_r
            role = "default"

            if node in manual_blue:
                fill_color = "#121d2f"
                stroke_color = "#58a6ff"
                stroke_width = 2.4
                radius = key_r
                role = "manual_selected"

            if node == source:
                fill_color = "#122117"
                stroke_color = "#3fb950"
                stroke_width = 2.2
                radius = key_r
                role = "source"
            elif node == target:
                fill_color = "#2a1912"
                stroke_color = "#ffa657"
                stroke_width = 2.2
                radius = key_r
                role = "target"
            elif node in processed:
                fill_color = "#111b27"
                stroke_color = "#388bfd"
                stroke_width = 2.0
                radius = base_r
                role = "processed"

            if (
                current_node is not None
                and node == current_node
                and node != source
                and node != target
            ):
                fill_color = "#272115"
                stroke_color = "#e3b341"
                stroke_width = 2.6
                radius = curr_r
                role = "current"

            node_radii[node] = radius

            nodes_payload.append(
                {
                    "id": node,
                    "x": sx,
                    "y": sy,
                    "r": radius,
                    "fill": fill_color,
                    "stroke": stroke_color,
                    "stroke_width": stroke_width,
                    "font_size": font_sz,
                    "role": role,
                }
            )

        edges_payload: List[Dict[str, Any]] = []
        for u, v in graph.edges:
            x1, y1 = positions[u]
            x2, y2 = positions[v]
            rad = edge_curvatures.get((u, v), 0.0)
            weight_val = int(graph[u][v].get("weight", 0))

            has_reverse = graph.has_edge(v, u)
            same_bi_weight = (
                has_reverse and int(graph[v][u].get("weight", 0)) == weight_val
            )

            # Punto medio de la curva en espacio cartesiano
            dx = x2 - x1
            dy = y2 - y1
            mid_x = (x1 + x2) / 2.0 + rad * dy
            mid_y = (y1 + y2) / 2.0 - rad * dx

            # Punto de control cuadrático Bezier para que la curva pase por (mid_x, mid_y) en t=0.5
            ctrl_x = 2.0 * mid_x - 0.5 * (x1 + x2)
            ctrl_y = 2.0 * mid_y - 0.5 * (y1 + y2)

            sx1, sy1 = to_svg(x1, y1)
            sx2, sy2 = to_svg(x2, y2)
            scx, scy = to_svg(ctrl_x, ctrl_y)

            is_optimal = (u, v) in optimal_edges
            is_unweighted = self.manual_build_mode and weight_val <= 0

            if is_optimal:
                color = "#f85149"
                width = 3.2 if edge_count <= 20 else 2.8
                dashed = False
            elif is_unweighted:
                color = "#484f58"
                width = 1.8
                dashed = True
            elif same_bi_weight:
                color = "#7c8896"
                width = 1.85 if edge_count <= 20 else 1.65
                dashed = False
            else:
                color = "#6e7681"
                width = 1.8 if edge_count <= 20 else 1.6
                dashed = False

            edges_payload.append(
                {
                    "u": u,
                    "v": v,
                    "x1": sx1,
                    "y1": sy1,
                    "cx": scx,
                    "cy": scy,
                    "x2": sx2,
                    "y2": sy2,
                    "r_u": node_radii.get(u, base_r),
                    "r_v": node_radii.get(v, base_r),
                    "weight": weight_val,
                    "color": color,
                    "width": width,
                    "dashed": dashed,
                    "is_optimal": is_optimal,
                    "is_bidirectional_equal": same_bi_weight,
                }
            )

        weight_labels_payload: List[Dict[str, Any]] = []
        drawn_shared_labels: Set[Tuple[str, str]] = set()
        for u, v in graph.edges:
            weight_val = int(graph[u][v].get("weight", 0))
            if (v, u) in drawn_shared_labels and (
                graph.has_edge(v, u)
                and int(graph[v][u].get("weight", 0)) == weight_val
            ):
                continue

            drawn_shared_labels.add((u, v))
            lx, ly = label_coords.get((u, v), (8.0, 5.0))
            slx, sly = to_svg(lx, ly)
            is_bi_equal = (
                graph.has_edge(v, u)
                and int(graph[v][u].get("weight", 0)) == weight_val
            )

            weight_labels_payload.append(
                {
                    "u": u,
                    "v": v,
                    "x": slx,
                    "y": sly,
                    "text": str(weight_val) if weight_val > 0 else "?",
                    "border_color": "#3d4652" if is_bi_equal else "#30363d",
                }
            )

        title_text = (
            "Construcción manual: haga clic en dos nodos para conectarlos"
            if self.manual_build_mode
            else "Red de nodos ponderada (Dijkstra)"
        )

        return {
            "title": title_text,
            "nodes": nodes_payload,
            "edges": edges_payload,
            "weight_labels": weight_labels_payload,
            "node_list": nodes,
            "edge_count": edge_count,
        }

    def _build_full_response(
        self, status_message: str, ok: bool = True, error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Empaqueta la respuesta completa para sincronizar el estado de la interfaz."""
        return {
            "ok": ok,
            "error": error,
            "status_message": status_message,
            "manual_build_mode": self.manual_build_mode,
            "is_manual_graph": self.is_manual_graph,
            "manual_connections": self.manual_connections,
            "manual_highlighted_nodes": self.manual_highlighted_nodes,
            "graph": self._build_graph_payload(),
            "panels": self.dijkstra.get_structured_panel_data(),
        }

    def get_initial_state(self) -> Dict[str, Any]:
        """Devuelve el estado inicial de la aplicación junto con la información del proyecto."""
        resp = self._build_full_response(
            "Grafo aleatorio inicial de 7 vértices generado. Seleccione origen y destino."
        )
        resp["project_info"] = self.project_info.to_dict()
        return resp

    def generate_random_graph(
        self,
        node_count: Any,
        allow_bidirectional: bool = False,
        allow_cycles: bool = False,
    ) -> Dict[str, Any]:
        """Genera un grafo aleatorio con las preferencias de bidireccionalidad y ciclos indicadas."""
        try:
            count = int(node_count)
            GraphGenerator.validate_node_count(count)
        except (ValueError, TypeError):
            return self._build_full_response(
                "Error de validación.",
                ok=False,
                error="Ingrese un número entero entre 7 y 16.",
            )

        self.manual_build_mode = False
        self.is_manual_graph = False
        self.manual_connections = []
        self.manual_highlighted_nodes = []

        graph, seed = GraphGenerator.create_random_graph(
            count,
            allow_bidirectional=bool(allow_bidirectional),
            allow_cycles=bool(allow_cycles),
        )
        self.dijkstra.set_graph(graph, seed)
        self.cached_positions = LayoutEngine.calculate_positions(graph, seed)

        modes_desc: List[str] = []
        if allow_bidirectional:
            modes_desc.append("bidireccional")
        if allow_cycles:
            modes_desc.append("con ciclos")
        extra_info = f" ({', '.join(modes_desc)})" if modes_desc else ""

        return self._build_full_response(
            f"Grafo aleatorio de {count} vértices generado{extra_info}. Seleccione origen y destino."
        )

    def start_manual_mode(self, node_count: Any) -> Dict[str, Any]:
        """Inicia el modo de construcción manual interactivo con nodos sin conexiones."""
        try:
            count = int(node_count)
            GraphGenerator.validate_node_count(count)
        except (ValueError, TypeError):
            return self._build_full_response(
                "Error de validación.",
                ok=False,
                error="Ingrese un número entero entre 7 y 16.",
            )

        self.manual_build_mode = True
        self.is_manual_graph = False
        self.manual_connections = []
        self.manual_highlighted_nodes = []

        graph, seed = GraphGenerator.create_empty_graph(count)
        self.dijkstra.set_graph(graph, seed)
        self.cached_positions = LayoutEngine.calculate_positions(graph, seed)

        return self._build_full_response(
            f"Modo construcción manual ({count} nodos): haga clic en el primer nodo para crear una conexión."
        )

    def edit_manual_graph(self) -> Dict[str, Any]:
        """
        Permite volver a editar un grafo manual ya confirmado, conservando sus conexiones
        actuales y reiniciando automáticamente el algoritmo de Dijkstra.
        """
        if not self.is_manual_graph or self.manual_build_mode:
            return self._build_full_response(
                "No hay un grafo manual confirmado para modificar.",
                ok=False,
                error="Solo se puede modificar un grafo manual previamente confirmado.",
            )

        self.dijkstra.reset_algorithm_data()
        self.manual_build_mode = True
        self.manual_highlighted_nodes = []

        # Reconstruir la lista de conexiones editables a partir de las aristas actuales del grafo
        rebuilt_connections: List[Dict[str, Any]] = []
        visited_pairs: Set[Tuple[str, str]] = set()
        for u, v, data in self.dijkstra.graph.edges(data=True):
            if (u, v) in visited_pairs:
                continue
            w = int(data.get("weight", 10))
            if (
                self.dijkstra.graph.has_edge(v, u)
                and int(self.dijkstra.graph[v][u].get("weight", -1)) == w
            ):
                visited_pairs.add((u, v))
                visited_pairs.add((v, u))
                rebuilt_connections.append(
                    {"u": u, "v": v, "weight": str(w), "bidirectional": True}
                )
            else:
                visited_pairs.add((u, v))
                rebuilt_connections.append(
                    {"u": u, "v": v, "weight": str(w), "bidirectional": False}
                )

        self.manual_connections = rebuilt_connections

        return self._build_full_response(
            "Modo edición manual activo: Dijkstra se ha reiniciado. Modifique las conexiones y presione Confirmar grafo."
        )

    def sync_manual_preview(
        self,
        connections: List[Dict[str, Any]],
        highlighted_nodes: List[str],
    ) -> Dict[str, Any]:
        """
        Actualiza en tiempo real las aristas y pesos del grafo durante la construcción
        manual sin recalcular las posiciones de los nodos.
        """
        self.manual_connections = connections
        self.manual_highlighted_nodes = highlighted_nodes

        nodes = self.dijkstra.get_nodes()
        self.dijkstra.graph.clear_edges()

        for conn in connections:
            u = str(conn.get("u", ""))
            v = str(conn.get("v", ""))
            if u not in nodes or v not in nodes or u == v:
                continue
            raw_w = str(conn.get("weight", "")).strip()
            try:
                w = int(raw_w)
                if w <= 0:
                    w = 0
            except ValueError:
                w = 0

            is_bi = bool(conn.get("bidirectional", False))
            self.dijkstra.graph.add_edge(u, v, weight=w)
            if is_bi:
                self.dijkstra.graph.add_edge(v, u, weight=w)

        return {
            "ok": True,
            "graph": self._build_graph_payload(),
        }

    def confirm_manual_graph(
        self, connections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Valida que todas las conexiones manuales tengan peso entero positivo y que
        ningún nodo haya quedado aislado, confirmando el grafo para ejecutar Dijkstra.
        """
        if not connections:
            return self._build_full_response(
                "Sin conexiones.",
                ok=False,
                error="Debe agregar al menos una conexión haciendo clic en los nodos.",
            )

        edges: List[Tuple[str, str, int]] = []
        connected_nodes: Set[str] = set()

        for conn in connections:
            u = str(conn.get("u", "")).strip()
            v = str(conn.get("v", "")).strip()
            raw_w = str(conn.get("weight", "")).strip()
            is_bi = bool(conn.get("bidirectional", False))

            if not raw_w:
                return self._build_full_response(
                    "Peso faltante.",
                    ok=False,
                    error=f"Debe asignar un peso a la conexión {u} → {v}.",
                )

            try:
                weight = int(raw_w)
                if weight <= 0:
                    raise ValueError
            except ValueError:
                return self._build_full_response(
                    "Peso inválido.",
                    ok=False,
                    error=f"El peso de la conexión {u} → {v} debe ser un entero positivo mayor que 0.",
                )

            edges.append((u, v, weight))
            if is_bi:
                edges.append((v, u, weight))
            connected_nodes.add(u)
            connected_nodes.add(v)

        all_nodes = set(self.dijkstra.get_nodes())
        isolated_nodes = sorted(
            list(all_nodes - connected_nodes),
            key=lambda x: int(x[1:]) if x[1:].isdigit() else 999,
        )
        if isolated_nodes:
            return self._build_full_response(
                "Nodos sin conectar.",
                ok=False,
                error=(
                    "No pueden quedar nodos aislados sin conectar.\n"
                    f"Nodos sin conexión: {', '.join(isolated_nodes)}"
                ),
            )

        node_count = len(all_nodes)
        try:
            graph, seed = GraphGenerator.create_manual_graph(
                node_count, edges, preserve_seed=self.dijkstra.layout_seed
            )
        except ValueError as err:
            return self._build_full_response(
                "Error en el grafo manual.", ok=False, error=str(err)
            )

        self.manual_build_mode = False
        self.is_manual_graph = True
        self.manual_connections = connections
        self.manual_highlighted_nodes = []

        self.dijkstra.set_graph(graph, seed)
        self.cached_positions = LayoutEngine.calculate_positions(graph, seed)

        return self._build_full_response(
            f"Grafo manual de {node_count} vértices confirmado correctamente. Seleccione origen y destino."
        )

    def initialize_dijkstra(self, source: str, target: str) -> Dict[str, Any]:
        """Inicializa el algoritmo de Dijkstra para el origen y destino seleccionados."""
        if self.manual_build_mode:
            return self._build_full_response(
                "Modo manual activo.",
                ok=False,
                error="Primero confirme la construcción manual del grafo.",
            )

        if self.dijkstra.graph.number_of_nodes() == 0:
            return self._build_full_response(
                "Grafo inexistente.",
                ok=False,
                error="Primero debe generar un grafo.",
            )

        try:
            self.dijkstra.initialize_dijkstra(source, target)
        except ValueError as err:
            return self._build_full_response(
                "Selección inválida.", ok=False, error=str(err)
            )

        return self._build_full_response(
            f"Dijkstra inicializado. Origen: {source} | Destino: {target}."
        )

    def next_step_dijkstra(self) -> Dict[str, Any]:
        """Ejecuta el siguiente paso del algoritmo de Dijkstra."""
        if self.dijkstra.source is None:
            return self._build_full_response(
                "Algoritmo no inicializado.",
                ok=False,
                error="Primero debe inicializar Dijkstra.",
            )

        if self.dijkstra.algorithm_finished:
            return self._build_full_response(
                "El algoritmo ya finalizó. Se muestran los resultados en el panel derecho."
            )

        self.dijkstra.execute_next_step()

        if self.dijkstra.algorithm_finished:
            msg = f"Iteración {self.dijkstra.iteration} completada. El algoritmo ha finalizado."
        else:
            msg = (
                f"Iteración {self.dijkstra.iteration}: "
                f"vértice procesado {self.dijkstra.current_node}."
            )

        return self._build_full_response(msg)

    def complete_dijkstra(self) -> Dict[str, Any]:
        """Ejecuta el algoritmo de Dijkstra completo hasta finalizar todos los vértices."""
        if self.dijkstra.source is None:
            return self._build_full_response(
                "Algoritmo no inicializado.",
                ok=False,
                error="Primero debe inicializar Dijkstra.",
            )

        self.dijkstra.execute_until_finished()
        return self._build_full_response(
            "Ejecución completa finalizada. Revise el cuadro de resultados en la derecha."
        )

    def save_graph_export(
        self, data_content: str, ext: str = "png"
    ) -> Dict[str, Any]:
        """Abre un cuadro de diálogo nativo para guardar el gráfico exportado en PNG o SVG."""
        if not webview.windows:
            return {"saved": False, "error": "No se encontró la ventana activa."}

        window = webview.windows[0]
        ext_clean = ext.lower().strip(".")
        if ext_clean == "svg":
            file_types = ("Archivo vectorial SVG (*.svg)", "Todos los archivos (*.*)")
            default_name = "grafo_dijkstra.svg"
        else:
            file_types = ("Imagen PNG (*.png)", "Todos los archivos (*.*)")
            default_name = "grafo_dijkstra.png"

        dialog_type = getattr(
            getattr(webview, "FileDialog", None),
            "SAVE",
            getattr(webview, "SAVE_DIALOG", 20),
        )

        result = window.create_file_dialog(
            dialog_type,
            save_filename=default_name,
            file_types=file_types,
        )

        if not result:
            return {"saved": False, "cancelled": True}

        save_path = result[0] if isinstance(result, (list, tuple)) else str(result)
        if not save_path:
            return {"saved": False, "cancelled": True}

        if not save_path.lower().endswith(f".{ext_clean}"):
            save_path = f"{save_path}.{ext_clean}"

        try:
            if ext_clean == "svg":
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(data_content)
            else:
                header, encoded = (
                    data_content.split(",", 1)
                    if "," in data_content
                    else ("", data_content)
                )
                binary_data = base64.b64decode(encoded)
                with open(save_path, "wb") as f:
                    f.write(binary_data)

            return {"saved": True, "path": save_path}
        except Exception as exc:
            return {"saved": False, "error": str(exc)}
