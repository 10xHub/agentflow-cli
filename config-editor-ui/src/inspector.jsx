import { closeInspector, copyJson, go, validate } from "./actions.js";
import { SECTION_ICONS } from "./icons.js";
import { commit, counts, fieldIdFor, isDirty, isStale, issuesFor, plural, store } from "./store.js";
import { EmptyPanel, Icon } from "./ui.jsx";

// Docked on the right from xl up (sticky, its own scroll); a drawer below that.
export function Inspector() {
  const { errors, warnings } = counts();
  const count = errors + warnings;
  const tab = (id, label, badge) => (
    <button
      type="button" role="tab" id={`tab-${id}`} aria-selected={store.tab === id ? "true" : "false"}
      class={`focus-ring inline-flex h-9 cursor-pointer items-center gap-2 rounded-lg px-3 text-sm font-medium transition-colors duration-150 ${store.tab === id
        ? "bg-raised text-ink" : "text-muted hover:text-ink"}`}
      onClick={() => commit((s) => { s.tab = id; })}
    >
      {label}{badge}
    </button>
  );
  return (
    <aside
      aria-label="Inspector"
      class={`fixed inset-y-0 right-0 z-40 flex w-[min(100vw,400px)] flex-col border-l border-line bg-surface transition-transform duration-200 ease-out xl:sticky xl:top-14 xl:bottom-auto xl:z-auto xl:self-start xl:h-[calc(100dvh-3.5rem)] xl:w-[380px] xl:shrink-0 xl:translate-x-0 ${store.inspectorOpen ? "translate-x-0" : "translate-x-full"}`}
    >
      <div class="flex h-14 shrink-0 items-center gap-1 border-b border-line px-3">
        <div role="tablist" class="flex flex-1 gap-1">
          {tab("problems", "Problems", store.validated !== null && count ? (
            <span class={`inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[11px] font-semibold ${errors ? "bg-danger-soft text-danger" : "bg-warn-soft text-warn"}`}>
              {count}
            </span>
          ) : null)}
          {tab("json", "10xgraph.json", null)}
        </div>
        <button type="button" class="icon-btn xl:hidden" aria-label="Close inspector" onClick={closeInspector}>
          <Icon name="x" class="size-5" />
        </button>
      </div>
      <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        {store.tab === "problems" ? <Problems /> : <JsonView />}
      </div>
    </aside>
  );
}

function Problems() {
  if (!store.schema) return null;
  if (store.validated === null) {
    return (
      <EmptyPanel icon="checkCircle" tint="text-faint" title="Not checked yet" text="Validate runs the same rules 10xgraph api applies when it starts.">
        <button type="button" class="btn btn-outline mt-5" disabled={!!store.busy} onClick={validate}>Validate now</button>
      </EmptyPanel>
    );
  }
  const { errors, warnings } = counts();
  const stale = isStale();
  const groups = store.sections.map((sec) => [sec, issuesFor(sec.id)]).filter(([, list]) => list.length);
  return (
    <div>
      <div class="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <p class="text-sm text-muted">
          <span class={errors ? "font-medium text-danger" : ""}>{plural(errors, "error")}</span>{" · "}
          <span class={warnings ? "font-medium text-warn" : ""}>{plural(warnings, "warning")}</span>
        </p>
        {stale ? <button type="button" class="text-sm font-medium text-brand hover:underline" onClick={validate}>Re-check</button> : null}
      </div>
      {stale ? (
        <div class="mx-4 mt-3 flex gap-2 rounded-lg bg-raised px-3 py-2 text-[13px] text-muted">
          <Icon name="info" class="mt-0.5 size-3.5 text-faint" />You changed the form since this check.
        </div>
      ) : null}
      {!store.issues.length ? (
        <EmptyPanel icon="checkCircle" tint="text-ok" title="No problems found" text="This configuration passes every check." />
      ) : (
        <div class="space-y-5 px-3 py-4">
          {groups.map(([sec, list]) => (
            <div key={sec.id}>
              <p class="eyebrow mb-1.5 flex items-center gap-2 px-2">
                <Icon name={SECTION_ICONS[sec.id] || "box"} class="size-3.5" />{sec.title}
              </p>
              <ul class="space-y-0.5">
                {list.map((issue, i) => {
                  const error = issue.level === "error";
                  return (
                    <li key={i}>
                      <button
                        type="button" onClick={() => go(sec.id, fieldIdFor(issue.path))}
                        class="focus-ring flex w-full cursor-pointer gap-2.5 rounded-lg px-2 py-2 text-left transition-colors duration-150 hover:bg-raised"
                      >
                        <Icon name={error ? "xCircle" : "alert"} class={`mt-0.5 size-4 ${error ? "text-danger" : "text-warn"}`} />
                        <span class="min-w-0">
                          <span class="block text-[13px] leading-5 text-body">{issue.message}</span>
                          {issue.path ? <span class="mt-0.5 block truncate font-mono text-xs text-faint">{issue.path}</span> : null}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function highlight(line) {
  const escaped = line.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return escaped.replace(
    /("(\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (m) => {
      let color = "var(--af-json-number)";
      if (m.startsWith('"')) color = m.endsWith(":") ? "var(--af-json-key)" : "var(--af-json-string)";
      else if (m === "true" || m === "false" || m === "null") color = "var(--af-json-literal)";
      return `<span style="color:${color}">${m}</span>`;
    },
  );
}

function JsonView() {
  const lines = JSON.stringify(store.config, null, 2).split("\n");
  return (
    <div>
      <div class="sticky top-0 flex items-center justify-between gap-3 border-b border-line bg-surface px-4 py-2.5">
        <p class="text-xs text-faint">{isDirty() || !store.exists ? "Preview of what Save will write" : "Matches the file on disk"}</p>
        <button type="button" class="btn btn-ghost h-8 px-2.5 text-xs" onClick={copyJson}>
          <Icon name="copy" class="size-3.5" />Copy
        </button>
      </div>
      <div class="py-3 pr-4 font-mono text-[12.5px] leading-5">
        {lines.map((line, i) => (
          <div key={i} class="flex">
            <span class="w-10 shrink-0 pr-3 text-right text-faint/70 select-none">{i + 1}</span>
            <span class="min-w-0 flex-1 break-all whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: highlight(line) }} />
          </div>
        ))}
      </div>
    </div>
  );
}
