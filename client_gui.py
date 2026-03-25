"""
client_gui.py  –  Tkinter GUI front-end for the Online Quiz System
Replaces main.py (terminal UI).  Requires client_network.py and quiz.py.
"""

import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
import threading
import time
import sys
import os


# ── bring in the network layer ──────────────────────────────────────────────
from client_network import QuizClient, recv_json
from quiz import MCQ, UserStats

# ═══════════════════════════════════════════════════════════════════════════
#  THEME / PALETTE
# ═══════════════════════════════════════════════════════════════════════════
BG          = "#0d1117"   # deep navy-black
PANEL       = "#161b22"   # card background
BORDER      = "#30363d"   # subtle border
ACCENT      = "#58a6ff"   # electric blue
ACCENT2     = "#3fb950"   # green (correct)
DANGER      = "#f85149"   # red (wrong)
WARN        = "#d29922"   # amber (skipped / timer)
TEXT        = "#e6edf3"   # near-white
SUBTEXT     = "#8b949e"   # muted grey
BTN_FG      = "#ffffff"
BTN_ACTIVE  = "#1f6feb"


def styled_btn(parent, text, command, width=18, bg=ACCENT, **kw):
    b = tk.Button(parent, text=text, command=command,
                  bg=bg, fg=BTN_FG, activebackground=BTN_ACTIVE,
                  activeforeground=BTN_FG, relief="flat", bd=0,
                  font=("Consolas", 10, "bold"), width=width,
                  padx=8, pady=6, cursor="hand2", **kw)
    b.bind("<Enter>", lambda e: b.config(bg=BTN_ACTIVE if bg == ACCENT else bg))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


def entry_widget(parent, show="", width=28):
    e = tk.Entry(parent, show=show, width=width,
                 bg=PANEL, fg=TEXT, insertbackground=ACCENT,
                 relief="flat", bd=0, font=("Consolas", 11),
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT)
    return e


