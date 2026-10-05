import { openInspector, save, scrollToTier, setAllOpen, setSection, toggleOpen, validate } from "./actions.js";
import { Field, fieldGroups } from "./fields.jsx";
import { SECTION_ICONS } from "./icons.js";
import { WIDGET_FIELD_IDS, counts, isDirty, isOn, issuesFor, plural, store } from "./store.js";
import { Callout, EmptyPanel, Group, Icon, IssueCallout, Pill, Toggle } from "./ui.jsx";
import { AuthWidget, AuthorizationWidget, RemoteToolsWidget } from "./widgets.jsx";

// ------------------------------------------------------------------ header

function FileInfo() {
  const name = store.path.split(/[\\/]/).pop() || "agentflow.json";
  const dir = store.path.slice(0, store.path.length - name.length);
  let badge = null;
  if (!store.schema) badge = null;
  else if (!store.exists) badge = <Pill class="bg-brand-soft text-brand">New</Pill>;
  else if (isDirty()) badge = <Pill class="bg-warn-soft text-warn">Unsaved</Pill>;
  else badge = <Pill class="bg-ok-soft text-ok">Saved</Pill>;
  return (
    <div class="flex min-w-0 flex-1 items-center gap-2" title={store.path || undefined}>
      <Icon name="file" class="size-4 text-faint" />
      <span class="truncate font-mono text-[13px] font-medium text-ink">{name}</span>
      {badge}
      {dir ? (
        <span class="hidden min-w-0 truncate font-mono text-xs text-faint lg:block" dir="rtl"><bdi>{dir}</bdi></span>
      ) : null}
    </div>
  );
}

export function Header() {
  const { errors, warnings } = counts();
  const ready = !!store.schema && !store.fatal;
  const validating = store.busy === "validate";
  return (
    <header class="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-line bg-surface/95 px-3 backdrop-blur sm:gap-3 sm:px-4">
      <div class="flex shrink-0 items-center gap-2.5">
        <svg viewBox="0 0 32 32" class="size-7 shrink-0" aria-hidden="true">
          <rect width="32" height="32" rx="8" fill="#2563eb" />
          <path d="M10 11 22 11M10 11 16 22M22 11 16 22" stroke="white" stroke-opacity=".55" stroke-width="2" />
          <circle cx="10" cy="11" r="3" fill="white" /><circle cx="22" cy="11" r="3" fill="white" /><circle cx="16" cy="22" r="3" fill="white" />
        </svg>
        <div class="hidden items-baseline gap-1.5 md:flex">
          <span class="text-[15px] font-semibold tracking-tight text-ink">Agentflow</span>
          <span class="text-[15px] text-faint">Config</span>
        </div>
      </div>
      <span class="hidden h-6 w-px shrink-0 bg-line md:block" aria-hidden="true" />
      <FileInfo />
      <button type="button" class="icon-btn relative xl:hidden" aria-label="Open problems and JSON preview" onClick={() => openInspector()}>
        <Icon name="panel" class="size-[18px]" />
        {errors || warnings ? (
          <span class={`absolute top-1 right-1 flex size-4 items-center justify-center rounded-full text-[10px] font-bold text-white ${errors ? "bg-danger" : "bg-warn"}`}>
            {errors || warnings}
          </span>
        ) : null}
      </button>
      <button type="button" class="btn btn-outline" aria-label="Validate configuration" disabled={!ready || !!store.busy} onClick={validate}>
        <Icon name={validating ? "spinner" : "checkCircle"} class={`size-4 ${validating ? "animate-spin" : ""}`} />
        <span class="hidden sm:inline">Validate</span>
      </button>
      <button
        type="button" class="btn btn-primary" onClick={save}
        disabled={!ready || !!store.busy || (store.exists && !isDirty() && !store.parseError)}
      >
        {store.busy === "save" ? <Icon name="spinner" class="size-4 animate-spin" /> : null}
        {store.exists ? "Save" : "Create file"}
        <span class="kbd hidden lg:inline-flex">Ctrl S</span>
      </button>
    </header>
  );
}

// ------------------------------------------------------------------ page

