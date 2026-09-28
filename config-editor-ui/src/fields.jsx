import { useEffect, useState } from "preact/hooks";
import { commit, deletePath, getPath, issueAt, setPath, store, valueOrDefault } from "./store.js";
import { Chips, FieldIssue, FieldMeta, Row, Select, Toggle } from "./ui.jsx";

// Fields grouped by their `group` label, skipping ones whose show_if does not match.
export function fieldGroups(sec) {
  const groups = [];
  for (const f of sec.fields) {
    if (f.show_if && valueOrDefault(f.show_if.path) !== f.show_if.equals) continue;
    const name = f.group || "";
    let group = groups.find((g) => g.name === name);
    if (!group) groups.push(group = { name, fields: [] });
    group.fields.push(f);
  }
  return groups;
}

const put = (path, value) => commit((s) => {
  if (value === undefined) deletePath(s.config, path);
  else setPath(s.config, path, value);
});

// Keeps the raw text while typing so "0." or "1e" do not get rewritten mid-edit.
function NumberInput({ id, value, field, invalid }) {
  const [text, setText] = useState(String(value ?? ""));
  useEffect(() => {
    if (text === "" ? value !== undefined : Number(text) !== value) setText(String(value ?? ""));
  }, [value]);
  return (
    <input
      id={id} type="number" inputmode="decimal" value={text}
      min={field.min} step={field.step} placeholder={field.placeholder ?? (field.default ?? "")}
      class={`input font-mono tabular-nums ${invalid ? "input-invalid" : ""}`}
      onInput={(e) => {
        const raw = e.currentTarget.value;
        setText(raw);
        if (raw === "") put(field.path, undefined);
        else if (!Number.isNaN(Number(raw))) put(field.path, Number(raw));
      }}
    />
  );
}

export function Field({ field: f }) {
  const key = f.path.join(".");
  const id = `f-${f.path.join("-")}`;
  const value = getPath(store.config, f.path);
  const issue = issueAt(key);
  const invalid = issue?.level === "error";

  if (f.type === "bool") {
    return (
      <div class="flex items-start justify-between gap-6 px-5 py-4">
        <div class="min-w-0">
          <FieldMeta label={f.label} path={key} help={f.help} id={id} />
          <FieldIssue issue={issue} />
        </div>
        <div class="pt-0.5">
          <Toggle id={id} on={(value ?? f.default ?? false) === true} label={f.label} onChange={(v) => put(f.path, v)} />
        </div>
      </div>
    );
  }

  if (f.type === "list") {
    return (
      <div class="px-5 py-4">
        <FieldMeta label={f.label} path={key} help={f.help} id={id} required={f.required} />
        <div class="mt-3">
          <Chips
            id={id} values={Array.isArray(value) ? value : []} placeholder={f.placeholder}
            onChange={(next) => put(f.path, next.length ? next : undefined)}
          />
          <FieldIssue issue={issue} />
        </div>
      </div>
    );
  }

  let control;
  if (f.type === "select") {
    control = (
      <Select
        id={id} options={f.options.map((o) => [o, o])} value={value ?? f.default ?? f.options[0]}
        invalid={invalid} onChange={(v) => put(f.path, v)}
      />
    );
  } else if (f.type === "number") {
    control = <NumberInput id={id} value={value} field={f} invalid={invalid} />;
  } else {
    control = (
      <input
        id={id} type="text" value={value ?? ""} placeholder={f.placeholder}
        autocomplete="off" spellcheck={false} autocapitalize="off"
        class={`input font-mono ${invalid ? "input-invalid" : ""}`}
        onInput={(e) => put(f.path, e.currentTarget.value === "" ? undefined : e.currentTarget.value)}
      />
    );
  }
  return (
    <Row>
      <FieldMeta label={f.label} path={key} help={f.help} id={id} required={f.required} />
      <div class="min-w-0 sm:pt-0.5">
        {control}
        <FieldIssue issue={issue} />
      </div>
    </Row>
  );
}
