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
    const collapseAllButton = document.getElementById("collapseAllButton");
    const expandAllButton = document.getElementById("expandAllButton");
    const moveUpButton = document.getElementById("moveUpButton");
    const moveDownButton = document.getElementById("moveDownButton");
    const clearSelectionButton = document.getElementById("clearSelectionButton");
    const deleteRowButton = document.getElementById("deleteRowButton");
    const filterChips = Array.from(document.querySelectorAll(".estimate-filter-chip"));
    const quickAddRowType = document.getElementById("quickAddRowType");
    const quickAddName = document.getElementById("quickAddName");
    const quickAddUnit = document.getElementById("quickAddUnit");
    const quickAddQuantity = document.getElementById("quickAddQuantity");
    const quickAddPrice = document.getElementById("quickAddPrice");
    const quickAddReference = document.getElementById("quickAddReference");
    const quickAddButton = document.getElementById("quickAddButton");
    const quickAddClearButton = document.getElementById("quickAddClearButton");
    const quickAddHint = document.getElementById("estimateQuickAddHint");
    const quickAddItemFields = Array.from(document.querySelectorAll(".quick-add-item-field"));
    const sectionNavigator = document.getElementById("estimateSectionNavigator");
    const sectionNavigatorCount = document.getElementById("estimateSectionNavigatorCount");
    const bottomStatus = document.getElementById("estimateBottomStatus");
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

    function formatMoneyLabel(value) {
        return formatNumber(value || 0);
    }

    function normalizeText(value) {
        return String(value || "").toLowerCase().replace(/\s+/g, " ").trim();
    }

    function currentDiscount() {
        return parseNumber(discountInput ? discountInput.value : 0);
    }

    function isEditableElement(target) {
        return Boolean(
            target &&
            (
                target.closest("input") ||
                target.closest("textarea") ||
                target.closest("select") ||
                target.closest("dialog")
            )
        );
    }

    let nextRowId = 1;

    function generateRowId() {
        const id = `row-${nextRowId}`;
        nextRowId += 1;
        return id;
    }

    function cloneRow(row) {
        return JSON.parse(JSON.stringify(row));
    }

    function normalizeRow(row) {
        const rowType = row && row.row_type === "section" ? "section" : "item";
        const clientId = row && row.client_id ? String(row.client_id) : generateRowId();

        if (rowType === "section") {
            return {
                client_id: clientId,
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
            client_id: clientId,
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

    function serializeRowsForSubmit() {
        return rows.map((row) => ({
            row_type: row.row_type,
            name: row.name,
            unit: row.unit,
            quantity: row.quantity,
            price: row.price,
            total: row.total,
            discounted_total: row.discounted_total,
            reference: row.reference,
        }));
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
    const collapsedSections = new Set();

    function setDirtyState(value) {
        isDirty = Boolean(value);
        if (dirtyBadge) {
            dirtyBadge.hidden = !isDirty;
        }
        updateBottomStatus();
    }

    function syncDialogFieldVisibility() {
        const isSection = dialogRowType.value === "section";
        itemFields.forEach((field) => {
            field.classList.toggle("dialog-hidden", isSection);
        });
    }

    function syncQuickAddFieldVisibility() {
        const isSection = quickAddRowType && quickAddRowType.value === "section";
        quickAddItemFields.forEach((field) => {
            field.classList.toggle("dialog-hidden", isSection);
        });
        if (quickAddHint) {
            const selected = selectedRow();
            const insertionTarget = selected ? `после строки «${selected.name || "без названия"}»` : "в конец сметы";
            quickAddHint.textContent = isSection
                ? `Новый раздел добавится ${insertionTarget}.`
                : `Новая позиция добавится ${insertionTarget}.`;
        }
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

    function rowMatchesSearch(row, query) {
        const haystack = normalizeText([
            row.row_type === "section" ? "раздел" : "позиция",
            row.name,
            row.unit,
            row.reference,
            row.quantity,
            row.price,
        ].join(" "));
        return !query || haystack.includes(query);
    }

    function buildSectionSummaries(query) {
        const summaries = new Map();
        let currentSectionId = null;
        let currentSectionOrder = -1;

        rows.forEach((row, index) => {
            if (row.row_type === "section") {
                currentSectionOrder += 1;
                currentSectionId = row.client_id;
                summaries.set(currentSectionId, {
                    id: row.client_id,
                    index,
                    order: currentSectionOrder,
                    name: row.name || "Раздел",
                    itemCount: 0,
                    total: 0,
                    discounted: 0,
                    matchesSelf: rowMatchesSearch(row, query),
                    visibleChildren: 0,
                });
                return;
            }

            const searchVisible = rowMatchesSearch(row, query);
            if (!currentSectionId || !summaries.has(currentSectionId)) {
                return;
            }
            const summary = summaries.get(currentSectionId);
            summary.itemCount += 1;
            summary.total += parseNumber(row.total);
            summary.discounted += parseNumber(row.discounted_total);
            if (searchVisible) {
                summary.visibleChildren += 1;
            }
        });

        return summaries;
    }

    function updateSelectionSummary(sectionSummaries) {
        const row = selectedRow();
        if (!row) {
            selectionTitle.textContent = "Ничего не выбрано";
            selectionMeta.textContent = "Выберите строку в таблице или добавьте новую.";
            return;
        }

        if (row.row_type === "section") {
            const summary = sectionSummaries.get(row.client_id);
            const parts = [];
            if (summary) {
                parts.push(`${summary.itemCount} поз.`);
                parts.push(`итого: ${formatMoneyLabel(summary.total)}`);
                parts.push(`со скидкой: ${formatMoneyLabel(summary.discounted)}`);
            }
            selectionTitle.textContent = row.name || "Раздел";
            selectionMeta.textContent = parts.length
                ? parts.join(" | ")
                : "Раздел без позиций. В него можно быстро добавлять строки.";
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
        if (row.discounted_total) {
            parts.push(`со скидкой: ${row.discounted_total}`);
        }
        selectionTitle.textContent = row.name || "Позиция";
        selectionMeta.textContent = parts.length
            ? parts.join(" | ")
            : "Позиция без заполненных числовых полей.";
    }

    function updateActionButtons() {
        const hasSelection = Boolean(selectedRow());
        const isFirst = selectedIndex <= 0;
        const isLast = selectedIndex < 0 || selectedIndex >= rows.length - 1;

        [
            editRowButton,
            duplicateRowButton,
            moveUpButton,
            moveDownButton,
            clearSelectionButton,
            deleteRowButton,
        ].forEach((button) => {
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

        const hasSections = rows.some((row) => row.row_type === "section");
        if (collapseAllButton) {
            collapseAllButton.disabled = !hasSections;
        }
        if (expandAllButton) {
            expandAllButton.disabled = !hasSections || collapsedSections.size === 0;
        }
    }

    function updateBottomStatus() {
        if (!bottomStatus) {
            return;
        }
        const row = selectedRow();
        if (isDirty && row) {
            bottomStatus.textContent = `Есть несохраненные изменения. Выбрана строка: ${row.name || "без названия"}`;
            return;
        }
        if (isDirty) {
            bottomStatus.textContent = "Есть несохраненные изменения. Не забудьте сохранить черновик.";
            return;
        }
        if (row && row.row_type === "section") {
            bottomStatus.textContent = `Выбран раздел «${row.name || "без названия"}». Можно быстро добавить в него позиции.`;
            return;
        }
        if (row) {
            bottomStatus.textContent = `Выбрана позиция «${row.name || "без названия"}».`;
            return;
        }
        bottomStatus.textContent = "Смета готова к редактированию";
    }

    function renderSectionNavigator(sectionSummaries) {
        if (!sectionNavigator || !sectionNavigatorCount) {
            return;
        }
        const orderedSections = Array.from(sectionSummaries.values()).sort((left, right) => left.order - right.order);
        sectionNavigatorCount.textContent = String(orderedSections.length);
        sectionNavigator.innerHTML = "";

        if (!orderedSections.length) {
            sectionNavigator.innerHTML = '<div class="estimate-section-empty">Разделы появятся после добавления строк типа «Раздел».</div>';
            return;
        }

        orderedSections.forEach((section) => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "estimate-section-nav-item";
            item.classList.toggle("is-collapsed", collapsedSections.has(section.id));
            item.addEventListener("click", () => {
                selectedIndex = section.index;
                renderRows();
            });

            const title = document.createElement("strong");
            title.textContent = section.name;

            const meta = document.createElement("span");
            meta.textContent = `${section.itemCount} поз. · ${formatMoneyLabel(section.discounted)}`;

            item.appendChild(title);
            item.appendChild(meta);
            sectionNavigator.appendChild(item);
        });
    }

    function createCell(content, className = "") {
        const cell = document.createElement("td");
        if (className) {
            cell.className = className;
        }
        if (content instanceof Node) {
            cell.appendChild(content);
        } else {
            cell.textContent = content;
        }
        return cell;
    }

    function createSectionRow(row, index, summary, queryActive) {
        const tr = document.createElement("tr");
        const isCollapsed = collapsedSections.has(row.client_id) && !queryActive;
        tr.dataset.index = String(index);
        tr.classList.add("estimate-row-section");
        tr.classList.toggle("estimate-row-selected", index === selectedIndex);
        tr.addEventListener("click", () => {
            selectedIndex = index;
            renderRows();
        });
        tr.addEventListener("dblclick", () => {
            selectedIndex = index;
            openDialog("edit", row.row_type, index);
        });

        const toggleButton = document.createElement("button");
        toggleButton.type = "button";
        toggleButton.className = "estimate-section-toggle";
        toggleButton.textContent = isCollapsed ? "+" : "−";
        toggleButton.title = isCollapsed ? "Развернуть раздел" : "Свернуть раздел";
        toggleButton.addEventListener("click", (event) => {
            event.stopPropagation();
            if (collapsedSections.has(row.client_id)) {
                collapsedSections.delete(row.client_id);
            } else {
                collapsedSections.add(row.client_id);
            }
            renderRows();
        });

        const titleWrap = document.createElement("div");
        titleWrap.className = "estimate-section-title-wrap";

        const title = document.createElement("div");
        title.className = "estimate-section-title";
        title.textContent = row.name || "Раздел";
        titleWrap.appendChild(title);

        const meta = document.createElement("div");
        meta.className = "estimate-section-meta";
        meta.textContent = `${summary.itemCount} поз. · итого ${formatMoneyLabel(summary.total)} · со скидкой ${formatMoneyLabel(summary.discounted)}`;
        titleWrap.appendChild(meta);

        tr.appendChild(createCell(toggleButton, "estimate-row-type"));
        tr.appendChild(createCell(titleWrap, "estimate-row-name"));
        tr.appendChild(createCell("—", "estimate-row-muted"));
        tr.appendChild(createCell(String(summary.itemCount || 0), "estimate-row-muted"));
        tr.appendChild(createCell("—", "estimate-row-muted"));
        tr.appendChild(createCell(formatMoneyLabel(summary.total), "estimate-row-muted"));
        tr.appendChild(createCell(formatMoneyLabel(summary.discounted), "estimate-row-muted"));
        return tr;
    }

    function createItemRow(row, index) {
        const tr = document.createElement("tr");
        tr.dataset.index = String(index);
        tr.classList.toggle("estimate-row-selected", index === selectedIndex);
        tr.addEventListener("click", () => {
            selectedIndex = index;
            renderRows();
        });
        tr.addEventListener("dblclick", () => {
            selectedIndex = index;
            openDialog("edit", row.row_type, index);
        });

        tr.appendChild(createCell("Позиция", "estimate-row-type"));
        tr.appendChild(createCell(row.name || "—", "estimate-row-name"));
        tr.appendChild(createCell(row.unit || "—"));
        tr.appendChild(createCell(row.quantity || "0"));
        tr.appendChild(createCell(row.price || "0"));
        tr.appendChild(createCell(row.total || "0"));
        tr.appendChild(createCell(row.discounted_total || "0"));
        return tr;
    }

    function renderRows() {
        recalcRows();
        rowsBody.innerHTML = "";
        const query = normalizeText(searchInput ? searchInput.value : "");
        const queryActive = Boolean(query);
        const sectionSummaries = buildSectionSummaries(query);

        let sectionCount = 0;
        let itemCount = 0;
        let totalSum = 0;
        let discountedSum = 0;
        let visibleRows = 0;
        let currentSectionId = null;
        let currentSectionCollapsed = false;

        rows.forEach((row, index) => {
            if (row.row_type === "section") {
                sectionCount += 1;
                currentSectionId = row.client_id;
                const summary = sectionSummaries.get(row.client_id) || {
                    itemCount: 0,
                    total: 0,
                    discounted: 0,
                    visibleChildren: 0,
                    matchesSelf: rowMatchesSearch(row, query),
                };
                currentSectionCollapsed = collapsedSections.has(row.client_id) && !queryActive;

                const showSection = !queryActive || summary.matchesSelf || summary.visibleChildren > 0;
                if (showSection) {
                    visibleRows += 1;
                    rowsBody.appendChild(createSectionRow(row, index, summary, queryActive));
                }
                return;
            }

            itemCount += 1;
            totalSum += parseNumber(row.total);
            discountedSum += parseNumber(row.discounted_total);

            if (activeFilter === "section") {
                return;
            }
            if (currentSectionCollapsed) {
                return;
            }
            if (!rowMatchesSearch(row, query)) {
                return;
            }

            visibleRows += 1;
            rowsBody.appendChild(createItemRow(row, index));
        });

        itemsPayloadInput.value = JSON.stringify(serializeRowsForSubmit());
        emptyState.hidden = rows.length !== 0;
        filteredEmptyState.hidden = rows.length === 0 || visibleRows !== 0;
        sectionCountNode.textContent = String(sectionCount);
        itemCountNode.textContent = String(itemCount);
        totalSumNode.textContent = formatNumber(totalSum);
        discountedSumNode.textContent = formatNumber(discountedSum);
        renderSectionNavigator(sectionSummaries);
        updateSelectionSummary(sectionSummaries);
        updateActionButtons();
        updateBottomStatus();
        syncQuickAddFieldVisibility();
    }

    function findInsertIndex() {
        if (selectedIndex >= 0 && selectedIndex < rows.length) {
            return selectedIndex + 1;
        }
        return rows.length;
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
        const duplicate = normalizeRow({
            ...cloneRow(row),
            client_id: generateRowId(),
            name: `${row.name || "Строка"} (копия)`,
        });
        rows.splice(selectedIndex + 1, 0, duplicate);
        selectedIndex += 1;
        setDirtyState(true);
        renderRows();
    }

    function clearSelection() {
        selectedIndex = -1;
        renderRows();
    }

    function clearQuickAddFields() {
        if (quickAddName) quickAddName.value = "";
        if (quickAddUnit) quickAddUnit.value = "";
        if (quickAddQuantity) quickAddQuantity.value = "";
        if (quickAddPrice) quickAddPrice.value = "";
        if (quickAddReference) quickAddReference.value = "";
        syncQuickAddFieldVisibility();
    }

    function buildQuickAddRow() {
        return normalizeRow({
            row_type: quickAddRowType ? quickAddRowType.value : "item",
            name: quickAddName ? quickAddName.value : "",
            unit: quickAddUnit ? quickAddUnit.value : "",
            quantity: quickAddQuantity ? quickAddQuantity.value : "",
            price: quickAddPrice ? quickAddPrice.value : "",
            reference: quickAddReference ? quickAddReference.value : "",
        });
    }

    function addQuickRow() {
        const draftRow = buildQuickAddRow();
        if (!draftRow.name) {
            window.alert("Введите название строки.");
            quickAddName?.focus();
            return;
        }
        const insertIndex = findInsertIndex();
        rows.splice(insertIndex, 0, draftRow);
        selectedIndex = insertIndex;
        setDirtyState(true);
        clearQuickAddFields();
        renderRows();
        quickAddName?.focus();
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
    collapseAllButton?.addEventListener("click", () => {
        rows
            .filter((row) => row.row_type === "section")
            .forEach((row) => collapsedSections.add(row.client_id));
        renderRows();
    });
    expandAllButton?.addEventListener("click", () => {
        collapsedSections.clear();
        renderRows();
    });

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

    quickAddRowType?.addEventListener("change", syncQuickAddFieldVisibility);
    quickAddButton?.addEventListener("click", addQuickRow);
    quickAddClearButton?.addEventListener("click", clearQuickAddFields);
    quickAddName?.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            event.preventDefault();
            addQuickRow();
        }
    });

    searchInput?.addEventListener("input", renderRows);
    dialogRowType?.addEventListener("change", syncDialogFieldVisibility);
    cancelEstimateDialog?.addEventListener("click", closeDialog);
    closeEstimateDialog?.addEventListener("click", closeDialog);

    saveEstimateRow?.addEventListener("click", () => {
        const draftRow = normalizeRow({
            client_id: editingIndex >= 0 && rows[editingIndex] ? rows[editingIndex].client_id : generateRowId(),
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
            const insertIndex = findInsertIndex();
            rows.splice(insertIndex, 0, draftRow);
            selectedIndex = insertIndex;
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
        itemsPayloadInput.value = JSON.stringify(serializeRowsForSubmit());
        setDirtyState(false);
    });

    window.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
            event.preventDefault();
            itemsPayloadInput.value = JSON.stringify(serializeRowsForSubmit());
            form.requestSubmit();
            return;
        }

        if ((event.altKey) && event.key === "ArrowUp" && !isEditableElement(event.target)) {
            event.preventDefault();
            moveSelectedRow(-1);
            return;
        }

        if ((event.altKey) && event.key === "ArrowDown" && !isEditableElement(event.target)) {
            event.preventDefault();
            moveSelectedRow(1);
            return;
        }

        if (event.key === "Delete" && !isEditableElement(event.target)) {
            event.preventDefault();
            deleteRowButton?.click();
            return;
        }

        if (event.key === "Enter" && !event.ctrlKey && !event.metaKey && !isEditableElement(event.target)) {
            const row = selectedRow();
            if (row) {
                event.preventDefault();
                openDialog("edit", row.row_type, selectedIndex);
            }
            return;
        }

        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
            if (dialog.open) {
                event.preventDefault();
                saveEstimateRow?.click();
                return;
            }
            if (document.activeElement === quickAddName) {
                event.preventDefault();
                addQuickRow();
            }
        }
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
