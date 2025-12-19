(function () {
    function init() {
      let lastTouchTime = 0;
      const drawer = document.getElementById("drawer");
      const backdrop = document.getElementById("backdrop");
      const graphArea = document.getElementById("graph-area");
  
      // If Dash hasn't rendered yet, try again shortly
      if (!drawer || !backdrop || !graphArea) {
        setTimeout(init, 100);
        return;
      }
  
      const DEFAULT = { open: false, width: 320 };
      let state = JSON.parse(localStorage.getItem("drawer-state")) || DEFAULT;
  
      function apply() {
        drawer.style.width = state.width + "px";
        drawer.style.transform = state.open ? "translateX(0)" : "translateX(100%)";
        backdrop.style.display = state.open ? "block" : "none";
      }
  
      function save() {
        localStorage.setItem("drawer-state", JSON.stringify(state));
      }
  
      apply();
  
      // ---- Button & backdrop actions (capture phase so Plotly can't steal taps) ----
      function handleAction(e) {
        const a = e.target?.dataset?.action;
        if (!a) return;
  
        e.preventDefault();
        e.stopPropagation();
  
        if (a === "toggle") state.open = !state.open;
        if (a === "close") state.open = false;
  
        if (a === "fullscreen") {
          if (!document.fullscreenElement) graphArea.requestFullscreen();
          else document.exitFullscreen();
        }
  
        save();
        apply();
      }
  
      document.addEventListener(
        "touchstart",
        (e) => {
          lastTouchTime = Date.now();
          handleAction(e);
        },
        true
      );
      
      document.addEventListener(
        "click",
        (e) => {
          // Ignore click if it follows a touch
          if (Date.now() - lastTouchTime < 500) return;
          handleAction(e);
        },
        true
      );
  
      // ---- Swipe from right edge ----
      let startX = null;
  
      document.addEventListener(
        "touchstart",
        (e) => {
          startX = e.touches[0].clientX;
        },
        { passive: true }
      );
  
      document.addEventListener(
        "touchend",
        (e) => {
          if (startX === null) return;
          const dx = e.changedTouches[0].clientX - startX;
  
          // open: swipe inward from right edge
          if (startX > window.innerWidth - 40 && dx < -60) state.open = true;
          // close: swipe left
          if (dx < -80) state.open = false;
  
          startX = null;
          save();
          apply();
        },
        { passive: true }
      );
  
      // ---- Resize handle ----
      let resizing = false;
  
      document.addEventListener("mousedown", (e) => {
        if (e.target && e.target.id === "resize") resizing = true;
      });
  
      document.addEventListener("mousemove", (e) => {
        if (!resizing) return;
        state.width = Math.max(240, Math.min(520, window.innerWidth - e.clientX));
        save();
        apply();
      });
  
      document.addEventListener("mouseup", () => {
        resizing = false;
      });
  
      // Optional: keep UI consistent on orientation change / resize
      window.addEventListener("resize", apply);
    }
  
    // Run after DOM is ready
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  })();
  