export function Page() {
  if (store.fatal) {
    return (
      <div class="panel mt-10">
        <EmptyPanel icon="xCircle" tint="text-danger" title={store.fatal.title} text={store.fatal.text} />
      </div>
    );
  }
  if (!store.schema) {
    return (
      <div class="animate-pulse space-y-4 pt-8" aria-label="Loading">
        <div class="h-7 w-48 rounded-md bg-raised" />
        <div class="h-4 w-80 max-w-full rounded-md bg-raised" />
        {[0, 1, 2, 3].map((i) => <div key={i} class="h-16 rounded-xl bg-raised" />)}
      </div>
    );
  }
  return (
    <>
      <div class="pt-8">
        <h1 class="text-xl font-semibold tracking-tight text-ink">Server configuration</h1>
        <p class="mt-1 max-w-prose text-sm leading-6 text-muted">
          Every agentflow.json option on one page. Fill in the essentials to get running, then switch on what you
          need on the way to production.
        </p>
      </div>
      <Toolbar />
      {store.parseError ? (
        <div class="mt-6">
          <Callout
            kind="warn" title="The existing file is not valid JSON"
            lines={[`${store.parseError}. The form starts from defaults; saving replaces the file and keeps the old one as agentflow.json.bak.`]}
          />
        </div>
      ) : null}
      {store.tiers.map((tier) => <Tier key={tier.id} tier={tier} />)}
    </>
  );
}

function Toolbar() {
  const allOpen = store.sections.every((s) => store.open.has(s.id));
  return (
    <div class="sticky top-14 z-20 -mx-4 mt-6 flex items-center gap-2 border-b border-line bg-canvas/90 px-4 py-2 backdrop-blur sm:-mx-8 sm:px-8">
      <nav class="-ml-2.5 flex min-w-0 flex-1 gap-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" aria-label="Jump to a tier">
        {store.tiers.map((tier) => <TierLink key={tier.id} tier={tier} />)}
      </nav>
      <button
        type="button" class="btn btn-ghost" aria-label={allOpen ? "Collapse all sections" : "Expand all sections"}
        onClick={() => setAllOpen(!allOpen)}
      >
        <Icon name={allOpen ? "collapse" : "expand"} />
        <span class="hidden sm:inline">{allOpen ? "Collapse all" : "Expand all"}</span>
      </button>
      <a href={store.schema.docs_url} target="_blank" rel="noopener" class="btn btn-ghost" aria-label="Configuration reference">
        <Icon name="book" />
        <span class="hidden sm:inline">Reference</span>
      </a>
    </div>
  );
}

function TierLink({ tier }) {
  const on = tier.list.filter(isOn).length;
  const { errors, warnings } = counts(store.issues.filter((i) => tier.list.some((s) => s.id === i.section)));
  return (
    <a
      href={`#tier-${tier.id}`} title={`${on} of ${plural(tier.list.length, "section")} on`}
      class="focus-ring inline-flex h-9 shrink-0 items-center gap-2 rounded-lg px-2.5 text-sm text-muted transition-colors duration-150 hover:bg-raised hover:text-ink"
      onClick={(e) => { e.preventDefault(); scrollToTier(tier.id); }}
    >
      <span class="font-medium">{tier.title}</span>
      <span class="font-mono text-xs text-faint tabular-nums">{on}/{tier.list.length}</span>
      {errors || warnings ? <span class={`size-1.5 rounded-full ${errors ? "bg-danger" : "bg-warn"}`} /> : null}
    </a>
  );
}

function Tier({ tier }) {
  const on = tier.list.filter(isOn).length;
  return (
    <section id={`tier-${tier.id}`} class="mt-10 scroll-mt-28" aria-labelledby={`tier-${tier.id}-title`}>
      <div class="mb-3">
        <div class="flex items-baseline gap-3">
          <h2 id={`tier-${tier.id}-title`} class="text-base font-semibold tracking-tight text-ink">{tier.title}</h2>
          <span class="text-xs text-faint">{on} of {tier.list.length} on</span>
        </div>
        <p class="mt-0.5 text-sm text-muted">{tier.tagline}</p>
      </div>
      <div class="space-y-3">
        {tier.list.map((sec) => <SectionCard key={sec.id} sec={sec} />)}
      </div>
    </section>
  );
}

