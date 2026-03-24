"""
server_gui.py  –  Tkinter GUI dashboard for the Online Quiz System Server
Replaces server.py (terminal server).  Keeps all original server logic intact
and adds a live admin dashboard.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import socket
import ssl
import json
import csv
import os
import sys
import struct
import time

# ── bring in quiz loader ────────────────────────────────────────────────────
try:
    from quiz import load_questions
except ImportError:
    print("[ERROR] quiz.py not found — make sure it is in the same folder.")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
#  THEME
# ═══════════════════════════════════════════════════════════════════════════
BG      = "#0d1117"
PANEL   = "#161b22"
BORDER  = "#30363d"
ACCENT  = "#58a6ff"
GREEN   = "#3fb950"
RED     = "#f85149"
WARN    = "#d29922"
TEXT    = "#e6edf3"
SUBTEXT = "#8b949e"

HOST = "0.0.0.0"
PORT = 5000
QUIZ_DURATION = 60  # seconds
selected_topic = "D"
selected_difficulty = "A"
selected_num_questions = 5
mp_active_clients = []

# ═══════════════════════════════════════════════════════════════════════════
#  SERVER STATE (shared across threads — protected by locks)
# ═══════════════════════════════════════════════════════════════════════════
active_connections = 0
connection_lock    = threading.Lock()

waiting_players    = []          # list of (username, conn)
quiz_started       = False
quiz_lock          = threading.Lock()
quiz_end_time      = None

# GUI reference — set after App is created
_app = None


# ═══════════════════════════════════════════════════════════════════════════
#  PROTOCOL HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def send_json(sock, data):
    message = json.dumps(data).encode()
    length  = struct.pack("!I", len(message))
    sock.sendall(length + message)


def recv_json(sock):
    raw_length = sock.recv(4)
    if not raw_length:
        return None
    length = struct.unpack("!I", raw_length)[0]
    data = b""
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            return None
        data += packet
    return json.loads(data.decode())


# ═══════════════════════════════════════════════════════════════════════════
#  SERVER LOGIC  (identical to server.py, minus the terminal prints)
# ═══════════════════════════════════════════════════════════════════════════
def log(msg):
    """Thread-safe GUI log."""
    if _app:
        _app.gui_log(msg)
    else:
        print(msg)


def authenticate(username, password):
    try:
        with open("users.txt", "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[0] == username and row[1] == password:
                    return True
    except FileNotFoundError:
        pass
    return False


def register_user(username, password):
    USERS_FILE = "users.txt"
    if not os.path.exists(USERS_FILE):
        open(USERS_FILE, "w").close()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            stored = line.split(",", 1)[0].strip()
            if stored == username:
                return "exists"
    with open(USERS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{username},{password}\n")
    log(f"[NEW USER] {username}")
    return "success"


def load_quiz(topic, difficulty):
    filename_map = {"A": "epd_questions.csv", "B": "c_questions.csv",
                    "C": "mental_ability_questions.csv",
                    "D": "python_questions.csv", "E": "maths_questions.csv"}
    topic_map    = {"A": "EPD", "B": "C Programming", "C": "Mental Ability",
                    "D": "Python", "E": "Triple Integration"}
    diff_map     = {"A": "Easy", "B": "Medium", "C": "Hard"}

    filename      = filename_map.get(topic, "python_questions.csv")
    topic_name    = topic_map.get(topic, topic)
    diff_name     = diff_map.get(difficulty, difficulty)
    questions     = load_questions(filename, topic_name, diff_name)

    return [{"id": q.id, "question": q.question,
             "A": q.option_a, "B": q.option_b,
             "C": q.option_c, "D": q.option_d,
             "correct": q.correct_option} for q in questions]


def build_leaderboard():
    stats = {}
    if not os.path.exists("user_stats.csv"):
        return []
    with open("user_stats.csv", "r") as f:
        for row in csv.reader(f):
            if len(row) < 4:
                continue
            stats[row[0]] = (int(row[1]), int(row[2]), int(row[3]))
    entries = [(c - i, c, s, u) for u, (c, i, s) in stats.items()]
    entries.sort(key=lambda x: (-x[0], -x[1], x[2], x[3]))
    return [{"rank": r, "username": e[3], "score": e[0]}
            for r, e in enumerate(entries[:3], 1)]


def start_multiplayer_quiz():
    global quiz_started, quiz_end_time
    with quiz_lock:
        if quiz_started:
            log("[MP] Already running.")
            return
        if not waiting_players:
            log("[MP] No players in lobby.")
            return
        quiz_started  = True
        start_time    = time.time() + 5
        quiz_end_time = start_time + QUIZ_DURATION
        log(f"[MP] Quiz starting! Players: {len(waiting_players)}")
        global mp_active_clients
        mp_active_clients = []

        for username, conn in waiting_players:
            mp_active_clients.append(conn)
            try:
                send_json(conn, {
                    "type": "quiz_start",
                    "start_time": start_time,
                    "duration": QUIZ_DURATION,
                    "topic": selected_topic,
                    "difficulty": selected_difficulty,
                    "num_questions": selected_num_questions
                })
            except Exception:
                pass
    if _app:
        _app.refresh_lobby()

def quiz_timer_monitor():
    global quiz_started, waiting_players
    while True:
        if quiz_started and quiz_end_time:
            if time.time() >= quiz_end_time:
                log("[MP] Quiz ended by server.")
                with quiz_lock:
                    for conn in mp_active_clients:
                        try:
                            send_json(conn, {"type": "quiz_end"})
                        except Exception:
                            pass
                    waiting_players.clear()
                    quiz_started = False
                if _app:
                    _app.refresh_lobby()
        time.sleep(1)


def handle_client(conn, addr):
    global active_connections, waiting_players
    with connection_lock:
        active_connections += 1
    log(f"[CONNECTED] {addr}  (total: {active_connections})")
    if _app:
        _app.update_conn_count(active_connections)

    try:
        while True:
            req = recv_json(conn)
            if not req:
                break
            req_type = req.get("type")
            log(f"[REQ] {req_type} ← {addr}")

            if req_type == "login":
                u, p = req.get("username"), req.get("password")
                ok   = authenticate(u, p)
                log(f"[LOGIN] {u} → {'OK' if ok else 'FAIL'}")
                send_json(conn, {"status": "success" if ok else "fail"})

            elif req_type == "signup":
                u, p  = req.get("username"), req.get("password")
                result = register_user(u, p)
                send_json(conn, {"status": result})

            elif req_type == "get_quiz":
                t, d  = req.get("topic"), req.get("difficulty")
                qs    = load_quiz(t, d)
                send_json(conn, {"questions": qs})

            elif req_type == "save_stats":
                u  = req["username"]
                c, w, s = req["correct"], req["wrong"], req["skipped"]
                rows  = []
                found = False
                if os.path.exists("user_stats.csv"):
                    with open("user_stats.csv", "r", newline="") as f:
                        rows = list(csv.reader(f))
                for row in rows:
                    if row[0] == u:
                        row[1] = str(int(row[1]) + c)
                        row[2] = str(int(row[2]) + w)
                        row[3] = str(int(row[3]) + s)
                        found  = True
                        break
                if not found:
                    rows.append([u, c, w, s])
                with open("user_stats.csv", "w", newline="") as f:
                    csv.writer(f).writerows(rows)
                log(f"[STATS] Updated for {u}: +{c}C +{w}W +{s}S")
                if _app:
                    _app.refresh_leaderboard()

            elif req_type == "join_multiplayer":
                u = req["username"]
                if quiz_started:
                    send_json(conn, {"status": "started",
                                     "message": "Quiz already started."})
                    continue
                with quiz_lock:
                    waiting_players.append((u, conn))
                log(f"[MP] {u} joined lobby ({len(waiting_players)} waiting)")
                if _app:
                    _app.refresh_lobby()
                send_json(conn, {"status": "waiting",
                                 "message": "Waiting for host..."})

            elif req_type == "get_leaderboard":
                send_json(conn, {"leaderboard": build_leaderboard()})

            elif req_type == "get_stats":
                u     = req["username"]
                stats = {"correct": 0, "incorrect": 0, "skipped": 0}
                if os.path.exists("user_stats.csv"):
                    with open("user_stats.csv", "r") as f:
                        for row in csv.reader(f):
                            if len(row) >= 4 and row[0] == u:
                                stats = {"correct": int(row[1]),
                                         "incorrect": int(row[2]),
                                         "skipped": int(row[3])}
                                break
                rank = 0
                if os.path.exists("user_stats.csv"):
                    entries = []
                    with open("user_stats.csv", "r") as f:
                        for row in csv.reader(f):
                            if len(row) >= 4:
                                net = int(row[1]) - int(row[2])
                                entries.append((net, int(row[1]), int(row[3]), row[0]))
                    entries.sort(key=lambda x: (-x[0], -x[1], x[2], x[3]))
                    for r, e in enumerate(entries, 1):
                        if e[3] == u:
                            rank = r
                            break
                stats["rank"] = rank
                send_json(conn, stats)

            elif req_type == "logout":
                log(f"[LOGOUT] {req.get('username')}")

            else:
                log(f"[UNKNOWN] {req}")

    except Exception as e:
        log(f"[ERROR] {addr} → {e}")
    finally:
        with connection_lock:
            active_connections -= 1
        # remove from lobby if present
        with quiz_lock:
            waiting_players = [(u, c) for u, c in waiting_players if c is not conn]
        conn.close()
        log(f"[DISCONNECTED] {addr}  (total: {active_connections})")
        if _app:
            _app.update_conn_count(active_connections)
            _app.refresh_lobby()


def start_server_thread():
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain("certs/server.crt", "certs/server.key")
    except Exception as e:
        log(f"[SSL ERROR] {e}\n"
            "Make sure certs/server.crt and certs/server.key exist.")
        return

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(10)
    secure_server = context.wrap_socket(server, server_side=True)
    log(f"[SERVER] Listening on port {PORT}")

    threading.Thread(target=quiz_timer_monitor, daemon=True).start()

    while True:
        try:
            conn, addr = secure_server.accept()
            threading.Thread(target=handle_client,
                             args=(conn, addr), daemon=True).start()
        except Exception as e:
            log(f"[ACCEPT ERROR] {e}")
            break


# ═══════════════════════════════════════════════════════════════════════════
#  GUI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════
class ServerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quiz Server — Admin Dashboard")
        self.geometry("980x640")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._start_server()

    # ── UI construction ──────────────────────────────────────────────────
    def _build_ui(self):
        # ── top bar ──
        top = tk.Frame(self, bg=PANEL, height=52)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="  ⚡ QUIZ SERVER DASHBOARD", bg=PANEL, fg=ACCENT,
                 font=("Consolas", 14, "bold")).pack(side="left", padx=16, pady=10)

        self._conn_lbl = tk.Label(top, text="Connections: 0", bg=PANEL, fg=GREEN,
                                  font=("Consolas", 10))
        self._conn_lbl.pack(side="right", padx=20, pady=10)

        self._status_dot = tk.Label(top, text="●  OFFLINE", bg=PANEL, fg=RED,
                                    font=("Consolas", 10, "bold"))
        self._status_dot.pack(side="right", padx=10)

        # ── main panes ──
        panes = tk.PanedWindow(self, orient="horizontal", bg=BORDER,
                               sashrelief="flat", sashwidth=3)
        panes.pack(fill="both", expand=True, padx=0, pady=0)

        # left panel — log
        left = tk.Frame(panes, bg=BG)
        panes.add(left, minsize=420)

        tk.Label(left, text=" SERVER LOG", bg=PANEL, fg=SUBTEXT,
                 font=("Consolas", 9, "bold"), anchor="w").pack(fill="x")

        self._log = scrolledtext.ScrolledText(
            left, bg=BG, fg=TEXT, font=("Consolas", 9),
            insertbackground=ACCENT, relief="flat", bd=0,
            state="disabled", wrap="word")
        self._log.pack(fill="both", expand=True, padx=0, pady=0)

        # colour tags
        self._log.tag_config("info",    foreground=TEXT)
        self._log.tag_config("success", foreground=GREEN)
        self._log.tag_config("error",   foreground=RED)
        self._log.tag_config("warn",    foreground=WARN)
        self._log.tag_config("accent",  foreground=ACCENT)

        # right panel — controls + lobby + leaderboard
        right = tk.Frame(panes, bg=BG)
        panes.add(right, minsize=340)

        # ── MP control ──
        mp_card = tk.Frame(right, bg=PANEL, padx=16, pady=14,
                           highlightthickness=1, highlightbackground=BORDER)
        mp_card.pack(fill="x", padx=12, pady=(12, 6))

        tk.Label(mp_card, text="MULTIPLAYER CONTROL", bg=PANEL, fg=SUBTEXT,
                 font=("Consolas", 9, "bold")).pack(anchor="w")

        self._lobby_lbl = tk.Label(mp_card, text="Lobby: 0 player(s)",
                                   bg=PANEL, fg=TEXT, font=("Consolas", 10))
        self._lobby_lbl.pack(anchor="w", pady=(6, 2))

        self._mp_status_lbl = tk.Label(mp_card, text="Status: Idle",
                                       bg=PANEL, fg=SUBTEXT,
                                       font=("Consolas", 9))
        self._mp_status_lbl.pack(anchor="w", pady=(0, 10))


        # --- Topic Selection ---
        tk.Label(mp_card, text="Topic", bg=PANEL, fg=SUBTEXT,
                font=("Consolas", 9)).pack(anchor="w")

        self._topic_var = tk.StringVar(value="D")

        topic_map = {
            "A": "EPD",
            "B": "C Programming",
            "C": "Mental Ability",
            "D": "Python",
            "E": "Triple Integration"
        }

        self._topic_dropdown = ttk.Combobox(
            mp_card,
            textvariable=self._topic_var,
            values=list(topic_map.values()),
            state="readonly"
        )
        self._topic_dropdown.pack(fill="x", pady=(2, 8))
        self._topic_dropdown.current(3)  # Python default


        # --- Difficulty Selection ---
        tk.Label(mp_card, text="Difficulty", bg=PANEL, fg=SUBTEXT,
                font=("Consolas", 9)).pack(anchor="w")

        self._diff_var = tk.StringVar(value="A")

        diff_map = {
            "A": "Easy",
            "B": "Medium",
            "C": "Hard"
        }

        self._diff_dropdown = ttk.Combobox(
            mp_card,
            textvariable=self._diff_var,
            values=list(diff_map.values()),
            state="readonly"
        )
        self._diff_dropdown.pack(fill="x", pady=(2, 8))
        self._diff_dropdown.current(0)


        # --- Duration ---
        tk.Label(mp_card, text="Duration (seconds)", bg=PANEL, fg=SUBTEXT,
                font=("Consolas", 9)).pack(anchor="w")

        self._duration_var = tk.IntVar(value=60)

        tk.Spinbox(
            mp_card,
            from_=10, to=600,
            textvariable=self._duration_var,
            bg=BG, fg=TEXT,
            font=("Consolas", 10)
        ).pack(fill="x", pady=(2, 10))


        # --- Number of Questions ---
        tk.Label(mp_card, text="Number of Questions", bg=PANEL, fg=SUBTEXT,
                font=("Consolas", 9)).pack(anchor="w")

        self._num_q_var = tk.IntVar(value=5)

        tk.Spinbox(
            mp_card,
            from_=1, to=50,
            textvariable=self._num_q_var,
            bg=BG, fg=TEXT,
            font=("Consolas", 10)
        ).pack(fill="x", pady=(2, 10))


        self._start_mp_btn = tk.Button(
            mp_card, text="▶  START MULTIPLAYER QUIZ",
            bg=GREEN, fg="#000", activebackground="#2ea043",
            relief="flat", bd=0, font=("Consolas", 10, "bold"),
            padx=8, pady=6, cursor="hand2",
            command=self._on_start_mp)
        self._start_mp_btn.pack(fill="x")

        self._end_mp_btn = tk.Button(
            mp_card, text="■  END QUIZ NOW",
            bg=RED, fg="#fff", activebackground="#da3633",
            relief="flat", bd=0, font=("Consolas", 10, "bold"),
            padx=8, pady=6, cursor="hand2",
            command=self._on_end_mp, state="disabled")
        self._end_mp_btn.pack(fill="x", pady=(6, 0))

        # ── lobby list ──
        lobby_card = tk.Frame(right, bg=PANEL, padx=16, pady=14,
                              highlightthickness=1, highlightbackground=BORDER)
        lobby_card.pack(fill="x", padx=12, pady=6)

        tk.Label(lobby_card, text="LOBBY PLAYERS", bg=PANEL, fg=SUBTEXT,
                 font=("Consolas", 9, "bold")).pack(anchor="w", pady=(0, 6))

        self._lobby_list = tk.Listbox(lobby_card, bg=BG, fg=ACCENT,
                                      font=("Consolas", 10),
                                      relief="flat", bd=0,
                                      highlightthickness=0,
                                      selectbackground=BORDER, height=5)
        self._lobby_list.pack(fill="x")

        # ── leaderboard ──
        lb_card = tk.Frame(right, bg=PANEL, padx=16, pady=14,
                           highlightthickness=1, highlightbackground=BORDER)
        lb_card.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        hdr_row = tk.Frame(lb_card, bg=PANEL)
        hdr_row.pack(fill="x")
        tk.Label(hdr_row, text="LEADERBOARD", bg=PANEL, fg=SUBTEXT,
                 font=("Consolas", 9, "bold")).pack(side="left")
        tk.Button(hdr_row, text="⟳", bg=PANEL, fg=ACCENT,
                  relief="flat", bd=0, font=("Consolas", 10),
                  cursor="hand2", command=self.refresh_leaderboard).pack(side="right")

        cols = ("Rank", "Username", "Score")
        self._lb_tree = ttk.Treeview(lb_card, columns=cols,
                                     show="headings", height=6)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                         background=BG, foreground=TEXT,
                         fieldbackground=BG,
                         font=("Consolas", 10),
                         rowheight=26)
        style.configure("Treeview.Heading",
                         background=PANEL, foreground=SUBTEXT,
                         font=("Consolas", 9, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", BORDER)])

        for c in cols:
            w = 60 if c == "Rank" else 140 if c == "Username" else 80
            self._lb_tree.heading(c, text=c)
            self._lb_tree.column(c, width=w, anchor="center")

        self._lb_tree.pack(fill="both", expand=True, pady=(8, 0))
        self.refresh_leaderboard()

    # ── server bootstrap ────────────────────────────────────────────────
    def _start_server(self):
        t = threading.Thread(target=start_server_thread, daemon=True)
        t.start()
        # give it a moment then mark online
        self.after(1000, lambda: self._status_dot.config(
            text="●  ONLINE", fg=GREEN))

    # ── GUI helpers ──────────────────────────────────────────────────────
    def gui_log(self, msg):
        """Append a line to the server log (thread-safe via after())."""
        def _append():
            self._log.config(state="normal")
            ts = time.strftime("%H:%M:%S")
            tag = "info"
            if "[ERROR]" in msg or "FAIL" in msg:
                tag = "error"
            elif "[CONNECTED]" in msg or "OK" in msg or "[NEW USER]" in msg:
                tag = "success"
            elif "[DISCONNECTED]" in msg or "[LOGOUT]" in msg:
                tag = "warn"
            elif "[MP]" in msg or "[SERVER]" in msg:
                tag = "accent"
            self._log.insert("end", f"[{ts}] {msg}\n", tag)
            self._log.see("end")
            self._log.config(state="disabled")
        self.after(0, _append)

    def update_conn_count(self, n):
        self.after(0, lambda: self._conn_lbl.config(
            text=f"Connections: {n}"))

    def refresh_lobby(self):
        def _refresh():
            self._lobby_list.delete(0, "end")
            for username, _ in waiting_players:
                self._lobby_list.insert("end", f"  👤  {username}")
            count = len(waiting_players)
            self._lobby_lbl.config(text=f"Lobby: {count} player(s)")
            if quiz_started:
                self._mp_status_lbl.config(text="Status: Quiz running", fg=GREEN)
                self._start_mp_btn.config(state="disabled")
                self._end_mp_btn.config(state="normal")
            else:
                self._mp_status_lbl.config(text="Status: Idle", fg=SUBTEXT)
                self._start_mp_btn.config(state="normal" if count > 0 else "disabled")
                self._end_mp_btn.config(state="disabled")
        self.after(0, _refresh)

    def refresh_leaderboard(self):
        def _refresh():
            for row in self._lb_tree.get_children():
                self._lb_tree.delete(row)
            medals = {1: "🥇", 2: "🥈", 3: "🥉"}
            for entry in build_leaderboard():
                self._lb_tree.insert("", "end", values=(
                    medals.get(entry["rank"], entry["rank"]),
                    entry["username"],
                    entry["score"]))
        self.after(0, _refresh)

    # ── button handlers ──────────────────────────────────────────────────
    def _on_start_mp(self):

        global selected_topic, selected_difficulty, QUIZ_DURATION
        global NUM_QUESTIONS
        NUM_QUESTIONS = self._num_q_var.get()

        if not waiting_players:
            messagebox.showwarning("Multiplayer", "No players in the lobby yet.")
            return

        # --- Get Topic ---
        topic_map_reverse = {
            "EPD": "A",
            "C Programming": "B",
            "Mental Ability": "C",
            "Python": "D",
            "Triple Integration": "E"
        }

        selected_topic = topic_map_reverse.get(self._topic_dropdown.get(), "D")

        # --- Get Difficulty ---
        diff_map_reverse = {
            "Easy": "A",
            "Medium": "B",
            "Hard": "C"
        }

        selected_difficulty = diff_map_reverse.get(self._diff_dropdown.get(), "A")

        # --- Get Duration ---
        QUIZ_DURATION = self._duration_var.get()

        log(f"[MP CONFIG] Topic={selected_topic}, Difficulty={selected_difficulty}, Duration={QUIZ_DURATION}, Questions={NUM_QUESTIONS}")

        threading.Thread(target=start_multiplayer_quiz, daemon=True).start()
        self.refresh_lobby()

    def _on_end_mp(self):
        global quiz_started, quiz_end_time, waiting_players
        with quiz_lock:
            log("[MP] Quiz ended manually by admin.")
            global mp_active_clients

            for conn in mp_active_clients:
                try:
                    send_json(conn, {"type": "quiz_end"})
                except:
                    pass
            waiting_players = []
            mp_active_clients = []
            quiz_started    = False
            quiz_end_time   = None
        self.refresh_lobby()

    def _on_close(self):
        if messagebox.askyesno("Exit", "Shut down the server?"):
            self.destroy()
            os._exit(0)


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = ServerApp()
    _app = app          # make server threads able to reach the GUI
    app.mainloop()