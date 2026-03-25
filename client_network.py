import socket
import ssl
import json
import struct
from quiz import MCQ


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



SERVER_IP = "10.1.16.202"   # change if server IP changes
PORT = 5000


class QuizClient:

    def __init__(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.minimum_version = ssl.TLSVersion.TLSv1_2

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

        send_json(self.conn, req)

        res = recv_json(self.conn)

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

        send_json(self.conn, req)

        res = recv_json(self.conn)

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

        send_json(self.conn, req)

        res = recv_json(self.conn)

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

        send_json(self.conn, req)

    def logout(self, username):

        req = {
            "type": "logout",
            "username": username
        }

        send_json(self.conn, req)
    

    def get_user_stats(self, username):

        req = {
            "type": "get_stats",
            "username": username
        }

        send_json(self.conn, req)

        res = recv_json(self.conn)

        return res
    

    def get_leaderboard(self):

        req = {
            "type": "get_leaderboard"
        }

        send_json(self.conn, req)

        res = recv_json(self.conn)

        return res["leaderboard"]
    
    def join_multiplayer(self, username, topic=None, difficulty=None):

        req = {
            "type": "join_multiplayer",
            "username": username
        }

        # optional (not required but useful)
        if topic:
            req["topic"] = topic
        if difficulty:
            req["difficulty"] = difficulty

        send_json(self.conn, req)

        return recv_json(self.conn)