// Small building blocks: icons, menus, dialogs, tabs and form rows.
import { For, Show, JSX, createSignal, onMount, onCleanup } from "solid-js";
import { menu, setMenu, Item, closeDialog, msg, setMsg } from "./store";
import { Help } from "./help";

export const Icon = (p: { n: string; size?: number }) => (
  <svg style={p.size ? { width: `${p.size}px`, height: `${p.size}px` } : undefined}><use href={`#i-${p.n}`} /></svg>
);

export const Menu = () => {
  // Open submenus by depth: hovering an item at depth d replaces everything deeper.
  const [subs, setSubs] = createSignal<{ x: number; y: number; px: number; items: Item[] }[]>([]);
  const close = () => { setMenu(null); setSubs([]); };
  const list = (items: Item[], x: number, y: number, depth: number, px = 0): JSX.Element => {
    let el!: HTMLDivElement;
    onMount(() => {
      const r = el.getBoundingClientRect();
      if (r.bottom > innerHeight - 4) el.style.top = `${Math.max(4, innerHeight - r.height - 4)}px`;
      if (r.right > innerWidth - 4) el.style.left = `${Math.max(4, depth ? px - r.width : innerWidth - r.width - 4)}px`;
    });
    return (
      <div class="menu" ref={el} style={{ left: `${x}px`, top: `${y}px` }} onMouseDown={e => e.stopPropagation()} onContextMenu={e => e.preventDefault()}>
        <For each={items}>{it => it === "-" ? <hr /> : (
          <button disabled={it.off} classList={{ on: it.on }}
            onMouseEnter={e => { const r = e.currentTarget.getBoundingClientRect(); setSubs([...subs().slice(0, depth), ...(it.sub ? [{ x: r.right, y: r.top - 4, px: r.left, items: it.sub }] : [])]); }}
            onClick={() => { if (it.sub) return; close(); it.run?.(); }}>
            <i class="tick">{it.on ? "✓" : it.icon ? <Icon n={it.icon} /> : ""}</i><span>{it.label}</span>{it.keys && <kbd>{it.keys}</kbd>}{it.sub && <b class="more">›</b>}
          </button>
        )}</For>
      </div>
    );
  };
  const down = (e: MouseEvent) => { if (!(e.target as HTMLElement).closest?.(".menu")) close(); };
  onMount(() => document.addEventListener("mousedown", down));
  onCleanup(() => document.removeEventListener("mousedown", down));
  return (
    <Show when={menu()}>{m => <>{list(m().items, m().x, m().y, 0)}<For each={subs()}>{(s, i) => list(s.items, s.x, s.y, i() + 1, s.px)}</For></>}</Show>
  );
};

export const Toast = () => (
  <Show when={msg()}>{m => <div id="toast" classList={{ ok: m().ok }} onClick={() => setMsg(null)}>{m().text}</div>}</Show>
);

/** A modal dialog. `ok` returns false to keep it open. */
export const Dialog = (p: { title: string; wide?: boolean; children: JSX.Element; ok?: () => boolean | void | Promise<boolean | void>; okText?: string; extra?: JSX.Element; cancel?: string; side?: boolean; help?: string }) => {
  const done = async () => { if (!p.ok || (await p.ok()) !== false) closeDialog(); };
  const key = (e: KeyboardEvent) => {
    if (e.key === "Escape") { e.stopPropagation(); closeDialog(); }
    if (e.key === "Enter" && !(e.target instanceof HTMLTextAreaElement) && !(e.target instanceof HTMLButtonElement)) { e.preventDefault(); done(); }
  };
  let el!: HTMLDivElement;
  /** Drag the dialog by its title bar, to see what is behind it. */
  const drag = (e: MouseEvent) => {
    if (e.button !== 0 || (e.target as HTMLElement).closest("button")) return;
    const m = new DOMMatrix(getComputedStyle(el).transform === "none" ? undefined : getComputedStyle(el).transform), x0 = e.clientX - m.e, y0 = e.clientY - m.f;
    const move = (ev: MouseEvent) => { el.style.transform = `translate(${ev.clientX - x0}px, ${Math.max(-el.offsetTop, ev.clientY - y0)}px)`; };
    const up = () => { removeEventListener("mousemove", move); removeEventListener("mouseup", up); };
    addEventListener("mousemove", move); addEventListener("mouseup", up);
    e.preventDefault();
  };
  onMount(() => ((el.querySelector("input:not([type=checkbox]),textarea") ?? el.querySelector(".btn.pri") ?? el.querySelector("footer .btn")) as HTMLElement | null)?.focus());
  return (
    <div class="ov" classList={{ dock: p.side }} onKeyDown={key}>
      <div class="dlg" classList={{ wide: p.wide }} ref={el}>
        <header onMouseDown={drag}>{p.title}{p.help && <Help k={p.help} />}<button class="x" onClick={closeDialog}>×</button></header>
        <div class="bd">{p.children}</div>
        <footer>{p.extra}<span class="grow" />{p.ok && <button class="btn pri" onClick={done}>{p.okText ?? "OK"}</button>}<button class="btn" onClick={closeDialog}>{p.cancel ?? (p.ok ? "Cancel" : "Close")}</button></footer>
      </div>
    </div>
  );
};

export const Tabs = (p: { tabs: [string, string][]; on: string; set: (k: string) => void }) => (
  <div class="dtabs"><For each={p.tabs}>{([k, l]) => <button classList={{ on: p.on === k }} onClick={() => p.set(k)}>{l}</button>}</For></div>
);

export const Row = (p: { label: string; children: JSX.Element }) => <><label>{p.label}</label><div>{p.children}</div></>;
export const Text = (p: { value: string | number | null | undefined; set: (v: string) => void; type?: string; disabled?: boolean; placeholder?: string; list?: string }) => (
  <input type={p.type ?? "text"} value={p.value ?? ""} disabled={p.disabled} placeholder={p.placeholder} list={p.list} onChange={e => p.set(e.currentTarget.value)} />
);
export const Pick = (p: { value: string; set: (v: string) => void; options: (string | [string, string])[]; disabled?: boolean }) => (
  <select value={p.value} disabled={p.disabled} onChange={e => p.set(e.currentTarget.value)}>
    <For each={p.options}>{o => typeof o === "string" ? <option value={o}>{o}</option> : <option value={o[0]}>{o[1]}</option>}</For>
  </select>
);
export const Check = (p: { label: string; value: boolean; set: (v: boolean) => void; disabled?: boolean }) => (
  <label class="chk"><input type="checkbox" checked={p.value} disabled={p.disabled} onChange={e => p.set(e.currentTarget.checked)} />{p.label}</label>
);
export const Seg = (p: { options: [string, string][]; value: string; set: (v: string) => void }) => (
  <div class="seg"><For each={p.options}>{([k, l]) => <button classList={{ on: p.value === k }} onClick={() => p.set(k)}>{l}</button>}</For></div>
);
