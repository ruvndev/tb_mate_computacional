/**
 * Renderizador de los paneles laterales de Dijkstra:
 * - Cuadro de RESULTADO FINAL (arriba del panel de etiquetas cuando finaliza el algoritmo)
 * - Pestaña Etiquetas actuales (con bloques codificados por color y guía de colores)
 * - Pestaña Historial (con etiquetas reemplazadas tachadas)
 * - Pestaña Decisiones (con registro detallado de iteraciones y comparaciones)
 */

class PanelsRenderer {
    constructor() {
        this.resultCard = document.getElementById("result-card");
        this.resultTitle = document.getElementById("result-title");
        this.resultEndpoints = document.getElementById("result-endpoints-badge");
        this.resultDistBadge = document.getElementById("result-distance-badge");
        this.resultCountBadge = document.getElementById("result-count-badge");
        this.resultPathsBox = document.getElementById("result-paths-container");

        this.tabCurrentLabels = document.getElementById("tab-current-labels");
        this.tabHistory = document.getElementById("tab-history");
        this.tabDecisions = document.getElementById("tab-decisions");
    }

    /**
     * Actualiza todos los paneles laterales según los datos estructurados del motor Dijkstra.
     */
    render(panelsData, isManualBuildMode = false) {
        if (!panelsData || !panelsData.initialized || isManualBuildMode) {
            this.hideResultCard();
            this._renderEmptyState();
            return;
        }

        this._renderCurrentLabels(panelsData.current_labels || []);
        this._renderHistory(panelsData.history || []);
        this._renderDecisions(panelsData.decisions || []);

        if (panelsData.algorithm_finished && panelsData.result) {
            this._renderResultCard(panelsData.result);
        } else {
            this.hideResultCard();
        }
    }

    hideResultCard() {
        if (this.resultCard) {
            this.resultCard.classList.add("hidden");
        }
    }

    _renderEmptyState() {
        if (this.tabCurrentLabels) {
            this.tabCurrentLabels.innerHTML = `
                <div class="panel-empty-msg">
                    Genere el grafo, seleccione el origen y el destino, e inicialice Dijkstra.
                </div>
            `;
        }
        if (this.tabHistory) {
            this.tabHistory.innerHTML = `
                <div class="panel-empty-msg">
                    El historial se mostrará cuando se inicialice Dijkstra.
                </div>
            `;
        }
        if (this.tabDecisions) {
            this.tabDecisions.innerHTML = `
                <div class="panel-empty-msg">
                    El registro de decisiones aparecerá al inicializar el algoritmo.
                </div>
            `;
        }
    }

    _renderResultCard(result) {
        if (!this.resultCard) {
            return;
        }
        this.resultCard.classList.remove("hidden");
        this.resultEndpoints.textContent = `Origen: ${result.source}  →  Destino: ${result.target}`;
        this.resultPathsBox.innerHTML = "";

        if (result.reachable) {
            this.resultCard.classList.remove("unreachable");
            this.resultTitle.textContent =
                "★ RESULTADO FINAL — CAMINOS MÍNIMOS HALLADOS";
            this.resultDistBadge.className = "result-stat-pill stat-green";
            this.resultDistBadge.textContent = `Distancia mínima: ${result.distance}`;
            this.resultCountBadge.className = "result-stat-pill stat-blue";
            this.resultCountBadge.textContent = `Caminos mínimos: ${result.path_count}`;

            (result.paths || []).forEach((routeText, idx) => {
                const line = document.createElement("div");
                line.className = "path-route-line";
                line.textContent = `Camino ${idx + 1}   ${routeText}`;
                this.resultPathsBox.appendChild(line);
            });
        } else {
            this.resultCard.classList.add("unreachable");
            this.resultTitle.textContent =
                "✕ RESULTADO FINAL — DESTINO INALCANZABLE";
            this.resultDistBadge.className = "result-stat-pill stat-red";
            this.resultDistBadge.textContent = "Distancia mínima: ∞";
            this.resultCountBadge.className = "result-stat-pill stat-red";
            this.resultCountBadge.textContent = "Caminos mínimos: 0";

            const msg = document.createElement("div");
            msg.className = "path-unreachable-msg";
            msg.textContent = `No existe un camino dirigido desde ${result.source} hasta ${result.target}.`;
            this.resultPathsBox.appendChild(msg);
        }
    }

