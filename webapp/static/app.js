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

    function normalize(text) {
        return (text || "").toLowerCase().replace(/ё/g, "е").replace(/\s+/g, " ").trim();
    }

    if (searchInput && rows.length) {
        searchInput.addEventListener("input", () => {
            const query = normalize(searchInput.value);
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
