"""Motor del algoritmo de Dijkstra paso a paso con soporte para múltiples caminos mínimos."""

from typing import Any, Dict, List, Optional, Tuple, cast
import networkx as nx


class DijkstraEngine:
    """
    Gestiona el estado del grafo activo y la ejecución paso a paso del algoritmo
    de Dijkstra, incluyendo etiquetas [L, X]_k, historial de etiquetas reemplazadas,
    predecesores óptimos alternativos (empates) y registro detallado de decisiones.
    """

    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self.layout_seed: int = 101

        self.labels: Dict[str, Tuple[float, Optional[str], int]] = {}
        self.label_history: Dict[
            str, List[Tuple[float, Optional[str], int, bool]]
        ] = {}
        self.optimal_predecessors: Dict[str, List[str]] = {}
        self.last_tie_iteration: Dict[str, int] = {}
        self.decision_history: List[str] = []
        self.processed_nodes: List[str] = []

        self.iteration: int = 0
        self.source: Optional[str] = None
        self.target: Optional[str] = None
        self.current_node: Optional[str] = None
        self.algorithm_finished: bool = False

    def reset_algorithm_data(self) -> None:
        """Reinicia todas las estructuras del algoritmo de Dijkstra sin alterar el grafo."""
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

    def set_graph(self, graph: nx.DiGraph, layout_seed: int) -> None:
        """Asigna un nuevo grafo al motor y reinicia los datos del algoritmo."""
        self.graph = graph
        self.layout_seed = layout_seed
        self.reset_algorithm_data()

    def get_nodes(self) -> List[str]:
        """Devuelve la lista ordenada de vértices del grafo."""
        return list(self.graph.nodes)

    def get_successors(self, node: str) -> List[str]:
        """Devuelve los vértices sucesores de un nodo dado."""
        return list(self.graph.successors(node))

    def get_edge_weight(self, source: str, target: str) -> int:
        """Obtiene el peso entero positivo de la arista (source -> target)."""
        edge_data: Dict[str, Any] = self.graph[source][target]
        weight = cast(int, edge_data["weight"])
        return int(weight)

    def initialize_dijkstra(
        self, source: str, target: str
    ) -> Dict[str, Tuple[float, Optional[str], int]]:
        """Inicializa las etiquetas [0, -]_0 para el origen y [∞, -]_0 para los demás vértices."""
        if source not in self.graph.nodes or target not in self.graph.nodes:
            raise ValueError("Seleccione vértices válidos de origen y destino.")
        if source == target:
            raise ValueError("El origen y el destino deben ser diferentes.")
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
            node: (float("inf"), None, 0) for node in self.graph.nodes
        }
        self.label_history = {node: [] for node in self.graph.nodes}
        self.optimal_predecessors = {node: [] for node in self.graph.nodes}
        self.last_tie_iteration.clear()

        self.labels[source] = (0, None, 0)
        self.label_history[source].append((0, None, 0, False))

        # Agrupar la inicialización en una única entrada estructurada
        self.decision_history = [
            (
                f"Inicialización: el origen {source} recibe distancia 0 ([0, -]_0).\n"
                f"Inicialización: los demás vértices reciben distancia ∞ ([∞, -]_0).\n"
                f"Objetivo: hallar el camino mínimo desde {source} hasta {target}."
            )
        ]

        return self.labels.copy()

    def get_unprocessed_nodes(self) -> List[str]:
        """Devuelve los vértices que aún no han sido procesados."""
        return [
            node
            for node in self.graph.nodes
            if node not in self.processed_nodes
        ]

    def select_next_node(self) -> Optional[str]:
        """
        Selecciona el vértice no procesado con la menor distancia acumulada finita.
        Los vértices con distancia infinita (∞) no son seleccionables como pivotes.
        """
        reachable_unprocessed = [
            node
            for node in self.get_unprocessed_nodes()
            if self.labels.get(node, (float("inf"), None, 0))[0] != float("inf")
        ]
        if not reachable_unprocessed:
            return None
        return min(
            reachable_unprocessed,
            key=lambda node: (
                self.labels[node][0],
                int(node[1:]) if node[1:].isdigit() else 999,
            ),
        )

    def execute_next_step(
        self,
    ) -> Dict[str, Tuple[float, Optional[str], int]]:
        """Ejecuta una iteración del algoritmo de Dijkstra agrupando sus decisiones."""
        if self.source is None:
            raise ValueError("Primero debe inicializar Dijkstra.")

        if self.algorithm_finished:
            return self.labels.copy()

        next_node = self.select_next_node()

        if next_node is None:
            self.algorithm_finished = True
            self._finalize_unreachable_nodes_in_log()
            return self.labels.copy()

        self.current_node = next_node
        self.iteration += 1
        self.processed_nodes.append(next_node)

        current_distance = self.labels[next_node][0]
        step_lines: List[str] = [
            f"Iteración {self.iteration}: se selecciona {next_node} con distancia acumulada {int(current_distance)}."
        ]

        neighbors = self.get_successors(next_node)
        if not neighbors:
            step_lines.append(
                f"El vértice {next_node} no tiene aristas salientes para evaluar."
            )

        for neighbor in neighbors:
            if neighbor in self.processed_nodes:
                step_lines.append(
                    f"Arista {next_node} -> {neighbor}: el vértice adyacente {neighbor} ya fue procesado (se conserva su etiqueta permanente)."
                )
                continue

            weight = self.get_edge_weight(next_node, neighbor)
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
                                True,
                            )

                previous_distance_text = (
                    "∞"
                    if current_distance_neighbor == float("inf")
                    else str(int(current_distance_neighbor))
                )

                self.optimal_predecessors[neighbor] = [next_node]
                self.last_tie_iteration.pop(neighbor, None)
                self.labels[neighbor] = (
                    candidate_distance,
                    next_node,
                    self.iteration,
                )
                self.label_history[neighbor].append(
                    (candidate_distance, next_node, self.iteration, False)
                )

                step_lines.append(
                    f"Arista {next_node} -> {neighbor}, peso {weight}: "
                    f"{int(current_distance)} + {weight} = {int(candidate_distance)} < {previous_distance_text}. "
                    f"Actualización: se asigna [{int(candidate_distance)}, {next_node}]_{self.iteration}."
                )

            elif candidate_distance == current_distance_neighbor:
                if next_node not in self.optimal_predecessors[neighbor]:
                    self.optimal_predecessors[neighbor].append(next_node)
                    combined_preds = "/".join(self.optimal_predecessors[neighbor])
                    original_iteration = self.labels[neighbor][2]
                    # Conservar el subíndice de iteración original en que se descubrió la distancia mínima
                    self.labels[neighbor] = (
                        candidate_distance,
                        combined_preds,
                        original_iteration,
                    )
                    self.last_tie_iteration[neighbor] = self.iteration
                    self.label_history[neighbor].append(
                        (candidate_distance, next_node, self.iteration, False)
                    )
                    step_lines.append(
                        f"Arista {next_node} -> {neighbor}, peso {weight}: "
                        f"{int(current_distance)} + {weight} = {int(candidate_distance)}. "
                        f"Empate en distancia mínima: se registra el predecesor alternativo {next_node} "
                        f"(predecesores óptimos: {combined_preds})."
                    )
                else:
                    step_lines.append(
                        f"Arista {next_node} -> {neighbor}: la alternativa {next_node} ya estaba registrada."
                    )

            else:
                step_lines.append(
                    f"Arista {next_node} -> {neighbor}, peso {weight}: "
                    f"{int(current_distance)} + {weight} = {int(candidate_distance)} > {int(current_distance_neighbor)}. "
                    "Sin mejora: se conserva la etiqueta anterior."
                )

        # Verificar si aún quedan vértices alcanzables pendientes para la siguiente iteración
        next_reachable = self.select_next_node()
        if next_reachable is None:
            self.algorithm_finished = True
            unreachable_nodes = [
                n
                for n in self.get_unprocessed_nodes()
                if self.labels.get(n, (float("inf"), None, 0))[0] == float("inf")
            ]
            if unreachable_nodes:
                step_lines.append(
                    "Finalización: no quedan vértices alcanzables por procesar. "
                    f"Vértices inalcanzables (distancia ∞): {', '.join(unreachable_nodes)}."
                )
            else:
                step_lines.append(
                    "Finalización: todos los vértices alcanzables del grafo fueron procesados."
                )
        else:
            step_lines.append(
                f"Fin de la iteración {self.iteration}. "
                f"Siguiente candidato de menor distancia acumulada: {next_reachable}."
            )

        self.decision_history.append("\n".join(step_lines))
        return self.labels.copy()

    def _finalize_unreachable_nodes_in_log(self) -> None:
        """Registra el cierre del algoritmo cuando ningún vértice restante es alcanzable."""
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

    def execute_until_finished(self) -> None:
        """Ejecuta pasos sucesivos de Dijkstra hasta finalizar la revisión de todos los nodos alcanzables."""
        if self.source is None:
            raise ValueError("Primero debe inicializar Dijkstra.")
        while not self.algorithm_finished:
            self.execute_next_step()

    def get_shortest_paths(self) -> List[List[str]]:
        """Reconstruye recursivamente todos los caminos mínimos desde el origen hasta el destino."""
        if self.source is None or self.target is None:
            return []

        if self.labels.get(self.target, (float("inf"), None, 0))[0] == float(
            "inf"
        ):
            return []

        def build_paths(
            node: str, visited: Optional[set] = None
        ) -> List[List[str]]:
            if visited is None:
                visited = {node}
            if node == self.source:
                return [[self.source]]

            paths: List[List[str]] = []
            predecessors = self.optimal_predecessors.get(node, [])

            for predecessor in predecessors:
                if predecessor in visited:
                    continue
                previous_paths = build_paths(
                    predecessor, visited | {predecessor}
                )
                for path in previous_paths:
                    paths.append(path + [node])

            return paths

        return build_paths(self.target)

    def get_shortest_distance(self) -> Optional[int]:
        """Devuelve la distancia mínima entera al destino, o None si es inalcanzable."""
        if self.target is None or self.target not in self.labels:
            return None
        distance = self.labels[self.target][0]
        if distance == float("inf"):
            return None
        return int(distance)

    def get_structured_panel_data(self) -> Dict[str, Any]:
        """
        Serializa las etiquetas actuales, el historial de etiquetas, el registro de
        decisiones y los resultados finales con sus categorías de color para el frontend.
        """
        nodes = self.get_nodes()
        processed = set(self.processed_nodes)
        current_iter = self.iteration

        if not self.labels:
            return {
                "initialized": False,
                "current_labels": [],
                "history": [],
                "decisions": [],
                "result": None,
            }

        current_labels_list: List[Dict[str, Any]] = []
        for node in nodes:
            distance, predecessor, iteration = self.labels.get(
                node, (float("inf"), None, 0)
            )
            distance_text = (
                "∞" if distance == float("inf") else str(int(distance))
            )
            predecessor_text = predecessor if predecessor is not None else "-"
            is_target = node == self.target
            is_source = node == self.source
            is_curr = node == self.current_node and not self.algorithm_finished
            tied_in_current_iter = (
                self.last_tie_iteration.get(node) == current_iter
                and current_iter > 0
                and distance != float("inf")
            )

            # Conservar siempre la identidad distintiva del nodo Destino en todas las etapas
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
                if (node in processed or self.algorithm_finished) and distance != float("inf"):
                    status = "★ Destino alcanzado (óptimo)"
                    block_tag = "target_reached_block"
                    badge = "★"
                elif self.algorithm_finished and distance == float("inf"):
                    status = "✕ Destino inalcanzable desde el origen"
                    block_tag = "unreachable_block"
                    badge = "✕"
                elif iteration == current_iter and current_iter > 0 and distance != float("inf"):
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
            elif distance == float("inf") and (node in processed or self.algorithm_finished):
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

            current_labels_list.append(
                {
                    "node": node,
                    "badge": badge,
                    "label_str": f"[{distance_text}, {predecessor_text}]_{iteration}",
                    "distance_text": distance_text,
                    "predecessor_text": predecessor_text,
                    "iteration": iteration,
                    "status": status,
                    "block_tag": block_tag,
                    "is_current": is_curr,
                }
            )

        history_list: List[Dict[str, Any]] = []
        for node in nodes:
            is_curr = (
                node == self.current_node and not self.algorithm_finished
            )
            entries = self.label_history.get(node, [])
            formatted_entries: List[Dict[str, Any]] = []
            for dist, pred, it_num, crossed in entries:
                d_txt = "∞" if dist == float("inf") else str(int(dist))
                p_txt = pred if pred is not None else "-"
                base_lbl = f"[{d_txt}, {p_txt}]_{it_num}"
                if crossed:
                    suffix = "(reemplazada)"
                    tag = "crossed"
                elif it_num == current_iter and current_iter > 0:
                    suffix = "◀ nueva"
                    tag = "active_now"
                else:
                    suffix = "✓ vigente"
                    tag = "active_valid"
                formatted_entries.append(
                    {
                        "base_label": base_lbl,
                        "suffix": suffix,
                        "tag": tag,
                        "crossed": crossed,
                    }
                )
            history_list.append(
                {
                    "node": node,
                    "is_current": is_curr,
                    "entries": formatted_entries,
                }
            )

        decisions_list: List[Dict[str, Any]] = []
        total_decisions = len(self.decision_history)
        for index, decision in enumerate(self.decision_history, start=1):
            decision_text = decision.strip()
            if not decision_text:
                continue
            is_latest = index == total_decisions
            lines_data: List[Dict[str, str]] = []
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
                    or "ya estaba registrada" in line
                    or "ya está registrada" in line
                    or "no tiene aristas salientes" in line
                ):
                    line_tag = "no_improve_line"
                elif (
                    "Se selecciona" in line
                    or "se selecciona" in line
                    or "Candidatos" in line
                    or "Inicialización:" in line
                    or "Objetivo:" in line
                    or "Fin de la iteración" in line
                    or "Siguiente candidato" in line
                ):
                    line_tag = "selected_line"
                elif (
                    "Alcanzado" in line
                    or "Finalizado" in line
                    or "Finalización:" in line
                    or "Inalcanzables" in line
                    or "termina" in line
                    or "fueron procesados" in line
                    or "procesados óptimamente" in line
                ):
                    line_tag = "finished_line"
                else:
                    line_tag = "default_line"
                lines_data.append({"text": line, "tag": line_tag})

            header_title = (
                "INICIALIZACIÓN"
                if index == 1
                else f"ITERACIÓN {index - 1}"
            )
            decisions_list.append(
                {
                    "index": index,
                    "is_latest": is_latest,
                    "header": f"{'▶ ' if is_latest else ''}DECISIÓN {index} — {header_title}",
                    "lines": lines_data,
                }
            )

        result_data: Optional[Dict[str, Any]] = None
        if self.algorithm_finished and self.source and self.target:
            paths = self.get_shortest_paths()
            min_dist = self.get_shortest_distance()
            result_data = {
                "reachable": bool(paths and min_dist is not None),
                "source": self.source,
                "target": self.target,
                "distance": min_dist,
                "path_count": len(paths),
                "paths": [" → ".join(p) for p in paths],
                "raw_paths": paths,
            }

        return {
            "initialized": True,
            "iteration": self.iteration,
            "source": self.source,
            "target": self.target,
            "current_node": self.current_node,
            "algorithm_finished": self.algorithm_finished,
            "current_labels": current_labels_list,
            "history": history_list,
            "decisions": decisions_list,
            "result": result_data,
        }
