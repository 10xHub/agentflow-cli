import { useEffect, useState } from "preact/hooks";
import { commit, isObject, issueAt, store } from "./store.js";
import { ChoiceGroup, Chips, FieldIssue, FieldMeta, Group, Icon, Row, Select, TextRow } from "./ui.jsx";

// ------------------------------------------------------------------ auth

export function AuthWidget() {
  const value = store.config.auth;
  const mode = isObject(value) ? "custom" : "jwt";
  return (
    <div class="space-y-6">
      <Group title="Method">
        <ChoiceGroup
          name="auth" label="Authentication method" value={mode}
          options={[
            ["jwt", "JWT", "Verify bearer tokens signed with JWT_SECRET_KEY."],
            ["custom", "Custom backend", "Your own BaseAuth subclass decides who is calling."],
          ]}
          onPick={(m) => commit((s) => { s.config.auth = m === "jwt" ? "jwt" : { method: "custom", path: "" }; })}
        />
      </Group>
      {mode === "custom" ? (
        <Group title="Backend">
          <div class="panel">
            <TextRow
              id="auth-path" label="Auth class" path="auth.path" value={value.path} placeholder="auth.custom:MyAuth"
              help="Import path of a BaseAuth subclass, as module:attribute." issue={issueAt("auth.path")}
              onInput={(v) => commit((s) => { s.config.auth = { ...s.config.auth, method: "custom", path: v }; })}
            />
          </div>
        </Group>
      ) : null}
    </div>
  );
}

// ------------------------------------------------------------------ authorization

function authzModeOf(v) {
  if (isObject(v)) return "rbac";
  if (typeof v === "string") {
    const key = v.trim().toLowerCase();
    if (key === "ownership") return "ownership";
    if (["allow_all", "default", "none"].includes(key)) return "allow_all";
  }
  return v === undefined || v === null ? null : "custom";
}

const AUTHZ_PRESETS = {
  ownership: () => "ownership",
  allow_all: () => "allow_all",
  custom: () => "",
  rbac: () => ({
    backend: "rbac",
    roles: { admin: ["*"], member: ["graph:invoke", "graph:stream", "graph:read", "checkpointer:read"] },
    default_scopes: [],
    isolation: "owner",
  }),
};

export function AuthorizationWidget({ sec }) {
  const value = store.config.authorization;
  const mode = authzModeOf(value) ?? "ownership";
  return (
    <div class="space-y-6">
      <Group title="Policy">
        <ChoiceGroup
          name="authz" label="Authorization policy" value={mode}
          options={[
            ["ownership", "Ownership", "Users can only reach threads they created."],
            ["allow_all", "Allow all", "Any authenticated user can do anything."],
            ["rbac", "Roles and scopes", "Map roles to scopes, on top of owner isolation."],
            ["custom", "Custom backend", "Your own AuthorizationBackend class."],
          ]}
          onPick={(m) => commit((s) => { s.config.authorization = AUTHZ_PRESETS[m](); })}
        />
      </Group>
      {mode === "custom" ? (
        <Group title="Backend">
          <div class="panel">
            <TextRow
              id="authz-path" label="Backend class" path="authorization" placeholder="auth.permissions:MyBackend"
              value={typeof value === "string" ? value : ""} issue={issueAt("authorization")}
              help="Import path of an AuthorizationBackend, as module:attribute."
              onInput={(v) => commit((s) => { s.config.authorization = v; })}
            />
          </div>
        </Group>
      ) : null}
      {mode === "rbac" ? <Rbac sec={sec} value={value} /> : null}
    </div>
  );
}

// Renames apply on blur or Enter; the draft lives here so re-renders do not reset it.
function RoleName({ id, name, onRename }) {
  const [draft, setDraft] = useState(name);
  useEffect(() => setDraft(name), [name]);
  return (
    <div>
      <label for={id} class="sr-only">Role name</label>
      <input
        id={id} type="text" value={draft} class="input font-mono" autocomplete="off" spellcheck={false}
        onInput={(e) => setDraft(e.currentTarget.value)}
        onChange={(e) => { if (!onRename(e.currentTarget.value.trim())) setDraft(name); }}
      />
    </div>
  );
}

