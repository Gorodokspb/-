(() => {
    const initialRowsNode = document.getElementById("estimateInitialRows");
    const initialPriceLibraryNode = document.getElementById("estimatePriceLibrary");
    const initialCalcStateNode = document.getElementById("estimateInitialCalcState");
    const rowsBody = document.getElementById("estimateRowsBody");
    const emptyState = document.getElementById("estimateEmptyState");
    const filteredEmptyState = document.getElementById("estimateFilteredEmptyState");
    const itemsPayloadInput = document.getElementById("estimateItemsPayload");
    const calcStatePayloadInput = document.getElementById("estimateCalcStatePayload");
    const discountInput = document.getElementById("estimateDiscountInput");
    const sectionCountNode = document.getElementById("estimateSectionCount");
    const itemCountNode = document.getElementById("estimateItemCount");
    const totalSumNode = document.getElementById("estimateTotalSum");
    const discountedSumNode = document.getElementById("estimateDiscountedSum");
    const totalValueNodes = [
        document.getElementById("estimateTotalSum"),
        document.getElementById("estimateTotalHeadValue"),
        document.getElementById("estimateTotalFooterValue"),
    ].filter(Boolean);
    const discountedValueNodes = [
        document.getElementById("estimateDiscountedSum"),
        document.getElementById("estimateDiscountedHeadValue"),
        document.getElementById("estimateDiscountedFooterValue"),
    ].filter(Boolean);
    const searchInput = document.getElementById("estimateSearchInput");
    const selectionTitle = document.getElementById("estimateSelectionTitle");
    const selectionMeta = document.getElementById("estimateSelectionMeta");
    const dirtyBadge = document.getElementById("estimateDirtyBadge");
    const form = document.getElementById("estimateEditorForm");
    const addSectionButton = document.getElementById("addSectionButton");
    const addItemButton = document.getElementById("addItemButton");
    const addBelowButton = document.getElementById("addBelowButton");
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
    const openEstimateCalculatorButton = document.getElementById("openEstimateCalculator");
    const openEstimateCalculatorInlineButton = document.getElementById("openEstimateCalculatorInline");
    const quickAddInlineButton = document.getElementById("quickAddInlineButton");
    const quickAddClearButton = document.getElementById("quickAddClearButton");
    const quickAddHint = document.getElementById("estimateQuickAddHint");
    const quickAddItemFields = Array.from(document.querySelectorAll(".quick-add-item-field"));
    const sectionNavigator = document.getElementById("estimateSectionNavigator");
    const sectionNavigatorCount = document.getElementById("estimateSectionNavigatorCount");
    const bottomStatus = document.getElementById("estimateBottomStatus");
    const drawer = document.getElementById("estimateDrawer");
    const drawerSearch = document.getElementById("estimateDrawerSearch");
    const ratesCountNode = document.getElementById("estimateRatesCount");
    const drawerCloseButton = document.getElementById("closeEstimateDrawer");
    const drawerTabs = Array.from(document.querySelectorAll(".estimate-drawer-tab"));
    const drawerPanels = Array.from(document.querySelectorAll(".estimate-drawer-panel"));
    const ratesLibrary = document.getElementById("estimateRatesLibrary");
    const operationsLibrary = document.getElementById("estimateOperationsLibrary");
    const templatesLibrary = document.getElementById("estimateTemplatesLibrary");
    const drawerOpeners = {
        rates: Array.from(document.querySelectorAll("#openDrawerRates, #openDrawerRatesTop")),
        operations: Array.from(document.querySelectorAll("#openDrawerOperations, #openDrawerOperationsTop")),
        templates: Array.from(document.querySelectorAll("#openDrawerTemplates, #openDrawerTemplatesTop")),
    };
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
    const rowNameLibrary = document.getElementById("estimateRowNameLibrary");
    const calculatorDialog = document.getElementById("estimateCalculatorDialog");
    const closeEstimateCalculator = document.getElementById("closeEstimateCalculator");
    const addCalculatorWall = document.getElementById("addCalculatorWall");
    const addCalculatorWindow = document.getElementById("addCalculatorWindow");
    const addCalculatorDoor = document.getElementById("addCalculatorDoor");
    const addCalculatorBox = document.getElementById("addCalculatorBox");
    const addCalculatorNiche = document.getElementById("addCalculatorNiche");
    const calcWallHeight = document.getElementById("calcWallHeight");
    const calcFloorLength = document.getElementById("calcFloorLength");
    const calcFloorWidth = document.getElementById("calcFloorWidth");
    const calcWallsContainer = document.getElementById("estimateCalculatorWalls");
    const calcOpeningsContainer = document.getElementById("estimateCalculatorOpenings");
    const calcFloorModsContainer = document.getElementById("estimateCalculatorFloorMods");
    const calcInsertButtons = Array.from(document.querySelectorAll("[data-calc-insert]"));
    const calcFloorResult = document.getElementById("calcFloorResult");
    const calcWallsResult = document.getElementById("calcWallsResult");
    const calcPlinthResult = document.getElementById("calcPlinthResult");
    const calcWindowSlopesResult = document.getElementById("calcWindowSlopesResult");
    const calcDoorSlopesResult = document.getElementById("calcDoorSlopesResult");

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

    function normalizeSearchText(value) {
        return normalizeText(value).replace(/ё/g, "е");
    }

    function currentDiscount() {
        return parseNumber(discountInput ? discountInput.value : 0);
    }

    const priceLibrary = (() => {
        if (!initialPriceLibraryNode) {
            return [];
        }
        try {
            const parsed = JSON.parse(initialPriceLibraryNode.textContent || "[]");
            return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
            console.warn("Не удалось разобрать библиотеку расценок", error);
            return [];
        }
    })();

    function defaultCalcState() {
        return {
            wall_height: "2.7",
            floor_length: "",
            floor_width: "",
            walls: ["0", "0", "0", "0"],
            openings: [],
            floor_mods: [],
        };
    }

    function normalizeCalcState(payload) {
        const base = defaultCalcState();
        if (!payload || typeof payload !== "object") {
            return base;
        }
        base.wall_height = String(payload.wall_height ?? payload.wallHeight ?? base.wall_height);
        base.floor_length = String(payload.floor_length ?? payload.floorLength ?? base.floor_length);
        base.floor_width = String(payload.floor_width ?? payload.floorWidth ?? base.floor_width);
        base.walls = Array.isArray(payload.walls) && payload.walls.length
            ? payload.walls.map((value) => String(value ?? "0"))
            : base.walls;
        base.openings = Array.isArray(payload.openings)
            ? payload.openings
                .filter((entry) => entry && typeof entry === "object")
                .map((entry) => ({
                    type: entry.type === "door" ? "door" : "window",
                    w: String(entry.w ?? entry.width ?? "0"),
                    h: String(entry.h ?? entry.height ?? "0"),
                }))
            : [];
        base.floor_mods = Array.isArray(payload.floor_mods || payload.floorMods)
            ? (payload.floor_mods || payload.floorMods)
                .filter((entry) => entry && typeof entry === "object")
                .map((entry) => ({
                    type: entry.type === "box" ? "box" : "niche",
                    w: String(entry.w ?? entry.width ?? "0"),
                    h: String(entry.h ?? entry.height ?? "0"),
                }))
            : [];
        return base;
    }

    const calcState = (() => {
        if (!initialCalcStateNode) {
            return defaultCalcState();
        }
        try {
            return normalizeCalcState(JSON.parse(initialCalcStateNode.textContent || "{}"));
        } catch (error) {
            console.warn("Не удалось разобрать состояние калькулятора", error);
            return defaultCalcState();
        }
    })();

    let calculatorResults = {
        floor: 0,
        walls: 0,
        plinth: 0,
        window_slopes: 0,
        door_slopes: 0,
    };

    function collectNameLibrary() {
        const library = new Map();
        priceLibrary.forEach((entry) => {
            if (!String(entry.name || "").trim()) {
                return;
            }
            library.set(normalizeSearchText(entry.name), {
                name: String(entry.name || "").trim(),
                unit: String(entry.unit || "").trim(),
                price: String(entry.price || "").trim(),
                reference: String(entry.reference || "").trim(),
            });
        });
        rows.forEach((row) => {
            if (row.row_type !== "item" || !String(row.name || "").trim()) {
                return;
            }
            const key = normalizeSearchText(row.name);
            if (!library.has(key)) {
                library.set(key, {
                    name: String(row.name || "").trim(),
                    unit: String(row.unit || "").trim(),
                    price: String(row.price || "").trim(),
                    reference: String(row.reference || "").trim(),
                });
            }
        });
        return Array.from(library.values()).sort((left, right) => left.name.localeCompare(right.name, "ru"));
    }

    function renderNameLibrary() {
        if (!rowNameLibrary) {
            return;
        }
        rowNameLibrary.innerHTML = "";
        collectNameLibrary().forEach((entry) => {
            const option = document.createElement("option");
            option.value = entry.name;
            rowNameLibrary.appendChild(option);
        });
    }

    function findLibraryMatch(value) {
        const query = normalizeSearchText(value);
        if (!query || query.length < 2) {
            return null;
        }
        const library = collectNameLibrary();
        const exact = library.find((entry) => normalizeSearchText(entry.name) === query);
        if (exact) {
            return exact;
        }
        const startsWith = library.filter((entry) => normalizeSearchText(entry.name).startsWith(query));
        if (startsWith.length === 1) {
            return startsWith[0];
        }
        const contains = library.filter((entry) => normalizeSearchText(entry.name).includes(query));
        if (contains.length === 1) {
            return contains[0];
        }
        return null;
    }

    function applySuggestedValues(nameField, unitField, priceField, referenceField) {
        if (!nameField) {
            return;
        }
        const match = findLibraryMatch(nameField.value);
        if (!match) {
            return;
        }
        if (normalizeSearchText(nameField.value) !== normalizeSearchText(match.name)) {
            nameField.value = match.name;
        }
        if (unitField && !String(unitField.value || "").trim() && match.unit) {
            unitField.value = match.unit;
        }
        if (priceField && !String(priceField.value || "").trim() && match.price) {
            priceField.value = match.price;
        }
        if (referenceField && !String(referenceField.value || "").trim() && match.reference) {
            referenceField.value = match.reference;
        }
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
    let pendingInsertAfterIndex = -1;
    let activeActionMenuIndex = -1;
    let activeFilter = "all";
    let isDirty = false;
    let activeDrawerTab = "rates";
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
        pendingInsertAfterIndex = -1;
        if (dialog.open) {
            dialog.close();
        }
    }

    function openDialog(mode, rowType, index = -1) {
        editingIndex = mode === "edit" ? index : -1;
        pendingInsertAfterIndex = mode === "create" ? index : -1;
        const existing = index >= 0 ? rows[index] : null;
        dialogTitle.textContent = mode === "edit" ? "Редактирование строки" : "Новая строка";
        dialogRowType.value = mode === "edit" && existing ? existing.row_type : rowType;
        dialogRowName.value = mode === "edit" && existing ? existing.name : "";
        dialogRowUnit.value = mode === "edit" && existing ? existing.unit : "";
        dialogRowQuantity.value = mode === "edit" && existing ? existing.quantity : "";
        dialogRowPrice.value = mode === "edit" && existing ? existing.price : "";
        dialogRowReference.value = mode === "edit" && existing ? existing.reference : "";
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
        if (!selectionTitle || !selectionMeta) {
            return;
        }
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
                parts.push(`${formatMoneyLabel(summary.total)}`);
                parts.push(`со скидкой ${formatMoneyLabel(summary.discounted)}`);
            }
            selectionTitle.textContent = row.name || "Раздел";
            selectionMeta.textContent = parts.length
                ? parts.join(" · ")
                : "Раздел без позиций.";
            return;
        }

        const parts = [];
        if (row.unit) {
            parts.push(row.unit);
        }
        if (row.quantity) {
            parts.push(`× ${row.quantity}`);
        }
        if (row.price) {
            parts.push(`${row.price}`);
        }
        if (row.discounted_total) {
            parts.push(`итог ${row.discounted_total}`);
        }
        selectionTitle.textContent = row.name || "Позиция";
        selectionMeta.textContent = parts.length
            ? parts.join(" · ")
            : "Заполни единицу, количество и цену.";
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

    function openDrawer(tabName = "rates") {
        if (!drawer) {
            return;
        }
        activeDrawerTab = tabName;
        drawer.dataset.open = "true";
        drawerTabs.forEach((tab) => {
            tab.classList.toggle("is-active", tab.dataset.drawerTab === tabName);
        });
        drawerPanels.forEach((panel) => {
            panel.classList.toggle("is-active", panel.dataset.drawerPanel === tabName);
        });
        renderDrawerLibraries();
    }

    function closeDrawer() {
        if (!drawer) {
            return;
        }
        drawer.dataset.open = "false";
    }

    function libraryCard({ title, description, pills = [], actionLabel = "", onAction = null }) {
        const card = document.createElement("article");
        card.className = "estimate-library-card";

        const strong = document.createElement("strong");
        strong.textContent = title;
        card.appendChild(strong);

        if (description) {
            const text = document.createElement("p");
            text.textContent = description;
            card.appendChild(text);
        }

        if (pills.length) {
            const meta = document.createElement("div");
            meta.className = "estimate-library-meta";
            pills.forEach((pillText) => {
                const pill = document.createElement("span");
                pill.className = "estimate-library-pill";
                pill.textContent = pillText;
                meta.appendChild(pill);
            });
            card.appendChild(meta);
        }

        if (actionLabel && typeof onAction === "function") {
            const actions = document.createElement("div");
            actions.className = "estimate-library-actions";
            const button = document.createElement("button");
            button.type = "button";
            button.className = "estimate-library-action-button";
            button.textContent = actionLabel;
            button.addEventListener("click", (event) => {
                event.stopPropagation();
                onAction();
            });
            actions.appendChild(button);
            card.appendChild(actions);
        }

        return card;
    }

    function updateQuickAddHint(message) {
        if (quickAddHint) {
            quickAddHint.textContent = message;
        }
    }

    function fillQuickAddFromLibrary(entry) {
        if (!entry) {
            return;
        }
        if (quickAddRowType) {
            quickAddRowType.value = "item";
        }
        if (quickAddName) {
            quickAddName.value = entry.name || "";
        }
        if (quickAddUnit) {
            quickAddUnit.value = entry.unit || "";
        }
        if (quickAddPrice) {
            quickAddPrice.value = entry.price || "";
        }
        if (quickAddReference && entry.reference) {
            quickAddReference.value = entry.reference;
        }
        syncQuickAddFieldVisibility();
        updateQuickAddHint(`Расценка «${entry.name || "позиция"}» подставлена в быстрое добавление. Укажи количество и нажми «Добавить сразу».`);
        quickAddQuantity?.focus();
    }

    function insertSectionFromTemplate(entry) {
        const row = normalizeRow({
            row_type: "section",
            name: entry?.name || "Новый раздел",
        });
        const insertIndex = findInsertIndex();
        rows.splice(insertIndex, 0, row);
        selectedIndex = insertIndex;
        activeActionMenuIndex = -1;
        setDirtyState(true);
        renderRows();
        updateQuickAddHint(`Раздел «${row.name}» добавлен в таблицу. Теперь можно сразу добавлять в него позиции.`);
    }

    function renderDrawerLibraries() {
        if (!ratesLibrary || !operationsLibrary || !templatesLibrary) {
            return;
        }

        const query = normalizeText(drawerSearch ? drawerSearch.value : "");
        const items = rows.filter((row) => row.row_type === "item");
        const sections = rows.filter((row) => row.row_type === "section");
        const activePriceLibrary = priceLibrary.length
            ? priceLibrary
            : collectNameLibrary().map((entry) => ({
                name: entry.name,
                unit: entry.unit,
                price: entry.price,
                reference: entry.reference,
            }));

        ratesLibrary.innerHTML = "";
        operationsLibrary.innerHTML = "";
        templatesLibrary.innerHTML = "";

        const filteredItems = items.filter((row) => {
            const haystack = normalizeText([row.name, row.reference, row.unit, row.price].join(" "));
            return !query || haystack.includes(query);
        });
        const filteredPriceLibrary = activePriceLibrary.filter((entry) => {
            const haystack = normalizeText([entry.name, entry.unit, entry.price].join(" "));
            return !query || haystack.includes(query);
        });
        const filteredSections = sections.filter((row) => {
            const haystack = normalizeText(row.name);
            return !query || haystack.includes(query);
        });

        if (ratesCountNode) {
            ratesCountNode.textContent = query ? `${filteredPriceLibrary.length} из ${activePriceLibrary.length}` : String(activePriceLibrary.length);
        }

        if (!filteredPriceLibrary.length) {
            ratesLibrary.innerHTML = '<div class="estimate-section-empty">По текущему фильтру подходящих расценок пока нет.</div>';
        } else {
            filteredPriceLibrary.forEach((entry) => {
                ratesLibrary.appendChild(
                    libraryCard({
                        title: entry.name || "Позиция без названия",
                        description: entry.reference
                            ? `Код: ${entry.reference}`
                            : "Расценка из серверной базы. Можно использовать как ориентир для новой строки.",
                        pills: [
                            entry.unit ? `Ед.: ${entry.unit}` : "Ед. не указана",
                            `Цена: ${entry.price || "0"}`,
                        ],
                        actionLabel: "В быстрый ввод",
                        onAction: () => fillQuickAddFromLibrary(entry),
                    }),
                );
            });
        }

        if (!filteredItems.length) {
            operationsLibrary.innerHTML = '<div class="estimate-section-empty">Нет строк для панели операций.</div>';
        } else {
            filteredItems.slice(0, 24).forEach((row) => {
                operationsLibrary.appendChild(
                    libraryCard({
                        title: row.name || "Позиция",
                        description: "Для этой позиции доступны базовые действия через таблицу: изменить, дублировать, переместить или удалить.",
                        pills: [
                            row.total ? `Стоимость: ${row.total}` : "Стоимость: 0",
                            row.discounted_total ? `Со скидкой: ${row.discounted_total}` : "Со скидкой: 0",
                        ],
                        actionLabel: "Выделить строку",
                        onAction: () => {
                            const index = rows.findIndex((candidate) => candidate.client_id === row.client_id);
                            if (index >= 0) {
                                selectedIndex = index;
                                activeActionMenuIndex = -1;
                                renderRows();
                            }
                        },
                    }),
                );
            });
        }

        if (!filteredSections.length) {
            templatesLibrary.innerHTML = '<div class="estimate-section-empty">Шаблоны этапов пока не собраны.</div>';
        } else {
            filteredSections.slice(0, 24).forEach((row) => {
                const summary = buildSectionSummaries("").get(row.client_id);
                templatesLibrary.appendChild(
                    libraryCard({
                        title: row.name || "Раздел",
                        description: "Раздел можно использовать как основу будущего шаблона этапа.",
                        pills: [
                            summary ? `Позиций: ${summary.itemCount}` : "Позиций: 0",
                            summary ? `Итого: ${formatMoneyLabel(summary.discounted)}` : "Итого: 0",
                        ],
                        actionLabel: "Добавить раздел",
                        onAction: () => insertSectionFromTemplate(row),
                    }),
                );
            });
        }
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

    function buildMenuItem(label, handler, className = "") {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `estimate-row-menu-item ${className}`.trim();
        button.textContent = label;
        button.addEventListener("click", (event) => {
            event.stopPropagation();
            activeActionMenuIndex = -1;
            handler();
        });
        return button;
    }

    function createRowActionWrap(index, row) {
        const actionWrap = document.createElement("div");
        actionWrap.className = "estimate-row-actions";

        const actionButton = document.createElement("button");
        actionButton.type = "button";
        actionButton.className = "estimate-row-menu";
        actionButton.textContent = "⋮";
        actionButton.title = "Действия по строке";
        actionButton.addEventListener("click", (event) => {
            event.stopPropagation();
            selectedIndex = index;
            activeActionMenuIndex = activeActionMenuIndex === index ? -1 : index;
            renderRows();
        });
        actionWrap.appendChild(actionButton);

        if (activeActionMenuIndex === index) {
            const menu = document.createElement("div");
            menu.className = "estimate-row-menu-panel";
            menu.addEventListener("click", (event) => event.stopPropagation());

            menu.appendChild(buildMenuItem("Изменить", () => openDialog("edit", row.row_type, index)));
            menu.appendChild(buildMenuItem("Добавить позицию ниже", () => openDialog("create", "item", index)));
            if (row.row_type === "section") {
                menu.appendChild(buildMenuItem("Добавить раздел ниже", () => openDialog("create", "section", index)));
            }
            menu.appendChild(buildMenuItem("Дублировать", duplicateSelectedRow));
            menu.appendChild(buildMenuItem("Удалить", () => deleteRowButton?.click(), "is-danger"));

            actionWrap.appendChild(menu);
        }

        return actionWrap;
    }

    function createSectionRow(row, index, summary, queryActive) {
        const tr = document.createElement("tr");
        const isCollapsed = collapsedSections.has(row.client_id) && !queryActive;
        tr.dataset.index = String(index);
        tr.classList.add("estimate-row-section");
        tr.classList.toggle("estimate-row-selected", index === selectedIndex);
        tr.addEventListener("click", () => {
            selectedIndex = index;
            activeActionMenuIndex = -1;
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

        const typeBadge = document.createElement("span");
        typeBadge.className = "estimate-row-type-badge is-section";
        typeBadge.textContent = "Раздел";
        typeBadge.title = "Раздел сметы";

        tr.appendChild(createCell(typeBadge, "estimate-row-type"));
        tr.appendChild(createCell(titleWrap, "estimate-row-name"));
        tr.appendChild(createCell("—", "estimate-row-muted"));
        tr.appendChild(createCell(String(summary.itemCount || 0), "estimate-row-muted"));
        tr.appendChild(createCell("—", "estimate-row-muted"));
        tr.appendChild(createCell(formatMoneyLabel(summary.total), "estimate-row-muted"));
        tr.appendChild(createCell(formatMoneyLabel(summary.discounted), "estimate-row-muted"));
        tr.appendChild(createCell(createRowActionWrap(index, row), "estimate-row-actions"));
        return tr;
    }

    function createItemRow(row, index) {
        const tr = document.createElement("tr");
        tr.dataset.index = String(index);
        tr.classList.toggle("estimate-row-selected", index === selectedIndex);
        tr.addEventListener("click", () => {
            selectedIndex = index;
            activeActionMenuIndex = -1;
            renderRows();
        });
        tr.addEventListener("dblclick", () => {
            selectedIndex = index;
            openDialog("edit", row.row_type, index);
        });

        const typeBadge = document.createElement("span");
        typeBadge.className = "estimate-row-type-badge";
        typeBadge.textContent = "Позиция";
        typeBadge.title = "Позиция сметы";

        const nameWrap = document.createElement("div");
        nameWrap.className = "estimate-row-name-wrap";
        const nameNode = document.createElement("div");
        nameNode.className = "estimate-row-name";
        nameNode.textContent = row.name || "—";
        nameWrap.appendChild(nameNode);

        tr.appendChild(createCell(typeBadge, "estimate-row-type"));
        tr.appendChild(createCell(nameWrap, ""));
        tr.appendChild(createCell(row.unit || "—"));
        tr.appendChild(createCell(row.quantity || "0"));
        tr.appendChild(createCell(row.price || "0"));
        tr.appendChild(createCell(row.total || "0"));
        tr.appendChild(createCell(row.discounted_total || "0"));
        tr.appendChild(createCell(createRowActionWrap(index, row), "estimate-row-actions"));
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
        totalValueNodes.forEach((node) => {
            node.textContent = formatNumber(totalSum);
        });
        discountedValueNodes.forEach((node) => {
            node.textContent = formatNumber(discountedSum);
        });
        renderNameLibrary();
        renderSectionNavigator(sectionSummaries);
        renderDrawerLibraries();
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
        activeActionMenuIndex = -1;
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
        activeActionMenuIndex = -1;
        setDirtyState(true);
        renderRows();
    }

    function clearSelection() {
        selectedIndex = -1;
        activeActionMenuIndex = -1;
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
        applySuggestedValues(quickAddName, quickAddUnit, quickAddPrice, quickAddReference);
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
        activeActionMenuIndex = -1;
        setDirtyState(true);
        clearQuickAddFields();
        renderRows();
        quickAddName?.focus();
    }

    function syncCalcStatePayload() {
        if (calcStatePayloadInput) {
            calcStatePayloadInput.value = JSON.stringify(calcState);
        }
    }

    function renderCalculatorSimpleList(container, entries, titleBuilder, onChange) {
        if (!container) {
            return;
        }
        container.innerHTML = "";
        if (!entries.length) {
            const empty = document.createElement("div");
            empty.className = "estimate-calculator-empty";
            empty.textContent = "Пока пусто";
            container.appendChild(empty);
            return;
        }
        entries.forEach((entry, index) => {
            const row = document.createElement("div");
            row.className = "estimate-calculator-row";
            const title = document.createElement("strong");
            title.textContent = titleBuilder(entry, index);
            row.appendChild(title);
            onChange(row, entry, index);
            container.appendChild(row);
        });
    }

    function renderCalculatorRows() {
        if (calcWallHeight) calcWallHeight.value = calcState.wall_height;
        if (calcFloorLength) calcFloorLength.value = calcState.floor_length;
        if (calcFloorWidth) calcFloorWidth.value = calcState.floor_width;

        renderCalculatorSimpleList(calcWallsContainer, calcState.walls, (_entry, index) => `Стена ${index + 1}`, (row, _entry, index) => {
            const input = document.createElement("input");
            input.type = "text";
            input.value = calcState.walls[index];
            input.placeholder = "0";
            input.addEventListener("input", () => {
                calcState.walls[index] = input.value;
                recalculateCalculator();
            });
            row.appendChild(input);
            if (calcState.walls.length > 1) {
                const remove = document.createElement("button");
                remove.type = "button";
                remove.className = "ghost-button-light estimate-inline-action estimate-inline-action-danger";
                remove.textContent = "Удалить";
                remove.addEventListener("click", () => {
                    calcState.walls.splice(index, 1);
                    renderCalculatorRows();
                    recalculateCalculator();
                });
                row.appendChild(remove);
            }
        });

        renderCalculatorSimpleList(calcOpeningsContainer, calcState.openings, (entry, index) => `${entry.type === "door" ? "Дверь" : "Окно"} ${index + 1}`, (row, entry, index) => {
            const width = document.createElement("input");
            width.type = "text";
            width.value = entry.w;
            width.placeholder = "Ширина";
            width.addEventListener("input", () => {
                calcState.openings[index].w = width.value;
                recalculateCalculator();
            });
            row.appendChild(width);
            const height = document.createElement("input");
            height.type = "text";
            height.value = entry.h;
            height.placeholder = "Высота";
            height.addEventListener("input", () => {
                calcState.openings[index].h = height.value;
                recalculateCalculator();
            });
            row.appendChild(height);
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "ghost-button-light estimate-inline-action estimate-inline-action-danger";
            remove.textContent = "Удалить";
            remove.addEventListener("click", () => {
                calcState.openings.splice(index, 1);
                renderCalculatorRows();
                recalculateCalculator();
            });
            row.appendChild(remove);
        });

        renderCalculatorSimpleList(calcFloorModsContainer, calcState.floor_mods, (entry, index) => `${entry.type === "box" ? "Короб (-)" : "Ниша (+)"} ${index + 1}`, (row, entry, index) => {
            const width = document.createElement("input");
            width.type = "text";
            width.value = entry.w;
            width.placeholder = "Ширина";
            width.addEventListener("input", () => {
                calcState.floor_mods[index].w = width.value;
                recalculateCalculator();
            });
            row.appendChild(width);
            const height = document.createElement("input");
            height.type = "text";
            height.value = entry.h;
            height.placeholder = "Высота";
            height.addEventListener("input", () => {
                calcState.floor_mods[index].h = height.value;
                recalculateCalculator();
            });
            row.appendChild(height);
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "ghost-button-light estimate-inline-action estimate-inline-action-danger";
            remove.textContent = "Удалить";
            remove.addEventListener("click", () => {
                calcState.floor_mods.splice(index, 1);
                renderCalculatorRows();
                recalculateCalculator();
            });
            row.appendChild(remove);
        });
    }

    function recalculateCalculator() {
        calcState.wall_height = calcWallHeight ? calcWallHeight.value : calcState.wall_height;
        calcState.floor_length = calcFloorLength ? calcFloorLength.value : calcState.floor_length;
        calcState.floor_width = calcFloorWidth ? calcFloorWidth.value : calcState.floor_width;

        const perimeter = calcState.walls.reduce((sum, value) => sum + parseNumber(value), 0);
        const height = parseNumber(calcState.wall_height);
        let floorArea = parseNumber(calcState.floor_length) * parseNumber(calcState.floor_width);
        calcState.floor_mods.forEach((entry) => {
            const area = parseNumber(entry.w) * parseNumber(entry.h);
            floorArea += entry.type === "box" ? -area : area;
        });

        let wallsArea = perimeter * height;
        let doorsWidth = 0;
        let windowSlopes = 0;
        let doorSlopes = 0;
        calcState.openings.forEach((entry) => {
            const width = parseNumber(entry.w);
            const openingHeight = parseNumber(entry.h);
            wallsArea -= width * openingHeight;
            if (entry.type === "door") {
                doorsWidth += width;
                doorSlopes += (2 * openingHeight + width);
            } else {
                windowSlopes += (2 * openingHeight + width);
            }
        });

        calculatorResults = {
            floor: Math.max(0, floorArea),
            walls: Math.max(0, wallsArea),
            plinth: Math.max(0, perimeter - doorsWidth),
            window_slopes: Math.max(0, windowSlopes),
            door_slopes: Math.max(0, doorSlopes),
        };

        if (calcFloorResult) calcFloorResult.textContent = `${formatNumber(calculatorResults.floor)} м.кв`;
        if (calcWallsResult) calcWallsResult.textContent = `${formatNumber(calculatorResults.walls)} м.кв`;
        if (calcPlinthResult) calcPlinthResult.textContent = `${formatNumber(calculatorResults.plinth)} м.пог`;
        if (calcWindowSlopesResult) calcWindowSlopesResult.textContent = `${formatNumber(calculatorResults.window_slopes)} м.пог`;
        if (calcDoorSlopesResult) calcDoorSlopesResult.textContent = `${formatNumber(calculatorResults.door_slopes)} м.пог`;
        syncCalcStatePayload();
    }

    function openCalculator() {
        if (!calculatorDialog) {
            return;
        }
        renderCalculatorRows();
        recalculateCalculator();
        calculatorDialog.showModal();
    }

    function closeCalculator() {
        syncCalcStatePayload();
        if (calculatorDialog?.open) {
            calculatorDialog.close();
        }
    }

    function insertCalculatorValue(key) {
        const value = calculatorResults[key];
        if (quickAddQuantity) {
            quickAddQuantity.value = formatNumber(value);
            quickAddQuantity.focus();
        }
        updateQuickAddHint(`Результат калькулятора подставлен в количество: ${formatNumber(value)}.`);
        closeCalculator();
    }

    addSectionButton?.addEventListener("click", () => openDialog("create", "section"));
    addItemButton?.addEventListener("click", () => openDialog("create", "item"));
    quickAddButton?.addEventListener("click", () => openDialog("create", "item"));
    addBelowButton?.addEventListener("click", () => {
        const row = selectedRowOrAlert();
        if (!row) {
            return;
        }
        openDialog("create", "item", selectedIndex);
    });

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
        activeActionMenuIndex = -1;
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
    quickAddInlineButton?.addEventListener("click", addQuickRow);
    quickAddClearButton?.addEventListener("click", clearQuickAddFields);
    openEstimateCalculatorButton?.addEventListener("click", openCalculator);
    openEstimateCalculatorInlineButton?.addEventListener("click", openCalculator);
    closeEstimateCalculator?.addEventListener("click", closeCalculator);
    calcWallHeight?.addEventListener("input", recalculateCalculator);
    calcFloorLength?.addEventListener("input", recalculateCalculator);
    calcFloorWidth?.addEventListener("input", recalculateCalculator);
    addCalculatorWall?.addEventListener("click", () => {
        calcState.walls.push("0");
        renderCalculatorRows();
        recalculateCalculator();
    });
    addCalculatorWindow?.addEventListener("click", () => {
        calcState.openings.push({ type: "window", w: "0", h: "0" });
        renderCalculatorRows();
        recalculateCalculator();
    });
    addCalculatorDoor?.addEventListener("click", () => {
        calcState.openings.push({ type: "door", w: "0", h: "0" });
        renderCalculatorRows();
        recalculateCalculator();
    });
    addCalculatorBox?.addEventListener("click", () => {
        calcState.floor_mods.push({ type: "box", w: "0", h: "0" });
        renderCalculatorRows();
        recalculateCalculator();
    });
    addCalculatorNiche?.addEventListener("click", () => {
        calcState.floor_mods.push({ type: "niche", w: "0", h: "0" });
        renderCalculatorRows();
        recalculateCalculator();
    });
    calcInsertButtons.forEach((button) => {
        button.addEventListener("click", () => insertCalculatorValue(button.dataset.calcInsert));
    });
    quickAddName?.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            event.preventDefault();
            addQuickRow();
        }
    });

    searchInput?.addEventListener("input", renderRows);
    drawerSearch?.addEventListener("input", renderDrawerLibraries);
    dialogRowType?.addEventListener("change", syncDialogFieldVisibility);
    dialogRowName?.addEventListener("change", () => applySuggestedValues(dialogRowName, dialogRowUnit, dialogRowPrice, dialogRowReference));
    dialogRowName?.addEventListener("blur", () => applySuggestedValues(dialogRowName, dialogRowUnit, dialogRowPrice, dialogRowReference));
    quickAddName?.addEventListener("change", () => applySuggestedValues(quickAddName, quickAddUnit, quickAddPrice, quickAddReference));
    quickAddName?.addEventListener("blur", () => applySuggestedValues(quickAddName, quickAddUnit, quickAddPrice, quickAddReference));
    cancelEstimateDialog?.addEventListener("click", closeDialog);
    closeEstimateDialog?.addEventListener("click", closeDialog);
    drawerCloseButton?.addEventListener("click", closeDrawer);

    Object.entries(drawerOpeners).forEach(([tabName, buttons]) => {
        buttons.forEach((button) => {
            button?.addEventListener("click", () => openDrawer(tabName));
        });
    });

    drawerTabs.forEach((tab) => {
        tab.addEventListener("click", () => openDrawer(tab.dataset.drawerTab || "rates"));
    });

    saveEstimateRow?.addEventListener("click", () => {
        applySuggestedValues(dialogRowName, dialogRowUnit, dialogRowPrice, dialogRowReference);
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
            const insertIndex = pendingInsertAfterIndex >= 0 ? pendingInsertAfterIndex + 1 : findInsertIndex();
            rows.splice(insertIndex, 0, draftRow);
            selectedIndex = insertIndex;
        }

        activeActionMenuIndex = -1;
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
        syncCalcStatePayload();
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

        if (event.key === "Escape" && calculatorDialog?.open) {
            closeCalculator();
            return;
        }

        if (event.key === "Escape" && drawer?.dataset.open === "true") {
            closeDrawer();
        }
    });

    window.addEventListener("beforeunload", (event) => {
        if (!isDirty) {
            return;
        }
        event.preventDefault();
        event.returnValue = "";
    });

    document.addEventListener("click", (event) => {
        if (!event.target.closest(".estimate-row-actions")) {
            if (activeActionMenuIndex !== -1) {
                activeActionMenuIndex = -1;
                renderRows();
            }
        }
    });

    syncCalcStatePayload();
    renderRows();
})();
