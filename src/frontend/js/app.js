/**
 * Controlador principal de la aplicación frontend.
 * Coordina los eventos de la interfaz, el modo de construcción/edición manual
 * de grafos, las ventanas modales y las llamadas asíncronas a `window.pywebview.api`.
 */

class DijkstraDesktopApp {
    constructor() {
        this.manualBuildMode = false;
        this.isManualGraph = false;
        this.manualConnections = [];
        this.manualFirstNode = null;
        this.manualHighlightedNodes = [];
        this.currentNodes = [];

        this.graphRenderer = new GraphRenderer(
            document.getElementById("graph-svg"),
            document.getElementById("graph-viewport"),
            (nodeId) => this.handleGraphNodeClick(nodeId)
        );
        this.panelsRenderer = new PanelsRenderer();

        this._cacheDomElements();
        this._bindUiEvents();
    }

    _cacheDomElements() {
        this.inputNodeCount = document.getElementById("input-node-count");
        this.selectGraphMode = document.getElementById("select-graph-mode");
        this.btnGenerateGraph = document.getElementById("btn-generate-graph");
        this.randomOptionsGroup = document.getElementById("random-options-group");
        this.chkRandomBi = document.getElementById("chk-random-bidirectional");
        this.chkRandomCycles = document.getElementById("chk-random-cycles");

        this.btnEditManualTop = document.getElementById("btn-edit-manual-top");
        this.btnEditManualPanel = document.getElementById("btn-edit-manual-panel");

        this.selectSource = document.getElementById("select-source-node");
        this.selectTarget = document.getElementById("select-target-node");
        this.btnInitDijkstra = document.getElementById("btn-init-dijkstra");
        this.btnNextStep = document.getElementById("btn-next-step");
        this.btnRunAll = document.getElementById("btn-run-all");

        this.dijkstraCard = document.getElementById("dijkstra-card");
        this.manualCard = document.getElementById("manual-card");
        this.manualInstruction = document.getElementById("manual-instruction-banner");
        this.manualSelectN1 = document.getElementById("manual-select-n1");
        this.manualSelectN2 = document.getElementById("manual-select-n2");
        this.manualInputWeight = document.getElementById("manual-input-weight");
        this.manualChkBi = document.getElementById("manual-chk-bi");
        this.btnAddManualForm = document.getElementById("btn-add-manual-form");
        this.manualConnectionsContainer = document.getElementById(
            "manual-connections-container"
        );
        this.btnConfirmManual = document.getElementById("btn-confirm-manual");

        this.statusBarText = document.getElementById("status-bar-text");

        this.btnProjectInfo = document.getElementById("btn-project-info");
        this.btnSystemGuide = document.getElementById("btn-system-guide");
        this.btnExportPng = document.getElementById("btn-export-png");
        this.btnExportSvg = document.getElementById("btn-export-svg");

        // Elementos del modal de diálogo (alertas y confirmaciones)
        this.modalDialog = document.getElementById("modal-dialog");
        this.dialogTitle = document.getElementById("dialog-title");
        this.dialogMessage = document.getElementById("dialog-message");
        this.btnDialogCancel = document.getElementById("btn-dialog-cancel");
        this.btnDialogConfirm = document.getElementById("btn-dialog-confirm");
    }

