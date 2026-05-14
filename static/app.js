// No missä se nyt oli — client-side glue
// 1. Pill checkbox toggle visuals (auto-submit-free)
// 2. Services select2 + localStorage persistence (across searches, forever)
// 3. Service worker registration

(function () {
  // ── 0. Immediate loading state for long server requests ─────────────
  const loadingOverlay = document.getElementById("loading-overlay");
  const loadingSub = document.getElementById("loading-subtext");
  function showLoading(message) {
    if (!loadingOverlay) return;
    if (loadingSub && message) loadingSub.textContent = message;
    loadingOverlay.hidden = false;
  }

  document.querySelectorAll("form.result-form").forEach((form) => {
    form.addEventListener("submit", () => {
      const titleInput = form.querySelector('input[name="selected_title"]');
      const title = titleInput ? titleInput.value : "";
      const msg = title
        ? `Loading ${title} availability`
        : "Fetching title data from JustWatch";
      showLoading(msg);
    });
  });
  const filtersForm = document.getElementById("filters-form");
  if (filtersForm) {
    filtersForm.addEventListener("submit", () => {
      showLoading("Applying filters and refreshing offers");
    });
  }

  // ── 1. Pill checkbox visual sync ────────────────────────────────────
  document.querySelectorAll("label.checkbox-pill").forEach((label) => {
    const cb = label.querySelector("input[type=checkbox]");
    if (!cb) return;
    const sync = () => label.classList.toggle("on", cb.checked);
    cb.addEventListener("change", sync);
    sync();
  });

  // ── 2. Services select + cross-search persistence ───────────────────
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
        const option = new Option(value, value, true, true);
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

      function formatServiceOption(state) {
        if (!state.id) return state.text;
        const $el = $(state.element);
        const available = Number($el.data("available")) === 1;
        const unavailable = Number($el.data("unavailable")) === 1;
        const icon = String($el.data("icon") || "").trim();
        const $row = $('<span class="svc-opt-row"></span>');
        if (available) $row.addClass("is-available");
        if (unavailable) $row.addClass("is-saved");
        if (icon) {
          $row.append($('<img class="svc-opt-logo" alt="" />').attr("src", icon));
        }
        $row.append($('<span class="svc-opt-name"></span>').text(state.text));
        return $row;
      }

      function hideSelectedMatcher(params, data) {
        if (!data.id) return data;
        const selected = new Set($services.val() || []);
        if (selected.has(String(data.id))) return null;
        const term = $.trim((params.term || "")).toLowerCase();
        if (!term) return data;
        const text = String(data.text || "").toLowerCase();
        return text.includes(term) ? data : null;
      }

      $services.select2({
        placeholder: "All services — pick to filter",
        allowClear: true,
        width: "100%",
        closeOnSelect: false,
        templateResult: formatServiceOption,
        templateSelection: formatServiceOption,
        matcher: hideSelectedMatcher,
      });

      // UX rule: dropdown can add selections, but unselect must happen via chips.
      $services.on("select2:unselecting", function (e) {
        const oe = e.params && e.params.args && e.params.args.originalEvent;
        if (!oe || !oe.target || typeof oe.target.closest !== "function") return;
        const fromResultsList = oe.target.closest(".select2-results__option");
        if (fromResultsList) {
          e.preventDefault();
        }
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

  // ── 3. Service worker ───────────────────────────────────────────────
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker
        .register("/sw.js", { scope: "/" })
        .catch((err) => console.warn("SW register failed", err));
    });
  }
})();
