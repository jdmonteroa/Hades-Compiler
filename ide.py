import sys, os, re, json, subprocess, tempfile
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except ImportError:
    print("\npip install customtkinter\n"); sys.exit(1)

try:
    import chardet; _CHARDET = True
except ImportError:
    _CHARDET = False

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

C = {
    "bg":          "#0D0D1A",
    "sidebar":     "#111120",
    "panel":       "#13132A",
    "editor":      "#0A0A16",
    "raised":      "#1A1A32",
    "surface":     "#20203C",
    "hover":       "#252548",
    "line":        "#1E1E3A",
    "border":      "#2A2A50",
    "border_lit":  "#3D3D70",
    "neon":        "#A855F7",
    "neon_dim":    "#7C3AED",
    "neon_glow":   "#C084FC",
    "neon_bg":     "#1A0836",
    "neon_border": "#6D28D9",
    "t1":          "#E2E8F0",
    "t2":          "#94A3B8",
    "t3":          "#4B5563",
    "ico":         "#64748B",
    "ico_hov":     "#E2E8F0",
    "ico_act":     "#A855F7",
    "green":       "#10B981",  "green_bg":  "#022C22",
    "amber":       "#F59E0B",  "amber_bg":  "#1C1000",
    "red":         "#EF4444",  "red_bg":    "#1C0505",
    "blue":        "#38BDF8",  "blue_bg":   "#051525",
    "cyan":        "#22D3EE",
    "hl_number":   "#FCA5A5",
    "hl_ident":    "#93C5FD",
    "hl_comment":  "#4B5563",
    "hl_keyword":  "#C084FC",
    "hl_arith":    "#FCD34D",
    "hl_rellog":   "#67E8F9",
    "hl_string":   "#86EFAC",
    "hl_char":     "#A7F3D0",
    "hl_assign":   "#FB923C",
    "hl_symbol":   "#CBD5E1",
}

FUI   = "Segoe UI"
FMONO = "Consolas"
FMDL2 = "Segoe MDL2 Assets"

ICO = {
    "new":     "\uE8A5",
    "open":    "\uE8E5",
    "save":    "\uE74E",
    "save_as": "\uEA35",
    "close":   "\uE8BB",
    "undo":    "\uE7A7",
    "redo":    "\uE7A6",
    "cut":     "\uE8C6",
    "copy":    "\uE8C8",
    "paste":   "\uE77F",
    "find":    "\uE721",
    "lex":     "\uE8FD",
    "syn":     "\uE943",
    "sem":     "\uEA86",
    "inter":   "\uE7EE",
    "run_all": "\uE768",
    "exec":    "\uE756",
    "file":    "\uE8A5",
    "dot":     "\uEB49",
    "check":   "\uE73E",
    "bug":     "\uEBE8",
    "chart":   "\uE9D2",
    "logo":    "\uE943",
    "warn":    "\uE7BA",
}

