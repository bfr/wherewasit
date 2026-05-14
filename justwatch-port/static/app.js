// Missä se nyt oli — client-side glue
// 1. Row expand/collapse for per-country detail
// 2. Pill checkbox toggle visuals (auto-submit-free)
// 3. Services select2 + localStorage persistence (across searches, forever)
// 4. Service worker registration

(function () {
  // ── 1. Row expand ───────────────────────────────────────────────────
  document.querySelectorAll(".row-toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const row = btn.closest(".ledger-row");
      if (!row) return;
      const panel = row.querySelector(".row-expand");
      if (!panel) return;
      const open = !panel.hasAttribute("hidden");
      if (open) {
        panel.setAttribute("hidden", "");
        btn.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
        btn.firstChild.nextSibling.textContent = " Per-country detail";
      } else {
        panel.removeAttribute("hidden");
        btn.classList.add("open");
        btn.setAttribute("aria-expanded", "true");
        btn.firstChild.nextSibling.textContent = " Hide per-country detail";
      }
    });
  });

  // ── 2. Pill checkbox visual sync ────────────────────────────────────
  document.querySelectorAll("label.checkbox-pill").forEach((label) => {
    const cb = label.querySelector("input[type=checkbox]");
    if (!cb) return;
    const sync = () => label.classList.toggle("on", cb.checked);
    cb.addEventListener("change", sync);
    sync();
  });

  // ── 3. Services select + cross-search persistence ───────────────────
  const SERVICE_STORAGE_KEY = "msno_selected_services_v1";

  function restoreServiceSelection($select) {
    if (($select.val() || []).length > 0) return [];
    try {
      const raw = localStorage.getItem(SERVICE_STORAGE_KEY);
      if (!raw) return [];
      const saved = JSON.parse(raw);
      if (!Array.isArray(saved)) return [];
      const available = new Set(
        $select.find("option").map((_, opt) => opt.value).get()
      );
      const missing = saved.filter((v) => !available.has(v));
      missing.forEach((value) => {
        const text = value + " (not in this title)";
        const option = new Option(text, value, true, true);
        option.dataset.unavailable = "1";
        $select.append(option);
      });
      const finalValues = [...new Set(saved)];
      if (finalValues.length > 0) {
        $select.val(finalValues).trigger("change.select2");
      }
      return missing;
    } catch (_) {
      return [];
    }
  }

  function persistServiceSelection($select) {
    try {
      const values = ($select.val() || []).filter(
        (v) =>
          !$select
            .find('option[value="' + v.replace(/"/g, '\\"') + '"]')
            .data("unavailable")
      );
      localStorage.setItem(SERVICE_STORAGE_KEY, JSON.stringify(values));
    } catch (_) {}
  }

  if (window.jQuery) {
    jQuery(function ($) {
      const $services = $("#services-select");
      if ($services.length === 0) return;

      $services.select2({
        placeholder: "All services — pick to filter",
        allowClear: true,
        width: "100%",
        closeOnSelect: false,
      });

      restoreServiceSelection($services);
      $services.on("change", () => persistServiceSelection($services));

      // explicit clear button — wipes both selection and persisted memory
      $("#services-clear").on("click", () => {
        try { localStorage.removeItem(SERVICE_STORAGE_KEY); } catch (_) {}
        $services.val(null).trigger("change");
      });

      // Reset filters: also uncheck pills
      $("#filters-reset").on("click", function () {
        setTimeout(() => {
          document.querySelectorAll("label.checkbox-pill").forEach((label) => {
            const cb = label.querySelector("input[type=checkbox]");
            if (cb) {
              label.classList.toggle("on", cb.checked);
            }
          });
        }, 10);
      });
    });
  }

  // ── 4. Service worker ───────────────────────────────────────────────
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker
        .register("/sw.js", { scope: "/" })
        .catch((err) => console.warn("SW register failed", err));
    });
  }
})();
