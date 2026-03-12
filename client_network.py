import socket
import ssl
import json
from quiz import MCQ

SERVER_IP = "10.1.17.90"   # change if server IP changes
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


    def save_stats(self, username, correct, wrong, skipped):

        req = {
            "type": "save_stats",
            "username": username,
            "correct": correct,
            "wrong": wrong,
            "skipped": skipped
        }

        self.conn.send(json.dumps(req).encode())

    def logout(self, username):

        req = {
            "type": "logout",
            "username": username
        }

        self.conn.send(json.dumps(req).encode())
    

    def get_user_stats(self, username):

        req = {
            "type": "get_stats",
            "username": username
        }

        self.conn.send(json.dumps(req).encode())

        res = json.loads(self.conn.recv(4096).decode())

        return res
    

    def get_leaderboard(self):

        req = {
            "type": "get_leaderboard"
        }

        self.conn.send(json.dumps(req).encode())

        res = json.loads(self.conn.recv(4096).decode())

        return res["leaderboard"]