def label(parent, text, size=11, color=TEXT, bold=False, **kw):
    weight = "bold" if bold else "normal"
    return tk.Label(parent, text=text, bg=parent["bg"] if "bg" not in kw else kw.pop("bg"),
                    fg=color, font=("Consolas", size, weight), **kw)


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Let Us Learn — Online Quiz System")
        self.state("zoomed")   # Windows fullscreen
        self.resizable(True, True)
        self.bind("<F11>", lambda e: self.attributes("-fullscreen", not self.attributes("-fullscreen")))
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.client: QuizClient | None = None
        self.username: str | None = None
        self.stats: UserStats | None = None

        # container that holds all frames
        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        self._connect_to_server()
        self._show_splash()

    # ── server connection ────────────────────────────────────────────────
    def _connect_to_server(self):
        try:
            self.client = QuizClient()
        except Exception as ex:
            messagebox.showerror("Connection Error",
                                 f"Cannot connect to server:\n{ex}\n\n"
                                 "Make sure the server is running.")
            self.destroy()
            sys.exit(1)

    def _on_close(self):
        try:
            if self.username and self.client:
                self.client.logout(self.username)
        except Exception:
            pass
        self.destroy()

    # ── frame helpers ────────────────────────────────────────────────────
    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    # ═══════════════════════════════════════════════════════════════════
    #  SPLASH / HOME
    # ═══════════════════════════════════════════════════════════════════
    def _show_splash(self):
        self._clear()
        f = tk.Frame(self.container, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")

        # ASCII-style logo rendered as labels
        logo_lines = [
            "  _         _     _   _       _",
            " | |    ___| |_  | | | |___  | |    ___  __ _ _ __ _ __",
            " | |   / _ \\ __| | | | / __| | |   / _ \\/ _` | '__| '_ \\",
            " | |__|  __/ |_  | |_| \\__ \\ | |__|  __/ (_| | |  | | | |",
            " |_____\\___|\\__|  \\___/|___/ |_____\\___|\\__,_|_|  |_| |_|",
        ]
        for line in logo_lines:
            tk.Label(f, text=line, bg=BG, fg=ACCENT,
                     font=("Courier", 9, "bold")).pack(anchor="w")

        label(f, "Online Quiz System", 12, SUBTEXT).pack(pady=(4, 20))

        btn_f = tk.Frame(f, bg=BG)
        btn_f.pack()
        styled_btn(btn_f, "⟶  Log In",  self._show_login,  width=20).grid(row=0, column=0, padx=8, pady=4)
        styled_btn(btn_f, "⟶  Sign Up", self._show_signup, width=20, bg="#238636").grid(row=0, column=1, padx=8, pady=4)
        styled_btn(btn_f, "Exit", self._on_close, width=10, bg="#21262d").grid(row=1, column=0, columnspan=2, pady=(8, 0))

    # ═══════════════════════════════════════════════════════════════════
    #  LOGIN
    # ═══════════════════════════════════════════════════════════════════
    def _show_login(self):
        self._clear()
        f = tk.Frame(self.container, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")

        label(f, "LOG IN", 16, ACCENT, True).pack(pady=(0, 20))

        form = tk.Frame(f, bg=BG)
        form.pack()

        label(form, "Username", bg=BG).grid(row=0, column=0, sticky="w", pady=4)
        u_entry = entry_widget(form)
        u_entry.grid(row=0, column=1, padx=(8, 0), pady=4)

        label(form, "Password", bg=BG).grid(row=1, column=0, sticky="w", pady=4)
        p_entry = entry_widget(form, show="●")
        p_entry.grid(row=1, column=1, padx=(8, 0), pady=4)

        status_lbl = label(f, "", 10, DANGER)
        status_lbl.pack(pady=(8, 0))

        def do_login():
            u = u_entry.get().strip()
            p = p_entry.get().strip()
            if not u or not p:
                status_lbl.config(text="Fields cannot be empty.")
                return
            try:
                ok = self.client.login(u, p)
            except Exception as ex:
                status_lbl.config(text=f"Error: {ex}")
                return
            if ok:
                self.username = u
                server_stats = self.client.get_user_stats(u)
                self.stats = UserStats(u,
                                       server_stats["correct"],
                                       server_stats["incorrect"],
                                       server_stats["skipped"])
                self._show_main_menu()
            else:
                status_lbl.config(text="Invalid username or password.")

        styled_btn(f, "Login", do_login, width=20).pack(pady=12)
        styled_btn(f, "← Back", self._show_splash, width=10, bg="#21262d").pack()
        u_entry.focus()
        self.bind("<Return>", lambda e: do_login())

    # ═══════════════════════════════════════════════════════════════════
    #  SIGNUP
    # ═══════════════════════════════════════════════════════════════════
    def _show_signup(self):
        self._clear()
        f = tk.Frame(self.container, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")

        label(f, "SIGN UP", 16, ACCENT2, True).pack(pady=(0, 20))

        form = tk.Frame(f, bg=BG)
        form.pack()

        label(form, "Username", bg=BG).grid(row=0, column=0, sticky="w", pady=4)
        u_entry = entry_widget(form)
        u_entry.grid(row=0, column=1, padx=(8, 0), pady=4)

        label(form, "Password", bg=BG).grid(row=1, column=0, sticky="w", pady=4)
        p_entry = entry_widget(form, show="●")
        p_entry.grid(row=1, column=1, padx=(8, 0), pady=4)

        label(form, "Confirm", bg=BG).grid(row=2, column=0, sticky="w", pady=4)
        c_entry = entry_widget(form, show="●")
        c_entry.grid(row=2, column=1, padx=(8, 0), pady=4)

        status_lbl = label(f, "", 10, DANGER)
        status_lbl.pack(pady=(8, 0))

        def do_signup():
            u = u_entry.get().strip()
            p = p_entry.get().strip()
            c = c_entry.get().strip()
            if not u or not p:
                status_lbl.config(text="Fields cannot be empty.")
                return
            if p != c:
                status_lbl.config(text="Passwords do not match.")
                return
            try:
                result = self.client.signup(u, p)
            except Exception as ex:
                status_lbl.config(text=f"Error: {ex}")
                return
            if result == "success":
                status_lbl.config(text="Account created! You can now log in.", fg=ACCENT2)
                self.after(1800, self._show_login)
            elif result == "exists":
                status_lbl.config(text=f"Username '{u}' already taken.", fg=DANGER)
            else:
                status_lbl.config(text="Signup failed.", fg=DANGER)

        styled_btn(f, "Create Account", do_signup, width=20, bg="#238636").pack(pady=12)
        styled_btn(f, "← Back", self._show_splash, width=10, bg="#21262d").pack()
        u_entry.focus()

    # ═══════════════════════════════════════════════════════════════════
    #  MAIN MENU (post-login)
    # ═══════════════════════════════════════════════════════════════════
    def _show_main_menu(self):
        self._clear()
        root_f = tk.Frame(self.container, bg=BG)
        root_f.pack(fill="both", expand=True)

        # top bar
        top = tk.Frame(root_f, bg=PANEL, height=48)
        top.pack(fill="x")
        top.pack_propagate(False)
        label(top, "  LET US LEARN", 13, ACCENT, True).pack(side="left", padx=12, pady=10)
        label(top, f"  Logged in as: {self.username}", 10, SUBTEXT).pack(side="left")
        styled_btn(top, "Logout", self._do_logout, width=8, bg="#21262d").pack(side="right", padx=12, pady=8)

        # nav buttons
        center = tk.Frame(root_f, bg=BG)
        center.place(relx=.5, rely=.5, anchor="center")

        label(center, f"Welcome, {self.username}!", 14, TEXT, True).pack(pady=(0, 24))

        menu_items = [
            ("📝  Give Test",           ACCENT,    self._show_quiz_setup),
            ("📊  Cumulative Stats",     "#6e40c9", self._show_stats),
            ("🏆  Leaderboard",          WARN,      self._show_leaderboard),
            ("⚡  Multiplayer Quiz",     ACCENT2,   self._show_multiplayer),
        ]
        for txt, col, cmd in menu_items:
            styled_btn(center, txt, cmd, width=28, bg=col).pack(pady=6)

    def _do_logout(self):
        try:
            self.client.logout(self.username)
        except Exception:
            pass
        self.username = None
        self.stats = None
        self._show_splash()

    # ═══════════════════════════════════════════════════════════════════
    #  QUIZ SETUP
    # ═══════════════════════════════════════════════════════════════════
    def _show_quiz_setup(self):
        self._clear()
        f = tk.Frame(self.container, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")

        label(f, "QUIZ SETUP", 15, ACCENT, True).pack(pady=(0, 20))

        topics = [("A", "EPD"), ("B", "C-Programming"),
                  ("C", "Mental Ability"), ("D", "Python"), ("E", "Triple Integration")]
        diffs  = [("A", "Easy"), ("B", "Medium"), ("C", "Hard")]

        topic_var = tk.StringVar(value="A")
        diff_var  = tk.StringVar(value="A")

        tk.Label(f, text="Topic", bg=BG, fg=SUBTEXT,
                 font=("Consolas", 10)).pack(anchor="w")
        t_frame = tk.Frame(f, bg=BG)
        t_frame.pack(anchor="w", pady=(2, 12))
        for code, name in topics:
            tk.Radiobutton(t_frame, text=f"  {name}", variable=topic_var, value=code,
                           bg=BG, fg=TEXT, selectcolor=PANEL, activebackground=BG,
                           font=("Consolas", 10), indicatoron=True).pack(anchor="w")

        tk.Label(f, text="Difficulty", bg=BG, fg=SUBTEXT,
                 font=("Consolas", 10)).pack(anchor="w")
        d_frame = tk.Frame(f, bg=BG)
        d_frame.pack(anchor="w", pady=(2, 16))
        diff_colors = {"A": ACCENT2, "B": WARN, "C": DANGER}
        for code, name in diffs:
            tk.Radiobutton(d_frame, text=f"  {name}", variable=diff_var, value=code,
                           bg=BG, fg=diff_colors[code], selectcolor=PANEL,
                           activebackground=BG, font=("Consolas", 10),
                           indicatoron=True).pack(anchor="w")

        num_var = tk.StringVar(value="10")
        row = tk.Frame(f, bg=BG)
        row.pack(anchor="w", pady=(0, 16))
        label(row, "No. of Questions:", bg=BG).pack(side="left")
        sp = tk.Spinbox(row, from_=1, to=50, textvariable=num_var, width=5,
                        bg=PANEL, fg=TEXT, buttonbackground=BORDER,
                        font=("Consolas", 11), relief="flat",
                        highlightthickness=1, highlightbackground=BORDER)
        sp.pack(side="left", padx=8)

        def start():
            topic = topic_var.get()
            diff  = diff_var.get()
            try:
                n = int(num_var.get())
            except ValueError:
                n = 10
            self._run_quiz(topic, diff, n)

        styled_btn(f, "▶  Start Quiz", start, width=20).pack(pady=4)
        styled_btn(f, "← Back",        self._show_main_menu, width=10, bg="#21262d").pack()

    # ═══════════════════════════════════════════════════════════════════
    #  QUIZ RUNNER
    # ═══════════════════════════════════════════════════════════════════
    def _run_quiz(self, topic, diff, requested_n):
        questions = self.client.get_quiz(topic, diff)
        if not questions:
            messagebox.showinfo("No Questions",
                                "No questions found for that topic/difficulty.")
            return
        questions = questions[:min(requested_n, len(questions))]

        diff_map = {"A": "Easy", "B": "Medium", "C": "Hard"}
        diff_name = diff_map.get(diff, "Easy")
        per_q = {"Easy": 30, "Medium": 60, "Hard": 120}[diff_name]
        total_time = per_q * len(questions)

        self._show_quiz_ui(questions, total_time)

    def _show_quiz_ui(self, questions, total_time):
        self._clear()

        self._q_index   = 0
        self._questions = questions
        self._total_t   = total_time
        self._start_t   = time.time()
        self._selected  = tk.StringVar(value="")
        self._quiz_done = False

        outer = tk.Frame(self.container, bg=BG)
        outer.pack(fill="both", expand=True)

        # header bar
        hdr = tk.Frame(outer, bg=PANEL, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        self._q_counter_lbl = label(hdr, "", 10, SUBTEXT)
        self._q_counter_lbl.pack(side="left", padx=12, pady=10)
        self._timer_lbl = label(hdr, "", 11, WARN, True)
        self._timer_lbl.pack(side="right", padx=12, pady=10)

        # question area
        mid = tk.Frame(outer, bg=BG)
        mid.pack(fill="both", expand=True, padx=40, pady=16)

        self._q_text = tk.Label(mid, text="", bg=BG, fg=TEXT,
                                font=("Consolas", 12), wraplength=700,
                                justify="left", anchor="w")
        self._q_text.pack(fill="x", pady=(0, 16))

        self._opt_frame = tk.Frame(mid, bg=BG)
        self._opt_frame.pack(fill="x")

        self._radio_btns = []
        for opt in ["A", "B", "C", "D"]:
            rb = tk.Radiobutton(self._opt_frame, text="", variable=self._selected,
                                value=opt, bg=BG, fg=TEXT, selectcolor=PANEL,
                                activebackground=BG, font=("Consolas", 11),
                                anchor="w", wraplength=680, justify="left",
                                indicatoron=False,
                                relief="flat", bd=0,
                                highlightthickness=1, highlightbackground=BORDER,
                                highlightcolor=ACCENT,
                                padx=12, pady=8, cursor="hand2")
            rb.pack(fill="x", pady=3)
            self._radio_btns.append(rb)

        # bottom bar
        bot = tk.Frame(outer, bg=PANEL, height=56)
        bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)

        styled_btn(bot, "⏭ Skip", self._skip_question, width=10, bg=WARN).pack(side="left", padx=12, pady=10)
        styled_btn(bot, "Next ▶", self._next_question, width=10).pack(side="right", padx=12, pady=10)

        self._load_question()
        self._tick()

    def _load_question(self):
        if self._q_index >= len(self._questions):
            self._finish_quiz()
            return
        q = self._questions[self._q_index]
        self._selected.set("")
        self._q_counter_lbl.config(
            text=f"Question {self._q_index + 1} / {len(self._questions)}")
        self._q_text.config(text=f"Q{q.id}:  {q.question}")
        opts = [q.option_a, q.option_b, q.option_c, q.option_d]
        for rb, opt_lbl, txt in zip(self._radio_btns,
                                    ["A", "B", "C", "D"], opts):
            rb.config(text=f"  {opt_lbl}.  {txt}", value=opt_lbl)

    def _next_question(self):
        if self._quiz_done:
            return
        q = self._questions[self._q_index]
        sel = self._selected.get()
        if not sel:
            # nothing chosen — treat as skip
            q.user_option = "S"
            q.is_correct  = 0
        else:
            q.user_option = sel
            q.is_correct  = 1 if sel == q.correct_option else 0
        self._q_index += 1
        self._load_question()

    def _skip_question(self):
        if self._quiz_done:
            return
        q = self._questions[self._q_index]
        q.user_option = "S"
        q.is_correct  = 0
        self._q_index += 1
        self._load_question()

    def _tick(self):
        if self._quiz_done:
            return
        elapsed  = time.time() - self._start_t
        remaining = self._total_t - elapsed
        if remaining <= 0:
            self._finish_quiz()
            return
        m, s = divmod(int(remaining), 60)
        color = DANGER if remaining < 30 else WARN
        self._timer_lbl.config(text=f"⏱  {m:02d}:{s:02d}", fg=color)
        self.after(500, self._tick)

    def _finish_quiz(self):
        self._quiz_done = True
        # mark any remaining as skipped
        for q in self._questions[self._q_index:]:
            if q.user_option == ' ':
                q.user_option = 'S'
                q.is_correct  = 0

        correct  = sum(1 for q in self._questions if q.is_correct)
        wrong    = sum(1 for q in self._questions
                       if q.user_option != 'S' and not q.is_correct)
        skipped  = sum(1 for q in self._questions if q.user_option == 'S')
        total    = len(self._questions)

        self.stats.total_correct   += correct
        self.stats.total_incorrect += wrong
        self.stats.total_skipped   += skipped

        try:
            self.client.save_stats(self.username, correct, wrong, skipped)
        except Exception:
            pass

        self._show_results_screen(self._questions, correct, wrong, skipped, total)

    # ═══════════════════════════════════════════════════════════════════
    #  RESULTS SCREEN
    # ═══════════════════════════════════════════════════════════════════
    def _show_results_screen(self, questions, correct, wrong, skipped, total):
        self._clear()
        f = tk.Frame(self.container, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")

        label(f, "QUIZ COMPLETE", 16, ACCENT, True).pack(pady=(0, 20))

        card = tk.Frame(f, bg=PANEL, padx=30, pady=20,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack()

        stats = [
            ("✅  Correct",   correct,  ACCENT2),
            ("❌  Incorrect", wrong,    DANGER),
            ("⏭  Skipped",   skipped,  WARN),
            ("📋  Total",     total,    TEXT),
        ]
        for txt, val, col in stats:
            row = tk.Frame(card, bg=PANEL)
            row.pack(fill="x", pady=3)
            label(row, txt, 11, col, bg=PANEL).pack(side="left")
            label(row, str(val), 14, col, True, bg=PANEL).pack(side="right", padx=12)

        if correct + wrong > 0:
            acc = correct * 100 // (correct + wrong)
            label(f, f"Accuracy: {acc}%", 12, ACCENT, True).pack(pady=(12, 0))

        btn_f = tk.Frame(f, bg=BG)
        btn_f.pack(pady=16)

        def review():
            self._show_review_screen(questions)

        styled_btn(btn_f, "Review Answers", review, width=16).grid(row=0, column=0, padx=6)
        styled_btn(btn_f, "Back to Menu", self._show_main_menu,
                   width=16, bg="#21262d").grid(row=0, column=1, padx=6)

    # ═══════════════════════════════════════════════════════════════════
    #  REVIEW SCREEN
    # ═══════════════════════════════════════════════════════════════════
    def _show_review_screen(self, questions):
        self._clear()
        outer = tk.Frame(self.container, bg=BG)
        outer.pack(fill="both", expand=True)

        hdr = tk.Frame(outer, bg=PANEL, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        label(hdr, "  ANSWER REVIEW", 12, ACCENT, True).pack(side="left", padx=12, pady=10)
        styled_btn(hdr, "← Menu", self._show_main_menu,
                   width=8, bg="#21262d").pack(side="right", padx=12, pady=8)

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=inner, anchor="nw")

        for q in questions:
            card = tk.Frame(inner, bg=PANEL, padx=16, pady=10,
                            highlightthickness=1, highlightbackground=BORDER)
            card.pack(fill="x", padx=20, pady=4)

            if q.user_option == 'S':
                icon, col = "⏭", WARN
                verdict = "Skipped"
            elif q.is_correct:
                icon, col = "✅", ACCENT2
                verdict = "Correct"
            else:
                icon, col = "❌", DANGER
                verdict = "Incorrect"

            top_row = tk.Frame(card, bg=PANEL)
            top_row.pack(fill="x")
            label(top_row, f"Q{q.id}: {q.question}", 10, TEXT,
                  bg=PANEL).pack(side="left", fill="x", expand=True)
            label(top_row, f"{icon} {verdict}", 10, col, True,
                  bg=PANEL).pack(side="right")

            bot_row = tk.Frame(card, bg=PANEL)
            bot_row.pack(fill="x", pady=(4, 0))
            label(bot_row, f"Your answer: {q.user_option}", 9, col,
                  bg=PANEL).pack(side="left")
            label(bot_row, f"Correct: {q.correct_option}", 9, ACCENT2,
                  bg=PANEL).pack(side="right")

        inner.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * int(e.delta / 120), "units"))

    # ═══════════════════════════════════════════════════════════════════
    #  STATS
    # ═══════════════════════════════════════════════════════════════════
    def _show_stats(self):
        self._clear()
        server_stats = self.client.get_user_stats(self.username)

        f = tk.Frame(self.container, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")

        label(f, "YOUR STATS", 15, "#6e40c9", True).pack(pady=(0, 20))

        card = tk.Frame(f, bg=PANEL, padx=30, pady=20,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack()

        correct   = server_stats.get("correct", 0)
        incorrect = server_stats.get("incorrect", 0)
        skipped   = server_stats.get("skipped", 0)
        rank      = server_stats.get("rank", 0)
        attempted = correct + incorrect
        total_q   = attempted + skipped

        rows = [
            ("✅  Correct",   correct,   ACCENT2),
            ("❌  Incorrect", incorrect, DANGER),
            ("⏭  Skipped",   skipped,   WARN),
        ]
        for txt, val, col in rows:
            r = tk.Frame(card, bg=PANEL)
            r.pack(fill="x", pady=3)
            label(r, txt, 11, col, bg=PANEL).pack(side="left")
            label(r, str(val), 14, col, True, bg=PANEL).pack(side="right", padx=12)

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=8)

        if attempted > 0:
            acc  = correct * 100 // attempted
            perc = (correct * 100 // total_q) if total_q else 0
            label(card, f"Accuracy:   {acc}%", 11, ACCENT, bg=PANEL).pack(anchor="w")
            label(card, f"Percentage: {perc}%", 11, ACCENT, bg=PANEL).pack(anchor="w")
        else:
            label(card, "No attempts yet.", 11, SUBTEXT, bg=PANEL).pack()

        if rank > 0:
            label(card, f"🏅 Your rank: #{rank}", 12, WARN, True, bg=PANEL).pack(pady=(8, 0))

        styled_btn(f, "← Back", self._show_main_menu,
                   width=10, bg="#21262d").pack(pady=16)

    # ═══════════════════════════════════════════════════════════════════
    #  LEADERBOARD
    # ═══════════════════════════════════════════════════════════════════
    def _show_leaderboard(self):
        self._clear()
        f = tk.Frame(self.container, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")

        label(f, "🏆  LEADERBOARD", 15, WARN, True).pack(pady=(0, 20))

        try:
            leaderboard = self.client.get_leaderboard()
        except Exception:
            leaderboard = []

        card = tk.Frame(f, bg=PANEL, padx=30, pady=20,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack()

        # header
        hdr = tk.Frame(card, bg=PANEL)
        hdr.pack(fill="x")
        for col_txt, w in [("#", 3), ("Username", 18), ("Score", 8)]:
            label(hdr, col_txt, 10, SUBTEXT, True, bg=PANEL,
                  width=w).pack(side="left", padx=4)

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=4)

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        if not leaderboard:
            label(card, "No stats available yet.", 11, SUBTEXT, bg=PANEL).pack(pady=8)
        else:
            for entry in leaderboard:
                row = tk.Frame(card, bg=PANEL)
                row.pack(fill="x", pady=2)
                rank_icon = medals.get(entry["rank"], str(entry["rank"]))
                label(row, rank_icon, 12, WARN, bg=PANEL, width=3).pack(side="left", padx=4)
                label(row, entry["username"], 11, TEXT, bg=PANEL, width=18).pack(side="left", padx=4)
                label(row, str(entry["score"]), 11, ACCENT2, True, bg=PANEL, width=8).pack(side="left", padx=4)

        styled_btn(f, "← Back", self._show_main_menu,
                   width=10, bg="#21262d").pack(pady=16)

    # ═══════════════════════════════════════════════════════════════════
    #  MULTIPLAYER
    # ═══════════════════════════════════════════════════════════════════
    def _show_multiplayer(self):
        self._clear()
        f = tk.Frame(self.container, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")

        label(f, "⚡  MULTIPLAYER", 15, ACCENT2, True).pack(pady=(0, 12))
        status_lbl = label(f, "Joining lobby...", 11, SUBTEXT)
        status_lbl.pack(pady=8)

        progress = ttk.Progressbar(f, mode="indeterminate", length=260)
        progress.pack(pady=8)
        progress.start(12)

        styled_btn(f, "← Back", self._show_main_menu,
                   width=10, bg="#21262d").pack(pady=12)

        def join_thread():
            try:
                response = self.client.join_multiplayer(self.username)
            except Exception as ex:
                self.after(0, lambda: status_lbl.config(
                    text=f"Error: {ex}", fg=DANGER))
                self.after(0, progress.stop)
                return

            if response.get("status") == "started":
                self.after(0, lambda: status_lbl.config(
                    text=response.get("message", "Quiz already running."),
                    fg=DANGER))
                self.after(0, progress.stop)
                return

            self.after(0, lambda: status_lbl.config(
                text="✅  In lobby — waiting for host to start...", fg=ACCENT2))

            # wait for quiz_start from server
            msg = recv_json(self.client.conn)
            if not msg:
                self.after(0, lambda: status_lbl.config(
                    text="Server disconnected.", fg=DANGER))
                return

            if msg.get("type") == "quiz_start":
                start_time = msg["start_time"]
                duration   = msg["duration"]

                topic = msg.get("topic", "D")
                difficulty = msg.get("difficulty", "A")

                wait       = start_time - time.time()

                def countdown(secs):
                    if secs > 0:
                        self.after(0, lambda: status_lbl.config(
                            text=f"Quiz starts in {secs}s ...", fg=WARN))
                        self.after(1000, lambda: countdown(secs - 1))
                    else:
                        self.after(0, lambda: [
                            progress.stop(),
                            self._launch_mp_quiz(duration, topic, difficulty)
                        ])

                self.after(0, lambda: countdown(max(0, int(wait))))

        threading.Thread(target=join_thread, daemon=True).start()

    def _launch_mp_quiz(self, duration, topic, difficulty):
        questions = self.client.get_quiz(topic, difficulty)
        
        if not questions:
            messagebox.showinfo("Multiplayer", "No questions received.")
            self._show_main_menu()
            return
        self._show_quiz_ui(questions, duration)

        def wait_for_end():
            end_msg = recv_json(self.client.conn)
            if end_msg and end_msg.get("type") == "quiz_end":
                self.after(0, lambda: messagebox.showinfo(
                    "Multiplayer", "Quiz ended by server!"))

        threading.Thread(target=wait_for_end, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()