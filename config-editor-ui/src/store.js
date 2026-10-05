// One mutable store. Components read it directly; every change goes through
// commit(), which re-renders the app. The tree is small, so a full render is cheap
// and Preact's diff keeps focus, selection, and scroll position intact.

// Sections not listed here land in the last tier, so new schema entries still render.
export const TIERS = [
  {
    id: "essential", title: "Essentials",
    tagline: "What the server needs to boot. Start here.",
    sections: ["core", "plugins"],
  },
  {
    id: "recommended", title: "Recommended",
    tagline: "Lock down access and see what your agents do before you ship.",
    sections: ["auth", "authorization", "rate_limit", "observability"],
  },
  {
    id: "advanced", title: "Advanced",
    tagline: "Tune connection limits, client-side tools, and your test loop.",
    sections: ["websocket", "ag_ui", "remote_tools", "test", "evaluation"],
  },
];

// Issues a widget renders beside its own input rather than at the top of the section.
export const WIDGET_FIELD_IDS = { "auth.path": "auth-path", authorization: "authz-path" };

export const TOKEN = new URLSearchParams(location.hash.slice(1)).get("token") || "";

export const store = {
  schema: null,
  sections: [],            // in page order
  tiers: [],               // TIERS with the resolved section objects in `list`
  fields: new Map(),       // "a.b.c" -> field definition
  config: {},
  version: null,
  exists: false,
  path: "",
  parseError: null,
  saved: "",               // snapshot of the last loaded/saved config
  validated: null,         // snapshot the current issues belong to
  issues: [],
  open: new Set(),         // ids of expanded sections
  tab: "problems",
  inspectorOpen: false,    // drawer state below the xl breakpoint
  busy: null,              // "validate" | "save" | null
  toolParams: {},          // remote tool index -> {text, error} while JSON is being edited
  toasts: [],
  fatal: null,             // {title, text} when the page cannot load
};

let rerender = () => {};
export const subscribe = (fn) => { rerender = fn; };
export function commit(mutate) {
  if (mutate) mutate(store);
  rerender();
}

// ------------------------------------------------------------------ helpers

export const clone = (v) => JSON.parse(JSON.stringify(v));
export const snapshot = () => JSON.stringify(store.config);
export const isObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
export const getPath = (obj, path) => path.reduce((acc, k) => (isObject(acc) ? acc[k] : undefined), obj);
export const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

export function setPath(obj, path, value) {
  let target = obj;
  for (const k of path.slice(0, -1)) {
    if (!isObject(target[k])) target[k] = {};
    target = target[k];
  }
  target[path[path.length - 1]] = value;
}

export function deletePath(obj, path) {
  const parents = [];
  let target = obj;
  for (const k of path.slice(0, -1)) {
    if (!isObject(target)) return;
    parents.push([target, k]);
    target = target[k];
  }
  if (isObject(target)) delete target[path[path.length - 1]];
  // Drop nested objects left empty, but never the section key itself.
  for (let i = parents.length - 1; i >= 1; i--) {
    const [parent, k] = parents[i];
    if (isObject(parent[k]) && Object.keys(parent[k]).length === 0) delete parent[k];
    else break;
  }
}

export function valueOrDefault(path) {
  const v = getPath(store.config, path);
  return v !== undefined ? v : store.fields.get(path.join("."))?.default;
}

export const section = (id) => store.sections.find((s) => s.id === id);
export const isDirty = () => snapshot() !== store.saved;
export const isOn = (sec) => !sec.optional || (sec.key in store.config && store.config[sec.key] !== null);
export const issuesFor = (id) => store.issues.filter((i) => i.section === id);
export const issueAt = (path) => store.issues.find((i) => i.path === path);
export const isStale = () => store.validated !== null && store.validated !== snapshot();
export function counts(list = store.issues) {
  const errors = list.filter((i) => i.level === "error").length;
  return { errors, warnings: list.length - errors };
}
export const fieldIdFor = (path) => WIDGET_FIELD_IDS[path] || `f-${path.replaceAll(".", "-")}`;
