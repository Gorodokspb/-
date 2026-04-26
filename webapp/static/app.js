(() => {
    const searchInput = document.getElementById("projectSearch");
    const chips = Array.from(document.querySelectorAll(".filter-chip"));
    const rows = Array.from(document.querySelectorAll(".project-row"));
    const visibleCount = document.getElementById("visibleProjectsCount");
    const emptyState = document.getElementById("projectsEmptyState");

    if (!searchInput || !chips.length || !rows.length || !visibleCount || !emptyState) {
        return;
    }

    let activeFilter = "all";

    function normalize(text) {
        return (text || "")
            .toLowerCase()
            .replace(/ё/g, "е")
            .replace(/\s+/g, " ")
            .trim();
    }

    function applyFilters() {
        const query = normalize(searchInput.value);
        let shown = 0;

        rows.forEach((row) => {
            const status = normalize(row.dataset.status || "");
            const haystack = normalize(row.dataset.search || "");
            const normalizedFilter = normalize(activeFilter);
            const matchStatus = normalizedFilter === "all" || status === normalizedFilter;
            const matchQuery = !query || haystack.includes(query);
            const visible = matchStatus && matchQuery;
            row.hidden = !visible;
            if (visible) {
                shown += 1;
            }
        });

        visibleCount.textContent = String(shown);
        emptyState.hidden = shown !== 0;
    }

    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            activeFilter = chip.dataset.filter || "all";
            chips.forEach((item) => item.classList.remove("is-active"));
            chip.classList.add("is-active");
            applyFilters();
        });
    });

    searchInput.addEventListener("input", applyFilters);
    applyFilters();
})();

(() => {
    const searchInput = document.getElementById("catalogSearch");
    const rows = Array.from(document.querySelectorAll(".catalog-row"));
    const headings = Array.from(document.querySelectorAll(".catalog-category-heading"));
    const categorySelects = Array.from(document.querySelectorAll("[data-bulk-category-select]"));
    const bulkSaveButton = document.getElementById("catalogBulkSaveButton");
    const bulkStatus = document.getElementById("catalogBulkStatus");
    const catalogCategoryChanges = new Map();

    function normalize(text) {
        return (text || "").toLowerCase().replace(/ё/g, "е").replace(/\s+/g, " ").trim();
    }

    function applyCatalogSearch() {
        const query = normalize(searchInput ? searchInput.value : "");
        rows.forEach((row) => {
            const match = !query || normalize(row.dataset.search || row.textContent).includes(query);
            row.hidden = !match;
        });
        headings.forEach((heading) => {
            let next = heading.nextElementSibling;
            let visible = false;
            while (next && !next.classList.contains("catalog-category-heading")) {
                if (next.classList.contains("catalog-row") && !next.hidden) {
                    visible = true;
                    break;
                }
                next = next.nextElementSibling;
            }
            heading.hidden = !visible;
        });
    }

    function updateBulkSaveState() {
        if (!bulkSaveButton) return;
        const hasChanges = catalogCategoryChanges.size > 0;
        bulkSaveButton.disabled = !hasChanges;
        bulkSaveButton.hidden = !hasChanges;
        bulkSaveButton.textContent = hasChanges
            ? `Сохранить все изменения (${catalogCategoryChanges.size})`
            : "Сохранить все изменения";
        if (bulkStatus && hasChanges) {
            bulkStatus.textContent = "Есть несохранённые категории";
        }
    }

    if (searchInput && rows.length) {
        searchInput.addEventListener("input", applyCatalogSearch);
    }

    categorySelects.forEach((select) => {
        select.addEventListener("change", () => {
            const itemId = Number(select.dataset.itemId);
            const originalCategory = select.dataset.originalCategory || "";
            const category = select.value;
            const row = select.closest(".catalog-row");
            if (category && category !== originalCategory) {
                catalogCategoryChanges.set(itemId, { id: itemId, category });
                select.classList.add("is-dirty");
                if (row) row.classList.add("is-dirty");
            } else {
                catalogCategoryChanges.delete(itemId);
                select.classList.remove("is-dirty");
                if (row) row.classList.remove("is-dirty");
            }
            updateBulkSaveState();
        });
    });

    if (bulkSaveButton) {
        bulkSaveButton.addEventListener("click", async () => {
            const payload = Array.from(catalogCategoryChanges.values());
            if (!payload.length) return;
            bulkSaveButton.disabled = true;
            if (bulkStatus) {
                bulkStatus.dataset.keepMessage = "1";
                bulkStatus.textContent = "Сохраняю...";
            }
            try {
                const response = await fetch("/catalog/bulk-update-categories", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
                if (!response.ok) {
                    let message = "Ошибка сохранения";
                    try {
                        const error = await response.json();
                        message = error.detail || message;
                    } catch (_) {}
                    throw new Error(message);
                }
                const result = await response.json();
                categorySelects.forEach((select) => {
                    select.dataset.originalCategory = select.value;
                    select.classList.remove("is-dirty");
                    const row = select.closest(".catalog-row");
                    if (row) {
                        row.classList.remove("is-dirty");
                        row.dataset.search = `${row.dataset.search || ""} ${select.value}`;
                    }
                });
                catalogCategoryChanges.clear();
                if (bulkStatus) {
                    bulkStatus.textContent = `Сохранено категорий: ${result.updated || 0}`;
                }
            } catch (error) {
                if (bulkStatus) {
                    bulkStatus.textContent = error.message || "Ошибка сохранения";
                }
            } finally {
                if (bulkStatus) {
                    delete bulkStatus.dataset.keepMessage;
                }
                updateBulkSaveState();
            }
        });
    }

    document.querySelectorAll("[data-open-modal]").forEach((button) => {
        button.addEventListener("click", () => {
            const modal = document.getElementById(button.dataset.openModal);
            if (modal) modal.hidden = false;
        });
    });
    document.querySelectorAll("[data-close-modal]").forEach((button) => {
        button.addEventListener("click", () => {
            const modal = document.getElementById(button.dataset.closeModal);
            if (modal) modal.hidden = true;
        });
    });
})();
