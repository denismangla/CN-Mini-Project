import csv
import os
import time
import sys
import msvcrt

MAX_QUESTIONS = 100
STATS_FILE = "user_stats.csv"

class MCQ:
    def __init__(self, id, topic, difficulty, question, option_a, option_b, option_c, option_d, correct_option):
        self.id = id
        self.topic = topic
        self.difficulty = difficulty
        self.question = question
        self.option_a = option_a
        self.option_b = option_b
        self.option_c = option_c
        self.option_d = option_d
        self.correct_option = correct_option.upper()
        self.user_option = ' '
        self.is_correct = 0

class UserStats:
    def __init__(self, username, total_correct=0, total_incorrect=0, total_skipped=0):
        self.username = username
        self.total_correct = total_correct
        self.total_incorrect = total_incorrect
        self.total_skipped = total_skipped

def display_topics():
    print("\n\nChoose a topic:")
    print("A. EPD")
    print("B. C-Programming")
    print("C. Mental Ability")
    print("D. Python")
    print("E. Triple Integration")
    sys.stdout.write("\tEnter your choice (A-E): ")
    sys.stdout.flush()

def get_topic_name(choice):
    choice = choice.upper()
    if choice == 'A': return "EPD"
    if choice == 'B': return "C Programming"
    if choice == 'C': return "Mental Ability"
    if choice == 'D': return "Python"
    if choice == 'E': return "Triple Integration"
    return None

def get_difficulty_name(choice):
    choice = choice.upper()
    if choice == 'A': return "Easy"
    if choice == 'B': return "Medium"
    if choice == 'C': return "Hard"
    return None

def load_questions(filename, topic, difficulty):
    questions = []
    try:
        with open(filename, 'r', encoding='utf-8-sig') as file:
            reader = csv.reader(file, delimiter='|')
            next(reader, None)  # Skip header
            for row in reader:
                if len(row) >= 9 and row[1].strip() == topic and row[2].strip() == difficulty:
                    q = MCQ(
                        int(row[0].strip()),
                        row[1].strip(),
                        row[2].strip(),
                        row[3].strip(),
                        row[4].strip(),
                        row[5].strip(),
                        row[6].strip(),
                        row[7].strip(),
                        row[8].strip()
                    )
                    questions.append(q)
    except FileNotFoundError:
        print(f"Error opening file: {filename}")
    return questions

def ask_question(q, quiz_start, total_quiz_time):
    input_char = None
    answered = False

    print(f"\nQ{q.id}: {q.question}")
    print(f"  A. {q.option_a}")
    print(f"  B. {q.option_b}")
    print(f"  C. {q.option_c}")
    print(f"  D. {q.option_d}")
    sys.stdout.write("\nChoose Option A-D, 'S' to skip: ")
    sys.stdout.flush()

    while True:
        now = time.time()
        elapsed = int(now - quiz_start)
        remaining = total_quiz_time - elapsed

        if remaining <= 0:
            q.user_option = 'S'
            q.is_correct = 0
            print("\nTime's up for the quiz!")
            break

        # Print time left
        sys.stdout.write(f"\r\t\t\t\t\t\t\t\t\tTime left: {remaining // 60:02d}:{remaining % 60:02d}")
        sys.stdout.flush()

        if msvcrt.kbhit():
            ch = msvcrt.getch()
            ch = ch.decode('utf-8').upper()

            if ord(ch) == 8:  # Backspace
                if input_char is not None:
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                    input_char = None
                continue

            if ch in ['A', 'B', 'C', 'D', 'S']:
                if input_char is not None:
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                input_char = ch
                print(f"\n{ch}")
                sys.stdout.flush()

            if input_char is not None:
                confirm = msvcrt.getch()
                if ord(confirm) == 13:  # Enter
                    q.user_option = input_char
                    q.is_correct = 1 if input_char == q.correct_option else 0
                    answered = True
                    break
                elif ord(confirm) == 8:  # Backspace
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                    input_char = None

        time.sleep(0.2)

    if answered:
        print(f"\nYou chose: {q.user_option}")
        time.sleep(0.5)

def show_results(questions):
    c = 0
    w = 0
    s = 0
    for q in questions:
        if q.user_option == 'S':
            s += 1
        elif q.is_correct:
            c += 1
        else:
            w += 1
    print("\nQuiz Completed!")
    print(f" Correct: {c}\n Incorrect: {w}\n Skipped: {s}")

def show_answer_review(questions):
    print("\nAnswer Review:")
    for q in questions:
        print(f"\nQ{q.id}: {q.question}")
        if q.user_option == 'S':
            print(f" You skipped. | Correct: {q.correct_option}")
        else:
            status = "Correct" if q.is_correct else "Incorrect"
            print(f" Your: {q.user_option} | Correct: {q.correct_option} \n {status}")

def load_user_stats(username):
    stats = UserStats(username)
    if not os.path.exists(STATS_FILE):
        return stats
    with open(STATS_FILE, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) == 4 and row[0] == username:
                stats.total_correct = int(row[1])
                stats.total_incorrect = int(row[2])
                stats.total_skipped = int(row[3])
                return stats
    return stats

def save_user_stats(stats):
    lines = []
    found = False
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            lines = f.readlines()
        with open(STATS_FILE, 'w') as f:
            for line in lines:
                row = line.strip().split(',')
                if len(row) == 4 and row[0] == stats.username:
                    f.write(f"{stats.username},{stats.total_correct},{stats.total_incorrect},{stats.total_skipped}\n")
                    found = True
                else:
                    f.write(line)
    if not found:
        with open(STATS_FILE, 'a') as f:
            f.write(f"{stats.username},{stats.total_correct},{stats.total_incorrect},{stats.total_skipped}\n")