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