    _renderCurrentLabels(labelsList) {
        if (!this.tabCurrentLabels) {
            return;
        }
        this.tabCurrentLabels.innerHTML = "";

        const hdr = document.createElement("div");
        hdr.className = "panel-section-header";
        hdr.textContent =
            "ETIQUETAS ACTUALES POR VÉRTICE\n================================";
        this.tabCurrentLabels.appendChild(hdr);

        let activeElement = null;

        for (const item of labelsList) {
            const block = document.createElement("div");
            block.className = `label-block ${item.block_tag}`;
            block.innerHTML = `
                <div>${this._escapeHtml(item.badge)} ${this._escapeHtml(item.node)} &nbsp;${this._escapeHtml(item.label_str)}</div>
                <div>&nbsp;&nbsp;&nbsp;Estado: ${this._escapeHtml(item.status)}</div>
            `;
            if (item.is_current) {
                activeElement = block;
            }
            this.tabCurrentLabels.appendChild(block);
        }

        // Guía de colores intuitiva al final del panel
        const guideBox = document.createElement("div");
        guideBox.className = "color-guide-box";
        guideBox.innerHTML = `
            <div class="panel-section-header">GUÍA DE COLORES\n===============</div>
            <div class="color-guide-item current_block">▶ Amarillo : Vértice actual en evaluación</div>
            <div class="color-guide-item updated_now_block">✦ Azul     : Etiqueta mejorada en este paso</div>
            <div class="color-guide-item tie_now_block">≡ Turquesa : Empate en distancia mínima (nuevo predecesor)</div>
            <div class="color-guide-item source_block">● Verde    : Vértice de origen</div>
            <div class="color-guide-item processed_block">✓ Celeste  : Vértice ya procesado</div>
            <div class="color-guide-item reachable_pending_block">◆ Violeta  : Vértice alcanzado pendiente</div>
            <div class="color-guide-item target_reached_block">★ Naranja  : Destino alcanzado</div>
        `;
        this.tabCurrentLabels.appendChild(guideBox);

        if (activeElement) {
            activeElement.scrollIntoView({ behavior: "smooth", block: "nearest" });
        } else {
            this.tabCurrentLabels.scrollTop = 0;
        }
    }

    _renderHistory(historyList) {
        if (!this.tabHistory) {
            return;
        }
        this.tabHistory.innerHTML = "";

        const hdr = document.createElement("div");
        hdr.className = "panel-section-header";
        hdr.textContent = "HISTORIAL DE ETIQUETAS\n=====================";
        this.tabHistory.appendChild(hdr);

        for (const nodeItem of historyList) {
            const group = document.createElement("div");
            group.className = "history-node-group";

            const title = document.createElement("div");
            title.className = `history-node-title ${nodeItem.is_current ? "current" : ""}`;
            title.textContent = `Vértice ${nodeItem.node}`;
            group.appendChild(title);

            if (!nodeItem.entries || nodeItem.entries.length === 0) {
                const emptyLine = document.createElement("div");
                emptyLine.className = "history-entry inf_muted";
                emptyLine.textContent = "  [∞, -]_0 (sin distancia finita registrada)";
                group.appendChild(emptyLine);
            } else {
                for (const entry of nodeItem.entries) {
                    const row = document.createElement("div");
                    row.className = `history-entry ${entry.tag}`;
                    if (entry.crossed) {
                        row.innerHTML = `&nbsp;&nbsp;<span class="lbl-strike">${this._escapeHtml(entry.base_label)}</span> ${this._escapeHtml(entry.suffix)}`;
                    } else {
                        row.innerHTML = `&nbsp;&nbsp;${this._escapeHtml(entry.base_label)} ${this._escapeHtml(entry.suffix)}`;
                    }
                    group.appendChild(row);
                }
            }

            this.tabHistory.appendChild(group);
        }
    }

    _renderDecisions(decisionsList) {
        if (!this.tabDecisions) {
            return;
        }
        this.tabDecisions.innerHTML = "";

        const hdr = document.createElement("div");
        hdr.className = "panel-section-header";
        hdr.textContent =
            "REGISTRO DE DECISIONES DEL ALGORITMO\n====================================";
        this.tabDecisions.appendChild(hdr);

        if (!decisionsList || decisionsList.length === 0) {
            const empty = document.createElement("div");
            empty.className = "panel-empty-msg";
            empty.textContent =
                "Todavía no hay decisiones registradas. Inicialice Dijkstra para comenzar.";
            this.tabDecisions.appendChild(empty);
            return;
        }

        for (const dec of decisionsList) {
            const card = document.createElement("div");
            card.className = "decision-card-item";

            const header = document.createElement("div");
            header.className = `decision-header ${dec.is_latest ? "latest" : "past"}`;
            header.textContent = dec.header;
            card.appendChild(header);

            for (const lineObj of dec.lines || []) {
                const lineEl = document.createElement("div");
                lineEl.className = `decision-line ${lineObj.tag}`;
                lineEl.textContent = lineObj.text;
                card.appendChild(lineEl);
            }

            this.tabDecisions.appendChild(card);
        }

        this.tabDecisions.scrollTop = this.tabDecisions.scrollHeight;
    }

    _escapeHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }
}
