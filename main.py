from client_network import QuizClient

client = QuizClient()

import os
import time
import sys
import csv
import msvcrt
from quiz import (
    MCQ,
    UserStats,
    display_topics,
    get_topic_name,
    get_difficulty_name,
    load_questions,
    ask_question,
    show_results,
    show_answer_review,
    load_user_stats,
    save_user_stats
)

# Constants
STATS_FILE = "user_stats.csv"
USERS_FILE = "users.txt"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def pause_and_clear(seconds=1.5):
    time.sleep(seconds)
    clear_screen()

def get_hidden_password(prompt="Enter password: "):
    """Read password char by char and echo '*' (Windows only)"""
    print(prompt, end='', flush=True)
    password = ""
    while True:
        ch = msvcrt.getch()
        if ch == b'\r':           # Enter
            print()
            break
        elif ch == b'\x08':       # Backspace
            if len(password) > 0:
                password = password[:-1]
                print('\b \b', end='', flush=True)
        elif len(password) < 100:
            password += ch.decode('utf-8', errors='ignore')
            print('*', end='', flush=True)
    return password.strip()

def get_user_rank(username):
    entries = []
    if not os.path.exists(STATS_FILE):
        return 0
    with open(STATS_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4: continue
            u, c, i, s = row[0], int(row[1]), int(row[2]), int(row[3])
            net = c - i
            entries.append((net, c, s, u))
    if not entries:
        return 0
    entries.sort(key=lambda x: (-x[0], -x[1], x[2], x[3]))
    for rank, (_, _, _, u) in enumerate(entries, 1):
        if u == username:
            return rank
    return 0

def show_leaderboard():

    leaderboard = client.get_leaderboard()

    if not leaderboard:
        print("No stats available yet.\n")
        return

    print("\n===== Leaderboard (Top 3) =====")
    print(f"{'#':<3} {'Username':<15} {'Score':<6}")

    for entry in leaderboard:
        print(f"{entry['rank']:<3} {entry['username']:<15} {entry['score']:<6}")

    print("================================")

def signup():
    clear_screen()
    print("=== Sign Up ===\n")

    username = input("Choose a username: ").strip()

    if not username:
        print("\nUsername cannot be empty.")
        pause_and_clear(2)
        return

    while True:

        password = get_hidden_password("Choose a password: ")
        confirm = get_hidden_password("Confirm password: ")

        if password != confirm:
            print("\nPasswords do not match.")
            pause_and_clear(2)
            return

        status = client.signup(username, password)

        if status == "exists":
            print(f"\nUsername '{username}' already exists.")
        elif status == "success":
            print(f"\nSignup successful! You can now log in as {username}.")
        else:
            print("\nSignup failed.")

        pause_and_clear(2)
        return
          
def login():
    clear_screen()
    print("=== Log In ===\n")

    username = input("Enter username: ").strip()
    password = get_hidden_password("Enter password: ")

    if client.login(username, password):
        print(f"\nLogin successful! Welcome back, {username}.")
        pause_and_clear(1.5)
        return username

    print("\nInvalid username or password.")
    pause_and_clear(2)
    return None

def run_quiz(username, stats):
    clear_screen()
    display_topics()
    topic_choice = input().strip().upper()
    topic = get_topic_name(topic_choice)
    if not topic:
        print("Invalid topic.")
        pause_and_clear(1.5)
        return

    print("\nSelect difficulty:\nA. Easy\nB. Medium\nC. Hard\nYour choice: ")
    diff_choice = input().strip().upper()
    diff = get_difficulty_name(diff_choice)
    if not diff:
        print("Invalid difficulty.")
        pause_and_clear(1.5)
        return

    filename_map = {
        'A': "epd_questions.csv",
        'B': "c_questions.csv",
        'C': "mental_ability_questions.csv",
        'D': "python_questions.csv",
        'E': "maths_questions.csv"
    }
    filename = filename_map.get(topic_choice)
    if not filename:
        print("Quiz for that topic not yet available.")
        pause_and_clear(1.5)
        return

    questions = client.get_quiz(topic_choice, diff_choice)
    if not questions:
        print(f"No questions found for {topic} - {diff}.")
        pause_and_clear(2)
        return

    total_avail = len(questions)
    print(f"Available questions: {total_avail}")
    try:
        num = int(input("How many do you want to attempt? "))
    except ValueError:
        num = total_avail
    if num <= 0 or num > total_avail:
        num = total_avail
        print(f"Using all {total_avail} questions.")

    questions = questions[:num]

    per_q = 30 if diff == "Easy" else 60 if diff == "Medium" else 120
    total_time = per_q * num
    start_time = time.time()

    print(f"\nYou have {total_time} seconds for {num} questions.\n")
    time.sleep(1.2)
    clear_screen()

    # ────────────────────────────────────────────────
    # Ask questions until time runs out or all done
    # ────────────────────────────────────────────────
    for q in questions:
        if time.time() - start_time >= total_time:
            print("\nTime's up!")
            break
        ask_question(q, start_time, total_time)

    # Mark any unanswered question as skipped
    # (this fixes the "last question always skipped" bug)
    for q in questions:
        if q.user_option == ' ':
            q.user_option = 'S'
            q.is_correct = 0

    show_results(questions)

    quiz_c = sum(1 for q in questions if q.is_correct)
    quiz_w = sum(1 for q in questions if q.user_option != 'S' and not q.is_correct)
    quiz_s = sum(1 for q in questions if q.user_option == 'S')

    stats.total_correct   += quiz_c
    stats.total_incorrect += quiz_w
    stats.total_skipped   += quiz_s
    save_user_stats(stats)
    client.save_stats(username, quiz_c, quiz_w, quiz_s)

    ans = input("\nDo you want to review your answers? (Y/N): ").strip().upper()
    if ans == 'Y':
        show_answer_review(questions)

    input("\nPress Enter to return to menu...")
    clear_screen()

def show_cumulative_performance(username, stats):
    clear_screen()
    print(f"\nYour all-time totals ({username}):")
    print(f"  Correct   : {stats.total_correct}")
    print(f"  Incorrect : {stats.total_incorrect}")
    print(f"  Skipped   : {stats.total_skipped}")

    attempted = stats.total_correct + stats.total_incorrect
    total_q = attempted + stats.total_skipped
    if attempted == 0:
        print("  Accuracy  : Not Available")
        print("  Percentage: Not Available")
    else:
        acc = (stats.total_correct * 100) // attempted
        print(f"  Accuracy  : {acc}%")
        perc = (stats.total_correct * 100) // total_q if total_q > 0 else 0
        print(f"  Percentage: {perc}%")

    rank = get_user_rank(username)
    if rank > 0:
        print(f"  Your rank : {rank}")
    else:
        print("  (You are not yet ranked.)")

    input("\nPress Enter to return...")
    clear_screen()


def multiplayer_quiz(username):

    clear_screen()
    print("Joining multiplayer lobby...")

    client.join_multiplayer(username)

    print("Waiting for server to start the quiz...")

    msg = recv_json(client.conn)

    if msg["type"] == "quiz_start":

        start_time = msg["start_time"]
        duration = msg["duration"]

        wait = start_time - time.time()

        if wait > 0:
            print(f"\nQuiz starts in {int(wait)} seconds...")
            time.sleep(wait)

        print("\n=== QUIZ STARTED ===")

        questions = client.get_quiz("D", "A")  # default topic

        start = time.time()

        for q in questions:

            if time.time() - start >= duration:
                print("\nTime's up!")
                break

            ask_question(q, start, duration)

        print("\nWaiting for server to end quiz...")

        end_msg = recv_json(client.conn)

        if end_msg and end_msg.get("type") == "quiz_end":
            print("\nQuiz ended by server!")

        input("\nPress Enter to return...")


def user_menu(username):
    server_stats = client.get_user_stats(username)

    stats = UserStats(
        username,
        server_stats["correct"],
        server_stats["incorrect"],
        server_stats["skipped"]
    )

    while True:
        clear_screen()
        print(f"Welcome, {username}!")
        print("\nChoose an option:")
        print("1. Give Test")
        print("2. Cumulative Performance")
        print("3. View Leaderboard")
        print("4. Logout")
        choice = input("\nEnter choice (1-4): ").strip()

        if choice == '1':
            run_quiz(username, stats)
        elif choice == '2':
            show_cumulative_performance(username, stats)
        elif choice == '3':
            clear_screen()
            show_leaderboard()
            input("\nPress Enter to return...")
        elif choice == '4':
            client.logout(username)
            clear_screen()
            print(f"Goodbye, {username}! | Logged Out Successfully.")
            pause_and_clear(1.8)
            return
        else:
            print("\nInvalid choice, try again.")
            pause_and_clear(1.2)

def main():
    while True:
        clear_screen()
        print(r"""
  _         _     _   _       _                          
 | |    ___| |_  | | | |___  | |    ___  __ _ _ __ _ __  
 | |   / _ \ __| | | | / __| | |   / _ \/ _` | '__| '_ \ 
 | |__|  __/ |_  | |_| \__ \ | |__|  __/ (_| | |  | | | |
 |_____\___|\__|  \___/|___/ |_____\___|\__,_|_|  |_| |_|

            Online Quiz System
        Test Your Knowledge Anytime
        """)
        print("\n1. Log In")
        print("2. Sign Up (New User)")
        print("3. Admin Login")
        print("4. Exit")
        print("5. Multiplayer Quiz")
        choice = input("\nEnter your choice: ").strip()

        if choice == '1':
            username = login()
            if username:
                user_menu(username)

        elif choice == '2':
            signup()

        elif choice == '3':
            clear_screen()
            print("\nAdmin Login not yet implemented.\n")
            pause_and_clear(1.5)

        elif choice == '4':
            print("\nAll the Best!\n")
            pause_and_clear(1.5)
            sys.exit(0)

        elif choice == '5':
            multiplayer_quiz(username)

        else:
            print("\nInvalid choice. Try again.\n")
            pause_and_clear(1.5)

if __name__ == "__main__":
    main()