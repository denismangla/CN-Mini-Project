import socket
import ssl
import threading
import json
import csv
from quiz import load_questions

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

    # check if user already exists
    with open("users.txt", "r", encoding="utf-8") as f:
        reader = csv.reader(f)

        for row in reader:
            if row[0] == username:
                return "exists"

    # add new user
    with open("users.txt", "a", encoding="utf-8") as f:
        f.write(f"{username},{password}\n")

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

    print("Client connected:", addr)

    try:

        while True:

            data = conn.recv(4096).decode()

            if not data:
                break

            req = json.loads(data)

            # LOGIN
            if req["type"] == "login":

                username = req["username"]
                password = req["password"]

                if authenticate(username, password):

                    conn.send(json.dumps({
                        "status": "success"
                    }).encode())

                else:

                    conn.send(json.dumps({
                        "status": "fail"
                    }).encode())

            # SIGNUP
            elif req["type"] == "signup":

                username = req["username"]
                password = req["password"]

                result = register_user(username, password)

                conn.send(json.dumps({
                    "status": result
                }).encode())

            # REQUEST QUIZ
            elif req["type"] == "get_quiz":

                topic = req["topic"]
                difficulty = req["difficulty"]

                questions = load_quiz(topic, difficulty)

                conn.send(json.dumps({
                    "questions": questions
                }).encode())

    except Exception as e:
        print("Error:", e)

    conn.close()
    print("Client disconnected:", addr)


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