function Rbac({ sec, value }) {
  const roleKey = "roles" in value || !("role_scopes" in value) ? "roles" : "role_scopes";
  const roles = isObject(value[roleKey]) ? value[roleKey] : {};
  const scopeOptions = ["*", ...(sec.scopes || [])];
  const entries = Object.entries(roles);
  const setRoles = (next) => commit(() => { value[roleKey] = next; });
  const addRole = () => {
    let n = entries.length + 1;
    while (`role${n}` in roles) n++;
    setRoles({ ...roles, [`role${n}`]: [] });
  };

  return (
    <>
      <Group title="Roles">
        <div class="panel">
          <div class="hidden grid-cols-[10rem_minmax(0,1fr)_auto] gap-3 border-b border-line px-5 py-2.5 sm:grid">
            <span class="text-xs font-medium text-faint">Role</span>
            <span class="text-xs font-medium text-faint">Scopes</span>
            <span class="w-9" />
          </div>
          {entries.length ? (
            <div class="divide-y divide-line">
              {entries.map(([name, scopes], index) => (
                <div key={index} class="grid gap-3 px-5 py-4 sm:grid-cols-[10rem_minmax(0,1fr)_auto] sm:items-start">
                  <RoleName
                    id={`role-name-${index}`} name={name}
                    onRename={(renamed) => {
                      if (!renamed || (renamed !== name && renamed in roles)) return false;
                      setRoles(Object.fromEntries(Object.entries(roles).map(([k, v]) => [k === name ? renamed : k, v])));
                      return true;
                    }}
                  />
                  <Chips
                    id={`role-scopes-${index}`} values={Array.isArray(scopes) ? scopes : []}
                    placeholder="Add a scope" suggestions={scopeOptions}
                    onChange={(next) => setRoles({ ...roles, [name]: next })}
                  />
                  <button
                    type="button" class="icon-btn justify-self-end hover:text-danger" aria-label={`Remove role ${name}`}
                    onClick={() => setRoles(Object.fromEntries(Object.entries(roles).filter(([k]) => k !== name)))}
                  >
                    <Icon name="trash" />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p class="px-5 py-6 text-center text-sm text-muted">No roles yet. Users only get the default scopes.</p>
          )}
          <div class="flex items-center justify-between gap-4 border-t border-line px-5 py-3">
            <p class="text-[13px] text-muted">
              Read from the user's roles (or role) claim. <code class="font-mono">*</code> grants every scope.
            </p>
            <button type="button" class="btn btn-ghost" onClick={addRole}><Icon name="plus" />Add role</button>
          </div>
        </div>
      </Group>
      <Group title="Defaults">
        <div class="panel divide-y divide-line">
          <div class="px-5 py-4">
            <FieldMeta
              label="Default scopes" path="authorization.default_scopes" id="rbac-default-scopes"
              help="Granted to every authenticated user, even without a role."
            />
            <div class="mt-3">
              <Chips
                id="rbac-default-scopes" values={Array.isArray(value.default_scopes) ? value.default_scopes : []}
                placeholder="graph:read" suggestions={scopeOptions}
                onChange={(next) => commit(() => { value.default_scopes = next; })}
              />
            </div>
          </div>
          <Row>
            <FieldMeta
              label="Thread isolation" path="authorization.isolation" id="rbac-isolation"
              help="owner keeps each user's threads private; none shares them."
            />
            <div class="min-w-0 sm:pt-0.5">
              <Select
                id="rbac-isolation" options={[["owner", "owner"], ["none", "none"]]} value={value.isolation ?? "owner"}
                onChange={(v) => commit(() => { value.isolation = v; })}
              />
            </div>
          </Row>
        </div>
      </Group>
    </>
  );
}

// ------------------------------------------------------------------ remote tools

export function RemoteToolsWidget() {
  const tools = Array.isArray(store.config.remote_tools) ? store.config.remote_tools : [];
  const addTool = () => {
    commit((s) => {
      tools.push({ node: "", name: "", description: "", parameters: { type: "object", properties: {}, required: [] } });
      s.config.remote_tools = tools;
    });
    requestAnimationFrame(() => document.getElementById(`tool-${tools.length - 1}-name`)?.focus());
  };

  if (!tools.length) {
    return (
      <div class="rounded-xl border border-dashed border-line-strong bg-surface px-6 py-10 text-center">
        <div class="mx-auto flex size-11 items-center justify-center rounded-full bg-raised text-faint">
          <Icon name="wrench" class="size-5" />
        </div>
        <p class="mt-4 text-sm font-semibold text-ink">No remote tools yet</p>
        <p class="mx-auto mt-1 max-w-sm text-sm leading-6 text-muted">
          Declare a tool here and the client that calls the API runs it, for example to read the user's location.
        </p>
        <button type="button" class="btn btn-outline mt-5" onClick={addTool}><Icon name="plus" />Add remote tool</button>
      </div>
    );
  }

  return (
    <div class="space-y-4">
      {tools.map((tool, index) => <ToolCard key={index} tools={tools} tool={tool} index={index} />)}
      <button
        type="button" onClick={addTool}
        class="focus-ring flex h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-line-strong text-sm font-medium text-muted transition-colors duration-150 hover:border-brand hover:text-brand"
      >
        <Icon name="plus" />Add remote tool
      </button>
    </div>
  );
}

function ToolCard({ tools, tool, index }) {
  const params = store.toolParams[index] ?? { text: JSON.stringify(tool.parameters ?? {}, null, 2), error: null };
  const update = (patch) => commit(() => { tools[index] = { ...tools[index], ...patch }; });
  const at = (key) => `remote_tools[${index}].${key}`;
  return (
    <section class="panel">
      <div class="flex items-center gap-3 border-b border-line px-5 py-3">
        <Icon name="wrench" class="size-4 text-faint" />
        <span class="min-w-0 flex-1 truncate font-mono text-sm font-medium text-ink">{tool.name || `tool_${index + 1}`}</span>
        {tool.node ? <span class="rounded-md border border-line bg-raised px-1.5 py-0.5 font-mono text-xs text-muted">{tool.node}</span> : null}
        <button
          type="button" class="icon-btn hover:text-danger" aria-label={`Remove ${tool.name || "tool"}`}
          onClick={() => commit((s) => { tools.splice(index, 1); s.toolParams = {}; })}
        >
          <Icon name="trash" />
        </button>
      </div>
      <div class="divide-y divide-line">
        <TextRow id={`tool-${index}-name`} label="Tool name" path={at("name")} value={tool.name} placeholder="get_location" onInput={(v) => update({ name: v })} />
        <TextRow id={`tool-${index}-node`} label="Graph node" path={at("node")} value={tool.node} placeholder="MAIN" help="The node whose model may call this tool." onInput={(v) => update({ node: v })} />
        <TextRow id={`tool-${index}-description`} label="Description" path={at("description")} value={tool.description} placeholder="Returns the user's current city" help="What the model reads when deciding to call it." onInput={(v) => update({ description: v })} />
        <div class="px-5 py-4">
          <FieldMeta label="Parameters" path={at("parameters")} help="JSON schema of the arguments. type must be object." id={`tool-${index}-params`} />
          <textarea
            id={`tool-${index}-params`} rows={7} spellcheck={false} value={params.text}
            class={`input mt-3 h-auto py-2.5 font-mono text-[13px] leading-5 ${params.error ? "input-invalid" : ""}`}
            onInput={(e) => {
              const text = e.currentTarget.value;
              commit((s) => {
                try {
                  tools[index] = { ...tools[index], parameters: JSON.parse(text) };
                  s.toolParams[index] = { text, error: null };
                } catch (err) {
                  s.toolParams[index] = { text, error: err.message };
                }
              });
            }}
          />
          <FieldIssue issue={params.error ? { level: "error", message: params.error } : null} />
        </div>
      </div>
    </section>
  );
}
