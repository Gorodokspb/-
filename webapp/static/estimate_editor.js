(() => {
    const initialRowsNode = document.getElementById("estimateInitialRows");
    const rowsBody = document.getElementById("estimateRowsBody");
    const emptyState = document.getElementById("estimateEmptyState");
    const filteredEmptyState = document.getElementById("estimateFilteredEmptyState");
    const itemsPayloadInput = document.getElementById("estimateItemsPayload");
    const discountInput = document.getElementById("estimateDiscountInput");
    const sectionCountNode = document.getElementById("estimateSectionCount");
    const itemCountNode = document.getElementById("estimateItemCount");
    const totalSumNode = document.getElementById("estimateTotalSum");
    const discountedSumNode = document.getElementById("estimateDiscountedSum");
    const searchInput = document.getElementById("estimateSearchInput");
    const selectionTitle = document.getElementById("estimateSelectionTitle");
    const selectionMeta = document.getElementById("estimateSelectionMeta");
    const dirtyBadge = document.getElementById("estimateDirtyBadge");
    const form = document.getElementById("estimateEditorForm");
    const addSectionButton = document.getElementById("addSectionButton");
    const addItemButton = document.getElementById("addItemButton");
    const editRowButton = document.getElementById("editRowButton");
    const duplicateRowButton = document.getElementById("duplicateRowButton");
    const moveUpButton = document.getElementById("moveUpButton");
    const moveDownButton = document.getElementById("moveDownButton");
    const clearSelectionButton = document.getElementById("clearSelectionButton");
    const deleteRowButton = document.getElementById("deleteRowButton");
    const filterChips = Array.from(document.querySelectorAll(".estimate-filter-chip"));
    const dialog = document.getElementById("estimateRowDialog");
    const dialogTitle = document.getElementById("estimateDialogTitle");
    const dialogRowType = document.getElementById("dialogRowType");
    const dialogRowName = document.getElementById("dialogRowName");
    const dialogRowUnit = document.getElementById("dialogRowUnit");
    const dialogRowQuantity = document.getElementById("dialogRowQuantity");
    const dialogRowPrice = document.getElementById("dialogRowPrice");
    const dialogRowReference = document.getElementById("dialogRowReference");
    const saveEstimateRow = document.getElementById("saveEstimateRow");
    const cancelEstimateDialog = document.getElementById("cancelEstimateDialog");
    const closeEstimateDialog = document.getElementById("closeEstimateDialog");
    const itemFields = Array.from(document.querySelectorAll(".dialog-item-field"));

    if (!initialRowsNode || !rowsBody || !itemsPayloadInput || !form) {
        return;
    }

    function parseNumber(value) {
        const normalized = String(value || "").trim().replace(/\s+/g, "").replace(",", ".");
        if (!normalized) {
            return 0;
        }
        const parsed = Number(normalized);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function formatNumber(value) {
        const rounded = Math.round((Number(value || 0) + Number.EPSILON) * 100) / 100;
        if (Math.abs(rounded - Math.round(rounded)) < 1e-9) {
            return String(Math.round(rounded));
        }
        return rounded.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
    }

    function normalizeText(value) {
        return String(value || "").toLowerCase().replace(/\s+/g, " ").trim();
    }

    function currentDiscount() {
        return parseNumber(discountInput ? discountInput.value : 0);
    }

    function cloneRow(row) {
        return JSON.parse(JSON.stringify(row));
    }

    function normalizeRow(row) {
        const rowType = row && row.row_type === "section" ? "section" : "item";
        if (rowType === "section") {
            return {
                row_type: "section",
                name: String((row && row.name) || "").trim() || "Новый раздел",
                unit: "",
                quantity: "",
                price: "",
                total: "",
                discounted_total: "",
                reference: "",
            };
        }

        const quantity = parseNumber(row && row.quantity);
        const price = parseNumber(row && row.price);
        const total = quantity * price;
        const discountedTotal = total * Math.max(0, 1 - currentDiscount() / 100);
        return {
            row_type: "item",
            name: String((row && row.name) || "").trim(),
            unit: String((row && row.unit) || "").trim(),
            quantity: quantity ? formatNumber(quantity) : "",
            price: price ? formatNumber(price) : "",
            total: total ? formatNumber(total) : "",
            discounted_total: discountedTotal ? formatNumber(discountedTotal) : "",
            reference: String((row && row.reference) || "").trim(),
        };
    }

    let rows;
    try {
        rows = JSON.parse(initialRowsNode.textContent || "[]");
    } catch {
        rows = [];
    }

    rows = Array.isArray(rows) ? rows.map(normalizeRow) : [];

    let selectedIndex = -1;
    let editingIndex = -1;
    let activeFilter = "all";
    let isDirty = false;

    function setDirtyState(value) {
        isDirty = Boolean(value);
        if (dirtyBadge) {
            dirtyBadge.hidden = !isDirty;
        }
    }

    function syncDialogFieldVisibility() {
        const isSection = dialogRowType.value === "section";
        itemFields.forEach((field) => {
            field.classList.toggle("dialog-hidden", isSection);
        });
    }

    function closeDialog() {
        editingIndex = -1;
        if (dialog.open) {
            dialog.close();
        }
    }

    function openDialog(mode, rowType, index = -1) {
        editingIndex = index;
        const existing = index >= 0 ? rows[index] : null;
        dialogTitle.textContent = mode === "edit" ? "Редактирование строки" : "Новая строка";
        dialogRowType.value = existing ? existing.row_type : rowType;
        dialogRowName.value = existing ? existing.name : "";
        dialogRowUnit.value = existing ? existing.unit : "";
        dialogRowQuantity.value = existing ? existing.quantity : "";
        dialogRowPrice.value = existing ? existing.price : "";
        dialogRowReference.value = existing ? existing.reference : "";
        syncDialogFieldVisibility();
        if (typeof dialog.showModal === "function") {
            dialog.showModal();
        } else {
            dialog.setAttribute("open", "open");
        }
        setTimeout(() => dialogRowName.focus(), 0);
    }

    function recalcRows() {
        rows = rows.map(normalizeRow);
    }

    function selectedRow() {
        if (selectedIndex < 0 || selectedIndex >= rows.length) {
            return null;
        }
        return rows[selectedIndex];
    }

    function selectedRowOrAlert() {
        const row = selectedRow();
        if (!row) {
            window.alert("Сначала выберите строку в таблице.");
            return null;
        }
        return row;
    }

    function updateSelectionSummary() {
        const row = selectedRow();
        if (!row) {
            selectionTitle.textContent = "Ничего не выбрано";
            selectionMeta.textContent = "Выберите строку в таблице или добавьте новую.";
            return;
        }

        if (row.row_type === "section") {
            selectionTitle.textContent = row.name || "Раздел";
            selectionMeta.textContent = `Раздел. Можно редактировать, дублировать или менять порядок.`;
            return;
        }

        const parts = [];
        if (row.unit) {
            parts.push(`ед.: ${row.unit}`);
        }
        if (row.quantity) {
            parts.push(`кол-во: ${row.quantity}`);
        }
        if (row.price) {
            parts.push(`цена: ${row.price}`);
        }
        selectionTitle.textContent = row.name || "Позиция";
        selectionMeta.textContent = parts.length ? parts.join(" | ") : "Позиция без заполненных числовых полей.";
    }

    function updateActionButtons() {
        const hasSelection = Boolean(selectedRow());
        const isFirst = selectedIndex <= 0;
        const isLast = selectedIndex < 0 || selectedIndex >= rows.length - 1;

        [editRowButton, duplicateRowButton, moveUpButton, moveDownButton, clearSelectionButton, deleteRowButton]
            .forEach((button) => {
                if (button) {
                    button.disabled = !hasSelection;
                }
            });

        if (moveUpButton) {
            moveUpButton.disabled = !hasSelection || isFirst;
        }
        if (moveDownButton) {
            moveDownButton.disabled = !hasSelection || isLast;
        }
    }

    function rowMatchesFilters(row) {
        const query = normalizeText(searchInput ? searchInput.value : "");
        const haystack = normalizeText([
            row.row_type === "section" ? "раздел" : "позиция",
            row.name,
            row.unit,
            row.reference,
            row.quantity,
            row.price,
        ].join(" "));

        const matchesText = !query || haystack.includes(query);
        const matchesType = activeFilter === "all" || row.row_type === activeFilter;
        return matchesText && matchesType;
    }

    function renderRows() {
        recalcRows();
        rowsBody.innerHTML = "";
        let sectionCount = 0;
        let itemCount = 0;
        let totalSum = 0;
        let discountedSum = 0;
        let visibleRows = 0;

        rows.forEach((row, index) => {
            if (row.row_type === "section") {
                sectionCount += 1;
            } else {
                itemCount += 1;
                totalSum += parseNumber(row.total);
                discountedSum += parseNumber(row.discounted_total);
            }

            const visible = rowMatchesFilters(row);
            if (!visible) {
                return;
            }
            visibleRows += 1;

            const tr = document.createElement("tr");
            tr.dataset.index = String(index);
            tr.classList.toggle("estimate-row-selected", index === selectedIndex);
            tr.classList.toggle("estimate-row-section", row.row_type === "section");
            tr.addEventListener("click", () => {
                selectedIndex = index;
                renderRows();
            });
            tr.addEventListener("dblclick", () => {
                selectedIndex = index;
                openDialog("edit", row.row_type, index);
            });

            const typeCell = document.createElement("td");
            typeCell.className = "estimate-row-type";
            typeCell.textContent = row.row_type === "section" ? "Раздел" : "Позиция";
            tr.appendChild(typeCell);

            const nameCell = document.createElement("td");
            nameCell.className = "estimate-row-name";
            nameCell.textContent = row.name || "—";
            tr.appendChild(nameCell);

            const unitCell = document.createElement("td");
            unitCell.className = row.row_type === "section" ? "estimate-row-muted" : "";
            unitCell.textContent = row.row_type === "section" ? "—" : (row.unit || "—");
            tr.appendChild(unitCell);

            const quantityCell = document.createElement("td");
            quantityCell.className = row.row_type === "section" ? "estimate-row-muted" : "";
            quantityCell.textContent = row.row_type === "section" ? "—" : (row.quantity || "0");
            tr.appendChild(quantityCell);

            const priceCell = document.createElement("td");
            priceCell.className = row.row_type === "section" ? "estimate-row-muted" : "";
            priceCell.textContent = row.row_type === "section" ? "—" : (row.price || "0");
            tr.appendChild(priceCell);

            const totalCell = document.createElement("td");
            totalCell.className = row.row_type === "section" ? "estimate-row-muted" : "";
            totalCell.textContent = row.row_type === "section" ? "—" : (row.total || "0");
            tr.appendChild(totalCell);

            const discountedCell = document.createElement("td");
            discountedCell.className = row.row_type === "section" ? "estimate-row-muted" : "";
            discountedCell.textContent = row.row_type === "section" ? "—" : (row.discounted_total || "0");
            tr.appendChild(discountedCell);

            rowsBody.appendChild(tr);
        });

        itemsPayloadInput.value = JSON.stringify(rows);
        emptyState.hidden = rows.length !== 0;
        filteredEmptyState.hidden = rows.length === 0 || visibleRows !== 0;
        sectionCountNode.textContent = String(sectionCount);
        itemCountNode.textContent = String(itemCount);
        totalSumNode.textContent = formatNumber(totalSum);
        discountedSumNode.textContent = formatNumber(discountedSum);
        updateSelectionSummary();
        updateActionButtons();
    }

    function moveSelectedRow(direction) {
        const row = selectedRowOrAlert();
        if (!row) {
            return;
        }
        const targetIndex = selectedIndex + direction;
        if (targetIndex < 0 || targetIndex >= rows.length) {
            return;
        }
        const [current] = rows.splice(selectedIndex, 1);
        rows.splice(targetIndex, 0, current);
        selectedIndex = targetIndex;
        setDirtyState(true);
        renderRows();
    }

    function duplicateSelectedRow() {
        const row = selectedRowOrAlert();
        if (!row) {
            return;
        }
        const duplicate = cloneRow(row);
        if (duplicate.row_type === "section") {
            duplicate.name = `${duplicate.name} (копия)`;
        } else {
            duplicate.name = `${duplicate.name} (копия)`;
        }
        rows.splice(selectedIndex + 1, 0, duplicate);
        selectedIndex += 1;
        setDirtyState(true);
        renderRows();
    }

    function clearSelection() {
        selectedIndex = -1;
        renderRows();
    }

    addSectionButton?.addEventListener("click", () => openDialog("create", "section"));
    addItemButton?.addEventListener("click", () => openDialog("create", "item"));

    editRowButton?.addEventListener("click", () => {
        const row = selectedRowOrAlert();
        if (!row) {
            return;
        }
        openDialog("edit", row.row_type, selectedIndex);
    });

    duplicateRowButton?.addEventListener("click", duplicateSelectedRow);
    moveUpButton?.addEventListener("click", () => moveSelectedRow(-1));
    moveDownButton?.addEventListener("click", () => moveSelectedRow(1));
    clearSelectionButton?.addEventListener("click", clearSelection);

    deleteRowButton?.addEventListener("click", () => {
        const row = selectedRowOrAlert();
        if (!row) {
            return;
        }
        const label = row.row_type === "section" ? "раздел" : "позицию";
        if (!window.confirm(`Удалить выбранную ${label}?`)) {
            return;
        }
        rows.splice(selectedIndex, 1);
        selectedIndex = -1;
        setDirtyState(true);
        renderRows();
    });

    filterChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            activeFilter = chip.dataset.filter || "all";
            filterChips.forEach((button) => button.classList.remove("is-active"));
            chip.classList.add("is-active");
            renderRows();
        });
    });

    searchInput?.addEventListener("input", renderRows);
    dialogRowType?.addEventListener("change", syncDialogFieldVisibility);
    cancelEstimateDialog?.addEventListener("click", closeDialog);
    closeEstimateDialog?.addEventListener("click", closeDialog);

    saveEstimateRow?.addEventListener("click", () => {
        const draftRow = normalizeRow({
            row_type: dialogRowType.value,
            name: dialogRowName.value,
            unit: dialogRowUnit.value,
            quantity: dialogRowQuantity.value,
            price: dialogRowPrice.value,
            reference: dialogRowReference.value,
        });

        if (!draftRow.name) {
            window.alert("Введите название строки.");
            dialogRowName.focus();
            return;
        }

        if (editingIndex >= 0) {
            rows[editingIndex] = draftRow;
            selectedIndex = editingIndex;
        } else {
            rows.push(draftRow);
            selectedIndex = rows.length - 1;
        }

        setDirtyState(true);
        closeDialog();
        renderRows();
    });

    discountInput?.addEventListener("input", () => {
        setDirtyState(true);
        renderRows();
    });

    Array.from(form.querySelectorAll("input[type='text'], textarea, select")).forEach((field) => {
        field.addEventListener("input", () => setDirtyState(true));
        field.addEventListener("change", () => setDirtyState(true));
    });

    form.addEventListener("submit", () => {
        recalcRows();
        itemsPayloadInput.value = JSON.stringify(rows);
        setDirtyState(false);
    });

    window.addEventListener("beforeunload", (event) => {
        if (!isDirty) {
            return;
        }
        event.preventDefault();
        event.returnValue = "";
    });

    renderRows();
})();
