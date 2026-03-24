import socket
import ssl
import threading
import json
import csv
from quiz import load_questions
import os
import sys
import struct
import time

HOST = "0.0.0.0"
PORT = 5000

active_connections = 0
connection_lock = threading.Lock()

waiting_players = []
quiz_started = False
quiz_lock = threading.Lock()
quiz_end_time = None
QUIZ_DURATION = 60  # seconds



def send_json(sock, data):
    message = json.dumps(data).encode()
    length = struct.pack("!I", len(message))
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


def show_active_connections():
    sys.stdout.write(f"\rActive connections: {active_connections}   ")
    sys.stdout.flush()


# -----------------------------
# USER AUTHENTICATION
# -----------------------------
def authenticate(username, password):

    with open("users.txt", "r", encoding="utf-8") as f:
        reader = csv.reader(f)

        for row in reader:
            if row[0] == username and row[1] == password:
                return True

    return False


# -----------------------------
# USER REGISTRATION
# -----------------------------
def register_user(username, password):

    USERS_FILE = "users.txt"

    # create file if it doesn't exist
    if not os.path.exists(USERS_FILE):
        open(USERS_FILE, "w").close()

    # check if username already exists
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            stored = line.split(",", 1)[0].strip()
            if stored == username:
                return "exists"

    # save new user
    with open(USERS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{username},{password}\n")

    print("User saved on server:", username)

    return "success"


# -----------------------------
# LOAD QUIZ QUESTIONS
# -----------------------------
def load_quiz(topic, difficulty):

    filename_map = {
        "A": "epd_questions.csv",
        "B": "c_questions.csv",
        "C": "mental_ability_questions.csv",
        "D": "python_questions.csv",
        "E": "maths_questions.csv"
    }

    topic_map = {
        "A": "EPD",
        "B": "C Programming",
        "C": "Mental Ability",
        "D": "Python",
        "E": "Triple Integration"
    }

    diff_map = {
        "A": "Easy",
        "B": "Medium",
        "C": "Hard"
    }

    filename = filename_map[topic]
    topic_name = topic_map[topic]
    difficulty_name = diff_map[difficulty]

    questions = load_questions(filename, topic_name, difficulty_name)

    result = []

    for q in questions:

        result.append({
            "id": q.id,
            "question": q.question,
            "A": q.option_a,
            "B": q.option_b,
            "C": q.option_c,
            "D": q.option_d,
            "correct": q.correct_option
        })

    return result


# -----------------------------
# BUILD LEADERBOARD
# -----------------------------

def build_leaderboard():

    stats = {}

    if not os.path.exists("user_stats.csv"):
        return []

    with open("user_stats.csv", "r") as f:
        reader = csv.reader(f)

        for row in reader:
            if len(row) < 4:
                continue

            username = row[0]
            correct = int(row[1])
            incorrect = int(row[2])
            skipped = int(row[3])

            # overwrite previous entries so latest stats remain
            stats[username] = (correct, incorrect, skipped)

    leaderboard = []

    for username, data in stats.items():

        correct, incorrect, skipped = data
        score = correct - incorrect

        leaderboard.append((score, correct, skipped, username))

    leaderboard.sort(key=lambda x: (-x[0], -x[1], x[2], x[3]))

    result = []

    for i, entry in enumerate(leaderboard[:3], 1):

        result.append({
            "rank": i,
            "username": entry[3],
            "score": entry[0]
        })

    return result


def start_multiplayer_quiz():

    global quiz_started, quiz_end_time

    with quiz_lock:

        if len(waiting_players) == 0:
            return

        quiz_started = True

        start_time = time.time() + 5
        quiz_end_time = start_time + QUIZ_DURATION

        print("\n[QUIZ STARTING IN 5 SECONDS]")

        for username, conn in waiting_players:
            try:
                send_json(conn, {
                    "type": "quiz_start",
                    "start_time": start_time,
                    "duration": QUIZ_DURATION
                })
            except:
                pass


def quiz_timer_monitor():

    global quiz_started, waiting_players

    while True:

        if quiz_started and quiz_end_time:

            if time.time() >= quiz_end_time:

                print("\n[QUIZ ENDED BY SERVER]")

                with quiz_lock:

                    for username, conn in waiting_players:
                        try:
                            send_json(conn, {
                                "type": "quiz_end"
                            })
                        except:
                            pass

                    waiting_players.clear()
                    quiz_started = False

        time.sleep(1)



# -----------------------------
# CLIENT HANDLER
# -----------------------------
def handle_client(conn, addr):

    global active_connections

    with connection_lock:
        active_connections += 1

    show_active_connections()

    print(f"\n[CONNECTED] {addr}")

    try:

        while True:

            data = conn.recv(4096)

            # client disconnected
            if not data:
                print(f"[DISCONNECTED] {addr}")
                break

            try:
                req = json.loads(data.decode())
            except Exception as e:
                print("Invalid JSON received:", e)
                continue

            req_type = req.get("type")

            print(f"[REQUEST] {req_type} from {addr}")

            # -------------------------
            # LOGIN REQUEST
            # -------------------------
            if req_type == "login":

                username = req.get("username")
                password = req.get("password")

                if authenticate(username, password):

                    print(f"[LOGIN SUCCESS] {username}")

                    conn.send(json.dumps({
                        "status": "success"
                    }).encode())

                else:

                    print(f"[LOGIN FAILED] {username}")

                    conn.send(json.dumps({
                        "status": "fail"
                    }).encode())

            # -------------------------
            # SIGNUP REQUEST
            # -------------------------
            elif req_type == "signup":

                username = req.get("username")
                password = req.get("password")

                print(f"[SIGNUP REQUEST] {username}")

                result = register_user(username, password)

                if result == "success":
                    print(f"[NEW USER SAVED] {username}")

                elif result == "exists":
                    print(f"[USER ALREADY EXISTS] {username}")

                conn.send(json.dumps({
                    "status": result
                }).encode())

            # -------------------------
            # QUIZ REQUEST
            # -------------------------
            elif req_type == "get_quiz":

                topic = req.get("topic")
                difficulty = req.get("difficulty")

                print(f"[QUIZ REQUEST] Topic={topic} Difficulty={difficulty}")

                questions = load_quiz(topic, difficulty)

                conn.send(json.dumps({
                    "questions": questions
                }).encode())

            # -------------------------
            # SAVE STATS REQUEST
            # -------------------------
            elif req_type == "save_stats":

                username = req["username"]
                correct = req["correct"]
                wrong = req["wrong"]
                skipped = req["skipped"]

                rows = []
                found = False

                # Read existing stats
                if os.path.exists("user_stats.csv"):
                    with open("user_stats.csv", "r", newline="") as f:
                        reader = csv.reader(f)
                        rows = list(reader)

                # Search for user
                for row in rows:
                    if row[0] == username:
                        row[1] = str(int(row[1]) + correct)
                        row[2] = str(int(row[2]) + wrong)
                        row[3] = str(int(row[3]) + skipped)
                        found = True
                        break

                # If user not found, add new entry
                if not found:
                    rows.append([username, correct, wrong, skipped])

                # Write updated data back
                with open("user_stats.csv", "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)

                print(f"[STATS UPDATED] {username}")

            
            elif req_type == "join_multiplayer":
                username = req["username"]

                with quiz_lock:
                    waiting_players.append((username, conn))

                print(f"{username} joined multiplayer lobby")

                # AFTER adding player
                if len(waiting_players) >= 2:
                    start_multiplayer_quiz()

                send_json(conn, {
                    "status": "waiting",
                    "message": "Waiting for quiz to start..."
                })



            elif req_type == "get_leaderboard":

                leaderboard = build_leaderboard()

                conn.send(json.dumps({
                    "leaderboard": leaderboard
                }).encode())


            elif req_type == "get_stats":

                username = req["username"]

                stats = {
                    "correct": 0,
                    "incorrect": 0,
                    "skipped": 0
                }

                if os.path.exists("user_stats.csv"):

                    with open("user_stats.csv", "r") as f:
                        reader = csv.reader(f)

                        for row in reader:
                            if row[0] == username:
                                stats["correct"] = int(row[1])
                                stats["incorrect"] = int(row[2])
                                stats["skipped"] = int(row[3])
                                break

                conn.send(json.dumps(stats).encode())


            else:
                print("[UNKNOWN REQUEST]", req)

    except Exception as e:
        print(f"[ERROR] {addr} -> {e}")

    finally:

        with connection_lock:
            active_connections -= 1

        show_active_connections()

        conn.close()

        print(f"\n[DISCONNECTED] {addr}")

# -----------------------------
# START SERVER
# -----------------------------
def start_server():

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain("certs/server.crt", "certs/server.key")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)

    secure_server = context.wrap_socket(server, server_side=True)

    print("Secure Quiz Server Running on Port", PORT)
    print("Active connections: 0", end="")

    threading.Thread(target=quiz_timer_monitor, daemon=True).start()

    while True:

        conn, addr = secure_server.accept()

        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


if __name__ == "__main__":
    start_server()