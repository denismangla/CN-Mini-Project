import socket
import ssl
import threading
import json
import csv
from quiz import load_questions
import os

HOST = "0.0.0.0"
PORT = 5000


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
# CLIENT HANDLER
# -----------------------------
def handle_client(conn, addr):

    print(f"[CONNECTED] {addr}")

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

                username = req.get("username")
                correct = req.get("correct")
                wrong = req.get("wrong")
                skipped = req.get("skipped")

                with open("user_stats.csv", "a") as f:
                    f.write(f"{username},{correct},{wrong},{skipped}\n")

                print(f"[STATS SAVED] {username}")
            
            elif req_type == "logout":

                username = req["username"]
                print(f"[LOGOUT] {username}")

            
            elif req_type == "get_leaderboard":

                entries = []

                if os.path.exists("user_stats.csv"):

                    with open("user_stats.csv", "r") as f:
                        reader = csv.reader(f)

                        for row in reader:
                            if len(row) < 4:
                                continue

                            username = row[0]
                            correct = int(row[1])
                            incorrect = int(row[2])
                            skipped = int(row[3])

                            score = correct - incorrect

                            entries.append((score, correct, skipped, username))

                entries.sort(key=lambda x: (-x[0], -x[1], x[2], x[3]))

                leaderboard = []

                for i, entry in enumerate(entries[:3], 1):
                    leaderboard.append({
                        "rank": i,
                        "username": entry[3],
                        "score": entry[0]
                    })

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
        conn.close()
        print(f"[CONNECTION CLOSED] {addr}")

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

    while True:

        conn, addr = secure_server.accept()

        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()


if __name__ == "__main__":
    start_server()