import {
  TIERS, TOKEN, clone, commit, counts, isDirty, isOn, plural, section, snapshot, store,
} from "./store.js";

// ------------------------------------------------------------------ network

async function api(method, url, body) {
  const headers = { "X-Agentflow-Token": TOKEN };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const res = await fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  let data = {};
  try { data = await res.json(); } catch { /* empty body */ }
  return { ok: res.ok, status: res.status, data };
}

const fatal = (title, text) => commit((s) => { s.fatal = { title, text }; });

function rank(order, id) {
  const i = order.indexOf(id);
  return i === -1 ? order.length : i;
}

function openIssues() {
  for (const issue of store.issues) if (section(issue.section)) store.open.add(issue.section);
}

export async function load() {
  if (!TOKEN) return fatal("Open the link printed by agentflow config", "This page needs the session token included in that link.");
  let res;
  try {
    res = await api("GET", "/api/state");
  } catch {
    return fatal("Cannot reach the config server", "Check that agentflow config is still running in your terminal, then reload.");
  }
  if (!res.ok) return fatal("This link has expired", res.data.error || "Restart agentflow config and open the new link it prints.");

  const data = res.data;
  commit((s) => {
    s.schema = data.schema;
    const order = TIERS.flatMap((t) => t.sections);
    s.sections = [...data.schema.sections].sort((a, b) => rank(order, a.id) - rank(order, b.id));
    s.tiers = TIERS.map((t) => ({ ...t, list: t.sections.map(section).filter(Boolean) }));
    s.tiers[s.tiers.length - 1].list.push(...s.sections.filter((sec) => !order.includes(sec.id)));
    for (const sec of s.sections) for (const f of sec.fields) s.fields.set(f.path.join("."), f);
    s.config = data.config;
    s.version = data.version;
    s.exists = data.exists;
    s.path = data.path;
    s.parseError = data.parse_error;
    s.issues = data.issues;
    const clean = data.exists && !data.parse_error;
    s.saved = clean ? snapshot() : "";
    s.validated = clean ? snapshot() : null;
    // Open everything that is required, switched on, or has something to fix.
    for (const sec of s.sections) if (!sec.optional || isOn(sec)) s.open.add(sec.id);
    openIssues();
  });
  const requested = new URLSearchParams(location.hash.slice(1)).get("section");
  if (requested && section(requested)) go(requested);
}

export async function validate() {
  if (store.busy || !guardJson()) return;
  commit((s) => { s.busy = "validate"; });
  try {
    const res = await api("POST", "/api/validate", { config: store.config });
    if (!res.ok) return toast("error", res.data.error || "Validation failed.");
    store.issues = res.data.issues;
    store.validated = snapshot();
    openIssues();
    const { errors, warnings } = counts();
    const show = { label: "Show", run: () => openInspector("problems") };
    if (errors) toast("error", `${plural(errors, "error")} to fix before saving.`, show);
    else if (warnings) toast("warning", `Valid, with ${plural(warnings, "warning")}.`, show);
    else toast("success", "Configuration is valid.");
  } catch {
    toast("error", "Cannot reach the config server.");
  } finally {
    commit((s) => { s.busy = null; });
  }
}

export async function save() {
  if (store.busy || !store.schema) return;
  if (store.exists && !isDirty() && !store.parseError) return toast("success", "No changes to save.");
  if (!guardJson()) return;
  commit((s) => { s.busy = "save"; });
  try {
    const res = await api("POST", "/api/save", { config: store.config, version: store.version });
    if (res.data.issues) {
      store.issues = res.data.issues;
      store.validated = snapshot();
      openIssues();
    }
    if (res.ok) {
      store.version = res.data.version;
      store.config = res.data.config;
      store.toolParams = {};
      store.validated = snapshot();
      store.saved = snapshot();
      store.exists = true;
      store.parseError = null;
      const name = res.data.path.split(/[\\/]/).pop();
      toast("success", res.data.backup ? `Saved ${name}. The previous version is in ${name}.bak.` : `Created ${name}.`);
    } else if (res.status === 409) {
      toast("error", res.data.error, { label: "Reload", run: () => location.reload() });
    } else if (res.status === 422) {
      const { errors } = counts();
      toast("error", `Not saved: ${plural(errors, "error")} to fix first.`, { label: "Show", run: () => openInspector("problems") });
    } else {
      toast("error", res.data.error || "Save failed.");
    }
  } catch {
    toast("error", "Cannot reach the config server.");
  } finally {
    commit((s) => { s.busy = null; });
  }
}

function guardJson() {
  const broken = Object.values(store.toolParams).some((t) => t.error);
  if (broken) {
    go("remote_tools");
    toast("error", "A remote tool has invalid parameters JSON.");
  }
  return !broken;
}

// ------------------------------------------------------------------ sections

export function setSection(sec, on) {
  commit((s) => {
    if (on) {
      s.config[sec.key] = clone(sec.default);
      s.open.add(sec.id);
    } else {
      delete s.config[sec.key];
    }
    if (sec.key === "remote_tools") s.toolParams = {};
  });
}

export function toggleOpen(id) {
  commit((s) => {
    if (s.open.has(id)) s.open.delete(id);
    else s.open.add(id);
  });
}

export function setAllOpen(open) {
  commit((s) => { s.open = open ? new Set(s.sections.map((sec) => sec.id)) : new Set(); });
}

const smooth = () => (window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth");

// Expand a section and bring it (or one of its fields) into view.
export function go(id, fieldId) {
  commit((s) => {
    s.open.add(id);
    s.inspectorOpen = false;
  });
  history.replaceState(null, "", `#token=${encodeURIComponent(TOKEN)}&section=${id}`);
  requestAnimationFrame(() => {
    const field = fieldId ? document.getElementById(fieldId) : null;
    if (field) {
      field.scrollIntoView({ block: "center", behavior: smooth() });
      field.focus({ preventScroll: true });
      return;
    }
    document.getElementById(`sec-${id}`)?.scrollIntoView({ block: "start", behavior: smooth() });
    document.getElementById(`acc-${id}`)?.focus({ preventScroll: true });
  });
}

export function scrollToTier(id) {
  document.getElementById(`tier-${id}`)?.scrollIntoView({ block: "start", behavior: smooth() });
}

// ------------------------------------------------------------------ inspector

export function openInspector(tab) {
  commit((s) => {
    if (tab) s.tab = tab;
    s.inspectorOpen = !window.matchMedia("(min-width: 1280px)").matches;
  });
}

export const closeInspector = () => commit((s) => { s.inspectorOpen = false; });

export async function copyJson() {
  try {
    await navigator.clipboard.writeText(JSON.stringify(store.config, null, 2) + "\n");
    toast("success", "Copied agentflow.json to the clipboard.");
  } catch {
    toast("error", "The clipboard is not available here.");
  }
}

// ------------------------------------------------------------------ toasts

let toastId = 0;

export function toast(kind, message, action) {
  const id = ++toastId;
  commit((s) => { s.toasts = [...s.toasts, { id, kind, message, action }]; });
  setTimeout(() => dismissToast(id), action ? 8000 : 4000);
}

export function dismissToast(id) {
  commit((s) => { s.toasts = s.toasts.filter((t) => t.id !== id); });
}
