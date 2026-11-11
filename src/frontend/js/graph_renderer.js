/**
 * Renderizador interactivo del grafo en SVG.
 * Recibe la geometría calculada en Python y dibuja aristas curvas Bezier,
 * puntas de flecha, etiquetas de peso y nodos interactivos, además de gestionar
 * las herramientas de zoom, desplazamiento, historial de vistas y exportación.
 */

class GraphRenderer {
    constructor(svgElement, viewportElement, onNodeClick) {
        this.svg = svgElement;
        this.viewport = viewportElement;
        this.onNodeClick = onNodeClick;

        this.edgesLayer = document.getElementById("edges-layer");
        this.labelsLayer = document.getElementById("labels-layer");
        this.nodesLayer = document.getElementById("nodes-layer");
        this.zoomRect = document.getElementById("zoom-selection-rect");
        this.titleEl = document.getElementById("graph-canvas-title");

        this.btnReset = document.getElementById("btn-view-reset");
        this.btnPrev = document.getElementById("btn-view-prev");
        this.btnNext = document.getElementById("btn-view-next");
        this.btnPan = document.getElementById("btn-tool-pan");
        this.btnZoom = document.getElementById("btn-tool-zoom");

        this.defaultBox = { x: 0, y: 0, w: 1600, h: 1000 };
        this.currentBox = { ...this.defaultBox };
        this.viewHistory = [{ ...this.defaultBox }];
        this.historyIndex = 0;

        this.activeTool = null; // null | 'pan' | 'zoom'
        this.isDragging = false;
        this.dragStartClient = { x: 0, y: 0 };
        this.dragStartSvg = { x: 0, y: 0 };
        this.dragStartBox = null;

        this.lastPayload = null;
        this._lastScaleFactor = 1.0;

        this._bindViewportEvents();
    }