# ─────────────────────────────────────────────
#  LEXER INTERNO para syntax highlighting
# ─────────────────────────────────────────────
_KEYWORDS = {
    "if", "else", "end", "do", "while", "switch", "case",
    "int", "float", "real", "main", "cin", "cout", "then", "until",
}
_TOKEN_PATTERNS = [
    ("COMMENT_MULTI",  r"/\*[\s\S]*?\*/"),
    ("COMMENT_LINE",   r"//[^\n]*"),
    ("STRING",         r'"[^"]*"'),
    ("CHAR",           r"'[^']*'"),
    ("FLOAT",          r"\b\d+\.\d+\b"),
    ("INTEGER",        r"\b\d+\b"),
    ("INCREMENT",      r"\+\+"),
    ("DECREMENT",      r"--"),
    ("AND",            r"&&"),
    ("OR",             r"\|\|"),
    ("LEQ",            r"<="),
    ("GEQ",            r">="),
    ("NEQ",            r"!="),
    ("EQ",             r"=="),
    ("PLUS",           r"\+"),
    ("MINUS",          r"-"),
    ("TIMES",          r"\*"),
    ("DIVIDE",         r"/"),
    ("MOD",            r"%"),
    ("POW",            r"\^"),
    ("LT",             r"<"),
    ("GT",             r">"),
    ("NOT",            r"!"),
    ("ASSIGN",         r"="),
    ("LPAREN",         r"\("),
    ("RPAREN",         r"\)"),
    ("LBRACE",         r"\{"),
    ("RBRACE",         r"\}"),
    ("COMMA",          r","),
    ("SEMICOLON",      r";"),
    ("ID",             r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"),
    ("WHITESPACE",     r"[ \t\n]+"),
    ("UNKNOWN",        r"."),
]
_MASTER = re.compile(
    "|".join(f"(?P<{n}>{p})" for n, p in _TOKEN_PATTERNS),
    re.DOTALL,
)
_ARITH  = {"PLUS","MINUS","TIMES","DIVIDE","MOD","POW","INCREMENT","DECREMENT"}
_RELLOG = {"LT","LEQ","GT","GEQ","NEQ","EQ","AND","OR","NOT"}


def _fast_lex(source: str):
    spans = []
    for mo in _MASTER.finditer(source):
        kind  = mo.lastgroup
        value = mo.group()
        s, e  = mo.start(), mo.end()
        if kind in ("WHITESPACE",):
            continue
        if kind == "UNKNOWN":
            spans.append((s, e, "hl_error"))
            continue
        if kind == "ID" and value in _KEYWORDS:
            kind = "KEYWORD"
        if   kind == "KEYWORD":                        spans.append((s, e, "hl_keyword"))
        elif kind in ("FLOAT", "INTEGER"):             spans.append((s, e, "hl_number"))
        elif kind == "ID":                             spans.append((s, e, "hl_ident"))
        elif kind in ("COMMENT_LINE","COMMENT_MULTI"): spans.append((s, e, "hl_comment"))
        elif kind in _ARITH:                           spans.append((s, e, "hl_arith"))
        elif kind in _RELLOG:                          spans.append((s, e, "hl_rellog"))
        elif kind == "ASSIGN":                         spans.append((s, e, "hl_assign"))
        elif kind in ("STRING",):                      spans.append((s, e, "hl_string"))
        elif kind in ("CHAR",):                        spans.append((s, e, "hl_char"))
        else:                                          spans.append((s, e, "hl_symbol"))
    return spans


# ─────────────────────────────────────────────
#  WIDGETS AUXILIARES
# ─────────────────────────────────────────────
class ToolBtn(ctk.CTkButton):
    def __init__(self, parent, icon_key, tip, cmd,
                 primary=False, w=56, h=54):
        icon = ICO.get(icon_key, icon_key)
        if primary:
            fc, hc, tc, bc, bw = C["neon"], C["neon_glow"], "#FFFFFF", C["neon"], 0
            fsize = 28
        else:
            fc, hc, tc, bc, bw = C["raised"], C["hover"], C["ico"], C["border"], 1
            fsize = 24
        super().__init__(
            parent, text=icon,
            font=ctk.CTkFont(family=FMDL2, size=fsize),
            fg_color=fc, hover_color=hc,
            text_color=tc,
            border_color=bc, border_width=bw,
            corner_radius=8, width=w, height=h,
            command=cmd,
        )
        self._dfg = tc
        self._tip = tip
        self._tw  = None
        if not primary:
            self.bind("<Enter>",  lambda e: self.configure(text_color=C["ico_hov"]), add="+")
            self.bind("<Leave>",  lambda e: self.configure(text_color=self._dfg), add="+")
        self.bind("<Enter>", self._show_tip, add="+")
        self.bind("<Leave>", self._hide_tip, add="+")

    def _show_tip(self, e):
        self._tw = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        x = self.winfo_rootx() + 4
        y = self.winfo_rooty() + self.winfo_height() + 5
        tw.wm_geometry(f"+{x}+{y}")
        outer = tk.Frame(tw, bg=C["neon_border"], padx=1, pady=1)
        outer.pack()
        tk.Label(outer, text=f"  {self._tip}  ",
                 bg=C["raised"], fg=C["t1"],
                 font=(FUI, 15), padx=10, pady=6).pack()

    def _hide_tip(self, e=None):
        if self._tw:
            self._tw.destroy()
            self._tw = None


class LineNumbers(tk.Canvas):
    W = 72
    def __init__(self, parent, tw):
        super().__init__(parent, bg=C["editor"],
                         width=self.W, highlightthickness=0, bd=0)
        self.tw  = tw
        self._job = None
        for s in ("<KeyRelease>","<ButtonRelease-1>","<MouseWheel>",
                  "<Button-4>","<Button-5>","<<Change>>",
                  "<Configure>","<<Paste>>","<<Cut>>"):
            self.tw.bind(s, self._sched, add="+")

    def _sched(self, _=None):
        if self._job: self.after_cancel(self._job)
        self._job = self.after(12, self.redraw)

    def redraw(self, _=None):
        self._job = None
        self.delete("all")
        W = self.W
        H = max(self.winfo_height(), 1)
        self.create_line(W-1, 0, W-1, H, fill=C["border"], width=1)
        try: cur = int(self.tw.index("insert").split(".")[0])
        except: cur = -1
        i = self.tw.index("@0,0")
        seen = set()
        while True:
            info = self.tw.dlineinfo(i)
            if not info: break
            ln = int(i.split(".")[0])
            _, y, _, lh, _ = info
            if ln not in seen:
                seen.add(ln)
                is_cur = ln == cur
                if is_cur:
                    self.create_rectangle(
                        4, y+2, W-5, y+lh-2,
                        fill=C["neon_bg"], outline=C["neon_border"], width=1)
                    fg  = C["neon_glow"]
                    fnt = (FMONO, 20, "bold")
                else:
                    fg  = C["t3"]
                    fnt = (FMONO, 20)
                self.create_text(W-10, y+lh//2,
                                 text=str(ln), anchor="e",
                                 fill=fg, font=fnt)
            nxt = self.tw.index(f"{i}+1line")
            if nxt == i: break
            i = nxt


class FileTab(tk.Frame):
    def __init__(self, parent, name, on_click, on_close, active=False):
        super().__init__(parent, bg=C["editor"] if active else C["panel"],
                         cursor="hand2")
        self._active    = active
        self._on_click  = on_click
        self._on_close  = on_close
        self._top_line  = tk.Frame(self, bg=C["neon"] if active else C["panel"], height=2)
        self._top_line.pack(fill="x", side="top")
        inner = tk.Frame(self, bg=self["bg"])
        inner.pack(fill="both", expand=True, padx=(14, 8), pady=(5, 6))
        tk.Label(inner, text=ICO["file"],
                 bg=self["bg"], fg=C["neon"] if active else C["t3"],
                 font=(FMDL2, 18)).pack(side="left", padx=(0, 5))
        self._lbl = tk.Label(inner, text=name,
                             bg=self["bg"],
                             fg=C["t1"] if active else C["t3"],
                             font=(FUI, 16, "bold" if active else "normal"))
        self._lbl.pack(side="left")
        self._x = tk.Label(inner, text=ICO["close"],
                            bg=self["bg"], fg=C["t3"],
                            font=(FMDL2, 15), cursor="hand2")
        self._x.pack(side="left", padx=(8, 0))
        for w in (self, inner, self._lbl, self._top_line):
            w.bind("<Button-1>", lambda e: on_click())
        self._x.bind("<Button-1>", lambda e: on_close())
        self._x.bind("<Enter>",   lambda e: self._x.config(fg=C["red"]))
        self._x.bind("<Leave>",   lambda e: self._x.config(fg=C["t3"]))

    def set_active(self, v):
        self._active = v
        bg = C["editor"] if v else C["panel"]
        self.config(bg=bg)
        self._top_line.config(bg=C["neon"] if v else C["panel"])
        self._lbl.config(
            fg=C["t1"] if v else C["t3"],
            font=(FUI, 16, "bold" if v else "normal"),
            bg=bg)
        for w in self.winfo_children():
            try: w.config(bg=bg)
            except: pass

    def set_modified(self, v):
        self._x.config(
            text=ICO["dot"] if v else ICO["close"],
            fg=C["amber"] if v else C["t3"])


class StatusBar(tk.Frame):
    _BG = "#0D0D1A"

    def __init__(self, parent):
        super().__init__(parent, bg=self._BG, height=36)
        self.pack_propagate(False)
        tk.Frame(self, bg=C["neon_border"], height=1).pack(fill="x", side="top")
        self._pv = tk.StringVar(value="  Listo  ")
        self._pl = tk.Label(self, textvariable=self._pv,
                            bg=C["neon_bg"], fg=C["neon_glow"],
                            font=(FMONO, 12, "bold"), padx=14, anchor="center")
        self._pl.pack(side="left", fill="y")
        self._sep()
        self._fv = tk.StringVar(value="_sin_titulo.src")
        tk.Label(self, textvariable=self._fv,
                 bg=self._BG, fg=C["t2"],
                 font=(FMONO, 12), padx=10, anchor="w").pack(side="left", fill="y")
        self._lv = tk.StringVar(value="Ln 1  Col 1")
        self._ll = tk.Label(self, textvariable=self._lv,
                            bg=C["neon_bg"], fg=C["neon_glow"],
                            font=(FMONO, 12, "bold"), padx=14, anchor="center")
        self._ll.pack(side="right", fill="y")
        self._sep("right")
        self._ev = tk.StringVar(value="utf-8")
        tk.Label(self, textvariable=self._ev,
                 bg=self._BG, fg=C["t3"],
                 font=(FMONO, 12), padx=10).pack(side="right", fill="y")
        self._sep("right")
        self._cv = tk.StringVar(value="1 línea")
        tk.Label(self, textvariable=self._cv,
                 bg=self._BG, fg=C["t3"],
                 font=(FMONO, 12), padx=10).pack(side="right", fill="y")

    def _sep(self, side="left"):
        tk.Frame(self, bg=C["border"], width=1
                 ).pack(side=side, fill="y", pady=6, padx=1)

    def cursor(self, ln, col): self._lv.set(f"Ln {ln}  Col {col}")
    def file(self, n):         self._fv.set(n)
    def lines(self, n):        self._cv.set(f"{n} {'línea' if n == 1 else 'líneas'}")
    def enc(self, e):          self._ev.set(e.lower())

    def phase(self, txt, bg=None, fg=None, icon=None):
        self._pv.set(f"  {txt}  ")
        self._pl.config(bg=bg or C["neon_bg"], fg=fg or C["neon_glow"])


# ─────────────────────────────────────────────
#  IDE PRINCIPAL
# ─────────────────────────────────────────────
class HadesIDE(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("HADES IDE  ·  Compiler Studio")
        self.geometry("1680x1020")
        self.minsize(1200, 750)
        self.configure(fg_color=C["bg"])

        self.current_file  = None
        self.modified      = False
        self.file_encoding = "utf-8"
        self.compiler_path = tk.StringVar(value="compiler.py")
        self._hl_job       = None
        self._tab_widget   = None

        self._setup_ttk()
        self._build_menu()
        self._build_topbar()
        self._build_statusbar()
        self._build_main()
        self._setup_hl_tags()

        self.bind("<Control-n>", lambda e: self._new())
        self.bind("<Control-o>", lambda e: self._open())
        self.bind("<Control-s>", lambda e: self._save())
        self.bind("<Control-S>", lambda e: self._save_as())
        self.bind("<Control-w>", lambda e: self._close_file())
        self.bind("<Control-a>", lambda e: self._select_all())
        self.bind("<Control-f>", lambda e: self._find_dlg())
        self.bind("<F1>",  lambda e: self._run_lex())
        self.bind("<F2>",  lambda e: self._run_syn())
        self.bind("<F3>",  lambda e: self._run_sem())
        self.bind("<F5>",  lambda e: self._run_all())
        self.protocol("WM_DELETE_WINDOW", self._exit)

    def _setup_hl_tags(self):
        ed = self._ed
        ed.tag_config("hl_keyword",  foreground=C["hl_keyword"])
        ed.tag_config("hl_number",   foreground=C["hl_number"])
        ed.tag_config("hl_ident",    foreground=C["hl_ident"])
        ed.tag_config("hl_comment",  foreground=C["hl_comment"])
        ed.tag_config("hl_arith",    foreground=C["hl_arith"])
        ed.tag_config("hl_rellog",   foreground=C["hl_rellog"])
        ed.tag_config("hl_assign",   foreground=C["hl_assign"])
        ed.tag_config("hl_string",   foreground=C["hl_string"])
        ed.tag_config("hl_char",     foreground=C["hl_char"])
        ed.tag_config("hl_symbol",   foreground=C["hl_symbol"])
        ed.tag_config("hl_error",    foreground=C["red"], underline=True)

    def _sched_hl(self, _=None):
        if self._hl_job: self.after_cancel(self._hl_job)
        self._hl_job = self.after(120, self._do_hl)

    def _do_hl(self):
        self._hl_job = None
        source = self._ed.get("1.0", "end-1c")
        hl_tags = ["hl_keyword","hl_number","hl_ident","hl_comment",
                   "hl_arith","hl_rellog","hl_assign","hl_string",
                   "hl_char","hl_symbol","hl_error"]
        for tag in hl_tags:
            self._ed.tag_remove(tag, "1.0", "end")
        for start_idx, end_idx, tag in _fast_lex(source):
            self._ed.tag_add(tag, f"1.0+{start_idx}c", f"1.0+{end_idx}c")

    def _setup_ttk(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("H.Treeview",
                    background=C["panel"], fieldbackground=C["panel"],
                    foreground=C["t2"], rowheight=44, borderwidth=0,
                    font=(FMONO, 18))
        s.configure("H.Treeview.Heading",
                    background=C["raised"], foreground=C["t2"],
                    relief="flat", font=(FUI, 15, "bold"))
        s.map("H.Treeview",
              background=[("selected", C["neon_bg"])],
              foreground=[("selected", C["neon_glow"])])

    def _build_menu(self):
        mo = dict(bg=C["raised"], fg=C["t1"],
                  activebackground=C["hover"], activeforeground=C["neon_glow"],
                  relief="flat", bd=0, font=(FUI, 15))
        mb = tk.Menu(self, **mo)
        self.config(menu=mb)
        def sub(l):
            m = tk.Menu(mb, tearoff=0, **mo)
            mb.add_cascade(label=f"  {l}  ", menu=m)
            return m
        def it(m, l, c): m.add_command(label=f"   {l}", command=c)
        fa = sub("Archivo")
        it(fa,"Nuevo               Ctrl+N", self._new)
        it(fa,"Abrir…              Ctrl+O", self._open)
        fa.add_separator()
        it(fa,"Guardar             Ctrl+S", self._save)
        it(fa,"Guardar como…",              self._save_as)
        fa.add_separator()
        it(fa,"Cerrar archivo      Ctrl+W", self._close_file)
        fa.add_separator()
        it(fa,"Salir",                       self._exit)
        ed = sub("Editar")
        it(ed,"Deshacer   Ctrl+Z", lambda: self._ed.edit_undo())
        it(ed,"Rehacer    Ctrl+Y", lambda: self._ed.edit_redo())
        ed.add_separator()
        it(ed,"Cortar     Ctrl+X", lambda: self._ed.event_generate("<<Cut>>"))
        it(ed,"Copiar     Ctrl+C", lambda: self._ed.event_generate("<<Copy>>"))
        it(ed,"Pegar      Ctrl+V", lambda: self._ed.event_generate("<<Paste>>"))
        ed.add_separator()
        it(ed,"Selec. todo Ctrl+A", self._select_all)
        it(ed,"Buscar…    Ctrl+F",  self._find_dlg)
        cm = sub("Compilar")
        it(cm,"Léxico       F1",  self._run_lex)
        it(cm,"Sintáctico   F2",  self._run_syn)
        it(cm,"Semántico    F3",  self._run_sem)
        cm.add_separator()
        it(cm,"Compilar todo F5", self._run_all)
        it(cm,"Ejecutar",          self._run_exec)
        cfg = sub("Configuración")
        it(cfg,"Ruta del compilador…", self._dlg_compiler)
        hl = sub("Ayuda")
        it(hl,"Atajos de teclado",   self._dlg_shortcuts)
        it(hl,"Leyenda de colores",  self._dlg_legend)
        it(hl,"Acerca de HADES IDE", self._dlg_about)

    def _build_topbar(self):
        bar = tk.Frame(self, bg=C["panel"], height=115)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=C["neon"], height=3).pack(fill="x", side="top")
        tk.Frame(bar, bg=C["border"], height=1).pack(fill="x", side="bottom")
        inn = tk.Frame(bar, bg=C["panel"])
        inn.pack(fill="both", expand=True, padx=16, pady=0)
        lf = tk.Frame(inn, bg=C["panel"])
        lf.pack(side="left")
        tk.Label(lf, text=ICO["logo"],
                 bg=C["panel"], fg=C["neon"],
                 font=(FMDL2, 32)).pack(side="left")
        tk.Label(lf, text=" HADES",
                 bg=C["panel"], fg=C["t1"],
                 font=(FUI, 24, "bold")).pack(side="left")
        tk.Label(lf, text=" IDE",
                 bg=C["panel"], fg=C["t3"],
                 font=(FUI, 18)).pack(side="left")
        def sep():
            tk.Frame(inn, bg=C["border_lit"], width=1
                     ).pack(side="left", fill="y", pady=14, padx=12)
        sep()
        for key, tip, cmd in [
            ("new",     "Nuevo    Ctrl+N",   self._new),
            ("open",    "Abrir    Ctrl+O",   self._open),
            ("save",    "Guardar  Ctrl+S",   self._save),
            ("save_as", "Guardar como",       self._save_as),
        ]:
            ToolBtn(inn, key, tip, cmd).pack(side="left", padx=2, pady=10)
        sep()
        for key, tip, cmd in [
            ("undo",  "Deshacer  Ctrl+Z", lambda: self._ed.edit_undo()),
            ("redo",  "Rehacer   Ctrl+Y", lambda: self._ed.edit_redo()),
            ("cut",   "Cortar    Ctrl+X", lambda: self._ed.event_generate("<<Cut>>")),
            ("copy",  "Copiar    Ctrl+C", lambda: self._ed.event_generate("<<Copy>>")),
            ("paste", "Pegar     Ctrl+V", lambda: self._ed.event_generate("<<Paste>>")),
            ("find",  "Buscar    Ctrl+F", self._find_dlg),
        ]:
            ToolBtn(inn, key, tip, cmd).pack(side="left", padx=2, pady=10)
        sep()
        for key, tip, cmd in [
            ("lex",   "Léxico         F1", self._run_lex),
            ("syn",   "Sintáctico     F2", self._run_syn),
            ("sem",   "Semántico      F3", self._run_sem),
        ]:
            ToolBtn(inn, key, tip, cmd).pack(side="left", padx=2, pady=10)
        ToolBtn(inn, "run_all", "Compilar todo  F5",
                self._run_all, primary=True, w=72, h=54
                ).pack(side="left", padx=(10, 2), pady=10)
        ToolBtn(inn, "exec", "Ejecutar resultado",
                self._run_exec).pack(side="left", padx=2, pady=10)
        sep()
        tk.Label(inn, text="Compilador:",
                 bg=C["panel"], fg=C["t3"],
                 font=(FUI, 13)).pack(side="right", padx=(0, 6))
        ef = tk.Frame(inn, bg=C["border_lit"], padx=1, pady=1)
        ef.pack(side="right", pady=16, padx=4)
        tk.Entry(ef, textvariable=self.compiler_path,
                 bg=C["raised"], fg=C["t2"],
                 insertbackground=C["neon"],
                 relief="flat", bd=0,
                 font=(FMONO, 14), width=26,
                 ).pack(ipady=8, padx=3)

    def _build_main(self):
        main = tk.Frame(self, bg=C["bg"])
        main.pack(fill="both", expand=True)
        self._hp = tk.PanedWindow(
            main, orient="horizontal",
            bg=C["border"], sashwidth=5,
            sashrelief="flat", sashpad=0,
        )
        self._hp.pack(fill="both", expand=True)
        left_pane  = tk.Frame(self._hp, bg=C["bg"])
        right_pane = tk.Frame(self._hp, bg=C["panel"])
        self._hp.add(left_pane,  minsize=700)
        self._hp.add(right_pane, minsize=340)
        self.after(150, lambda: self._hp.sash_place(0, 1750, 0))
        self._build_editor_pane(left_pane)
        self._build_right_pane(right_pane)

    def _build_editor_pane(self, parent):
        vp = tk.PanedWindow(parent, orient="vertical",
                            bg=C["border"], sashwidth=5, sashrelief="flat")
        vp.pack(fill="both", expand=True)
        top = tk.Frame(vp, bg=C["bg"])
        bot = tk.Frame(vp, bg=C["panel"])
        vp.add(top, minsize=400)
        vp.add(bot, minsize=150)
        self.after(150, lambda: vp.sash_place(0, 0, 1900))
        self._build_editor(top)
        self._build_diag(bot)

    def _build_editor(self, parent):
        self._tabbar = tk.Frame(parent, bg=C["panel"], height=48)
        self._tabbar.pack(fill="x")
        self._tabbar.pack_propagate(False)
        tk.Frame(parent, bg=C["line"], height=1).pack(fill="x")
        self._refresh_tab()
        ef = tk.Frame(parent, bg=C["editor"])
        ef.pack(fill="both", expand=True)
        self._ed = tk.Text(
            ef,
            bg=C["editor"], fg=C["t1"],
            insertbackground=C["neon"],
            selectbackground=C["neon_bg"],
            selectforeground=C["t1"],
            relief="flat", bd=0,
            font=(FMONO, 22),
            undo=True, maxundo=-1,
            wrap="none",
            padx=22, pady=16,
            spacing1=4, spacing3=4,
            exportselection=True,
            insertwidth=2,
        )
        vsb = ctk.CTkScrollbar(
            ef, orientation="vertical", command=self._yscroll,
            fg_color=C["editor"], button_color=C["surface"],
            button_hover_color=C["neon_dim"], corner_radius=3, width=10,
        )
        vsb.pack(side="right", fill="y", padx=(0, 2), pady=2)
        hsb = tk.Scrollbar(ef, orient="horizontal", command=self._ed.xview,
                           bg=C["surface"], troughcolor=C["editor"],
                           relief="flat", bd=0, width=8)
        hsb.pack(side="bottom", fill="x")
        self._ed.config(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._ln = LineNumbers(ef, self._ed)
        self._ln.pack(side="left", fill="y")
        self._ed.pack(side="left", fill="both", expand=True)
        self._ed.tag_config("curline", background=C["raised"])
        self._ed.tag_config("found",
                            background=C["neon_bg"], foreground=C["neon_glow"])
        self._ed.bind("<KeyRelease>",      self._on_key)
        self._ed.bind("<ButtonRelease-1>", self._on_click)
        self._ed.bind("<<Paste>>",         self._on_paste)
        self._ed.bind("<<Cut>>",           self._on_change)
        self._ed.bind("<MouseWheel>",      lambda e: self._ln._sched())
        self._ed.bind("<Button-4>",        lambda e: self._ln._sched())
        self._ed.bind("<Button-5>",        lambda e: self._ln._sched())
        for _nav in ("<Left>","<Right>","<Up>","<Down>",
                     "<Home>","<End>","<Prior>","<Next>",
                     "<Control-Home>","<Control-End>",
                     "<Shift-Left>","<Shift-Right>","<Shift-Up>","<Shift-Down>"):
            self._ed.bind(_nav, lambda e: self.after(1, self._upd_cursor), add="+")
        ctx = tk.Menu(self, tearoff=0,
                      bg=C["raised"], fg=C["t1"],
                      activebackground=C["hover"], activeforeground=C["neon_glow"],
                      relief="flat", font=(FUI, 15))
        ctx.add_command(label="   Cortar              Ctrl+X",
            command=lambda: self._ed.event_generate("<<Cut>>"))
        ctx.add_command(label="   Copiar              Ctrl+C",
            command=lambda: self._ed.event_generate("<<Copy>>"))
        ctx.add_command(label="   Pegar               Ctrl+V",
            command=lambda: self._ed.event_generate("<<Paste>>"))
        ctx.add_separator()
        ctx.add_command(label="   Seleccionar todo   Ctrl+A", command=self._select_all)
        ctx.add_separator()
        ctx.add_command(label="   Deshacer           Ctrl+Z",
            command=lambda: self._ed.edit_undo())
        ctx.add_command(label="   Rehacer            Ctrl+Y",
            command=lambda: self._ed.edit_redo())
        ctx.add_separator()
        ctx.add_command(label="   Buscar…             Ctrl+F", command=self._find_dlg)
        def show_ctx(e):
            try: ctx.tk_popup(e.x_root, e.y_root)
            finally: ctx.grab_release()
        self._ed.bind("<Button-3>", show_ctx)
        self._ed.bind("<Button-2>", show_ctx)

    def _refresh_tab(self):
        for w in self._tabbar.winfo_children():
            w.destroy()
        name = os.path.basename(self.current_file) if self.current_file else "_sin_titulo.src"
        self._tab_widget = FileTab(
            self._tabbar, name,
            on_click=lambda: None,
            on_close=self._close_file,
            active=True,
        )
        self._tab_widget.pack(side="left", fill="y", padx=(4, 0))
        if self.modified:
            self._tab_widget.set_modified(True)

    def _yscroll(self, *a):
        self._ed.yview(*a)
        self._ln._sched()

    def _build_diag(self, parent):
        hdr = tk.Frame(parent, bg=C["raised"], height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Frame(hdr, bg=C["neon"], width=5).pack(side="left", fill="y")
        tk.Label(hdr, text=ICO["bug"],
                 bg=C["raised"], fg=C["neon"],
                 font=(FMDL2, 22)).pack(side="left", padx=(10, 3))
        tk.Label(hdr, text="DIAGNÓSTICO",
                 bg=C["raised"], fg=C["t2"],
                 font=(FUI, 16, "bold")).pack(side="left", padx=4)
        tk.Frame(hdr, bg=C["line"], height=1).pack(fill="x", side="bottom")
        nb = ctk.CTkTabview(
            parent,
            fg_color=C["panel"],
            segmented_button_fg_color=C["raised"],
            segmented_button_selected_color=C["neon_bg"],
            segmented_button_selected_hover_color=C["neon_dim"],
            segmented_button_unselected_color=C["raised"],
            segmented_button_unselected_hover_color=C["hover"],
            text_color=C["t1"],
            corner_radius=0, border_width=0,
        )
        self._diag_nb = nb
        nb.pack(fill="both", expand=True)
        self.err_lex, self.err_syn, self.err_sem, self.err_out = (
            self._err_tab(nb, l)
            for l in ["Léxicos", "Sintácticos", "Semánticos", "Ejecución"]
        )

    def _err_tab(self, nb, label):
        nb.add(label)
        f = nb.tab(label)
        t = tk.Text(f, bg=C["panel"], fg=C["t2"],
                    font=(FMONO, 18),
                    relief="flat", bd=0, state="disabled",
                    padx=16, pady=10,
                    selectbackground=C["neon_bg"],
                    exportselection=True)
        vsb = ctk.CTkScrollbar(f, orientation="vertical", command=t.yview,
                                fg_color=C["panel"], button_color=C["surface"],
                                button_hover_color=C["neon_dim"], width=10)
        vsb.pack(side="right", fill="y")
        t.config(yscrollcommand=vsb.set)
        t.pack(fill="both", expand=True)
        t.tag_config("err",  foreground=C["red"],   background=C["red_bg"])
        t.tag_config("warn", foreground=C["amber"])
        t.tag_config("ok",   foreground=C["green"])
        t.tag_config("info", foreground=C["blue"])
        t.tag_config("hdr",  foreground=C["neon_glow"], font=(FMONO, 18, "bold"))
        t.tag_config("line",          foreground=C["t2"])
        t.tag_config("code_snippet",  foreground=C["t1"],   font=(FMONO, 18))
        t.tag_config("code_pointer",  foreground=C["amber"], font=(FMONO, 18, "bold"))
        t.tag_config("code_pointer_err", foreground=C["red"], font=(FMONO, 18, "bold"))
        return t

    def _build_right_pane(self, parent):
        hdr = tk.Frame(parent, bg=C["raised"], height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Frame(hdr, bg=C["neon"], width=5).pack(side="left", fill="y")
        tk.Label(hdr, text=ICO["chart"],
                 bg=C["raised"], fg=C["neon"],
                 font=(FMDL2, 22)).pack(side="left", padx=(10, 3))
        tk.Label(hdr, text="RESULTADOS DEL ANÁLISIS",
                 bg=C["raised"], fg=C["t2"],
                 font=(FUI, 16, "bold")).pack(side="left", padx=4)
        tk.Frame(hdr, bg=C["line"], height=1).pack(fill="x", side="bottom")
        self._right_nb = ctk.CTkTabview(
            parent,
            fg_color=C["panel"],
            segmented_button_fg_color=C["raised"],
            segmented_button_selected_color=C["neon_bg"],
            segmented_button_selected_hover_color=C["neon_dim"],
            segmented_button_unselected_color=C["raised"],
            segmented_button_unselected_hover_color=C["hover"],
            text_color=C["t2"],
            corner_radius=0, border_width=0,
        )
        self._right_nb.pack(fill="both", expand=True)
        for l in ["Léxico","Sintáctico","Semántico","Símbolos","Cód. Inter."]:
            self._right_nb.add(l)
        self._tree(self._right_nb.tab("Léxico"),
                   ("Token","Tipo","Categoría","Línea","Col"), "tree_lex")
        self.tv_syn   = self._syn_tree(self._right_nb.tab("Sintáctico"))
        self.tv_sem   = self._tv(self._right_nb.tab("Semántico"))
        self._tree(self._right_nb.tab("Símbolos"),
                   ("Identificador","Tipo","Ámbito","Línea","Valor"), "tree_sym")
        self.tv_inter = self._tv(self._right_nb.tab("Cód. Inter."))

    def _tree(self, parent, cols, attr):
        f = tk.Frame(parent, bg=C["panel"])
        f.pack(fill="both", expand=True)
        tree = ttk.Treeview(f, columns=cols, show="headings", style="H.Treeview")
        widths = {"Línea":90,"Col":75,"Ámbito":120}
        for c in cols:
            w = widths.get(c, 160)
            tree.heading(c, text=c, anchor="center")
            tree.column(c, width=w, minwidth=40, anchor="center")
        vsb = ctk.CTkScrollbar(f, orientation="vertical", command=tree.yview,
                                fg_color=C["panel"], button_color=C["surface"],
                                button_hover_color=C["neon_dim"], width=10)
        vsb.pack(side="right", fill="y")
        hsb = tk.Scrollbar(f, orient="horizontal", command=tree.xview,
                           bg=C["surface"], troughcolor=C["panel"],
                           relief="flat", bd=0, width=8)
        hsb.pack(side="bottom", fill="x")
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.pack(fill="both", expand=True)
        tree.tag_configure("odd",  background=C["panel"])
        tree.tag_configure("even", background=C["raised"])
        tree.tag_configure("kw",   background=C["neon_bg"], foreground=C["hl_keyword"])
        tree.tag_configure("num",  background=C["panel"],   foreground=C["hl_number"])
        tree.tag_configure("cmt",  background=C["panel"],   foreground=C["hl_comment"])
        tree.tag_configure("str",  background=C["panel"],   foreground=C["hl_string"])
        tree.tag_configure("op",   background=C["panel"],   foreground=C["hl_arith"])
        tree.tag_configure("rel",  background=C["panel"],   foreground=C["hl_rellog"])
        tree.tag_configure("err",  background=C["red_bg"],  foreground=C["red"])
        setattr(self, attr, tree)

    def _tv(self, parent):
        f = tk.Frame(parent, bg=C["panel"])
        f.pack(fill="both", expand=True)
        t = tk.Text(f, bg=C["panel"], fg=C["t2"],
                    font=(FMONO, 18),
                    relief="flat", bd=0, state="disabled",
                    padx=16, pady=12, spacing1=4, spacing3=4,
                    selectbackground=C["neon_bg"], exportselection=True)
        vsb = ctk.CTkScrollbar(f, orientation="vertical", command=t.yview,
                                fg_color=C["panel"], button_color=C["surface"],
                                button_hover_color=C["neon_dim"], width=10)
        vsb.pack(side="right", fill="y")
        t.config(yscrollcommand=vsb.set)
        t.pack(fill="both", expand=True)
        t.tag_config("ok",   foreground=C["green"])
        t.tag_config("warn", foreground=C["amber"])
        t.tag_config("err",  foreground=C["red"])
        t.tag_config("hdr",  foreground=C["amber"], font=(FMONO, 18, "bold"))
        t.tag_config("node", foreground=C["neon_glow"])
        t.tag_config("leaf", foreground=C["blue"])
        t.tag_config("dim",  foreground=C["t3"])
        return t

    # ══════════════════════════════════════════════════════════════════════
    #  ÁRBOL SINTÁCTICO AST — colores semánticos por rol de nodo
    # ══════════════════════════════════════════════════════════════════════
    # Categorías de nodos del AST compacto:
    #   "op"       → operadores binarios/unarios  (+, -, *, /, ==, &&, =, ++…)
    #   "programa" → raíz del programa
    #   "if"       → control condicional
    #   "while"    → bucle while
    #   "do-while" → bucle do-while
    #   "do-until" → bucle do-until
    #   "switch"   → selector
    #   "cin"/"cout"→ E/S
    #   "declarar" → declaraciones de tipo
    #   "bloque"   → secuencia de instrucciones
    #   "condición"/"entonces"/"sino"/"cuerpo" → subnodos de control
    #   "ID"       → identificador (hoja)
    #   "INT"/"REAL"/"STR"/"CHAR" → literales (hoja)
    #   "ERROR"    → error de recuperación
    #   "case"     → rama de switch

    _ARITH_OPS  = {"+", "-", "*", "/", "%", "^", "+u", "-u",
                   "++", "--", "+?", "-?", "*?", "/?", "%?"}
    _RELAT_OPS  = {"==", "!=", "<", ">", "<=", ">="}
    _LOGIC_OPS  = {"&&", "||", "!"}
    _ASSIGN_OPS = {"="}
    _CTRL_NODES = {"if", "while", "do-while", "do-until", "switch", "case"}
    _IO_NODES   = {"cin", "cout"}
    _TYPE_NODES = {"declarar"}
    _SUB_NODES  = {"condición", "entonces", "sino", "cuerpo", "expr", "casos",
                   "bloque", "case"}
    _LEAF_NODES = {"ID", "INT", "REAL", "FLOAT", "STR", "CHAR"}

    def _ast_node_tag(self, label, value):
        """Retorna el tag de color para un nodo del AST."""
        if label == "ERROR":                     return "ast_error"
        if label == "programa":                  return "ast_root"
        if label == "op":
            if value in self._ARITH_OPS:         return "ast_arith"
            if value in self._RELAT_OPS:         return "ast_relat"
            if value in self._LOGIC_OPS:         return "ast_logic"
            if value in self._ASSIGN_OPS:        return "ast_assign"
            return "ast_op"
        if label in self._CTRL_NODES:            return "ast_ctrl"
        if label in self._IO_NODES:              return "ast_io"
        if label in self._TYPE_NODES:            return "ast_type"
        if label in self._SUB_NODES:             return "ast_sub"
        if label in self._LEAF_NODES:
            if label == "ID":                    return "ast_id"
            return "ast_lit"
        return "ast_struct"

    def _syn_tree(self, parent):
        """Panel del árbol AST compacto colapsable."""
        f = tk.Frame(parent, bg=C["panel"])
        f.pack(fill="both", expand=True)

        # ── Botones colapsar/expandir ─────────────────────────────────────
        btn_bar = tk.Frame(f, bg=C["raised"], height=58)
        btn_bar.pack(fill="x", side="top")
        btn_bar.pack_propagate(False)
        tk.Frame(btn_bar, bg=C["neon_border"], height=1).pack(fill="x", side="bottom")

        def _make_btn(parent, text, cmd):
            btn = tk.Label(parent, text=text,
                           bg=C["raised"], fg=C["t2"],
                           font=(FUI, 14, "bold"), padx=22, pady=0,
                           cursor="hand2", anchor="center")
            btn.bind("<Enter>",    lambda e: btn.config(bg=C["hover"], fg=C["neon_glow"]))
            btn.bind("<Leave>",    lambda e: btn.config(bg=C["raised"], fg=C["t2"]))
            btn.bind("<Button-1>", lambda e: cmd())
            btn.pack(side="left", fill="y", padx=(0, 0))
            return btn

        tk.Frame(btn_bar, bg=C["neon_border"], width=1).pack(side="left", fill="y", pady=8)

        def _collapse_all():
            tv = f._tv
            if not getattr(tv, "_tree_data", None): return
            def _collect_paths(node, path="0"):
                if node.get("children"):
                    tv._collapsed.add(path)
                    for i, c in enumerate(node["children"]):
                        if c: _collect_paths(c, f"{path}.{i}")
            tv._collapsed = set()
            _collect_paths(tv._tree_data)
            tv._line_path = {}
            tv.config(state="normal"); tv.delete("1.0", "end")
            self._render_ast_node(tv, tv._tree_data, prefix="", is_last=True, path="0", depth=0)
            tv.config(state="disabled"); tv.yview_moveto(0)

        def _expand_all():
            tv = f._tv
            if not getattr(tv, "_tree_data", None): return
            tv._collapsed = set()
            tv._line_path = {}
            tv.config(state="normal"); tv.delete("1.0", "end")
            self._render_ast_node(tv, tv._tree_data, prefix="", is_last=True, path="0", depth=0)
            tv.config(state="disabled"); tv.yview_moveto(0)

        _make_btn(btn_bar, "▶  Colapsar todo", _collapse_all)
        tk.Frame(btn_bar, bg=C["border"], width=1).pack(side="left", fill="y", pady=8)
        _make_btn(btn_bar, "▼  Expandir todo", _expand_all)
        tk.Frame(btn_bar, bg=C["neon_border"], width=1).pack(side="left", fill="y", pady=8)

        # ── Leyenda de colores del AST ────────────────────────────────────
        legend_items = [
            ("●", "ast_root",   "Programa"),
            ("●", "ast_assign", "Asignación"),
            ("●", "ast_arith",  "Aritmético"),
            ("●", "ast_relat",  "Relacional"),
            ("●", "ast_logic",  "Lógico"),
            ("●", "ast_ctrl",   "Control"),
            ("●", "ast_io",     "E/S"),
            ("●", "ast_type",   "Declaración"),
            ("●", "ast_id",     "Identificador"),
            ("●", "ast_lit",    "Literal"),
            ("●", "ast_error",  "Error"),
        ]
        legend_frame = tk.Frame(btn_bar, bg=C["raised"])
        legend_frame.pack(side="right", fill="y", padx=8)
        legend_text = tk.Text(
            legend_frame,
            bg=C["raised"], relief="flat", bd=0,
            height=1, width=120,
            state="disabled",
            font=(FMONO, 13),
            padx=4, pady=8,
        )
        legend_text.pack(fill="both", expand=True)
        # Configurar tags de la leyenda
        _tag_colors = {
            "ast_root":   C["neon_glow"],
            "ast_assign": C["hl_assign"],
            "ast_arith":  C["hl_arith"],
            "ast_relat":  C["hl_rellog"],
            "ast_logic":  C["cyan"],
            "ast_ctrl":   C["amber"],
            "ast_io":     C["green"],
            "ast_type":   C["hl_keyword"],
            "ast_id":     C["hl_ident"],
            "ast_lit":    C["hl_number"],
            "ast_error":  C["red"],
            "ast_op":     C["hl_arith"],
            "ast_sub":    C["t3"],
            "ast_struct": C["t2"],
        }
        for tname, tcolor in _tag_colors.items():
            legend_text.tag_config(tname,  foreground=tcolor)
            legend_text.tag_config(tname + "_bold",
                                   foreground=tcolor, font=(FMONO, 13, "bold"))
        legend_text.tag_config("ast_line", foreground=C["border_lit"])
        legend_text.tag_config("ast_dim",  foreground=C["t3"])
        legend_text.config(state="normal")
        for i, (sym, tag, lbl) in enumerate(legend_items):
            legend_text.insert("end", f" {sym} ", tag + "_bold")
            legend_text.insert("end", lbl, "ast_dim")
            if i < len(legend_items) - 1:
                legend_text.insert("end", "  ", "ast_dim")
        legend_text.config(state="disabled")

        # ── Text widget principal ─────────────────────────────────────────
        t = tk.Text(
            f,
            bg=C["panel"], fg=C["t2"],
            font=(FMONO, 18),
            relief="flat", bd=0,
            state="disabled",
            padx=20, pady=16,
            spacing1=6, spacing3=6,
            wrap="none",
            selectbackground=C["neon_bg"],
            exportselection=True,
            cursor="arrow",
            tabs=("1c",),
        )
        vsb = ctk.CTkScrollbar(f, orientation="vertical", command=t.yview,
                                fg_color=C["panel"], button_color=C["surface"],
                                button_hover_color=C["neon_dim"], width=10)
        hsb = tk.Scrollbar(f, orient="horizontal", command=t.xview,
                           bg=C["surface"], troughcolor=C["panel"],
                           highlightthickness=0, bd=0)
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        t.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        t.pack(fill="both", expand=True)

        # ── Configurar todos los tags de color AST ────────────────────────
        for tname, tcolor in _tag_colors.items():
            t.tag_config(tname,            foreground=tcolor)
            t.tag_config(tname + "_bold",  foreground=tcolor, font=(FMONO, 18, "bold"))

        t.tag_config("ast_error",      foreground=C["red"], background=C["red_bg"])
        t.tag_config("ast_error_bold", foreground=C["red"], background=C["red_bg"],
                     font=(FMONO, 18, "bold"))
        t.tag_config("ast_line",       foreground=C["border_lit"])
        t.tag_config("ast_arrow",      foreground=C["t3"])

        t._tree_data   = None
        t._collapsed   = set()
        t._line_path   = {}

        t.bind("<Button-1>", lambda e, w=t: self._syn_click(w, e))

        f._tv = t
        return f

    def _syn_fill(self, tv, node):
        """Renderiza el AST en el Text widget."""
        tv.config(state="normal")
        tv.delete("1.0", "end")
        tv._tree_data = node
        tv._collapsed = set()
        tv._line_path = {}
        self._render_ast_node(tv, node, prefix="", is_last=True, path="0", depth=0)
        tv.config(state="disabled")
        tv.see("1.0")

    def _render_ast_node(self, tv, node, prefix, is_last, path, depth=0):
        """
        Dibuja un nodo AST compacto.
        - Operadores (label='op') muestran solo su símbolo, en color por tipo.
        - Hojas (ID/INT/REAL…) muestran etiqueta + valor.
        - Nodos de control muestran su keyword directamente.
        """
        label    = node.get("label", "?")
        value    = node.get("value", "")
        children = [c for c in node.get("children", []) if c]
        collapsed = path in tv._collapsed
        has_ch    = bool(children)

        # ── Prefijo ASCII ─────────────────────────────────────────────────
        if depth == 0:
            line_prefix = ""
            new_prefix  = "  "
        else:
            connector   = "└── " if is_last else "├── "
            line_prefix = prefix + connector
            new_prefix  = prefix + ("    " if is_last else "│   ")

        # ── Flecha colapsar/expandir ──────────────────────────────────────
        if has_ch:
            arrow = "▼ " if not collapsed else "▶ "
        else:
            arrow = "  "

        # ── Determinar tag y texto a mostrar ─────────────────────────────
        tag = self._ast_node_tag(label, value)

        if label == "op":
            # Operador: mostrar el símbolo en grande, tipo entre paréntesis pequeño
            display_main  = value
            display_extra = ""
        elif label in self._LEAF_NODES:
            # Hoja: "tipo  valor"  ej: "ID  x"  o  "INT  23"
            display_main  = value
            display_extra = f"  ‹{label}›"
        elif label in self._CTRL_NODES | self._IO_NODES | self._TYPE_NODES:
            # Keyword de control: mostrar keyword + valor si lo tiene
            display_main  = label
            display_extra = f"  {value}" if value else ""
        elif label == "programa":
            display_main  = "programa"
            display_extra = f"  ‹{value}›" if value else ""
        elif label == "ERROR":
            display_main  = "⚠ ERROR"
            display_extra = f"  {value}" if value else ""
        else:
            # Subnodos (condición, entonces, cuerpo…)
            display_main  = label
            display_extra = f"  {value}" if value else ""

        # ── Insertar la línea ─────────────────────────────────────────────
        if line_prefix:
            tv.insert("end", line_prefix, "ast_line")
        tv.insert("end", arrow, "ast_arrow")

        # Registrar posición DESPUÉS de insertar el prefijo/flecha,
        # ANTES de insertar el label — así "end-1c" apunta exactamente
        # al carácter que acabamos de escribir, cuya línea es la correcta.
        cur_line = tv.index("end-1c").split(".")[0]
        tv._line_path[cur_line] = path

        tv.insert("end", display_main, tag + "_bold" if depth == 0 or label in ("op",) else tag)
        if display_extra:
            extra_tag = "ast_dim" if label not in self._LEAF_NODES else (
                "ast_id" if label == "ID" else "ast_lit"
            )
            tv.insert("end", display_extra, extra_tag)
        tv.insert("end", "\n")

        # ── Hijos recursivos ──────────────────────────────────────────────
        if has_ch and not collapsed:
            for i, child in enumerate(children):
                self._render_ast_node(tv, child, new_prefix,
                                      i == len(children) - 1,
                                      f"{path}.{i}",
                                      depth + 1)

    def _syn_click(self, tv, event):
        """Toggle colapso al hacer clic en un nodo."""
        if not getattr(tv, "_line_path", None): return
        click_idx = tv.index(f"@{event.x},{event.y}")
        line_no   = click_idx.split(".")[0]
        path = tv._line_path.get(line_no)
        if path is None: return
        if path in tv._collapsed:
            tv._collapsed.discard(path)
        else:
            tv._collapsed.add(path)
        if tv._tree_data:
            yview = tv.yview()
            tv._line_path = {}
            tv.config(state="normal"); tv.delete("1.0", "end")
            self._render_ast_node(tv, tv._tree_data,
                                  prefix="", is_last=True, path="0", depth=0)
            tv.config(state="disabled")
            tv.yview_moveto(yview[0])

    def _build_statusbar(self):
        self.sb = StatusBar(self)
        self.sb.pack(fill="x", side="bottom")

    # ── Helpers ───────────────────────────────────────────────────────────
    def _wset(self, w, content, tag=""):
        w.config(state="normal"); w.delete("1.0","end")
        w.insert("end", content, tag); w.config(state="disabled")

    def _wadd(self, w, content, tag=""):
        w.config(state="normal")
        w.insert("end", (content or "") + "\n", tag)
        w.config(state="disabled")

    def _clr(self, t):
        for it in t.get_children(): t.delete(it)

    # ── Archivos ──────────────────────────────────────────────────────────
    def _ask_save(self):
        if not self.modified: return True
        r = messagebox.askyesnocancel("HADES IDE", "Guardar cambios?")
        if r is None: return False
        if r: self._save()
        return True

    def _new(self):
        if not self._ask_save(): return
        self._ed.delete("1.0", "end")
        self.current_file  = None
        self.modified      = False
        self.file_encoding = "utf-8"
        self._refresh_tab()
        self.sb.file("_sin_titulo.src"); self.sb.enc("utf-8")
        self.sb.lines(0); self._ln.redraw()

    def _open(self):
        if not self._ask_save(): return
        path = filedialog.askopenfilename(
            title="Abrir archivo",
            filetypes=[("Código fuente","*.src *.lng *.txt *.py *.c *.cpp *.java"),
                       ("Texto plano","*.txt"),("Todos","*.*")])
        if path: self._load(path)

    def _load(self, path):
        try: raw = open(path, "rb").read()
        except Exception as e:
            messagebox.showerror("HADES IDE", f"Error:\n{e}"); return
        enc = "utf-8"
        if _CHARDET:
            enc = chardet.detect(raw).get("encoding") or "utf-8"
        content = None
        for a in [enc, "utf-8", "latin-1", "cp1252", "iso-8859-1"]:
            try: content = raw.decode(a); enc = a; break
            except: pass
        if content is None:
            content = raw.decode("latin-1", errors="replace"); enc = "latin-1"
        self.file_encoding = enc
        self.current_file  = path
        self.modified      = False
        self._ed.delete("1.0", "end")
        self._ed.insert("1.0", content)
        self._ed.edit_reset()
        self._ed.mark_set("insert", "1.0")
        self._ed.see("1.0")
        self._refresh_tab()
        self.sb.file(os.path.basename(path)); self.sb.enc(enc)
        self._ln.redraw(); self._upd_lines()
        self._do_hl()
        self.sb.phase("Cargado", bg=C["green_bg"], fg=C["green"], icon=ICO["check"])
        self.after(2500, lambda: self.sb.phase("Listo"))

    def _save(self, _=None):
        if self.current_file is None: self._save_as(); return
        try:
            with open(self.current_file, "w",
                      encoding=self.file_encoding, errors="replace") as f:
                f.write(self._ed.get("1.0", "end-1c"))
            self.modified = False
            if self._tab_widget: self._tab_widget.set_modified(False)
            self.sb.phase("Guardado", bg=C["green_bg"], fg=C["green"], icon=ICO["save"])
            self.after(2000, lambda: self.sb.phase("Listo"))
        except Exception as e:
            messagebox.showerror("HADES IDE", f"Error:\n{e}")

    def _save_as(self):
        path = filedialog.asksaveasfilename(
            title="Guardar como", defaultextension=".src",
            filetypes=[("Código","*.src"),("Texto","*.txt"),("Todos","*.*")])
        if not path: return
        self.current_file  = path
        self.file_encoding = "utf-8"
        self._refresh_tab()
        self.sb.file(os.path.basename(path)); self.sb.enc("utf-8")
        self._save()

    def _close_file(self):
        if not self._ask_save(): return
        self._ed.delete("1.0", "end")
        self.current_file = None; self.modified = False
        self._refresh_tab()
        self.sb.file("_sin_titulo.src"); self.sb.lines(0); self._ln.redraw()

    def _exit(self):
        if not self._ask_save(): return
        self.destroy()

    # ── Eventos del editor ────────────────────────────────────────────────
    def _on_key(self, _=None):
        self._mark_mod(); self._upd_cursor()
        self._sched_hl(); self._upd_lines(); self._ln._sched()

    def _on_click(self, _=None):
        self._upd_cursor(); self._hl_cur(); self._ln._sched()

    def _on_paste(self, _=None):
        self.after(20, self._post_paste)

    def _post_paste(self):
        self._mark_mod(); self._do_hl()
        self._upd_lines(); self._ln.redraw(); self._upd_cursor()

    def _on_change(self, _=None):
        self._mark_mod(); self._upd_lines(); self._ln._sched()

    def _mark_mod(self):
        if not self.modified:
            self.modified = True
            if self._tab_widget: self._tab_widget.set_modified(True)

    def _upd_cursor(self):
        pos = self._ed.index("insert")
        ln, col = pos.split(".")
        self.sb.cursor(int(ln), int(col)+1); self._hl_cur()

    def _hl_cur(self):
        self._ed.tag_remove("curline", "1.0", "end")
        ln = self._ed.index("insert").split(".")[0]
        self._ed.tag_add("curline", f"{ln}.0", f"{ln}.end+1c")

    def _upd_lines(self):
        self.sb.lines(int(self._ed.index("end-1c").split(".")[0]))

    def _select_all(self, _=None):
        self._ed.tag_add("sel", "1.0", "end")
        self._ed.mark_set("insert", "end")

    def _find_dlg(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Buscar")
        dlg.geometry("480x170")
        dlg.resizable(False, False)
        dlg.configure(fg_color=C["raised"])
        dlg.transient(self); dlg.grab_set()
        tk.Frame(dlg, bg=C["neon"], height=3).pack(fill="x")
        hf = tk.Frame(dlg, bg=C["raised"])
        hf.pack(anchor="w", padx=20, pady=(12,4))
        tk.Label(hf, text=ICO["find"],
                 bg=C["raised"], fg=C["neon"],
                 font=(FMDL2, 14)).pack(side="left")
        tk.Label(hf, text="  Buscar en el editor:",
                 bg=C["raised"], fg=C["t2"],
                 font=(FUI, 12)).pack(side="left")
        sv = tk.StringVar()
        entry = ctk.CTkEntry(dlg, textvariable=sv,
                             fg_color=C["editor"],
                             border_color=C["border_lit"], border_width=1,
                             text_color=C["t1"],
                             font=ctk.CTkFont(FMONO, 12),
                             corner_radius=6, height=36)
        entry.pack(fill="x", padx=20); entry.focus_set()
        msg = ctk.CTkLabel(dlg, text="", fg_color="transparent",
                           text_color=C["t3"], font=ctk.CTkFont(FUI, 10))
        msg.pack(anchor="w", padx=22)
        def search():
            self._ed.tag_remove("found", "1.0", "end")
            q = sv.get()
            if not q: return
            start = self._ed.index("insert")
            idx = self._ed.search(q, start, stopindex="end", nocase=True)
            if not idx:
                idx = self._ed.search(q, "1.0", stopindex="end", nocase=True)
            if idx:
                end_ = f"{idx}+{len(q)}c"
                self._ed.tag_add("found", idx, end_)
                self._ed.mark_set("insert", end_)
                self._ed.see(idx)
                msg.configure(text=f"  Encontrado en {idx}", text_color=C["green"])
            else:
                msg.configure(text="  No encontrado", text_color=C["red"])
        bf = ctk.CTkFrame(dlg, fg_color="transparent")
        bf.pack(pady=8, padx=20, anchor="w")
        ctk.CTkButton(bf, text="Buscar siguiente", command=search,
                      fg_color=C["neon"], hover_color=C["neon_glow"],
                      text_color="#FFF", corner_radius=6, width=156, height=32,
                      font=ctk.CTkFont(FUI, 11)).pack(side="left", padx=(0,8))
        ctk.CTkButton(bf, text="Cerrar", command=dlg.destroy,
                      fg_color=C["raised"], hover_color=C["hover"],
                      text_color=C["t3"], border_color=C["border"], border_width=1,
                      corner_radius=6, width=84, height=32,
                      font=ctk.CTkFont(FUI, 11)).pack(side="left")
        entry.bind("<Return>", lambda e: search())
        entry.bind("<Escape>", lambda e: dlg.destroy())

    # ── Ejecutar fases ────────────────────────────────────────────────────
    def _save_tmp(self):
        if self.current_file:
            self._save()
            return self.current_file
        content = self._ed.get("1.0", "end-1c")
        tmp = tempfile.NamedTemporaryFile(
            suffix=".src", mode="w", encoding="utf-8", delete=False)
        tmp.write(content); tmp.close()
        return tmp.name

    def _ensure_ply(self):
        try:
            import ply.lex, ply.yacc
            return True, ""
        except ImportError:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "ply"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=60
                )
                if result.returncode == 0:
                    return True, "PLY instalado correctamente."
                else:
                    return False, f"No se pudo instalar PLY:\n{result.stderr}"
            except Exception as e:
                return False, f"Error al intentar instalar PLY: {e}"

    def _run_compiler(self, phase):
        src = self._save_tmp()
        cp  = self.compiler_path.get()
        if not os.path.isabs(cp):
            cp = os.path.join(os.path.dirname(os.path.abspath(__file__)), cp)
        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"]       = "1"
            proc = subprocess.run(
                [sys.executable, cp, phase, src],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=15, env=env,
            )
            return proc.stdout, proc.stderr, proc.returncode
        except FileNotFoundError:
            return "", f"No se encontró el compilador: {cp}", 1
        except subprocess.TimeoutExpired:
            return "", "Tiempo de espera agotado (15s)", 1
        except Exception as e:
            return "", str(e), 1

    # ── F1 LÉXICO ─────────────────────────────────────────────────────────
    def _run_lex(self):
        ok, msg = self._ensure_ply()
        if not ok:
            self.err_lex.config(state="normal")
            self.err_lex.delete("1.0", "end")
            self.err_lex.insert("end", f"\n  ERROR: {msg}\n\n", "err")
            self.err_lex.insert("end",
                "  Abre una terminal y ejecuta:\n      pip install ply\n"
                "  Luego reinicia la IDE.\n", "warn")
            self.err_lex.config(state="disabled")
            self._diag_nb.set("Léxicos")
            self.sb.phase("PLY no instalado", bg=C["red_bg"], fg=C["red"])
            return

        self.sb.phase("Analizando Léxico...", bg=C["neon_bg"], fg=C["neon_glow"])
        self._clr(self.tree_lex)
        self.err_lex.config(state="normal"); self.err_lex.delete("1.0", "end")
        self.err_lex.config(state="disabled")

        src_path = self._save_tmp()
        _src_for_lex_diag = self._ed.get("1.0", "end-1c").splitlines()
        compiler = self.compiler_path.get()
        if not os.path.isabs(compiler):
            compiler = os.path.join(os.path.dirname(os.path.abspath(__file__)), compiler)

        try:
            _env_utf8 = os.environ.copy()
            _env_utf8["PYTHONIOENCODING"] = "utf-8"
            _env_utf8["PYTHONUTF8"]       = "1"
            result = subprocess.run(
                [sys.executable, compiler, "lexical", src_path],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=10, env=_env_utf8,
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()

            if not stdout:
                self.err_lex.config(state="normal")
                self.err_lex.insert("end",
                    f"\n  ERROR: el compilador no produjo salida.\n"
                    f"  Compilador: {compiler}\n"
                    f"  Código de salida: {result.returncode}\n\n", "hdr")
                if stderr:
                    self.err_lex.insert("end", "  Detalle:\n\n", "hdr")
                    for line in stderr.splitlines():
                        self.err_lex.insert("end", f"  {line}\n", "err")
                self.err_lex.config(state="disabled")
                self._diag_nb.set("Léxicos")
                self.sb.phase("Error al ejecutar compilador", bg=C["red_bg"], fg=C["red"])
                return

            data = json.loads(stdout)
            tokens = data.get("tokens", [])
            lex_errors = data.get("errors", [])

            self.err_lex.config(state="normal")
            if lex_errors:
                self.err_lex.insert("end",
                    f"   SE ENCONTRARON {len(lex_errors)} ERROR(ES) LÉXICO(S):\n\n", "hdr")
                for e in lex_errors:
                    tipo  = e.get("tipo","Léxico")
                    linea = e.get("linea", "?")
                    col   = e.get("col","?")
                    msg_e = e.get("mensaje", "")
                    self.err_lex.insert("end",
                        f"   [{tipo}]  Línea {linea}, Col {col}:\n"
                        f"      {msg_e}\n", "err")
                    try:
                        ln_idx = int(linea) - 1
                        if 0 <= ln_idx < len(_src_for_lex_diag):
                            code_line = _src_for_lex_diag[ln_idx]
                            col_idx   = max(0, int(col) - 1)
                            pointer   = " " * col_idx + "^"
                            self.err_lex.insert("end", f"      ┌─ Línea {linea}:\n", "line")
                            self.err_lex.insert("end", f"      │  {code_line}\n", "code_snippet")
                            self.err_lex.insert("end", f"      │  {pointer}\n", "code_pointer_err")
                            self.err_lex.insert("end", f"      └──────\n", "line")
                    except Exception:
                        pass
                    self.err_lex.insert("end", "\n", "err")
                self.sb.phase(f"Léxico: {len(lex_errors)} errores",
                              bg=C["amber_bg"], fg=C["amber"])
            else:
                self.err_lex.insert("end", "   Análisis léxico completado sin errores ✓\n", "ok")
                self.sb.phase("Léxico OK", bg=C["green_bg"], fg=C["green"])
            self.err_lex.config(state="disabled")

            cat_map = {
                "KEYWORD": "kw", "NUMBER": "num", "COMMENT": "cmt",
                "STRING": "str", "ARITH_OP": "op", "RELAT_OP": "rel",
                "LOGIC_OP": "rel", "ASSIGN": "op", "SYMBOL": "odd",
            }
            for i, tok in enumerate(tokens):
                category  = tok.get("category", "SYMBOL")
                color_tag = cat_map.get(category, "odd")
                self.tree_lex.insert("", "end", values=(
                    tok.get("token"), tok.get("type"), tok.get("category"),
                    tok.get("line"),  tok.get("col")
                ), tags=(color_tag,))

            self._right_nb.set("Léxico")
            self._diag_nb.set("Léxicos")

        except Exception as e:
            self._wadd(self.err_out, f"Error en _run_lex: {str(e)}", "err")

    # ── F2 SINTÁCTICO ─────────────────────────────────────────────────────
    def _run_syn(self):
        ok, msg = self._ensure_ply()
        if not ok:
            self.err_syn.config(state="normal"); self.err_syn.delete("1.0", "end")
            self.err_syn.insert("end", f"\n  ERROR: {msg}\n\n", "err")
            self.err_syn.insert("end",
                "  Abre una terminal y ejecuta:\n      pip install ply\n"
                "  Luego reinicia la IDE.\n", "warn")
            self.err_syn.config(state="disabled")
            self._diag_nb.set("Sintácticos")
            self.sb.phase("PLY no instalado", bg=C["red_bg"], fg=C["red"])
            return

        self.sb.phase("Analizando Sintáctico…", bg=C["neon_bg"], fg=C["neon_glow"])

        tv = self.tv_syn._tv
        tv.config(state="normal"); tv.delete("1.0", "end"); tv.config(state="disabled")
        self.err_syn.config(state="normal"); self.err_syn.delete("1.0", "end")
        self.err_syn.config(state="disabled")

        _src_for_diag = self._ed.get("1.0", "end-1c").splitlines()
        src_path = self._save_tmp()
        compiler = self.compiler_path.get()
        if not os.path.isabs(compiler):
            compiler = os.path.join(os.path.dirname(os.path.abspath(__file__)), compiler)

        try:
            _env_utf8 = os.environ.copy()
            _env_utf8["PYTHONIOENCODING"] = "utf-8"
            _env_utf8["PYTHONUTF8"]       = "1"
            result = subprocess.run(
                [sys.executable, compiler, "syntactic", src_path],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=20, env=_env_utf8,
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()

            if not stdout:
                self.err_syn.config(state="normal")
                self.err_syn.insert("end",
                    f"\n  ERROR: el compilador no produjo salida.\n"
                    f"  Compilador: {compiler}\n"
                    f"  Código de salida: {result.returncode}\n\n", "hdr")
                if stderr:
                    self.err_syn.insert("end", "  Detalle:\n\n", "hdr")
                    for line in stderr.splitlines():
                        self.err_syn.insert("end", f"  {line}\n", "err")
                self.err_syn.config(state="disabled")
                self._diag_nb.set("Sintácticos")
                self.sb.phase("Error al ejecutar compilador", bg=C["red_bg"], fg=C["red"])
                return

            data = json.loads(stdout)
            lex_errors = data.get("lex_errors", [])
            syn_errors = data.get("syn_errors", [])
            all_errors = data.get("errors", [])

            if not lex_errors and not syn_errors and all_errors:
                lex_errors = [e for e in all_errors
                              if isinstance(e, dict) and "Léxico" in e.get("tipo","")]
                syn_errors = [e for e in all_errors
                              if isinstance(e, dict) and "Léxico" not in e.get("tipo","")]

            total   = len(lex_errors) + len(syn_errors)
            fatales = [e for e in all_errors if isinstance(e,dict) and e.get("fatal")]
            normales= [e for e in all_errors if isinstance(e,dict) and not e.get("fatal")]

            self.err_syn.config(state="normal")

            if total == 0:
                self.err_syn.insert("end",
                    "\n  ✓  Análisis sintáctico completado sin errores\n", "ok")
            else:
                self.err_syn.insert("end",
                    f"  ══════════════════════════════════════\n"
                    f"  RESUMEN DE ERRORES\n"
                    f"  ══════════════════════════════════════\n", "hdr")
                self.err_syn.insert("end",
                    f"  Total  : {total}\n"
                    f"  Léxicos: {len(lex_errors)}   Sintácticos: {len(syn_errors)}\n"
                    f"  Fatales: {len(fatales)}   Recuperados: {len(normales)}\n"
                    f"  ──────────────────────────────────────\n\n", "hdr")

                if lex_errors:
                    self.err_syn.insert("end",
                        f"  ▸ ERRORES LÉXICOS ({len(lex_errors)})\n"
                        f"  ──────────────────────────────────────\n", "hdr")
                    for i, e in enumerate(lex_errors, 1):
                        tipo  = e.get("tipo","Léxico")
                        linea = e.get("linea","?"); col = e.get("col","?")
                        msg_e = e.get("mensaje","")
                        self.err_syn.insert("end",
                            f"  #{i}  Tipo   : {tipo}\n"
                            f"      Línea  : {linea}   Columna: {col}\n"
                            f"      Estado : recuperado\n"
                            f"      Mensaje: {msg_e}\n", "warn")
                        try:
                            ln_idx = int(linea) - 1
                            if 0 <= ln_idx < len(_src_for_diag):
                                code_line = _src_for_diag[ln_idx]
                                col_idx   = max(0, int(col) - 1)
                                pointer   = " " * col_idx + "^"
                                self.err_syn.insert("end", f"      ┌─ Línea {linea}:\n", "line")
                                self.err_syn.insert("end", f"      │  {code_line}\n", "code_snippet")
                                self.err_syn.insert("end", f"      │  {pointer}\n", "code_pointer")
                                self.err_syn.insert("end", f"      └──────\n", "line")
                        except Exception: pass
                        self.err_syn.insert("end", "\n", "warn")

                if syn_errors:
                    self.err_syn.insert("end",
                        f"  ▸ ERRORES SINTÁCTICOS ({len(syn_errors)})\n"
                        f"  ──────────────────────────────────────\n", "hdr")
                    for i, e in enumerate(syn_errors, 1):
                        if not isinstance(e, dict):
                            self.err_syn.insert("end", f"  #{i}  {e}\n\n", "err")
                            continue
                        tipo  = e.get("tipo","Sintáctico")
                        linea = e.get("linea","?"); col = e.get("col","?")
                        msg_e = e.get("mensaje",""); fatal = e.get("fatal",False)
                        etag       = "err" if fatal else "warn"
                        estado_tag = "err" if fatal else "ok"
                        estado_txt = "FATAL" if fatal else "recuperado"
                        self.err_syn.insert("end",
                            f"  #{i}  Tipo   : {tipo}\n"
                            f"      Línea  : {linea}   Columna: {col}\n"
                            f"      Estado : {estado_txt}\n"
                            f"      Mensaje: {msg_e}\n", etag)
                        try:
                            ln_idx = int(linea) - 1
                            if 0 <= ln_idx < len(_src_for_diag):
                                code_line = _src_for_diag[ln_idx]
                                col_idx   = max(0, int(col) - 1)
                                pointer   = " " * col_idx + "^"
                                self.err_syn.insert("end", f"      ┌─ Línea {linea}:\n", "line")
                                self.err_syn.insert("end", f"      │  {code_line}\n", "code_snippet")
                                self.err_syn.insert("end", f"      │  {pointer}\n",
                                    "code_pointer_err" if fatal else "code_pointer")
                                self.err_syn.insert("end", f"      └──────\n", "line")
                        except Exception: pass
                        self.err_syn.insert("end", "\n", etag)

            self.err_syn.config(state="disabled")
            self.err_syn.see("1.0")
            self._diag_nb.set("Sintácticos")

            # ── Árbol AST ────────────────────────────────────────────────
            if data.get("tree"):
                self._syn_fill(tv, data["tree"])
                self._right_nb.set("Sintáctico")

            # ── Status bar ───────────────────────────────────────────────
            if total == 0:
                self.sb.phase("Sintáctico OK ✓", bg=C["green_bg"], fg=C["green"])
            elif any(e.get("fatal") for e in all_errors if isinstance(e, dict)):
                self.sb.phase(f"Sintáctico: {total} error(es)", bg=C["red_bg"], fg=C["red"])
            else:
                self.sb.phase(f"Sintáctico: {total} recuperados", bg=C["amber_bg"], fg=C["amber"])
            self.after(4000, lambda: self.sb.phase("Listo"))

        except json.JSONDecodeError as ex:
            raw = (result.stdout or "")[:300] if result else ""
            self.err_syn.config(state="normal")
            self.err_syn.insert("end",
                f"\n  ERROR al parsear respuesta:\n  {ex}\n\n"
                f"  Salida recibida:\n  {raw}\n", "err")
            self.err_syn.config(state="disabled")
            self._diag_nb.set("Sintácticos")
            self.sb.phase("Error de compilador", bg=C["red_bg"], fg=C["red"])

        except Exception as ex:
            import traceback
            tb = traceback.format_exc()
            self.err_syn.config(state="normal")
            self.err_syn.insert("end",
                f"\n  ERROR INESPERADO:\n  {ex}\n\n  Detalle:\n", "err")
            for line in tb.splitlines()[-6:]:
                self.err_syn.insert("end", f"  {line}\n", "err")
            self.err_syn.config(state="disabled")
            self._diag_nb.set("Sintácticos")
            self.sb.phase("Error inesperado", bg=C["red_bg"], fg=C["red"])

    def _run_sem(self):
        self.sb.phase("Analizando Semántico…", bg=C["neon_bg"], fg=C["neon_glow"])
        self._wset(self.tv_sem, ""); self._wset(self.err_sem, "")
        self._clr(self.tree_sym)
        stdout, stderr, rc = self._run_compiler("semantic")
        if stderr.strip():
            self.err_sem.config(state="normal")
            for line in stderr.strip().splitlines():
                self.err_sem.insert("end", line + "\n", "err")
            self.err_sem.config(state="disabled")
        if stdout.strip():
            try:
                d = json.loads(stdout)
                msg_s = d.get("message",""); syms = d.get("symbols",[])
                tag = "ok" if d.get("status") == "ok" else "err"
                self._wset(self.tv_sem, msg_s, tag)
                for i, s in enumerate(syms):
                    tg = "even" if i % 2 == 0 else "odd"
                    self.tree_sym.insert("", "end",
                        values=(s["name"],s["type"],s.get("scope",""),
                                s.get("line",""),s.get("value","")), tags=(tg,))
                self._right_nb.set("Semántico")
            except json.JSONDecodeError:
                self._wset(self.tv_sem, stdout)
        bg = C["green_bg"] if rc == 0 else C["red_bg"]
        fg = C["green"]    if rc == 0 else C["red"]
        self.sb.phase("Semántico OK" if rc == 0 else "Error semántico", bg=bg, fg=fg)
        self.after(3000, lambda: self.sb.phase("Listo"))

    def _run_all(self):
        self._run_lex()
        self.after(200, self._run_syn)

    def _run_exec(self):
        self.sb.phase("Ejecutando…", bg=C["neon_bg"], fg=C["neon_glow"])
        self._wset(self.err_out, "")
        stdout, stderr, rc = self._run_compiler("execute")
        self.err_out.config(state="normal")
        if stdout.strip(): self.err_out.insert("end", stdout + "\n", "ok")
        if stderr.strip(): self.err_out.insert("end", stderr + "\n", "err")
        self.err_out.config(state="disabled")
        bg = C["green_bg"] if rc == 0 else C["red_bg"]
        fg = C["green"]    if rc == 0 else C["red"]
        self.sb.phase("Ejecución terminada" if rc == 0 else "Error de ejecución", bg=bg, fg=fg)
        self.after(3000, lambda: self.sb.phase("Listo"))

    # ── Diálogos ──────────────────────────────────────────────────────────
    def _dlg_compiler(self):
        p = filedialog.askopenfilename(
            title="Seleccionar compilador",
            filetypes=[("Python","*.py"),("Ejecutable","*.exe *.sh"),("Todos","*.*")])
        if p: self.compiler_path.set(p)

    def _dlg_legend(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Leyenda de colores")
        dlg.geometry("480x440")
        dlg.resizable(False, False)
        dlg.configure(fg_color=C["raised"])
        dlg.transient(self)
        tk.Frame(dlg, bg=C["neon"], height=3).pack(fill="x")
        ctk.CTkLabel(dlg, text="  LEYENDA DE COLORES  —  Syntax Highlighting",
                     fg_color="transparent", text_color=C["t1"],
                     font=ctk.CTkFont(FUI, 14, weight="bold")).pack(pady=12)
        items = [
            (C["hl_number"],  "Color 1", "Números enteros y reales",       "42  3.14"),
            (C["hl_ident"],   "Color 2", "Identificadores",                "miVar  x1"),
            (C["hl_comment"], "Color 3", "Comentarios  // y /* */",        "// comentario"),
            (C["hl_keyword"], "Color 4", "Palabras reservadas",            "if  while  int"),
            (C["hl_arith"],   "Color 5", "Operadores aritméticos",         "+ - * / % ^ ++ --"),
            (C["hl_rellog"],  "Color 6", "Operadores relacionales/lógicos","< <= > >= != == && ||"),
            (C["hl_string"],  "Extra",   "Cadenas de texto",               '"hola mundo"'),
            (C["hl_char"],    "Extra",   "Caracteres",                     "'a'"),
            (C["hl_assign"],  "Extra",   "Asignación",                     "="),
            (C["hl_symbol"],  "Extra",   "Símbolos",                       "( ) { } , ;"),
        ]
        sf = ctk.CTkScrollableFrame(dlg, fg_color="transparent",
                                    scrollbar_button_color=C["neon_dim"],
                                    scrollbar_button_hover_color=C["neon"])
        sf.pack(fill="both", expand=True, padx=16)
        for color, label, desc, example in items:
            row = tk.Frame(sf, bg=C["raised"])
            row.pack(fill="x", pady=3)
            tk.Label(row, text="██", fg=color, bg=C["raised"],
                     font=(FMONO, 14)).pack(side="left", padx=8)
            tk.Label(row, text=label, fg=C["amber"], bg=C["raised"],
                     font=(FMONO, 10), width=8).pack(side="left")
            tk.Label(row, text=desc, fg=C["t2"], bg=C["raised"],
                     font=(FUI, 10), width=28, anchor="w").pack(side="left")
            tk.Label(row, text=example, fg=color, bg=C["raised"],
                     font=(FMONO, 10)).pack(side="left", padx=8)
        ctk.CTkButton(dlg, text="Cerrar", command=dlg.destroy,
                      fg_color=C["neon"], hover_color=C["neon_glow"],
                      text_color="#FFF", corner_radius=6, width=100, height=32,
                      font=ctk.CTkFont(FUI, 11)).pack(pady=10)

    def _dlg_shortcuts(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Atajos — HADES IDE")
        dlg.geometry("500x560")
        dlg.resizable(False, False)
        dlg.configure(fg_color=C["raised"])
        dlg.transient(self)
        tk.Frame(dlg, bg=C["neon"], height=3).pack(fill="x")
        ctk.CTkLabel(dlg, text="  ATAJOS DE TECLADO", fg_color="transparent",
                     text_color=C["t1"],
                     font=ctk.CTkFont(FUI, 15, weight="bold")).pack(pady=14)
        rows = [
            ("Ctrl+N","Nuevo archivo"),("Ctrl+O","Abrir archivo"),
            ("Ctrl+S","Guardar"),("Ctrl+Shift+S","Guardar como"),
            ("Ctrl+W","Cerrar archivo"),("Ctrl+Z / Y","Deshacer / Rehacer"),
            ("Ctrl+X / C / V","Cortar / Copiar / Pegar"),
            ("Ctrl+A","Seleccionar todo"),("Ctrl+F","Buscar"),
            ("Clic derecho","Menú contextual"),
            ("F1","Análisis Léxico"),("F2","Análisis Sintáctico"),
            ("F3","Análisis Semántico"),("F5","Compilar todo"),("Alt+F4","Salir"),
        ]
        sf = ctk.CTkScrollableFrame(dlg, fg_color="transparent",
                                    scrollbar_button_color=C["neon_dim"],
                                    scrollbar_button_hover_color=C["neon"])
        sf.pack(fill="both", expand=True, padx=20)
        for key, desc in rows:
            row = tk.Frame(sf, bg=C["raised"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text=key, width=18, anchor="w",
                     bg=C["panel"], fg=C["amber"],
                     font=(FMONO, 10), padx=10, pady=5).pack(side="left")
            tk.Label(row, text=desc, anchor="w",
                     bg=C["raised"], fg=C["t2"],
                     font=(FUI, 10)).pack(side="left", padx=12)
        ctk.CTkButton(dlg, text="Cerrar", command=dlg.destroy,
                      fg_color=C["neon"], hover_color=C["neon_glow"],
                      text_color="#FFF", corner_radius=6, width=100, height=34,
                      font=ctk.CTkFont(FUI, 11)).pack(pady=12)

    def _dlg_about(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Acerca de HADES IDE")
        dlg.geometry("430x500")
        dlg.resizable(False, False)
        dlg.configure(fg_color=C["raised"])
        dlg.transient(self)
        tk.Frame(dlg, bg=C["neon"], height=3).pack(fill="x")
        tk.Label(dlg, text=ICO["logo"],
                 bg=C["raised"], fg=C["neon"],
                 font=(FMDL2, 56)).pack(pady=(20, 4))
        ctk.CTkLabel(dlg, text="HADES IDE", fg_color="transparent",
                     text_color=C["t1"],
                     font=ctk.CTkFont(FUI, 24, weight="bold")).pack()
        ctk.CTkLabel(dlg, text="Compiler Studio  ·  v8.0  —  AST compacto",
                     fg_color="transparent", text_color=C["t3"],
                     font=ctk.CTkFont(FUI, 11)).pack(pady=(0, 16))
        for feat in [
            "  AST real: operador como raíz de cada expresión",
            "  Sin nodos intermedios (expresion_simple, termino, factor…)",
            "  Colores semánticos por rol: aritmético, relacional, lógico…",
            "  Leyenda integrada en el panel del árbol",
            "  Errores léxicos en diagnóstico sin bloquear el análisis",
            "  Syntax highlighting en tiempo real (6 colores)",
            "  Árbol colapsable nodo por nodo (clic para toggle)",
            "  Editor con fuente Consolas 22pt",
        ]:
            ctk.CTkLabel(dlg, text=feat, anchor="w",
                         fg_color="transparent", text_color=C["t2"],
                         font=ctk.CTkFont(FUI, 10)).pack(fill="x", padx=38)
        ctk.CTkLabel(dlg, text="\nPython 3.10+  ·  CustomTkinter  ·  PLY  ·  MIT",
                     fg_color="transparent", text_color=C["t3"],
                     font=ctk.CTkFont(FUI, 9)).pack()
        ctk.CTkButton(dlg, text="Cerrar", command=dlg.destroy,
                      fg_color=C["neon"], hover_color=C["neon_glow"],
                      text_color="#FFF", corner_radius=6, width=100, height=34,
                      font=ctk.CTkFont(FUI, 11)).pack(pady=12)


if __name__ == "__main__":
    app = HadesIDE()
    app.mainloop()
