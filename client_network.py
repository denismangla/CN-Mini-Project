import socket
import ssl
import json
from quiz import MCQ

SERVER_IP = "10.1.16.128"   # change if server IP changes
PORT = 5000


class QuizClient:

    def __init__(self):

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.conn = context.wrap_socket(sock, server_hostname=SERVER_IP)

        self.conn.connect((SERVER_IP, PORT))


    # -----------------------------
    # LOGIN
    # -----------------------------
    def login(self, username, password):

        req = {
            "type": "login",
            "username": username,
            "password": password
        }

        self.conn.send(json.dumps(req).encode())

        res = json.loads(self.conn.recv(4096).decode())

        return res["status"] == "success"


    # -----------------------------
    # SIGNUP
    # -----------------------------
    def signup(self, username, password):

        req = {
            "type": "signup",
            "username": username,
            "password": password
        }

        self.conn.send(json.dumps(req).encode())

        res = json.loads(self.conn.recv(4096).decode())

        return res["status"]


    # -----------------------------
    # GET QUIZ QUESTIONS
    # -----------------------------
    def get_quiz(self, topic, difficulty):

        req = {
            "type": "get_quiz",
            "topic": topic,
            "difficulty": difficulty
        }

        self.conn.send(json.dumps(req).encode())

        res = json.loads(self.conn.recv(4096).decode())

        questions = []

        for q in res["questions"]:

            question_obj = MCQ(
                q["id"],
                "",
                "",
                q["question"],
                q["A"],
                q["B"],
                q["C"],
                q["D"],
                q["correct"]
            )

            questions.append(question_obj)

        return questions