    /**
     * Calcula el factor de compensación de tamaño para que, al achicar la ventana,
     * los nodos y textos mantengan su tamaño visual o solo se reduzcan levemente
     * sin desacomodar sus posiciones en el grafo.
     */
    _getResponsiveScaleFactor() {
        if (!this.viewport) {
            return 1.0;
        }
        const rect = this.viewport.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) {
            return 1.0;
        }
        const viewportScale = Math.min(
            rect.width / this.defaultBox.w,
            rect.height / this.defaultBox.h
        );
        const refScale = 0.55;
        if (viewportScale >= refScale) {
            return 1.0;
        }
        const rawBoost = Math.pow(
            refScale / Math.max(0.18, viewportScale),
            0.72
        );
        return Math.min(1.52, Math.max(1.0, rawBoost));
    }

    /**
     * Convierte coordenadas de pantalla (clientX, clientY) al sistema interno del SVG.
     */
    clientToSvgPoint(clientX, clientY) {
        const pt = this.svg.createSVGPoint();
        pt.x = clientX;
        pt.y = clientY;
        const ctm = this.svg.getScreenCTM();
        if (!ctm) {
            return { x: 0, y: 0 };
        }
        return pt.matrixTransform(ctm.inverse());
    }

    /**
     * Aplica un viewBox al SVG y opcionalmente lo registra en el historial de vistas.
     */
    setViewBox(box, pushHistory = false) {
        const w = Math.max(160, Math.min(3200, box.w));
        const h = Math.max(100, Math.min(2000, box.h));
        const x = Math.max(-800, Math.min(1600, box.x));
        const y = Math.max(-500, Math.min(1000, box.y));

        this.currentBox = { x, y, w, h };
        this.svg.setAttribute("viewBox", `${x} ${y} ${w} ${h}`);

        if (pushHistory) {
            this.viewHistory = this.viewHistory.slice(0, this.historyIndex + 1);
            this.viewHistory.push({ ...this.currentBox });
            this.historyIndex = this.viewHistory.length - 1;
            this._updateHistoryButtons();
        }
    }

    resetView(pushHistory = true) {
        this.setViewBox({ ...this.defaultBox }, pushHistory);
    }

    prevView() {
        if (this.historyIndex > 0) {
            this.historyIndex -= 1;
            this.setViewBox(this.viewHistory[this.historyIndex], false);
            this._updateHistoryButtons();
        }
    }

    nextView() {
        if (this.historyIndex < this.viewHistory.length - 1) {
            this.historyIndex += 1;
            this.setViewBox(this.viewHistory[this.historyIndex], false);
            this._updateHistoryButtons();
        }
    }

    setToolMode(mode) {
        this.activeTool = this.activeTool === mode ? null : mode;
        this.btnPan.classList.toggle("active", this.activeTool === "pan");
        this.btnZoom.classList.toggle("active", this.activeTool === "zoom");
        this.viewport.classList.toggle("mode-pan", this.activeTool === "pan");
        this.viewport.classList.toggle("mode-zoom", this.activeTool === "zoom");
    }

    _updateHistoryButtons() {
        if (this.btnPrev) {
            this.btnPrev.disabled = this.historyIndex <= 0;
        }
        if (this.btnNext) {
            this.btnNext.disabled = this.historyIndex >= this.viewHistory.length - 1;
        }
    }

    _bindViewportEvents() {
        if (this.btnReset) {
            this.btnReset.addEventListener("click", () => this.resetView(true));
        }
        if (this.btnPrev) {
            this.btnPrev.addEventListener("click", () => this.prevView());
        }
        if (this.btnNext) {
            this.btnNext.addEventListener("click", () => this.nextView());
        }
        if (this.btnPan) {
            this.btnPan.addEventListener("click", () => this.setToolMode("pan"));
        }
        if (this.btnZoom) {
            this.btnZoom.addEventListener("click", () => this.setToolMode("zoom"));
        }

        // Rueda del ratón para acercar/alejar suavemente
        this.viewport.addEventListener(
            "wheel",
            (e) => {
                e.preventDefault();
                const factor = e.deltaY < 0 ? 0.86 : 1.16;
                const cursorSvg = this.clientToSvgPoint(e.clientX, e.clientY);
                const newW = this.currentBox.w * factor;
                const newH = this.currentBox.h * factor;
                if (newW < 200 || newW > 2600) {
                    return;
                }
                const relX = (cursorSvg.x - this.currentBox.x) / this.currentBox.w;
                const relY = (cursorSvg.y - this.currentBox.y) / this.currentBox.h;
                const newX = cursorSvg.x - relX * newW;
                const newY = cursorSvg.y - relY * newH;
                this.setViewBox({ x: newX, y: newY, w: newW, h: newH }, true);
            },
            { passive: false }
        );

        this.viewport.addEventListener("mousedown", (e) => {
            if (e.button !== 0) {
                return;
            }
            if (!this.activeTool) {
                return;
            }
            this.isDragging = true;
            this.dragStartClient = { x: e.clientX, y: e.clientY };
            this.dragStartSvg = this.clientToSvgPoint(e.clientX, e.clientY);
            this.dragStartBox = { ...this.currentBox };

            if (this.activeTool === "pan") {
                this.viewport.classList.add("dragging");
            } else if (this.activeTool === "zoom") {
                this.zoomRect.setAttribute("x", this.dragStartSvg.x);
                this.zoomRect.setAttribute("y", this.dragStartSvg.y);
                this.zoomRect.setAttribute("width", 0);
                this.zoomRect.setAttribute("height", 0);
                this.zoomRect.classList.remove("hidden");
            }
        });

        window.addEventListener("mousemove", (e) => {
            if (!this.isDragging) {
                return;
            }
            if (this.activeTool === "pan") {
                const rect = this.viewport.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) {
                    return;
                }
                const dxSvg =
                    ((e.clientX - this.dragStartClient.x) / rect.width) *
                    this.dragStartBox.w;
                const dySvg =
                    ((e.clientY - this.dragStartClient.y) / rect.height) *
                    this.dragStartBox.h;
                this.setViewBox(
                    {
                        x: this.dragStartBox.x - dxSvg,
                        y: this.dragStartBox.y - dySvg,
                        w: this.dragStartBox.w,
                        h: this.dragStartBox.h,
                    },
                    false
                );
            } else if (this.activeTool === "zoom") {
                const currSvg = this.clientToSvgPoint(e.clientX, e.clientY);
                const x = Math.min(this.dragStartSvg.x, currSvg.x);
                const y = Math.min(this.dragStartSvg.y, currSvg.y);
                const w = Math.abs(currSvg.x - this.dragStartSvg.x);
                const h = Math.abs(currSvg.y - this.dragStartSvg.y);
                this.zoomRect.setAttribute("x", x);
                this.zoomRect.setAttribute("y", y);
                this.zoomRect.setAttribute("width", w);
                this.zoomRect.setAttribute("height", h);
            }
        });

        window.addEventListener("mouseup", (e) => {
            if (!this.isDragging) {
                return;
            }
            this.isDragging = false;
            this.viewport.classList.remove("dragging");

            if (this.activeTool === "pan") {
                this.setViewBox(this.currentBox, true);
            } else if (this.activeTool === "zoom") {
                this.zoomRect.classList.add("hidden");
                const currSvg = this.clientToSvgPoint(e.clientX, e.clientY);
                const w = Math.abs(currSvg.x - this.dragStartSvg.x);
                const h = Math.abs(currSvg.y - this.dragStartSvg.y);
                if (w > 40 && h > 40) {
                    const x = Math.min(this.dragStartSvg.x, currSvg.x);
                    const y = Math.min(this.dragStartSvg.y, currSvg.y);
                    const aspect = 1600 / 1000;
                    let finalW = w;
                    let finalH = h;
                    if (w / h > aspect) {
                        finalH = w / aspect;
                    } else {
                        finalW = h * aspect;
                    }
                    this.setViewBox({ x, y, w: finalW, h: finalH }, true);
                }
            }
        });

        const handleViewportResize = () => {
            if (!this.lastPayload) {
                return;
            }
            const newFactor = this._getResponsiveScaleFactor();
            if (Math.abs(newFactor - this._lastScaleFactor) > 0.012) {
                this.render(this.lastPayload);
            }
        };

        if (typeof ResizeObserver !== "undefined" && this.viewport) {
            this._resizeObserver = new ResizeObserver(handleViewportResize);
            this._resizeObserver.observe(this.viewport);
        } else {
            window.addEventListener("resize", handleViewportResize);
        }
    }

    /**
     * Recorta los extremos de una curva cuadrática Bezier para que comience y termine
     * exactamente en el borde exterior de los nodos origen y destino.
     */
    _computeTrimmedBezierPath(edge, scaleFactor = 1.0) {
        const { x1, y1, cx, cy, x2, y2, r_u, r_v } = edge;
        const scaledRu = r_u * scaleFactor;
        const scaledRv = r_v * scaleFactor;

        // Dirección de salida desde (x1, y1) hacia el punto de control (cx, cy)
        let dxStart = cx - x1;
        let dyStart = cy - y1;
        let lenStart = Math.hypot(dxStart, dyStart);
        if (lenStart < 1e-3) {
            dxStart = x2 - x1;
            dyStart = y2 - y1;
            lenStart = Math.max(1e-3, Math.hypot(dxStart, dyStart));
        }

        // Dirección de llegada desde (cx, cy) hacia el nodo destino (x2, y2)
        let dxEnd = x2 - cx;
        let dyEnd = y2 - cy;
        let lenEnd = Math.hypot(dxEnd, dyEnd);
        if (lenEnd < 1e-3) {
            dxEnd = x2 - x1;
            dyEnd = y2 - y1;
            lenEnd = Math.max(1e-3, Math.hypot(dxEnd, dyEnd));
        }

        const startPad = scaledRu + 2;
        const endPad = scaledRv + 6;

        const sx = x1 + (dxStart / lenStart) * startPad;
        const sy = y1 + (dyStart / lenStart) * startPad;
        const ex = x2 - (dxEnd / lenEnd) * endPad;
        const ey = y2 - (dyEnd / lenEnd) * endPad;

        return `M ${sx.toFixed(2)} ${sy.toFixed(2)} Q ${cx.toFixed(2)} ${cy.toFixed(2)} ${ex.toFixed(2)} ${ey.toFixed(2)}`;
    }

    /**
     * Renderiza el grafo completo a partir del objeto `graphPayload` devuelto por Python.
     */
    render(graphPayload) {
        if (!graphPayload) {
            return;
        }
        this.lastPayload = graphPayload;

        const scaleFactor = this._getResponsiveScaleFactor();
        this._lastScaleFactor = scaleFactor;
        const pillScale = 1 + (scaleFactor - 1) * 0.65;
        const strokeScale = Math.pow(scaleFactor, 0.45);

        if (this.titleEl && graphPayload.title) {
            this.titleEl.textContent = graphPayload.title;
        }

        const svgNS = "http://www.w3.org/2000/svg";
        this.edgesLayer.innerHTML = "";
        this.labelsLayer.innerHTML = "";
        this.nodesLayer.innerHTML = "";

        // Ordenar aristas para que las aristas óptimas del camino mínimo queden siempre encima
        const sortedEdges = [...(graphPayload.edges || [])].sort((a, b) => {
            return (a.is_optimal ? 1 : 0) - (b.is_optimal ? 1 : 0);
        });

        for (const edge of sortedEdges) {
            const pathEl = document.createElementNS(svgNS, "path");
            pathEl.setAttribute(
                "d",
                this._computeTrimmedBezierPath(edge, scaleFactor)
            );
            pathEl.setAttribute("fill", "none");
            pathEl.setAttribute("stroke", edge.color);
            pathEl.setAttribute(
                "stroke-width",
                (edge.width * strokeScale).toFixed(2)
            );
            pathEl.setAttribute("stroke-linecap", "round");

            if (edge.dashed) {
                pathEl.setAttribute("stroke-dasharray", "7 5");
            }

            let markerId = "arrow-normal";
            if (edge.is_optimal) {
                markerId = "arrow-optimal";
            } else if (edge.dashed) {
                markerId = "arrow-unweighted";
            } else if (edge.is_bidirectional_equal) {
                markerId = "arrow-bi";
            }
            pathEl.setAttribute("marker-end", `url(#${markerId})`);
            this.edgesLayer.appendChild(pathEl);
        }

        // Dibujar etiquetas de peso sobre las aristas
        for (const lbl of graphPayload.weight_labels || []) {
            const group = document.createElementNS(svgNS, "g");
            const textStr = String(lbl.text);
            const boxW = Math.max(34, textStr.length * 10.5 + 18) * pillScale;
            const boxH = 26 * pillScale;

            const rect = document.createElementNS(svgNS, "rect");
            rect.setAttribute("x", (lbl.x - boxW / 2).toFixed(2));
            rect.setAttribute("y", (lbl.y - boxH / 2).toFixed(2));
            rect.setAttribute("width", boxW.toFixed(2));
            rect.setAttribute("height", boxH.toFixed(2));
            rect.setAttribute("rx", (6 * pillScale).toFixed(2));
            rect.setAttribute("ry", (6 * pillScale).toFixed(2));
            rect.setAttribute("fill", "#161b22");
            rect.setAttribute("fill-opacity", "0.96");
            rect.setAttribute("stroke", lbl.border_color || "#30363d");
            rect.setAttribute("stroke-width", (1.2 * strokeScale).toFixed(2));

            const text = document.createElementNS(svgNS, "text");
            text.setAttribute("x", lbl.x.toFixed(2));
            text.setAttribute("y", lbl.y.toFixed(2));
            text.setAttribute("text-anchor", "middle");
            text.setAttribute("dominant-baseline", "central");
            text.setAttribute("fill", "#e6edf3");
            text.setAttribute("font-family", "Segoe UI, sans-serif");
            text.setAttribute("font-size", `${(14.5 * pillScale).toFixed(1)}px`);
            text.setAttribute("font-weight", "600");
            text.textContent = textStr;

            group.appendChild(rect);
            group.appendChild(text);
            this.labelsLayer.appendChild(group);
        }

        // Dibujar nodos interactivos
        for (const node of graphPayload.nodes || []) {
            const group = document.createElementNS(svgNS, "g");
            group.setAttribute("class", "svg-node-group");
            group.dataset.nodeId = node.id;

            const scaledRadius = (node.r * scaleFactor).toFixed(2);
            const scaledFont = (node.font_size * scaleFactor).toFixed(1);

            const circle = document.createElementNS(svgNS, "circle");
            circle.setAttribute("cx", node.x.toFixed(2));
            circle.setAttribute("cy", node.y.toFixed(2));
            circle.setAttribute("r", scaledRadius);
            circle.setAttribute("fill", node.fill);
            circle.setAttribute("stroke", node.stroke);
            circle.setAttribute(
                "stroke-width",
                (node.stroke_width * strokeScale).toFixed(2)
            );

            const label = document.createElementNS(svgNS, "text");
            label.setAttribute("x", node.x.toFixed(2));
            label.setAttribute("y", node.y.toFixed(2));
            label.setAttribute("text-anchor", "middle");
            label.setAttribute("dominant-baseline", "central");
            label.setAttribute("fill", "#e6edf3");
            label.setAttribute("font-family", "Segoe UI, sans-serif");
            label.setAttribute("font-size", `${scaledFont}px`);
            label.setAttribute("font-weight", "700");
            label.style.pointerEvents = "none";
            label.textContent = node.id;

            group.appendChild(circle);
            group.appendChild(label);

            group.addEventListener("click", (e) => {
                if (this.activeTool) {
                    return;
                }
                e.stopPropagation();
                if (typeof this.onNodeClick === "function") {
                    this.onNodeClick(node.id);
                }
            });

            this.nodesLayer.appendChild(group);
        }
    }

    /**
     * Genera una cadena SVG autónoma (con fondo oscuro #0d1117 incluido) lista para exportar.
     */
    buildStandaloneSvgString() {
        const clone = this.svg.cloneNode(true);
        const zoomRectClone = clone.querySelector("#zoom-selection-rect");
        if (zoomRectClone) {
            zoomRectClone.remove();
        }
        const bgRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        bgRect.setAttribute("x", this.currentBox.x);
        bgRect.setAttribute("y", this.currentBox.y);
        bgRect.setAttribute("width", this.currentBox.w);
        bgRect.setAttribute("height", this.currentBox.h);
        bgRect.setAttribute("fill", "#0d1117");
        clone.insertBefore(bgRect, clone.firstChild);
        clone.setAttribute("width", "1600");
        clone.setAttribute("height", "1000");
        return new XMLSerializer().serializeToString(clone);
    }

    /**
     * Convierte el SVG actual en una imagen PNG en base64 utilizando un Canvas HTML5.
     */
    buildPngDataUrl() {
        return new Promise((resolve, reject) => {
            const svgString = this.buildStandaloneSvgString();
            const svgBlob = new Blob([svgString], {
                type: "image/svg+xml;charset=utf-8",
            });
            const url = URL.createObjectURL(svgBlob);
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement("canvas");
                canvas.width = 1600;
                canvas.height = 1000;
                const ctx = canvas.getContext("2d");
                ctx.fillStyle = "#0d1117";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                URL.revokeObjectURL(url);
                resolve(canvas.toDataURL("image/png"));
            };
            img.onerror = (err) => {
                URL.revokeObjectURL(url);
                reject(err);
            };
            img.src = url;
        });
    }
}
