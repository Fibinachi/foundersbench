"""Founders Bench desktop app — a windowed box with a CLI inside.

First launch prompts for the user's API key (BYOK); the key is stored
locally at ~/.foundersbench/config.json (mode 600) and never leaves
the machine except to the chosen provider.

Usage:
    python -m foundersbench.app

Layout:
    [founder selector] [Brief the bench...]
    +--------------------------------------------------+
    | transcript (read-only)                           |
    |                                                  |
    +--------------------------------------------------+
    | input entry                            [Send]    |
    | status bar                                       |
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import sys
import threading
from datetime import datetime
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk
except ImportError:  # pragma: no cover
    print("Founders Bench needs tkinter (python3-tk).", file=sys.stderr)
    sys.exit(1)

from foundersbench.founders import FOUNDERS, enabled_founders

CONFIG_DIR = Path.home() / ".foundersbench"
CONFIG_PATH = CONFIG_DIR / "config.json"

PROVIDERS = (
    ("anthropic", "Anthropic (recommended — best citation discipline)"),
    ("openai", "OpenAI"),
)
ENV_FOR = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}


# ---------------------------------------------------------------------------
# API key handling: env -> config file -> first-launch prompt
# ---------------------------------------------------------------------------

def _read_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _write_config(provider: str, api_key: str) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps({"provider": provider, "api_key": api_key}),
        encoding="utf-8",
    )
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass


def resolve_api_key() -> tuple[str | None, str | None]:
    """Return (provider, api_key), preferring env vars, then saved config."""
    for provider, env in ENV_FOR.items():
        key = os.environ.get(env)
        if key:
            return provider, key
    cfg = _read_config()
    if cfg.get("api_key"):
        return cfg.get("provider", "anthropic"), cfg["api_key"]
    return None, None


class ApiKeyDialog(tk.Toplevel):
    """First-launch modal: pick a provider, paste a key, save locally."""

    def __init__(self, parent: tk.Tk):
        super().__init__(parent)
        self.title("Founders Bench — API key")
        self.resizable(False, False)
        self.result: tuple[str, str] | None = None
        self.transient(parent)
        self.grab_set()

        ttk.Label(
            self,
            text="Founders Bench brings your own key.\n"
                 "Enter an API key to run the bench — it is stored\n"
                 "only on this machine.",
            justify="left",
        ).pack(padx=20, pady=(20, 10), anchor="w")

        self.provider_var = tk.StringVar(value="anthropic")
        for value, label in PROVIDERS:
            ttk.Radiobutton(
                self, text=label, value=value, variable=self.provider_var
            ).pack(padx=20, anchor="w")

        ttk.Label(self, text="API key:").pack(padx=20, pady=(10, 0), anchor="w")
        self.key_entry = ttk.Entry(self, width=52, show="•")
        self.key_entry.pack(padx=20, pady=(0, 10))
        self.key_entry.focus_set()

        btns = ttk.Frame(self)
        btns.pack(pady=(0, 20))
        ttk.Button(btns, text="Save & continue",
                   command=self._on_save).pack(side="left", padx=5)
        ttk.Button(btns, text="Skip for now",
                   command=self._on_skip).pack(side="left", padx=5)

        self.bind("<Return>", lambda _e: self._on_save())
        self.protocol("WM_DELETE_WINDOW", self._on_skip)
        self._center(parent)

    def _center(self, parent: tk.Tk) -> None:
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _on_save(self) -> None:
        key = self.key_entry.get().strip()
        if not key:
            messagebox.showwarning("Missing key", "Paste an API key, or skip for now.")
            return
        provider = self.provider_var.get()
        _write_config(provider, key)
        os.environ[ENV_FOR[provider]] = key
        self.result = (provider, key)
        self.destroy()

    def _on_skip(self) -> None:
        self.result = None
        self.destroy()


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

def load_documents(corpus_files: list[str]) -> list[dict]:
    docs: list[dict] = []
    seen: set[str] = set()
    base = Path(__file__).resolve().parent.parent.parent
    for rel in corpus_files:
        path = base / rel
        if not path.exists():
            print(f"  corpus file not found, skipping: {rel}", file=sys.stderr)
            continue
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("document_id") in seen:
                    continue
                seen.add(d["document_id"])
                docs.append(d)
    return docs


def to_historical_documents(raw: list[dict]):
    from foundersbench.models import HistoricalDocument

    out = []
    for r in raw:
        date = None
        if r.get("date"):
            try:
                date = datetime.fromisoformat(r["date"])
            except ValueError:
                pass
        out.append(HistoricalDocument(
            document_id=r["document_id"],
            author=r.get("author", ""),
            date=date,
            recipient=r.get("recipient"),
            collection=r.get("collection", ""),
            corpus_layer=r.get("corpus_layer", ""),
            title=r.get("title", ""),
            full_text=r.get("full_text", ""),
        ))
    return out


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class FoundersBenchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Founders Bench")
        root.geometry("920x700")
        root.minsize(640, 480)

        provider, _key = resolve_api_key()
        if provider is None:
            # Hidden root while the modal key dialog runs.
            root.withdraw()
            dlg = ApiKeyDialog(root)
            root.wait_window(dlg)
            root.deiconify()
            provider, _key = resolve_api_key()

        self.provider_name = provider or "none"
        self.briefing: str | None = None

        # --- background worker (asyncio in its own thread) ---
        self._results: queue.Queue = queue.Queue()
        self._loop = asyncio.new_event_loop()
        self._worker = threading.Thread(target=self._run_loop, daemon=True)
        self._worker.start()

        # --- corpus + agent service (loaded lazily per founder) ---
        self._indexes: dict[str, object] = {}
        self._services: dict[str, object] = {}
        self._agents: dict[str, object] = {}
        self._raw_docs: list[dict] | None = None

        self._build_widgets()
        self._refresh_status("Loading corpus…")
        # Load corpus off the UI thread; index build can take a few seconds.
        threading.Thread(target=self._load_corpus_bg, daemon=True).start()
        self.root.after(100, self._pump_results)

    # -- setup ----------------------------------------------------------

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _build_widgets(self) -> None:
        top = ttk.Frame(self.root, padding=(10, 8, 10, 4))
        top.pack(fill="x")

        ttk.Label(top, text="Speaking with:").pack(side="left")
        self.founder_var = tk.StringVar()
        self.founder_menu = ttk.OptionMenu(top, self.founder_var, None)
        self.founder_menu.pack(side="left", padx=(6, 12))

        menu = self.founder_menu["menu"]
        self._founder_keys: list[str] = []
        first_enabled: str | None = None
        for key, cfg in FOUNDERS.items():
            label = cfg["name"] + ("" if cfg.get("enabled") else " — coming soon")
            if cfg.get("enabled"):
                self._founder_keys.append(key)
                if first_enabled is None:
                    first_enabled = key
                menu.add_radiobutton(
                    label=cfg["name"], variable=self.founder_var, value=key,
                    command=self._on_founder_change,
                )
            else:
                menu.add_command(label=label, state="disabled")
        if first_enabled:
            self.founder_var.set(first_enabled)

        ttk.Button(top, text="Brief the bench…",
                   command=self._on_brief).pack(side="right")

        self.transcript = scrolledtext.ScrolledText(
            self.root, wrap="word", state="disabled", font=("TkDefaultFont", 11),
            padx=12, pady=10,
        )
        self.transcript.pack(fill="both", expand=True, padx=10, pady=4)
        self.transcript.tag_configure("you", foreground="#1a56db",
                                      font=("TkDefaultFont", 11, "bold"))
        self.transcript.tag_configure("agent", foreground="#111827",
                                      font=("TkDefaultFont", 11, "bold"))
        self.transcript.tag_configure("sources", foreground="#6b7280",
                                      font=("TkDefaultFont", 10, "italic"))
        self.transcript.tag_configure("system", foreground="#6b7280",
                                      font=("TkDefaultFont", 10, "italic"))

        bottom = ttk.Frame(self.root, padding=(10, 4, 10, 6))
        bottom.pack(fill="x")
        self.input_entry = ttk.Entry(bottom)
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.input_entry.bind("<Return>", lambda _e: self._on_send())
        send_btn = ttk.Button(bottom, text="Send", command=self._on_send)
        send_btn.pack(side="right")

        self.status_var = tk.StringVar(value="Starting…")
        ttk.Label(self.root, textvariable=self.status_var,
                  relief="sunken", anchor="w",
                  font=("TkDefaultFont", 9)).pack(fill="x", side="bottom")

        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Change API key…", command=self._on_change_key)
        filemenu.add_separator()
        filemenu.add_command(label="Quit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

    # -- corpus ----------------------------------------------------------

    def _load_corpus_bg(self) -> None:
        from foundersbench.agent_service import FounderAgentService
        from foundersbench.models import BenchMode, BenchSession, FounderAgent
        from foundersbench.providers import default_provider
        from foundersbench.retrieval import CorpusIndex

        # Union of corpus files across enabled founders.
        files: list[str] = []
        for key in enabled_founders():
            for rel in FOUNDERS[key]["corpus_files"]:
                if rel not in files:
                    files.append(rel)
        self._raw_docs = load_documents(files)
        documents = to_historical_documents(self._raw_docs)
        provider = default_provider()

        for key, cfg in enabled_founders().items():
            agent = FounderAgent(
                name=cfg["name"], era=cfg["era"], role=cfg["role"],
                affiliation=cfg["affiliation"],
                corpus_collections=cfg["corpus_collections"],
                death_year=cfg["death_year"],
            )
            # Per-founder index keeps retrieval scoped; cheap at this scale.
            scoped = [d for d in documents
                      if d.collection in set(cfg["corpus_collections"])]
            self._agents[key] = agent
            self._indexes[key] = CorpusIndex(scoped)
            self._services[key] = FounderAgentService(self._indexes[key], provider)
            self._results.put(("status",
                               f"{cfg['name']}: {len(scoped)} documents indexed"))
        self._results.put(("ready", provider.name if provider.is_configured() else "none"))

    # -- chat ------------------------------------------------------------

    def _append(self, text: str, tag: str | None = None) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", text, tag or ())
        self.transcript.insert("end", "\n")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _on_founder_change(self) -> None:
        key = self.founder_var.get()
        cfg = FOUNDERS.get(key, {})
        self._append(f"— Now speaking with {cfg.get('name', key)}. "
                     f"Ask about the Constitution, the Bill of Rights, "
                     f"or brief the bench on modern facts. —", "system")
        self._refresh_status()

    def _on_brief(self) -> None:
        dlg = tk.Toplevel(self.root)
        dlg.title("Brief the bench")
        dlg.geometry("560x320")
        dlg.transient(self.root)
        dlg.grab_set()
        ttk.Label(
            dlg,
            text="Describe modern facts the founder never encountered\n"
                 "(e.g. Flock cameras, thermal imaging). They will apply\n"
                 "their principles to your briefing.",
            justify="left",
        ).pack(padx=16, pady=(14, 6), anchor="w")
        txt = scrolledtext.ScrolledText(dlg, wrap="word", height=10)
        txt.pack(fill="both", expand=True, padx=16)
        txt.focus_set()

        def _ok() -> None:
            self.briefing = txt.get("1.0", "end").strip() or None
            if self.briefing:
                self._append("— Briefing attached to your next question. —",
                             "system")
            dlg.destroy()

        ttk.Button(dlg, text="Attach to next question",
                   command=_ok).pack(pady=10)

    def _on_send(self) -> None:
        text = self.input_entry.get().strip()
        if not text:
            return
        key = self.founder_var.get()
        if key not in self._services:
            self._append("Corpus still loading — one moment.", "system")
            return
        self.input_entry.delete(0, "end")
        self._append(f"You: {text}", "you")
        self._append("…", "system")
        self._thinking_mark = True
        future = asyncio.run_coroutine_threadsafe(
            self._ask(key, text), self._loop)
        future.add_done_callback(
            lambda fut: self._results.put(("turn", fut)))

    async def _ask(self, key: str, text: str):
        from foundersbench.models import BenchMode, BenchSession
        agent = self._agents[key]
        service = self._services[key]
        session = BenchSession(mode=BenchMode.ONE_ON_ONE, era="Founding",
                               user_question=text,
                               briefing_context=self.briefing)
        self.briefing = None  # one-shot
        return await service.respond(agent, session, text)

    def _pump_results(self) -> None:
        try:
            while True:
                kind, payload = self._results.get_nowait()
                if kind == "turn":
                    self._remove_thinking_mark()
                    try:
                        turn = payload.result()
                    except Exception as e:  # pragma: no cover
                        self._append(f"[error] {e}", "system")
                        continue
                    self._append(f"{turn.speaker_name}: {turn.text}")
                    if turn.citations:
                        self._append("Sources:", "sources")
                        for c in turn.citations:
                            self._append(f"  [{c.label}]", "sources")
                    if turn.is_fallback:
                        self._append("— provider unreachable or no key; "
                                     "response is a labeled fallback —",
                                     "system")
                elif kind == "status":
                    self._refresh_status(str(payload))
                elif kind == "ready":
                    name = str(payload)
                    if name == "none":
                        self._append("— No API key configured. Responses will "
                                     "be labeled fallbacks until you add a "
                                     "key (File → Change API key…). —",
                                     "system")
                    self._refresh_status()
                    key = self.founder_var.get()
                    cfg = FOUNDERS.get(key, {})
                    self._append(
                        f"— {cfg.get('name', 'Founder')} is ready. Ask about "
                        f"the Constitution or the Bill of Rights. —",
                        "system")
        except queue.Empty:
            pass
        self.root.after(100, self._pump_results)

    def _remove_thinking_mark(self) -> None:
        # Drop the trailing "…" line added at send time.
        self.transcript.configure(state="normal")
        end = self.transcript.index("end-1c")
        start = self.transcript.index(f"{end} linestart")
        if self.transcript.get(start, end).strip() == "…":
            self.transcript.delete(start, end + "+1c")
        self.transcript.configure(state="disabled")

    # -- misc ------------------------------------------------------------

    def _refresh_status(self, extra: str | None = None) -> None:
        key = self.founder_var.get() if hasattr(self, "founder_var") else None
        cfg = FOUNDERS.get(key, {}) if key else {}
        parts = [
            cfg.get("name", "…"),
            f"provider: {self.provider_name}",
        ]
        if extra:
            parts.append(extra)
        else:
            n = len(self._raw_docs) if self._raw_docs else 0
            parts.append(f"{n} documents")
        self.status_var.set("  |  ".join(parts))

    def _on_change_key(self) -> None:
        dlg = ApiKeyDialog(self.root)
        self.root.wait_window(dlg)
        provider, _key = resolve_api_key()
        self.provider_name = provider or "none"
        # Rebuild provider on services so the new key takes effect.
        from foundersbench.providers import default_provider
        new_provider = default_provider()
        for key, svc in self._services.items():
            svc.provider = new_provider
        self._refresh_status()
        self._append("— API key updated. —", "system")


def main() -> None:
    root = tk.Tk()
    app = FoundersBenchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
