import random
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional, Tuple, Any, cast

import networkx as nx
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


class ProjectInfo:
    def __init__(self) -> None:
        self.course = "Matemática Computacional (1AMA0726)"
        self.theme = "Algoritmos de caminos mínimos"
        self.delivery = "Avance de la Semana 6 (TB1)"
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

        self.processed_nodes: List[str] = []

        self.iteration = 0

        self.source: Optional[str] = None
        self.target: Optional[str] = None

        self.current_node: Optional[str] = None

        self.algorithm_finished = False

    def reset_algorithm_data(self) -> None:
        self.labels.clear()
        self.label_history.clear()
        self.processed_nodes.clear()

        self.iteration = 0
        self.source = None
        self.target = None
        self.current_node = None

        self.algorithm_finished = False

    def create_random_dag(self, node_count: int) -> None:
        self.graph.clear()
        self.reset_algorithm_data()

        nodes = [f"N{i}" for i in range(1, node_count + 1)]

        self.graph.add_nodes_from(nodes)

        for index in range(node_count - 1):
            source_node = nodes[index]
            target_node = nodes[index + 1]

            self.graph.add_edge(
                source_node,
                target_node,
                weight=random.randint(1, 20),
            )

        for source_index in range(node_count):
            for target_index in range(source_index + 2, node_count):

                if random.random() < 0.25:
                    source_node = nodes[source_index]
                    target_node = nodes[target_index]

                    if not self.graph.has_edge(
                        source_node,
                        target_node
                    ):
                        self.graph.add_edge(
                            source_node,
                            target_node,
                            weight=random.randint(1, 20),
                        )

    def create_manual_graph(
        self,
        node_count: int,
        edges: List[Tuple[str, str, int]]
    ) -> None:

        self.graph.clear()
        self.reset_algorithm_data()

        nodes = [f"N{i}" for i in range(1, node_count + 1)]

        self.graph.add_nodes_from(nodes)

        for source, target, weight in edges:
            self.graph.add_edge(
                source,
                target,
                weight=weight,
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

        self.labels[source] = (0, None, 0)

        self.label_history[source].append(
            (0, None, 0, False)
        )

        return self.labels.copy()

    def get_unprocessed_reachable_nodes(self) -> List[str]:
        available_nodes = []

        for node in self.graph.nodes:

            if node in self.processed_nodes:
                continue

            distance = self.labels[node][0]

            if distance != float("inf"):
                available_nodes.append(node)

        return available_nodes

    def select_next_node(self) -> Optional[str]:
        available_nodes = self.get_unprocessed_reachable_nodes()

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
            return self.labels.copy()

        self.current_node = next_node

        self.iteration += 1

        self.processed_nodes.append(next_node)

        current_distance = self.labels[next_node][0]

        for neighbor in self.get_successors(next_node):

            if neighbor in self.processed_nodes:
                continue

            weight = self.get_edge_weight(
                next_node,
                neighbor
            )

            candidate_distance = current_distance + weight

            current_distance_neighbor = self.labels[neighbor][0]

            if candidate_distance < current_distance_neighbor:

                if current_distance_neighbor != float("inf"):
                    old_distance, old_predecessor, old_iteration = (
                        self.labels[neighbor]
                    )

                    self.label_history[neighbor].append(
                        (
                            old_distance,
                            old_predecessor,
                            old_iteration,
                            True
                        )
                    )

                new_label = (
                    candidate_distance,
                    next_node,
                    self.iteration
                )

                self.labels[neighbor] = new_label

                self.label_history[neighbor].append(
                    (
                        candidate_distance,
                        next_node,
                        self.iteration,
                        False
                    )
                )

        remaining_nodes = [
            node
            for node in self.graph.nodes
            if node not in self.processed_nodes
            and self.labels[node][0] != float("inf")
        ]

        if not remaining_nodes:
            self.algorithm_finished = True

        if (
            self.target is not None
            and self.target in self.processed_nodes
        ):
            self.algorithm_finished = True

        return self.labels.copy()

    def is_valid_dag(self) -> bool:
        return nx.is_directed_acyclic_graph(self.graph)

    def get_shortest_path(self) -> List[str]:
        if self.source is None or self.target is None:
            return []

        if self.labels[self.target][0] == float("inf"):
            return []

        path = []

        current = self.target

        while current is not None:
            path.append(current)

            predecessor = self.labels[current][1]

            if predecessor is None:
                break

            current = predecessor

        path.reverse()

        if not path or path[0] != self.source:
            return []

        return path

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

        self.root.geometry(
            "1450x900"
        )

        self.root.minsize(
            1200,
            760
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

        self.canvas: Optional[
            FigureCanvasTkAgg
        ] = None

        self.figure: Optional[
            Figure
        ] = None

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
            label="Nuevo grafo",
            command=self.generate_graph
        )

        project_menu.add_command(
            label="Reiniciar Dijkstra",
            command=self.initialize_algorithm
        )

        project_menu.add_command(
            label="Siguiente paso",
            command=self.execute_next_step
        )

        project_menu.add_command(
            label="Ejecutar hasta terminar",
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

        help_menu = tk.Menu(
            menu_bar,
            tearoff=0
        )

        help_menu.add_command(
            label="Qué hace el sistema",
            command=lambda: self.show_help(0)
        )

        help_menu.add_command(
            label="Cómo usar el sistema",
            command=lambda: self.show_help(1)
        )

        help_menu.add_command(
            label="Dijkstra paso a paso",
            command=lambda: self.show_help(2)
        )

        help_menu.add_command(
            label="Etiquetas y conceptos",
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
            weight=4
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
            text="Etiquetas de Dijkstra",
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
                "[L, X]_k | "
                "L = distancia | "
                "X = predecesor | "
                "k = iteración"
            ),
            font=("Segoe UI", 9)
        ).pack(
            anchor="w",
            pady=(0, 6)
        )

        text_frame = ttk.Frame(
            labels_frame
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

        self.labels_text = tk.Text(
            text_frame,
            width=42,
            height=25,
            state="disabled",
            font=("Consolas", 10),
            yscrollcommand=scrollbar.set,
            padx=8,
            pady=8
        )

        self.labels_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.config(
            command=self.labels_text.yview
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

            self.graph_model.create_manual_graph(
                node_count,
                edges
            )

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

        nodes = self.graph_model.get_nodes()

        node_count = len(nodes)

        if node_count <= 8:
            columns = 4
        elif node_count <= 12:
            columns = 5
        else:
            columns = 6

        positions: Dict[
            str,
            Tuple[float, float]
        ] = {}

        for index, node in enumerate(nodes):

            column = index % columns
            row = index // columns

            x = float(column) * 2.4
            y = float(-row) * 2.2

            if row % 2 == 1:
                y -= 0.5

            positions[node] = (
                x,
                y
            )

        return positions

    def display_graph(self) -> None:

        if self.graph_frame is None:
            return

        if self.canvas is not None:

            self.canvas.get_tk_widget().destroy()

        self.figure = Figure(
            figsize=(9, 7),
            dpi=100
        )

        axis = self.figure.add_subplot(
            111
        )

        graph = self.graph_model.graph

        positions = self.calculate_positions()

        nodes = self.graph_model.get_nodes()

        source = self.graph_model.source
        target = self.graph_model.target

        processed = set(
            self.graph_model.processed_nodes
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
                node_size=1000,
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
                node_size=1100,
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
                node_size=1100,
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
                node_size=1000,
                node_color="#CDE7F0",
                edgecolors="#16697A",
                linewidths=2
            )

        if self.graph_model.current_node is not None:

            nx.draw_networkx_nodes(
                graph,
                positions,
                ax=axis,
                nodelist=[
                    self.graph_model.current_node
                ],
                node_size=1200,
                node_color="#FFF3BF",
                edgecolors="#8A6D1D",
                linewidths=3
            )

        nx.draw_networkx_labels(
            graph,
            positions,
            ax=axis,
            font_size=10,
            font_weight="bold"
        )

        nx.draw_networkx_edges(
            graph,
            positions,
            ax=axis,
            arrows=True,
            arrowsize=20,
            width=1.5,
            node_size=1000,
            connectionstyle="arc3,rad=0.08"
        )

        edge_labels = nx.get_edge_attributes(
            graph,
            "weight"
        )

        nx.draw_networkx_edge_labels(
            graph,
            positions,
            edge_labels=edge_labels,
            ax=axis,
            font_size=9,
            label_pos=0.5,
            rotate=False,
            bbox={
                "boxstyle": "round,pad=0.18",
                "fc": "white",
                "ec": "none",
                "alpha": 0.9
            }
        )

        axis.set_title(
            "Grafo dirigido acíclico ponderado",
            fontsize=14,
            fontweight="bold",
            pad=12
        )

        axis.axis("off")
        axis.margins(0.20)

        self.canvas = FigureCanvasTkAgg(
            self.figure,
            master=self.graph_frame
        )

        self.canvas.draw()

        self.canvas.get_tk_widget().pack(
            fill="both",
            expand=True
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

        while not self.graph_model.algorithm_finished:

            self.graph_model.execute_next_step()

        self.update_labels_view()
        self.display_graph()

        self.show_final_result()

    def show_final_result(self) -> None:

        path = self.graph_model.get_shortest_path()

        distance = self.graph_model.get_shortest_distance()

        if not path or distance is None:

            self.status_var.set(
                "No existe un camino desde el origen hasta el destino."
            )

            messagebox.showinfo(
                "Resultado",
                "No existe un camino alcanzable "
                "desde el origen hasta el destino."
            )

            return

        path_text = " → ".join(
            path
        )

        self.status_var.set(
            f"Algoritmo terminado | "
            f"Distancia mínima: {distance} | "
            f"Camino: {path_text}"
        )

        messagebox.showinfo(
            "Camino mínimo",
            (
                f"Distancia mínima: {distance}\n\n"
                f"Camino mínimo:\n{path_text}"
            )
        )

    def update_labels_view(self) -> None:

        if self.labels_text is None:
            return

        self.labels_text.config(
            state="normal"
        )

        self.labels_text.delete(
            "1.0",
            tk.END
        )

        self.labels_text.insert(
            tk.END,
            "ESTADO ACTUAL\n"
            "══════════════════════════════════════\n\n"
        )

        for node in self.graph_model.get_nodes():

            history = (
                self.graph_model.label_history.get(
                    node,
                    []
                )
            )

            if not history:

                self.labels_text.insert(
                    tk.END,
                    f"{node:<5} [∞, -]_0\n"
                )

                continue

            for (
                distance,
                predecessor,
                iteration,
                crossed
            ) in history:

                if distance == float("inf"):

                    distance_text = "∞"

                else:

                    distance_text = str(
                        int(distance)
                    )

                predecessor_text = (
                    predecessor
                    if predecessor is not None
                    else "-"
                )

                text = (
                    f"{node:<5} "
                    f"[{distance_text}, "
                    f"{predecessor_text}]_{iteration}"
                )

                if crossed:

                    self.labels_text.insert(
                        tk.END,
                        "   ~~ "
                    )

                    start = self.labels_text.index(
                        tk.END
                    )

                    self.labels_text.insert(
                        tk.END,
                        text
                    )

                    end = self.labels_text.index(
                        tk.END
                    )

                    self.labels_text.tag_add(
                        "crossed",
                        start,
                        end
                    )

                    self.labels_text.insert(
                        tk.END,
                        " ~~\n"
                    )

                else:

                    self.labels_text.insert(
                        tk.END,
                        f"   {text}\n"
                    )

        self.labels_text.insert(
            tk.END,
            "\n"
        )

        self.labels_text.insert(
            tk.END,
            "══════════════════════════════════════\n"
        )

        self.labels_text.insert(
            tk.END,
            "Leyenda\n"
        )

        self.labels_text.insert(
            tk.END,
            "L = distancia acumulada\n"
        )

        self.labels_text.insert(
            tk.END,
            "X = predecesor\n"
        )

        self.labels_text.insert(
            tk.END,
            "k = iteración\n"
        )

        self.labels_text.insert(
            tk.END,
            "~~ ~~ = etiqueta reemplazada\n"
        )

        self.labels_text.tag_config(
            "crossed",
            foreground="#A00000",
            overstrike=True
        )

        self.labels_text.config(
            state="disabled"
        )

    def clear_labels(self) -> None:

        if self.labels_text is None:
            return

        self.labels_text.config(
            state="normal"
        )

        self.labels_text.delete(
            "1.0",
            tk.END
        )

        self.labels_text.config(
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
            "650x520"
        )

        information_window.minsize(
            600,
            470
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

        ttk.Label(
            container,
            text="Información del proyecto",
            font=("Segoe UI", 18, "bold")
        ).pack(
            pady=(0, 5)
        )

        ttk.Label(
            container,
            text=self.project_info.theme,
            font=("Segoe UI", 11)
        ).pack(
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
                font=("Segoe UI", 9, "bold")
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
                font=("Segoe UI", 10)
            ).pack(
                anchor="w",
                pady=3
            )

        tk.Button(
            container,
            text="Cerrar",
            command=information_window.destroy,
            width=12,
            height=1,
            font=("Segoe UI", 10, "bold")
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
                    "Si la nueva distancia es menor, "
                    "se reemplaza la etiqueta anterior."
                ),
                (
                    "Finalización",
                    "El proceso termina cuando el destino "
                    "es procesado o ya no existen vértices "
                    "alcanzables sin procesar."
                ),
            ]
        )

        self.create_help_text(
            labels_tab,
            "Etiquetas y conceptos",
            [
                (
                    "[L, X]_k",
                    "L representa la distancia acumulada, "
                    "X el predecesor y k la iteración."
                ),
                (
                    "[0, -]_0",
                    "Etiqueta inicial del origen."
                ),
                (
                    "[∞, -]_0",
                    "Nodo cuya distancia todavía "
                    "no ha sido determinada."
                ),
                (
                    "Etiqueta tachada",
                    "Representa una etiqueta anterior "
                    "que fue reemplazada por otra "
                    "con menor acumulado."
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