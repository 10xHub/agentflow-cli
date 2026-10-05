import { render } from "preact";
import { useEffect, useReducer } from "preact/hooks";
import { closeInspector, dismissToast, load, save } from "./actions.js";
import { Inspector } from "./inspector.jsx";
import { Header, Page } from "./page.jsx";
import { isDirty, store, subscribe } from "./store.js";
import { Icon } from "./ui.jsx";

const TOAST_LOOK = {
  success: ["checkCircle", "text-ok"],
  warning: ["alert", "text-warn"],
  error: ["xCircle", "text-danger"],
};

function Toasts() {
  return (
    <div class="pointer-events-none fixed right-4 bottom-4 left-4 z-50 flex flex-col items-end gap-2 sm:left-auto" aria-live="polite">
      {store.toasts.map((t) => {
        const [icon, tint] = TOAST_LOOK[t.kind];
        return (
          <div
            key={t.id} role={t.kind === "error" ? "alert" : "status"}
            class="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border border-line bg-surface px-4 py-3 text-sm shadow-pop"
          >
            <Icon name={icon} class={`mt-0.5 size-4 ${tint}`} />
            <p class="min-w-0 flex-1 leading-5 text-body">{t.message}</p>
            {t.action ? (
              <button type="button" class="shrink-0 font-medium text-brand hover:underline" onClick={() => { dismissToast(t.id); t.action.run(); }}>
                {t.action.label}
              </button>
            ) : null}
            <button type="button" class="-mr-1 shrink-0 cursor-pointer rounded text-faint hover:text-ink" aria-label="Dismiss" onClick={() => dismissToast(t.id)}>
              <Icon name="x" />
            </button>
          </div>
        );
      })}
    </div>
  );
}

function App() {
  const [, rerender] = useReducer((n) => n + 1, 0);

  useEffect(() => {
    subscribe(rerender);
    const onKey = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
      else if (e.key === "Escape" && store.inspectorOpen) closeInspector();
    };
    const onUnload = (e) => { if (store.schema && isDirty()) e.preventDefault(); };
    document.addEventListener("keydown", onKey);
    window.addEventListener("beforeunload", onUnload);
    load();
    return () => {
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("beforeunload", onUnload);
    };
  }, []);

  return (
    <>
      <a href="#main" class="sr-only z-50 rounded-md bg-brand-solid px-3 py-2 text-white focus:not-sr-only focus:fixed focus:top-3 focus:left-3">
        Skip to content
      </a>
      <Header />
      <div class="flex">
        <main id="main" tabindex={-1} class="min-w-0 flex-1 focus:outline-none">
          <div class="mx-auto w-full max-w-4xl px-4 pb-24 sm:px-8">
            <Page />
          </div>
        </main>
        <Inspector />
      </div>
      {store.inspectorOpen ? <div class="fixed inset-0 z-30 bg-black/50 xl:hidden" onClick={closeInspector} /> : null}
      <Toasts />
    </>
  );
}

render(<App />, document.getElementById("app"));
