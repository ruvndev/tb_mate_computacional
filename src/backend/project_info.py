"""Información académica y de integrantes del proyecto."""

from typing import Dict, List, Any


class ProjectInfo:
    """Almacena los metadatos académicos del proyecto y los integrantes del grupo."""

    def __init__(self) -> None:
        self.course = "Matemática Computacional (1AMA0726)"
        self.theme = "Algoritmos de caminos mínimos"
        self.delivery = "Entrega final de la semana 11 (TB)"
        self.group = "3"
        self.description = (
            "Aplicación desarrollada en Python para construir grafos "
            "dirigidos, acíclicos y ponderados. Permite ejecutar el "
            "algoritmo de Dijkstra paso a paso, consultar las etiquetas "
            "y el registro de decisiones, y visualizar los caminos "
            "mínimos mediante una representación gráfica de red."
        )

        self.integrants: List[str] = [
            "Adriana Sofia Gamboa Coronado",
            "Edward Miguel Rodríguez Mamani",
            "Edwart Mathias Estrada Camus",
            "Ruben Alvaro Palpa Guimaray",
            "Tayra Valentina Espinoza Ramírez",
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Serializa los datos del proyecto para enviarlos al frontend."""
        return {
            "course": self.course,
            "theme": self.theme,
            "delivery": self.delivery,
            "group": self.group,
            "description": self.description,
            "integrants": list(self.integrants),
        }
