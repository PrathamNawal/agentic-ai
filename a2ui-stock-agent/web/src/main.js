import { MessageProcessor } from "@a2ui/web_core/v0_9";
import { basicCatalog } from "@a2ui/lit/v0_9"; // also registers <a2ui-surface> and the basic components

const log = document.getElementById("log");
const keyEl = document.getElementById("key");
const modelEl = document.getElementById("model");
const send = document.getElementById("send");

try { keyEl.value = sessionStorage.getItem("groq_key") || ""; } catch {}
keyEl.addEventListener("input", () => { try { sessionStorage.setItem("groq_key", keyEl.value); } catch {} });

// One processor for the page; each agent response creates a new surface.
const processor = new MessageProcessor([basicCatalog]);
let mount = null;
processor.onSurfaceCreated((surface) => {
  const el = document.createElement("a2ui-surface");
  el.surface = surface;
  mount?.appendChild(el);
});

function add(cls, text) {
  const d = document.createElement("div");
  d.className = "msg " + cls;
  d.textContent = text;
  log.append(d);
  d.scrollIntoView({ block: "end" });
  return d;
}

document.getElementById("f").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = document.getElementById("q");
  const message = q.value.trim();
  if (!message) return;
  if (!keyEl.value.trim()) { add("err", "Add your Groq API key above first."); return; }
  q.value = ""; send.disabled = true;
  add("user", message);
  const wait = add("", "…");
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Groq-Api-Key": keyEl.value.trim() },
      body: JSON.stringify({ message, model: modelEl.value }),
    });
    const j = await r.json();
    wait.remove();
    if (!r.ok) { add("err", j.detail || `Error ${r.status}`); return; }
    if (j.a2ui.length) {
      const holder = document.createElement("div");
      holder.className = "surface";
      log.append(holder);
      mount = holder;
      processor.processMessages(j.a2ui);
      holder.scrollIntoView({ block: "end" });
    }
    if (j.text) add("", j.text);
  } catch (err) {
    wait.remove(); add("err", "Request failed: " + err);
  } finally { send.disabled = false; }
});
