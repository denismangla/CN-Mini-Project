"""
client_gui.py  –  Tkinter GUI front-end for the Online Quiz System
Replaces main.py (terminal UI).  Requires client_network.py and quiz.py.

Enhancements:
  1. Submit + Back buttons in quiz
  2. Mark for Review per question
  3. Question panel (answered / marked / unvisited)
  4. Answer review shows all options with correct/wrong highlighting
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

# Question panel state colours
Q_UNVISITED = "#21262d"   # dark grey
Q_ANSWERED  = "#1a4a1a"   # dark green
Q_REVIEW    = "#5a3e00"   # dark amber
Q_CURRENT   = ACCENT      # blue highlight


def styled_btn(parent, text, command, width=18, bg=ACCENT, **kw):
    b = tk.Button(parent, text=text, command=command,
                  bg=bg, fg=BTN_FG, activebackground=BTN_ACTIVE,
                  activeforeground=BTN_FG, relief="flat", bd=0,
                  font=("Consolas", 12, "bold"), width=width,
                  padx=8, pady=6, cursor="hand2", **kw)
    b.bind("<Enter>", lambda e: b.config(bg=BTN_ACTIVE if bg == ACCENT else bg))
    b.bind("<Leave>", lambda e: b.config(bg=bg))
    return b


def entry_widget(parent, show="", width=28):
    e = tk.Entry(parent, show=show, width=width,
                 bg=PANEL, fg=TEXT, insertbackground=ACCENT,
                 relief="flat", bd=0, font=("Consolas", 13),
                 highlightthickness=1, highlightbackground=BORDER,
                 highlightcolor=ACCENT)
    return e


def label(parent, text, size=11, color=TEXT, bold=False, **kw):
    weight = "bold" if bold else "normal"
    return tk.Label(parent, text=text,
                    bg=parent["bg"] if "bg" not in kw else kw.pop("bg"),
                    fg=color, font=("Consolas", size + 2, weight), **kw)


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Let Us Learn — Online Quiz System")
        self.state("zoomed")
        self.resizable(True, True)
        self.bind("<F11>", lambda e: self.attributes("-fullscreen",
                                                     not self.attributes("-fullscreen")))
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.client: QuizClient | None = None
        self.username: str | None = None
        self.stats: UserStats | None = None

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

        logo_lines = [
            "  _         _     _   _       _",
            " | |    ___| |_  | | | |___  | |    ___  __ _ _ __ _ __",
            " | |   / _ \\ __| | | | / __| | |   / _ \\/ _` | '__| '_ \\",
            " | |__|  __/ |_  | |_| \\__ \\ | |__|  __/ (_| | |  | | | |",
            " |_____\\___|\\__|  \\___/|___/ |_____\\___|\\__,_|_|  |_| |_|",
        ]
        for line in logo_lines:
            tk.Label(f, text=line, bg=BG, fg=ACCENT,
                     font=("Courier", 11, "bold")).pack(anchor="w")

        label(f, "Online Quiz System", 12, SUBTEXT).pack(pady=(4, 20))

        btn_f = tk.Frame(f, bg=BG)
        btn_f.pack()
        styled_btn(btn_f, "⟶  Log In",  self._show_login,  width=20).grid(
            row=0, column=0, padx=8, pady=4)
        styled_btn(btn_f, "⟶  Sign Up", self._show_signup, width=20,
                   bg="#238636").grid(row=0, column=1, padx=8, pady=4)
        styled_btn(btn_f, "Exit", self._on_close, width=10,
                   bg="#21262d").grid(row=1, column=0, columnspan=2, pady=(8, 0))

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
    #  MAIN MENU
    # ═══════════════════════════════════════════════════════════════════
    def _show_main_menu(self):
        self._clear()
        root_f = tk.Frame(self.container, bg=BG)
        root_f.pack(fill="both", expand=True)

        top = tk.Frame(root_f, bg=PANEL, height=48)
        top.pack(fill="x")
        top.pack_propagate(False)
        label(top, "  LET US LEARN", 13, ACCENT, True).pack(side="left", padx=12, pady=10)
        label(top, f"  Logged in as: {self.username}", 10, SUBTEXT).pack(side="left")
        styled_btn(top, "Logout", self._do_logout, width=8, bg="#21262d").pack(
            side="right", padx=12, pady=8)

        center = tk.Frame(root_f, bg=BG)
        center.place(relx=.5, rely=.5, anchor="center")

        label(center, f"Welcome, {self.username}!", 14, TEXT, True).pack(pady=(0, 24))

        menu_items = [
            ("📝  Give Test",        ACCENT,    self._show_quiz_setup),
            ("📊  Cumulative Stats", "#6e40c9", self._show_stats),
            ("🏆  Leaderboard",      WARN,      self._show_leaderboard),
            ("⚡  Multiplayer Quiz", ACCENT2,   self._show_multiplayer),
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
                  ("C", "Mental Ability"), ("D", "Python"),
                  ("E", "Triple Integration")]
        diffs  = [("A", "Easy"), ("B", "Medium"), ("C", "Hard")]

        topic_var = tk.StringVar(value="A")
        diff_var  = tk.StringVar(value="A")

        tk.Label(f, text="Topic", bg=BG, fg=SUBTEXT,
                 font=("Consolas", 12)).pack(anchor="w")
        t_frame = tk.Frame(f, bg=BG)
        t_frame.pack(anchor="w", pady=(2, 12))
        for code, name in topics:
            tk.Radiobutton(t_frame, text=f"  {name}", variable=topic_var, value=code,
                           bg=BG, fg=TEXT, selectcolor=PANEL, activebackground=BG,
                           font=("Consolas", 12), indicatoron=True).pack(anchor="w")

        tk.Label(f, text="Difficulty", bg=BG, fg=SUBTEXT,
                 font=("Consolas", 12)).pack(anchor="w")
        d_frame = tk.Frame(f, bg=BG)
        d_frame.pack(anchor="w", pady=(2, 16))
        diff_colors = {"A": ACCENT2, "B": WARN, "C": DANGER}
        for code, name in diffs:
            tk.Radiobutton(d_frame, text=f"  {name}", variable=diff_var, value=code,
                           bg=BG, fg=diff_colors[code], selectcolor=PANEL,
                           activebackground=BG, font=("Consolas", 12),
                           indicatoron=True).pack(anchor="w")

        num_var = tk.StringVar(value="10")
        row = tk.Frame(f, bg=BG)
        row.pack(anchor="w", pady=(0, 16))
        label(row, "No. of Questions:", bg=BG).pack(side="left")
        sp = tk.Spinbox(row, from_=1, to=10, textvariable=num_var, width=5,
                        bg=PANEL, fg=TEXT, buttonbackground=BORDER,
                        font=("Consolas", 13), relief="flat",
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
        styled_btn(f, "← Back", self._show_main_menu, width=10, bg="#21262d").pack()

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

        diff_map  = {"A": "Easy", "B": "Medium", "C": "Hard"}
        diff_name = diff_map.get(diff, "Easy")
        per_q     = {"Easy": 30, "Medium": 60, "Hard": 120}[diff_name]
        total_time = per_q * len(questions)

        self._show_quiz_ui(questions, total_time)

    # ═══════════════════════════════════════════════════════════════════
    #  QUIZ UI  (enhanced)
    # ═══════════════════════════════════════════════════════════════════
    def _show_quiz_ui(self, questions, total_time):
        self._clear()

        self._q_index   = 0
        self._questions = questions
        self._total_t   = total_time
        self._start_t   = time.time()
        self._quiz_done = False

        # per-question state  { index: {"answer": str|"", "marked": bool, "visited": bool} }
        self._q_state = {i: {"answer": "", "marked": False, "visited": False}
                         for i in range(len(questions))}
        self._selected = tk.StringVar(value="")

        # ── root layout: left panel + main area ─────────────────────
        outer = tk.Frame(self.container, bg=BG)
        outer.pack(fill="both", expand=True)

        # ── LEFT: question navigation panel ─────────────────────────
        left_panel = tk.Frame(outer, bg=PANEL, width=200,
                              highlightthickness=1, highlightbackground=BORDER)
        left_panel.pack(side="left", fill="y")
        left_panel.pack_propagate(False)

        label(left_panel, "Questions", 10, SUBTEXT, True, bg=PANEL).pack(
            pady=(12, 4), padx=10, anchor="w")

        # legend
        legend_f = tk.Frame(left_panel, bg=PANEL)
        legend_f.pack(fill="x", padx=10, pady=(0, 8))
        for col, txt in [(ACCENT2, "Answered"), (WARN, "Review"), (SUBTEXT, "Unvisited")]:
            row = tk.Frame(legend_f, bg=PANEL)
            row.pack(anchor="w", pady=1)
            tk.Frame(row, bg=col, width=10, height=10).pack(side="left", padx=(0, 4))
            tk.Label(row, text=txt, bg=PANEL, fg=SUBTEXT,
                     font=("Consolas", 10)).pack(side="left")

        tk.Frame(left_panel, bg=BORDER, height=1).pack(fill="x", padx=10, pady=4)

        # summary counters
        self._lbl_answered = tk.Label(left_panel, text="", bg=PANEL,
                                      fg=ACCENT2, font=("Consolas", 11))
        self._lbl_answered.pack(anchor="w", padx=12)
        self._lbl_review   = tk.Label(left_panel, text="", bg=PANEL,
                                      fg=WARN, font=("Consolas", 11))
        self._lbl_review.pack(anchor="w", padx=12)
        self._lbl_unvisited = tk.Label(left_panel, text="", bg=PANEL,
                                       fg=SUBTEXT, font=("Consolas", 11))
        self._lbl_unvisited.pack(anchor="w", padx=12)

        tk.Frame(left_panel, bg=BORDER, height=1).pack(fill="x", padx=10, pady=6)

        # grid of question number buttons (5 per row)
        grid_f = tk.Frame(left_panel, bg=PANEL)
        grid_f.pack(fill="x", padx=10)
        self._q_btns = []
        for i in range(len(questions)):
            btn = tk.Button(grid_f, text=str(i + 1), width=3, height=1,
                            bg=Q_UNVISITED, fg=TEXT,
                            font=("Consolas", 11, "bold"), relief="flat",
                            cursor="hand2", bd=0,
                            command=lambda idx=i: self._jump_to(idx))
            btn.grid(row=i // 5, column=i % 5, padx=2, pady=2)
            self._q_btns.append(btn)

        # ── RIGHT: main quiz area ────────────────────────────────────
        right = tk.Frame(outer, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # header bar
        hdr = tk.Frame(right, bg=PANEL, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        self._q_counter_lbl = label(hdr, "", 10, SUBTEXT)
        self._q_counter_lbl.pack(side="left", padx=12, pady=10)
        self._timer_lbl = label(hdr, "", 11, WARN, True)
        self._timer_lbl.pack(side="right", padx=12, pady=10)

        # question text
        mid = tk.Frame(right, bg=BG)
        mid.pack(fill="both", expand=True, padx=40, pady=16)

        self._q_text = tk.Label(mid, text="", bg=BG, fg=TEXT,
                                font=("Consolas", 14), wraplength=700,
                                justify="left", anchor="w")
        self._q_text.pack(fill="x", pady=(0, 16))

        self._opt_frame = tk.Frame(mid, bg=BG)
        self._opt_frame.pack(fill="x")

        self._radio_btns = []
        for opt in ["A", "B", "C", "D"]:
            rb = tk.Radiobutton(self._opt_frame, text="",
                                variable=self._selected, value=opt,
                                bg=BG, fg=TEXT, selectcolor=PANEL,
                                activebackground=BG, font=("Consolas", 13),
                                anchor="w", wraplength=680, justify="left",
                                indicatoron=False, relief="flat", bd=0,
                                highlightthickness=1, highlightbackground=BORDER,
                                highlightcolor=ACCENT,
                                padx=12, pady=8, cursor="hand2")
            rb.pack(fill="x", pady=3)
            self._radio_btns.append(rb)

        # ── bottom bar ───────────────────────────────────────────────
        bot = tk.Frame(right, bg=PANEL, height=56)
        bot.pack(fill="x", side="bottom")
        bot.pack_propagate(False)

        # Left side: Back
        styled_btn(bot, "◀ Back", self._prev_question,
                   width=10, bg="#21262d").pack(side="left", padx=8, pady=10)

        # Middle-left: Mark for Review
        self._mark_btn = tk.Button(bot, text="🔖 Mark for Review",
                                   command=self._toggle_mark,
                                   bg=Q_REVIEW, fg=BTN_FG,
                                   activebackground="#7a5200",
                                   relief="flat", bd=0,
                                   font=("Consolas", 12, "bold"),
                                   width=16, padx=8, pady=6, cursor="hand2")
        self._mark_btn.pack(side="left", padx=8, pady=10)

        # Right side: Submit Quiz
        styled_btn(bot, "✔ Submit Quiz", self._confirm_submit,
                   width=14, bg=DANGER).pack(side="right", padx=8, pady=10)

        # Right side: Next
        styled_btn(bot, "Next ▶", self._next_question,
                   width=10).pack(side="right", padx=4, pady=10)

        # Mark btn hover
        self._mark_btn.bind("<Enter>",
                            lambda e: self._mark_btn.config(bg="#7a5200"))
        self._mark_btn.bind("<Leave>",
                            lambda e: self._mark_btn.config(
                                bg=Q_REVIEW if not self._q_state[self._q_index]["marked"]
                                else WARN))

        self._load_question()
        self._tick()

    # ── question panel helpers ───────────────────────────────────────
    def _refresh_panel(self):
        """Refresh all question grid buttons and summary counters."""
        answered  = 0
        marked    = 0
        unvisited = 0

        for i, st in self._q_state.items():
            if not st["visited"]:
                color = Q_UNVISITED
                unvisited += 1
            elif st["marked"]:
                color = WARN
                marked += 1
            elif st["answer"]:
                color = ACCENT2
                answered += 1
            else:
                color = "#3a3f47"   # visited but unanswered

            # highlight current
            if i == self._q_index:
                color = ACCENT

            self._q_btns[i].config(bg=color,
                                   fg="#000000" if i == self._q_index else TEXT)

        self._lbl_answered.config(text=f"✅ Answered  : {answered}")
        self._lbl_review.config(text=f"🔖 For Review: {marked}")
        self._lbl_unvisited.config(text=f"○  Unvisited : {unvisited}")

    def _update_mark_btn(self):
        marked = self._q_state[self._q_index]["marked"]
        if marked:
            self._mark_btn.config(text="🔖 Marked ✓", bg=WARN)
        else:
            self._mark_btn.config(text="🔖 Mark for Review", bg=Q_REVIEW)

    def _toggle_mark(self):
        st = self._q_state[self._q_index]
        st["marked"] = not st["marked"]
        self._update_mark_btn()
        self._refresh_panel()

    # ── navigation ──────────────────────────────────────────────────
    def _save_current_answer(self):
        """Persist whatever is selected to _q_state without advancing."""
        sel = self._selected.get()
        self._q_state[self._q_index]["answer"] = sel
        self._q_state[self._q_index]["visited"] = True

    def _load_question(self):
        if self._q_index >= len(self._questions):
            self._finish_quiz()
            return

        q  = self._questions[self._q_index]
        st = self._q_state[self._q_index]
        st["visited"] = True

        # restore previous selection
        self._selected.set(st["answer"])

        self._q_counter_lbl.config(
            text=f"Question {self._q_index + 1} / {len(self._questions)}")
        self._q_text.config(text=f"Q{q.id}:  {q.question}")

        opts = [q.option_a, q.option_b, q.option_c, q.option_d]
        for rb, opt_lbl, txt in zip(self._radio_btns,
                                    ["A", "B", "C", "D"], opts):
            rb.config(text=f"  {opt_lbl}.  {txt}", value=opt_lbl)

        self._update_mark_btn()
        self._refresh_panel()

    def _next_question(self):
        if self._quiz_done:
            return
        self._save_current_answer()
        if self._q_index < len(self._questions) - 1:
            self._q_index += 1
            self._load_question()
        else:
            # Already on last question — prompt submit
            self._confirm_submit()

    def _prev_question(self):
        if self._quiz_done:
            return
        self._save_current_answer()
        if self._q_index > 0:
            self._q_index -= 1
            self._load_question()

    def _jump_to(self, idx):
        if self._quiz_done:
            return
        self._save_current_answer()
        self._q_index = idx
        self._load_question()

    # ── submit confirmation ──────────────────────────────────────────
    def _confirm_submit(self):
        if self._quiz_done:
            return
        self._save_current_answer()

        unanswered = sum(1 for st in self._q_state.values() if not st["answer"])
        marked     = sum(1 for st in self._q_state.values() if st["marked"])

        msg = f"Are you sure you want to submit?\n\n"
        if unanswered:
            msg += f"⚠  {unanswered} question(s) unanswered\n"
        if marked:
            msg += f"🔖 {marked} question(s) marked for review\n"

        if messagebox.askyesno("Submit Quiz", msg):
            self._finish_quiz()

    # ── timer ────────────────────────────────────────────────────────
    def _tick(self):
        if self._quiz_done:
            return
        elapsed   = time.time() - self._start_t
        remaining = self._total_t - elapsed
        if remaining <= 0:
            self._finish_quiz()
            return
        m, s  = divmod(int(remaining), 60)
        color = DANGER if remaining < 30 else WARN
        self._timer_lbl.config(text=f"⏱  {m:02d}:{s:02d}", fg=color)
        self.after(500, self._tick)

    # ── finish ───────────────────────────────────────────────────────
    def _finish_quiz(self):
        self._quiz_done = True

        # commit _q_state back to MCQ objects
        for i, q in enumerate(self._questions):
            ans = self._q_state[i]["answer"]
            if not ans:
                q.user_option = "S"
                q.is_correct  = 0
            else:
                q.user_option = ans
                q.is_correct  = 1 if ans == q.correct_option else 0

        correct = sum(1 for q in self._questions if q.is_correct)
        wrong   = sum(1 for q in self._questions
                      if q.user_option != "S" and not q.is_correct)
        skipped = sum(1 for q in self._questions if q.user_option == "S")
        total   = len(self._questions)

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

        styled_btn(btn_f, "Review Answers", lambda: self._show_review_screen(questions),
                   width=16).grid(row=0, column=0, padx=6)
        styled_btn(btn_f, "Back to Menu", self._show_main_menu,
                   width=16, bg="#21262d").grid(row=0, column=1, padx=6)

    # ═══════════════════════════════════════════════════════════════════
    #  REVIEW SCREEN  (enhanced — shows all options, highlights correct/wrong)
    # ═══════════════════════════════════════════════════════════════════
    def _show_review_screen(self, questions):
        self._clear()
        outer = tk.Frame(self.container, bg=BG)
        outer.pack(fill="both", expand=True)

        # header
        hdr = tk.Frame(outer, bg=PANEL, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        label(hdr, "  ANSWER REVIEW", 12, ACCENT, True).pack(side="left", padx=12, pady=10)
        styled_btn(hdr, "← Menu", self._show_main_menu,
                   width=8, bg="#21262d").pack(side="right", padx=12, pady=8)

        # legend row
        leg = tk.Frame(outer, bg=BG)
        leg.pack(fill="x", padx=20, pady=(8, 4))
        for col, txt in [(ACCENT2, "Correct answer"), (DANGER, "Your wrong answer"),
                         (BORDER, "Unchosen option")]:
            tk.Frame(leg, bg=col, width=14, height=14).pack(side="left", padx=(0, 4))
            tk.Label(leg, text=txt, bg=BG, fg=SUBTEXT,
                     font=("Consolas", 9)).pack(side="left", padx=(0, 16))

        # scrollable area
        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        vsb    = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=inner, anchor="nw")

        opt_keys  = ["A", "B", "C", "D"]

        for q in questions:
            # card
            card = tk.Frame(inner, bg=PANEL, padx=16, pady=12,
                            highlightthickness=1, highlightbackground=BORDER)
            card.pack(fill="x", padx=20, pady=5)

            # verdict
            if q.user_option == "S":
                icon, col, verdict = "⏭", WARN, "Skipped"
            elif q.is_correct:
                icon, col, verdict = "✅", ACCENT2, "Correct"
            else:
                icon, col, verdict = "❌", DANGER, "Incorrect"

            # question header row
            top_row = tk.Frame(card, bg=PANEL)
            top_row.pack(fill="x")
            label(top_row, f"Q{q.id}: {q.question}", 10, TEXT,
                  bg=PANEL, wraplength=700, justify="left",
                  anchor="w").pack(side="left", fill="x", expand=True)
            label(top_row, f"{icon} {verdict}", 10, col, True,
                  bg=PANEL).pack(side="right")

            # divider
            tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=(6, 8))

            # all four options
            opt_texts = [q.option_a, q.option_b, q.option_c, q.option_d]
            for key, opt_text in zip(opt_keys, opt_texts):
                is_correct_opt = (key == q.correct_option)
                is_user_choice = (key == q.user_option)

                # determine row style
                if is_correct_opt:
                    row_bg    = "#0d2818"    # dark green tint
                    opt_fg    = ACCENT2
                    border_c  = ACCENT2
                    prefix    = "✓"
                elif is_user_choice and not is_correct_opt:
                    row_bg    = "#2d1215"    # dark red tint
                    opt_fg    = DANGER
                    border_c  = DANGER
                    prefix    = "✗"
                else:
                    row_bg    = "#1c2128"    # neutral dark
                    opt_fg    = SUBTEXT
                    border_c  = BORDER
                    prefix    = " "

                opt_row = tk.Frame(card, bg=row_bg,
                                   highlightthickness=1,
                                   highlightbackground=border_c)
                opt_row.pack(fill="x", pady=2, padx=4)

                tk.Label(opt_row, text=f" {prefix} {key}. ", bg=row_bg,
                         fg=opt_fg, font=("Consolas", 12, "bold"),
                         padx=6, pady=5).pack(side="left")
                tk.Label(opt_row, text=opt_text, bg=row_bg, fg=opt_fg,
                         font=("Consolas", 12), anchor="w", justify="left",
                         padx=4, pady=5, wraplength=650).pack(side="left", fill="x")

        inner.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(
                            -1 * int(e.delta / 120), "units"))

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
            label(card, f"🏅 Your rank: #{rank}", 12, WARN, True,
                  bg=PANEL).pack(pady=(8, 0))

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

        hdr = tk.Frame(card, bg=PANEL)
        hdr.pack(fill="x")
        for col_txt, w in [("#", 3), ("Username", 18), ("Score", 8)]:
            label(hdr, col_txt, 12, SUBTEXT, True, bg=PANEL,
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
                label(row, entry["username"], 11, TEXT, bg=PANEL, width=18).pack(
                    side="left", padx=4)
                label(row, str(entry["score"]), 11, ACCENT2, True, bg=PANEL,
                      width=8).pack(side="left", padx=4)

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
                self.after(0, lambda: status_lbl.config(text=f"Error: {ex}", fg=DANGER))
                self.after(0, progress.stop)
                return

            if response.get("status") == "started":
                self.after(0, lambda: status_lbl.config(
                    text=response.get("message", "Quiz already running."), fg=DANGER))
                self.after(0, progress.stop)
                return

            self.after(0, lambda: status_lbl.config(
                text="✅  In lobby — waiting for host to start...", fg=ACCENT2))

            msg = recv_json(self.client.conn)
            if not msg:
                self.after(0, lambda: status_lbl.config(
                    text="Server disconnected.", fg=DANGER))
                return

            if msg.get("type") == "quiz_start":
                start_time    = msg["start_time"]
                duration      = msg["duration"]
                topic         = msg.get("topic", "D")
                difficulty    = msg.get("difficulty", "A")
                num_questions = msg.get("num_questions", 10)
                wait          = start_time - time.time()

                def countdown(secs):
                    if secs > 0:
                        self.after(0, lambda: status_lbl.config(
                            text=f"Quiz starts in {secs}s ...", fg=WARN))
                        self.after(1000, lambda: countdown(secs - 1))
                    else:
                        self.after(0, lambda: [
                            progress.stop(),
                            self._launch_mp_quiz(duration, topic, difficulty, num_questions)
                        ])

                self.after(0, lambda: countdown(max(0, int(wait))))

        threading.Thread(target=join_thread, daemon=True).start()

    def _launch_mp_quiz(self, duration, topic, difficulty, num_questions=10):
        questions = self.client.get_quiz(topic, difficulty)
        if not questions:
            messagebox.showinfo("Multiplayer", "No questions received.")
            self._show_main_menu()
            return
        questions = questions[:min(num_questions, len(questions))]
        self._show_quiz_ui(questions, duration)

        def wait_for_end():
            end_msg = recv_json(self.client.conn)
            if end_msg and end_msg.get("type") == "quiz_end":
                leaderboard = end_msg.get("leaderboard", [])
                self.after(0, lambda: self._finish_mp_quiz(leaderboard))

        threading.Thread(target=wait_for_end, daemon=True).start()

    def _finish_mp_quiz(self, leaderboard):
        """Called when server sends quiz_end — save stats then show MP leaderboard."""
        # Save answers and stats without navigating to the solo results screen
        if not self._quiz_done:
            self._quiz_done = True
            # Commit _q_state to MCQ objects
            for i, q in enumerate(self._questions):
                ans = self._q_state[i]["answer"]
                if not ans:
                    q.user_option = "S"
                    q.is_correct  = 0
                else:
                    q.user_option = ans
                    q.is_correct  = 1 if ans == q.correct_option else 0
            correct = sum(1 for q in self._questions if q.is_correct)
            wrong   = sum(1 for q in self._questions
                          if q.user_option != "S" and not q.is_correct)
            skipped = sum(1 for q in self._questions if q.user_option == "S")
            self.stats.total_correct   += correct
            self.stats.total_incorrect += wrong
            self.stats.total_skipped   += skipped
            try:
                self.client.save_stats(self.username, correct, wrong, skipped)
            except Exception:
                pass
        self._show_mp_leaderboard(leaderboard)

    # ═══════════════════════════════════════════════════════════════════
    #  MULTIPLAYER LEADERBOARD SCREEN
    # ═══════════════════════════════════════════════════════════════════
    def _show_mp_leaderboard(self, leaderboard):
        self._clear()
        outer = tk.Frame(self.container, bg=BG)
        outer.pack(fill="both", expand=True)

        # header
        hdr = tk.Frame(outer, bg=PANEL, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        label(hdr, "  ⚡ MULTIPLAYER — FINAL RESULTS", 13, ACCENT, True).pack(
            side="left", padx=12, pady=12)
        styled_btn(hdr, "← Menu", self._show_main_menu,
                   width=8, bg="#21262d").pack(side="right", padx=12, pady=10)

        # centre content
        center = tk.Frame(outer, bg=BG)
        center.place(relx=.5, rely=.5, anchor="center")

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        colors = {1: WARN, 2: SUBTEXT, 3: "#cd7f32"}   # gold, silver, bronze

        if not leaderboard:
            label(center, "No scores recorded.", 13, SUBTEXT).pack(pady=20)
        else:
            # Winner banner
            winner = leaderboard[0]
            banner = tk.Frame(center, bg=PANEL, padx=40, pady=20,
                              highlightthickness=2, highlightbackground=WARN)
            banner.pack(pady=(0, 24), fill="x")
            label(banner, "🏆  WINNER", 12, WARN, True, bg=PANEL).pack()
            label(banner, winner["username"], 20, WARN, True, bg=PANEL).pack(pady=4)
            label(banner, f"{winner['score']} correct answers", 12, TEXT,
                  bg=PANEL).pack()

            # All players table
            table = tk.Frame(center, bg=PANEL, padx=24, pady=16,
                             highlightthickness=1, highlightbackground=BORDER)
            table.pack(fill="x")

            # column headers
            hdr_row = tk.Frame(table, bg=PANEL)
            hdr_row.pack(fill="x", pady=(0, 6))
            tk.Frame(hdr_row, bg=BORDER, height=1).pack(fill="x")

            col_hdr = tk.Frame(table, bg=PANEL)
            col_hdr.pack(fill="x", pady=(0, 4))
            for txt, w in [("  ", 4), ("Player", 22), ("Score", 10)]:
                label(col_hdr, txt, 11, SUBTEXT, True, bg=PANEL,
                      width=w).pack(side="left", padx=4)

            tk.Frame(table, bg=BORDER, height=1).pack(fill="x", pady=(0, 6))

            for entry in leaderboard:
                rank  = entry["rank"]
                medal = medals.get(rank, f"#{rank}")
                col   = colors.get(rank, TEXT)

                row = tk.Frame(table, bg=PANEL)
                row.pack(fill="x", pady=3)

                label(row, medal, 13, col, True, bg=PANEL,
                      width=4).pack(side="left", padx=4)
                label(row, entry["username"], 13, col, rank == 1,
                      bg=PANEL, width=22).pack(side="left", padx=4)
                label(row, str(entry["score"]), 13, col, True,
                      bg=PANEL, width=10).pack(side="left", padx=4)

        styled_btn(center, "Back to Menu", self._show_main_menu,
                   width=20, bg="#21262d").pack(pady=(24, 0))


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()