function SectionCard({ sec }) {
  const on = isOn(sec);
  const open = store.open.has(sec.id);
  const { errors, warnings } = counts(issuesFor(sec.id));
  const bodyId = `body-${sec.id}`;

  let status = null;
  if (errors) {
    status = (
      <span class="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-danger" title={plural(errors, "error")}>
        <Icon name="xCircle" class="size-3.5" />{errors}
      </span>
    );
  } else if (warnings) {
    status = (
      <span class="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-warn" title={plural(warnings, "warning")}>
        <Icon name="alert" class="size-3.5" />{warnings}
      </span>
    );
  }

  return (
    <section id={`sec-${sec.id}`} class={`panel scroll-mt-32 ${errors ? "border-danger/40" : ""}`}>
      <div class="flex items-center gap-3 pr-4 sm:pr-5">
        <h3 class="min-w-0 flex-1">
          <button
            type="button" id={`acc-${sec.id}`} aria-expanded={open ? "true" : "false"} aria-controls={bodyId}
            class="focus-ring flex w-full cursor-pointer items-center gap-3 rounded-xl py-3.5 pl-3 text-left sm:pl-4"
            onClick={() => toggleOpen(sec.id)}
          >
            <Icon name="chevronDown" class={`size-4 text-faint transition-transform duration-200 ${open ? "" : "-rotate-90"}`} />
            <span class={`flex size-9 shrink-0 items-center justify-center rounded-lg border border-line ${on ? "bg-brand-soft text-brand" : "bg-raised text-faint"}`}>
              <Icon name={SECTION_ICONS[sec.id] || "box"} class="size-[18px]" />
            </span>
            <span class="min-w-0 flex-1">
              <span class="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                <span class={`text-sm font-semibold ${on ? "text-ink" : "text-muted"}`}>{sec.title}</span>
                {sec.key ? (
                  <code class="hidden rounded border border-line bg-raised px-1.5 font-mono text-[11px] leading-4 text-faint sm:inline">{sec.key}</code>
                ) : null}
              </span>
              <span class="mt-0.5 block text-[13px] leading-5 text-muted">{sec.description}</span>
            </span>
            {status}
          </button>
        </h3>
        {sec.optional ? (
          <div class="flex shrink-0 items-center gap-2.5">
            <span class="hidden w-6 text-xs font-medium text-faint sm:inline">{on ? "On" : "Off"}</span>
            <Toggle id={`toggle-${sec.id}`} on={on} label={`${on ? "Turn off" : "Turn on"} ${sec.title}`} onChange={(v) => setSection(sec, v)} />
          </div>
        ) : null}
      </div>
      {/* grid-rows 0fr -> 1fr animates the height without measuring it. */}
      <div
        id={bodyId} role="region" aria-labelledby={`acc-${sec.id}`} inert={!open}
        class={`grid transition-[grid-template-rows] duration-200 ease-out ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}
      >
        <div class="min-h-0 overflow-hidden">
          <div class="space-y-6 rounded-b-xl border-t border-line bg-canvas/60 px-4 py-5 sm:px-5">
            <SectionBody sec={sec} on={on} />
          </div>
        </div>
      </div>
    </section>
  );
}

function SectionBody({ sec, on }) {
  if (!on) {
    return (
      <div class="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
        <p class="text-sm leading-6 text-muted">
          <code class="font-mono text-[13px] text-body">{sec.key}</code> is not in agentflow.json. {sec.off_summary || ""}
        </p>
        <button type="button" class="btn btn-outline" onClick={() => setSection(sec, true)}>
          <Icon name="power" />Turn on {sec.title.toLowerCase()}
        </button>
      </div>
    );
  }
  const inline = new Set([...sec.fields.map((f) => f.path.join(".")), ...Object.keys(WIDGET_FIELD_IDS)]);
  const general = issuesFor(sec.id).filter((i) => !inline.has(i.path));
  return (
    <>
      {general.length ? <div class="space-y-2">{general.map((issue, i) => <IssueCallout key={i} issue={issue} />)}</div> : null}
      {sec.notes?.length ? <Callout kind="info" lines={sec.notes} /> : null}
      {sec.widget === "auth" ? <AuthWidget /> : null}
      {sec.widget === "authorization" ? <AuthorizationWidget sec={sec} /> : null}
      {sec.widget === "remote_tools" ? <RemoteToolsWidget /> : null}
      {fieldGroups(sec).map((group) => (
        <Group key={group.name} title={group.name}>
          <div class="panel divide-y divide-line">
            {group.fields.map((f) => <Field key={f.path.join(".")} field={f} />)}
          </div>
        </Group>
      ))}
    </>
  );
}