    _bindUiEvents() {
        // Alternar visibilidad de casillas Bidireccional / Ciclos según el modo seleccionado
        this.selectGraphMode.addEventListener("change", () => {
            this._updateModeControlsVisibility();
        });

        // Generar grafo (Aleatorio o Manual)
        this.btnGenerateGraph.addEventListener("click", () => {
            this.handleGenerateGraph();
        });

        // Modificar grafo manual confirmado
        this.btnEditManualTop.addEventListener("click", () => {
            this.handleEditManualGraph();
        });
        this.btnEditManualPanel.addEventListener("click", () => {
            this.handleEditManualGraph();
        });

        // Controles de ejecución de Dijkstra
        this.btnInitDijkstra.addEventListener("click", () => {
            this.handleInitializeDijkstra();
        });
        this.btnNextStep.addEventListener("click", () => {
            this.handleNextStepDijkstra();
        });
        this.btnRunAll.addEventListener("click", () => {
            this.handleCompleteDijkstra();
        });

        // Formulario convencional dentro del modo manual
        this.btnAddManualForm.addEventListener("click", () => {
            this.handleAddManualFromForm();
        });
        this.manualInputWeight.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                this.handleAddManualFromForm();
            }
        });

        // Confirmar grafo manual
        this.btnConfirmManual.addEventListener("click", () => {
            this.handleConfirmManualGraph();
        });

        // Pestañas del panel de Dijkstra
        document.querySelectorAll("#dijkstra-card .tab-btn").forEach((btn) => {
            btn.addEventListener("click", () => {
                const targetId = btn.dataset.tab;
                document
                    .querySelectorAll("#dijkstra-card .tab-btn")
                    .forEach((b) => {
                        b.classList.toggle("active", b === btn);
                        b.setAttribute("aria-selected", b === btn ? "true" : "false");
                    });
                document
                    .querySelectorAll("#dijkstra-card .tab-pane")
                    .forEach((pane) => {
                        pane.classList.toggle("active", pane.id === targetId);
                    });
            });
        });

        // Pestañas del modal Guía del sistema
        document.querySelectorAll("[data-guide-tab]").forEach((btn) => {
            btn.addEventListener("click", () => {
                const targetId = btn.dataset.guideTab;
                document
                    .querySelectorAll("[data-guide-tab]")
                    .forEach((b) => b.classList.toggle("active", b === btn));
                document
                    .querySelectorAll(".guide-pane")
                    .forEach((pane) =>
                        pane.classList.toggle("active", pane.id === targetId)
                    );
            });
        });

        // Abrir / cerrar modales de información y guía
        this.btnProjectInfo.addEventListener("click", () => {
            document
                .getElementById("modal-project-info")
                .classList.remove("hidden");
        });
        this.btnSystemGuide.addEventListener("click", () => {
            document
                .getElementById("modal-system-guide")
                .classList.remove("hidden");
        });

        document.querySelectorAll("[data-close-modal]").forEach((btn) => {
            btn.addEventListener("click", () => {
                const modalId = btn.dataset.closeModal;
                document.getElementById(modalId).classList.add("hidden");
            });
        });

        // Exportación de imagen PNG / vector SVG
        this.btnExportPng.addEventListener("click", () => this.exportGraph("png"));
        this.btnExportSvg.addEventListener("click", () => this.exportGraph("svg"));
    }

    /**
     * Inicializa la aplicación consultando el estado inicial al backend en Python.
     */
    async initialize() {
        try {
            const response = await window.pywebview.api.get_initial_state();
            if (response.project_info) {
                this._populateProjectInfoModal(response.project_info);
            }
            this.applyBackendState(response, true, true);
        } catch (err) {
            console.error("Error al obtener estado inicial:", err);
            this.setStatus("Error al conectar con el núcleo en Python.");
        }
    }

    _populateProjectInfoModal(info) {
        const subtitle = document.getElementById("info-theme-subtitle");
        const desc = document.getElementById("info-description");
        const grid = document.getElementById("info-academic-grid");
        const list = document.getElementById("info-integrants-list");

        if (subtitle) subtitle.textContent = info.theme || "";
        if (desc) desc.textContent = info.description || "";

        if (grid) {
            const fields = [
                ["Curso:", info.course],
                ["Tema:", info.theme],
                ["Entrega:", info.delivery],
                ["Grupo:", info.group],
            ];
            grid.innerHTML = fields
                .map(
                    ([label, val]) => `
                    <div class="info-field-label">${label}</div>
                    <div class="info-field-value">${val || ""}</div>
                `
                )
                .join("");
        }

        if (list && Array.isArray(info.integrants)) {
            list.innerHTML = info.integrants
                .map((name) => `<li>${name}</li>`)
                .join("");
        }
    }

    /**
     * Aplica la respuesta completa del backend a todos los componentes de la interfaz.
     */
    applyBackendState(
        response,
        resetSelectors = false,
        resetZoom = false
    ) {
        if (!response) {
            return;
        }

        if (!response.ok && response.error) {
            this.showAlert("Aviso de validación", response.error);
            if (response.status_message) {
                this.setStatus(response.status_message);
            }
            return;
        }

        this.manualBuildMode = Boolean(response.manual_build_mode);
        this.isManualGraph = Boolean(response.is_manual_graph);

        if (Array.isArray(response.manual_connections)) {
            this.manualConnections = response.manual_connections.map((c) => ({
                u: String(c.u),
                v: String(c.v),
                weight: String(c.weight ?? ""),
                bidirectional: Boolean(c.bidirectional),
            }));
        }

        const nodes = (response.graph && response.graph.node_list) || [];
        const nodesChanged =
            nodes.length !== this.currentNodes.length ||
            nodes.some((n, i) => n !== this.currentNodes[i]);
        this.currentNodes = nodes;

        if (resetSelectors || nodesChanged) {
            this._populateNodeSelectors(nodes);
        }

        this._updateModeControlsVisibility();

        if (this.manualBuildMode) {
            this.panelsRenderer.hideResultCard();
            this.dijkstraCard.classList.add("hidden");
            this.manualCard.classList.remove("hidden");
            this._renderManualConnectionsList();
        } else {
            this.manualCard.classList.add("hidden");
            this.dijkstraCard.classList.remove("hidden");
            this.panelsRenderer.render(response.panels, false);
        }

        if (resetZoom) {
            this.graphRenderer.resetView(false);
        }
        this.graphRenderer.render(response.graph);

        if (response.status_message) {
            this.setStatus(response.status_message);
        }
    }

    _updateModeControlsVisibility() {
        const isRandomSelected = this.selectGraphMode.value === "Aleatorio";
        this.randomOptionsGroup.classList.toggle("hidden", !isRandomSelected);

        const canEditManual = this.isManualGraph && !this.manualBuildMode;
        this.btnEditManualTop.classList.toggle("hidden", !canEditManual);
        this.btnEditManualPanel.classList.toggle("hidden", !canEditManual);
    }

    _populateNodeSelectors(nodes) {
        const buildOptions = (arr) =>
            arr.map((n) => `<option value="${n}">${n}</option>`).join("");

        const htmlOptions = buildOptions(nodes);
        this.selectSource.innerHTML = htmlOptions;
        this.selectTarget.innerHTML = htmlOptions;
        this.manualSelectN1.innerHTML = htmlOptions;
        this.manualSelectN2.innerHTML = htmlOptions;

        if (nodes.length > 0) {
            this.selectSource.value = nodes[0];
            this.selectTarget.value = nodes[nodes.length - 1];
            this.manualSelectN1.value = nodes[0];
            this.manualSelectN2.value = nodes.length > 1 ? nodes[1] : nodes[0];
        }
    }

    setStatus(text) {
        if (this.statusBarText) {
            this.statusBarText.textContent = text;
        }
    }

    // =========================================================================
    // ACCIONES DE GENERACIÓN Y DIJKSTRA
    // =========================================================================

    async handleGenerateGraph() {
        const rawCount = parseInt(this.inputNodeCount.value, 10);
        if (isNaN(rawCount) || rawCount < 7 || rawCount > 16) {
            await this.showAlert(
                "Cantidad inválida",
                "El número de nodos debe ser un entero entre 7 y 16."
            );
            return;
        }

        const mode = this.selectGraphMode.value;
        if (mode === "Aleatorio") {
            const allowBi = this.chkRandomBi.checked;
            const allowCycles = this.chkRandomCycles.checked;
            const resp = await window.pywebview.api.generate_random_graph(
                rawCount,
                allowBi,
                allowCycles
            );
            this.applyBackendState(resp, true, true);
        } else {
            this.manualFirstNode = null;
            this.manualHighlightedNodes = [];
            this.manualInstruction.textContent =
                "Haga clic en el primer nodo en el grafo (se resaltará en azul), luego en el segundo nodo para crear la conexión.";
            const resp = await window.pywebview.api.start_manual_mode(rawCount);
            this.applyBackendState(resp, true, true);
        }
    }

    async handleEditManualGraph() {
        if (!this.isManualGraph || this.manualBuildMode) {
            return;
        }
        this.selectGraphMode.value = "Manual";
        this.manualFirstNode = null;
        this.manualHighlightedNodes = [];
        this.manualInstruction.textContent =
            "Modo edición: haga clic en los nodos en el grafo o use el cuadro superior para agregar o modificar conexiones.";

        const resp = await window.pywebview.api.edit_manual_graph();
        this.applyBackendState(resp, false, false);
    }

    async handleInitializeDijkstra() {
        if (this.manualBuildMode) {
            await this.showAlert(
                "Modo manual activo",
                "Primero confirme la construcción manual del grafo."
            );
            return;
        }
        const source = this.selectSource.value;
        const target = this.selectTarget.value;
        if (!source || !target) {
            await this.showAlert(
                "Selección incompleta",
                "Seleccione los vértices de origen y destino."
            );
            return;
        }
        if (source === target) {
            await this.showAlert(
                "Selección inválida",
                "El origen y el destino deben ser diferentes."
            );
            return;
        }

        const resp = await window.pywebview.api.initialize_dijkstra(
            source,
            target
        );
        this.applyBackendState(resp, false, false);
    }

    async handleNextStepDijkstra() {
        if (this.manualBuildMode) {
            await this.showAlert(
                "Modo manual activo",
                "Primero confirme la construcción manual del grafo."
            );
            return;
        }
        const resp = await window.pywebview.api.next_step_dijkstra();
        this.applyBackendState(resp, false, false);
    }

    async handleCompleteDijkstra() {
        if (this.manualBuildMode) {
            await this.showAlert(
                "Modo manual activo",
                "Primero confirme la construcción manual del grafo."
            );
            return;
        }
        const resp = await window.pywebview.api.complete_dijkstra();
        this.applyBackendState(resp, false, false);
    }

    // =========================================================================
    // CONSTRUCCIÓN Y EDICIÓN MANUAL INTERACTIVA DEL GRAFO
    // =========================================================================

    async handleGraphNodeClick(clickedNode) {
        if (!this.manualBuildMode) {
            return;
        }

        if (this.manualFirstNode === null) {
            this.manualFirstNode = clickedNode;
            this.manualHighlightedNodes = [clickedNode];
            this.manualInstruction.textContent = `Nodo ${clickedNode} seleccionado. Ahora haga clic en el nodo destino para crear la conexión.`;
            this.setStatus(
                `Nodo ${clickedNode} seleccionado en azul. Haga clic en otro nodo para conectar.`
            );
            await this._syncManualPreview();
            return;
        }

        const u = this.manualFirstNode;
        const v = clickedNode;

        if (u === v) {
            this.manualFirstNode = null;
            this.manualHighlightedNodes = [];
            this.manualInstruction.textContent =
                "Selección cancelada. Haga clic en el primer nodo para iniciar una conexión.";
            this.setStatus(`Selección de ${u} cancelada.`);
            await this._syncManualPreview();
            return;
        }

        this.manualHighlightedNodes = [u, v];
        await this._syncManualPreview();

        // Intentar agregar o volver bidireccional con las mismas validaciones
        await this._processManualConnectionRequest(u, v, "", false, true);

        this.manualFirstNode = null;
        this.manualHighlightedNodes = [];
        this.manualInstruction.textContent =
            "Haga clic en el primer nodo en el grafo (se resaltará en azul), luego en el segundo nodo para crear la conexión.";
        await this._syncManualPreview();
    }

    async handleAddManualFromForm() {
        if (!this.manualBuildMode) {
            return;
        }

        const u = this.manualSelectN1.value.trim();
        const v = this.manualSelectN2.value.trim();
        const weightStr = this.manualInputWeight.value.trim();
        const isBi = this.manualChkBi.checked;

        if (!u || !v) {
            await this.showAlert(
                "Datos incompletos",
                "Seleccione tanto el Nodo 1 como el Nodo 2."
            );
            return;
        }

        if (u === v) {
            await this.showAlert(
                "Conexión inválida",
                "No se permiten conexiones de un nodo a sí mismo. Seleccione dos nodos distintos."
            );
            return;
        }

        if (!weightStr) {
            await this.showAlert(
                "Peso faltante",
                `Ingrese un peso entero positivo para la conexión ${u} → ${v}.`
            );
            this.manualInputWeight.focus();
            return;
        }

        const weightInt = Number(weightStr);
        if (!Number.isInteger(weightInt) || weightInt <= 0) {
            await this.showAlert(
                "Peso inválido",
                `El peso de la conexión ${u} → ${v} debe ser un número entero mayor que 0.`
            );
            this.manualInputWeight.focus();
            return;
        }

        this.manualFirstNode = null;
        this.manualHighlightedNodes = [u, v];
        await this._syncManualPreview();

        const addedOrUpdated = await this._processManualConnectionRequest(
            u,
            v,
            String(weightInt),
            isBi,
            false
        );

        if (addedOrUpdated) {
            this.manualInputWeight.value = "";
            this.manualChkBi.checked = false;
        }

        this.manualHighlightedNodes = [];
        await this._syncManualPreview();
    }

    /**
     * Valida e inserta/actualiza una conexión manual tanto desde clic gráfico como desde el formulario.
     * Detecta conexiones inversas (preguntando si desea volverla bidireccional) y conexiones repetidas.
     */
    async _processManualConnectionRequest(
        u,
        v,
        weightStr,
        isBi,
        fromCanvasClick
    ) {
        const idxSame = this.manualConnections.findIndex(
            (c) =>
                (c.u === u && c.v === v) ||
                (c.u === v && c.v === u && c.bidirectional)
        );
        const idxRev = this.manualConnections.findIndex(
            (c) => c.u === v && c.v === u && !c.bidirectional
        );

        // 1. Si existe la conexión inversa unidireccional v -> u
        if (idxRev !== -1) {
            const revConn = this.manualConnections[idxRev];
            const promptText = fromCanvasClick
                ? `Ya existe la conexión ${v} → ${u}.\n¿Desea volverla bidireccional (${v} ↔ ${u})?`
                : `Ya existe la conexión inversa ${v} → ${u}.\n¿Desea volverla bidireccional (${v} ↔ ${u})${weightStr ? ` con peso ${weightStr}` : ""}?`;

            const makeBi = await this.showConfirm(
                "Conexión inversa detectada",
                promptText
            );
            if (makeBi) {
                revConn.bidirectional = true;
                if (weightStr) {
                    revConn.weight = weightStr;
                }
                this._renderManualConnectionsList();
                this.setStatus(
                    `La conexión ${v} ↔ ${u} ahora es bidireccional.`
                );
                return true;
            }
            return false;
        }

        // 2. Si ya existe la misma conexión u -> v (o bidireccional equivalente)
        if (idxSame !== -1) {
            const existingConn = this.manualConnections[idxSame];
            if (fromCanvasClick) {
                this.setStatus(
                    `La conexión ${existingConn.u} → ${existingConn.v} ya existe en la lista.`
                );
                const inputEl = this.manualConnectionsContainer.querySelector(
                    `[data-conn-idx="${idxSame}"] .conn-weight-input`
                );
                if (inputEl) {
                    inputEl.focus();
                    inputEl.select();
                }
                return false;
            } else {
                const modeDesc = isBi ? "bidireccional" : "unidireccional";
                const overwrite = await this.showConfirm(
                    "Conexión existente",
                    `La conexión entre ${u} y ${v} ya existe.\n¿Desea sobrescribirla con peso ${weightStr} (${modeDesc})?`
                );
                if (overwrite) {
                    existingConn.u = u;
                    existingConn.v = v;
                    existingConn.weight = weightStr;
                    existingConn.bidirectional = isBi;
                    this._renderManualConnectionsList();
                    this.setStatus(
                        `Conexión ${u} ${isBi ? "↔" : "→"} ${v} actualizada con peso ${weightStr}.`
                    );
                    return true;
                }
                return false;
            }
        }

        // 3. Crear nueva conexión
        const defaultWeight = fromCanvasClick ? "10" : weightStr;
        this.manualConnections.push({
            u,
            v,
            weight: defaultWeight,
            bidirectional: isBi,
        });
        this._renderManualConnectionsList();

        const newIdx = this.manualConnections.length - 1;
        if (fromCanvasClick) {
            const inputEl = this.manualConnectionsContainer.querySelector(
                `[data-conn-idx="${newIdx}"] .conn-weight-input`
            );
            if (inputEl) {
                inputEl.focus();
                inputEl.select();
            }
            this.setStatus(
                `Conexión ${u} → ${v} creada. Edite su peso o marque Bidireccional si lo desea.`
            );
        } else {
            this.setStatus(
                `Conexión ${u} ${isBi ? "↔" : "→"} ${v} (peso ${weightStr}) agregada.`
            );
        }
        return true;
    }

    _renderManualConnectionsList() {
        this.manualConnectionsContainer.innerHTML = "";

        if (this.manualConnections.length === 0) {
            this.manualConnectionsContainer.innerHTML = `
                <div class="panel-empty-msg" style="padding: 8px 4px;">
                    Aún no hay conexiones. Haga clic en dos nodos del grafo o utilice el formulario superior.
                </div>
            `;
            return;
        }

        this.manualConnections.forEach((conn, idx) => {
            const row = document.createElement("div");
            row.className = "connection-row";
            row.dataset.connIdx = idx;

            const arrowSymbol = conn.bidirectional ? "↔" : "→";
            const labelSpan = document.createElement("span");
            labelSpan.className = `conn-nodes-label ${conn.bidirectional ? "bi" : ""}`;
            labelSpan.textContent = `${conn.u} ${arrowSymbol} ${conn.v}`;

            const weightInput = document.createElement("input");
            weightInput.type = "number";
            weightInput.min = "1";
            weightInput.value = conn.weight;
            weightInput.placeholder = "Peso";
            weightInput.className = "input-control conn-weight-input";
            weightInput.addEventListener("input", () => {
                conn.weight = weightInput.value.trim();
                this._syncManualPreview();
            });

            const biLabel = document.createElement("label");
            biLabel.className = "checkbox-label";
            const biCheck = document.createElement("input");
            biCheck.type = "checkbox";
            biCheck.checked = Boolean(conn.bidirectional);
            const biText = document.createElement("span");
            biText.textContent = "Bidireccional";
            biLabel.appendChild(biCheck);
            biLabel.appendChild(biText);

            biCheck.addEventListener("change", () => {
                conn.bidirectional = biCheck.checked;
                if (conn.bidirectional) {
                    // Si había una fila inversa separada v -> u, eliminarla al unificar en bidireccional
                    const revIdx = this.manualConnections.findIndex(
                        (other, oIdx) =>
                            oIdx !== idx &&
                            other.u === conn.v &&
                            other.v === conn.u
                    );
                    if (revIdx !== -1) {
                        this.manualConnections.splice(revIdx, 1);
                    }
                }
                this._renderManualConnectionsList();
                this._syncManualPreview();
            });

            const delBtn = document.createElement("button");
            delBtn.className = "btn conn-del-btn";
            delBtn.title = "Eliminar conexión";
            delBtn.textContent = "✕";
            delBtn.addEventListener("click", () => {
                this.manualConnections.splice(idx, 1);
                this._renderManualConnectionsList();
                this._syncManualPreview();
                this.setStatus(`Conexión ${conn.u} → ${conn.v} eliminada.`);
            });

            row.appendChild(labelSpan);
            row.appendChild(weightInput);
            row.appendChild(biLabel);
            row.appendChild(delBtn);

            this.manualConnectionsContainer.appendChild(row);
        });

        this.manualConnectionsContainer.scrollTop =
            this.manualConnectionsContainer.scrollHeight;
    }

    async _syncManualPreview() {
        try {
            const resp = await window.pywebview.api.sync_manual_preview(
                this.manualConnections,
                this.manualHighlightedNodes
            );
            if (resp && resp.ok && resp.graph) {
                this.graphRenderer.render(resp.graph);
            }
        } catch (err) {
            console.error("Error sincronizando vista previa manual:", err);
        }
    }

    async handleConfirmManualGraph() {
        if (!this.manualBuildMode) {
            return;
        }
        const resp = await window.pywebview.api.confirm_manual_graph(
            this.manualConnections
        );
        this.applyBackendState(resp, false, false);
    }

    // =========================================================================
    // EXPORTACIÓN DEL GRÁFICO (PNG / SVG)
    // =========================================================================

    async exportGraph(ext) {
        try {
            let content = "";
            if (ext === "svg") {
                content = this.graphRenderer.buildStandaloneSvgString();
            } else {
                content = await this.graphRenderer.buildPngDataUrl();
            }
            const res = await window.pywebview.api.save_graph_export(
                content,
                ext
            );
            if (res && res.saved) {
                this.setStatus(`Gráfico guardado en: ${res.path}`);
                await this.showAlert(
                    "Gráfico guardado",
                    `El gráfico se guardó correctamente en:\n${res.path}`
                );
            } else if (res && res.error) {
                await this.showAlert("Error al guardar", res.error);
            }
        } catch (err) {
            await this.showAlert(
                "Error de exportación",
                `No se pudo exportar el gráfico: ${err}`
            );
        }
    }

    // =========================================================================
    // DIÁLOGOS PERSONALIZADOS (ALERTA Y CONFIRMACIÓN)
    // =========================================================================

    showAlert(title, message) {
        return new Promise((resolve) => {
            this.dialogTitle.textContent = title;
            this.dialogMessage.textContent = message;
            this.btnDialogCancel.classList.add("hidden");
            this.btnDialogConfirm.textContent = "Aceptar";
            this.modalDialog.classList.remove("hidden");

            const onConfirm = () => {
                cleanup();
                resolve(true);
            };

            const cleanup = () => {
                this.btnDialogConfirm.removeEventListener("click", onConfirm);
                this.modalDialog.classList.add("hidden");
            };

            this.btnDialogConfirm.addEventListener("click", onConfirm);
        });
    }

    showConfirm(title, message) {
        return new Promise((resolve) => {
            this.dialogTitle.textContent = title;
            this.dialogMessage.textContent = message;
            this.btnDialogCancel.classList.remove("hidden");
            this.btnDialogCancel.textContent = "No";
            this.btnDialogConfirm.textContent = "Sí";
            this.modalDialog.classList.remove("hidden");

            const onConfirm = () => {
                cleanup();
                resolve(true);
            };
            const onCancel = () => {
                cleanup();
                resolve(false);
            };

            const cleanup = () => {
                this.btnDialogConfirm.removeEventListener("click", onConfirm);
                this.btnDialogCancel.removeEventListener("click", onCancel);
                this.modalDialog.classList.add("hidden");
            };

            this.btnDialogConfirm.addEventListener("click", onConfirm);
            this.btnDialogCancel.addEventListener("click", onCancel);
        });
    }
}

// Inicializar cuando pywebview esté listo
window.addEventListener("DOMContentLoaded", () => {
    const app = new DijkstraDesktopApp();
    window.dijkstraApp = app;

    if (window.pywebview && window.pywebview.api) {
        app.initialize();
    } else {
        window.addEventListener("pywebviewready", () => {
            app.initialize();
        });
    }
});
