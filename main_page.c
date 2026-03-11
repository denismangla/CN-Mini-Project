#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <stdlib.h>
#include <conio.h>
#include "quiz.h"
#include <time.h>


#define MAX_USERS 1000
#define MAX_LEN 100

#ifdef _WIN32
  #include <windows.h>
  #define sleep_ms(ms) Sleep(ms)
#else
  #include <unistd.h>
  #define sleep_ms(ms) usleep((ms)*1000)
#endif


#define LINE_BUF 128

typedef struct {
    char username[50];
    int total_correct;
    int total_incorrect;
    int total_skipped;
    int net_score;
} LBEntry;

static int cmp_desc(const void *a, const void *b) {
    const LBEntry *x = a;
    const LBEntry *y = b;

    if (y->net_score != x->net_score)
        return y->net_score - x->net_score;

    if (y->total_correct != x->total_correct)
        return y->total_correct - x->total_correct;

    if (x->total_skipped != y->total_skipped)
        return x->total_skipped - y->total_skipped;

    return strcmp(x->username, y->username);
}

int getUserRank(const char *username) {
    LBEntry entries[MAX_USERS];
    int count = 0;
    char line[LINE_BUF];

    FILE *f = fopen("user_stats.csv", "r");
    if (!f) return 0;
    while (fgets(line, sizeof line, f) && count < MAX_USERS) {
        int c,i,s;
        char user[50];
        if (sscanf(line, "%49[^,],%d,%d,%d", user, &c,&i,&s) == 4) {
            strcpy(entries[count].username,     user);
            entries[count].total_correct   = c;
            entries[count].total_incorrect = i;
            entries[count].total_skipped   = s;
            entries[count].net_score       = c - i;
            count++;
        }
    }
    fclose(f);

    if (count == 0) return 0;
    qsort(entries, count, sizeof(LBEntry), cmp_desc);

    for (int idx = 0; idx < count; idx++) {
        if (strcmp(entries[idx].username, username) == 0)
            return idx + 1;
    }
    return 0;
}

void showLeaderboard(void) {
    FILE *f = fopen("user_stats.csv", "r");
    if (!f) {
        printf("No stats available yet.\n");
        return;
    }

    LBEntry entries[MAX_USERS];
    int count = 0;
    char line[LINE_BUF];

    while (fgets(line, sizeof line, f) && count < MAX_USERS) {
        int c,i,s;
        char user[50];
        if (sscanf(line, "%49[^,],%d,%d,%d", user, &c, &i, &s) == 4) {
            strcpy(entries[count].username, user);
            entries[count].total_correct   = c;
            entries[count].total_incorrect = i;
            entries[count].total_skipped   = s;
            entries[count].net_score       = c - i;
            count++;
        }
    }
    fclose(f);

    if (count == 0) {
        printf("No user data to show.\n");
        return;
    }

    qsort(entries, count, sizeof(LBEntry), cmp_desc);

    printf("\n===== Leaderboard (Top %d) =====\n", count < 3 ? count : 3);
    printf("%-3s %-15s %-6s\n",
           "#", "Username", "Score");

    int to_show = count < 3 ? count : 3;
    for (int i = 0; i < to_show; i++) {
        printf("%-3d %-15s %-6d\n",
               i+1,
               entries[i].username,
               entries[i].net_score);
    }
    printf("===============================\n\n");
}


int login();
void signup();
int checkCredentials(const char *username, const char *password);
void startQuiz(const char *username);
void clearScreen() {
    #ifdef _WIN32
        system("cls");
    #else
        system("clear");
    #endif
    }
int main() {
    int choice;
    char username[MAX_LEN];
    clearScreen();
    while (1) {
        printf(" _____     _       _ _____         _      _____                         _   _\n|     |_ _|_|___  / |_   _|___ ___| |_   |  _  |___ ___ ___ ___ ___ ___| |_|_|___ ___ \n|  |  | | | |- _|/ /  | | | -_|_ -|  _|  |   __|  _| -_| . | . |  _| . |  _| | . |   |\n|__  _|___|_|___|_/   |_| |___|___|_|    |__|  |_| |___|  _|__,|_| |__,|_| |_|___|_|_|\n   |__|                                                |_|                                ");
        printf("\n\n1. Log In\n");
        printf("2. Sign Up (New User)\n");
        printf("3. Admin Login\n");
        printf("4. Exit\n");
        printf("Enter your choice: ");
        scanf("%d", &choice);
        getchar();

        switch (choice) {
            case 1:
                if (login(username)) {
                    clearScreen();
                    printf("Welcome, %s!\n\n", username);
                    startQuiz(username);
                } else {
                    clearScreen();
                    printf("\nInvalid username or password.\n");
                }
                break;
            case 2:
                signup();
                break;
            case 3:
            clearScreen();
                printf("\nAdmin Login not yet implemented.\n");
                break;
            case 4:
                printf("\nAll the Best!\n");
                exit(0);
            default:
                clearScreen();
                printf("Invalid choice. Try again.\n");
        }
    }

    return 0;
}

int login(char *username) {
    char password[MAX_LEN];
    char ch;
    int i = 0;

    printf("\nEnter username: ");
    fgets(username, MAX_LEN, stdin);
    size_t len = strlen(username);
    if (len > 0 && username[len - 1] == '\n') username[len - 1] = '\0';

    printf("Enter password: ");
    while (1) {
        ch = getch();
        if (ch == 13) break;
        else if (ch == 8) {
            if (i > 0) {
                i--;
                printf("\b \b");
            }
        } else if (i < MAX_LEN - 1) {
            password[i++] = ch;
            printf("*");
        }
    }
    password[i] = '\0';
    printf("\n");

    return checkCredentials(username, password);
}

void signup() {
    char username[MAX_LEN], password[MAX_LEN], ch;
    int i = 0;

    printf("\nChoose a username: ");
    fgets(username, MAX_LEN, stdin);
    size_t len = strlen(username);
    if (len > 0 && username[len - 1] == '\n') username[len - 1] = '\0';

    FILE *fp = fopen("users.txt", "r");
    if (fp != NULL) {
        char line[MAX_LEN];
        while (fgets(line, sizeof(line), fp)) {
            char storedUsername[MAX_LEN];
            sscanf(line, "%[^,\n]", storedUsername);
            if (strcmp(storedUsername, username) == 0) {
                fclose(fp);
                clearScreen();
                printf("\n Username '%s' already exists. Please try another.\n", username);
                return;
            }
        }
        fclose(fp);
    }

    printf("Choose a password: ");
    while (1) {
        ch = getch();
        if (ch == 13) break;
        else if (ch == 8) {
            if (i > 0) {
                i--;
                printf("\b \b");
            }
        } else if (i < MAX_LEN - 1) {
            password[i++] = ch;
            printf("*");
        }
    }
    password[i] = '\0';
    printf("\n");

    fp = fopen("users.txt", "a");
    if (fp == NULL) {
        printf("Error opening user file.\n");
        return;
    }
    fprintf(fp, "%s,%s\n", username, password);
    fclose(fp);

    clearScreen();
    printf("\n Signup successful! You can now log in.\n");
}

int checkCredentials(const char *username, const char *password) {
    FILE *fp = fopen("users.txt", "r");
    if (fp == NULL) {
        printf("Could not open users file.\n");
        return 0;
    }

    char fileUsername[MAX_LEN], filePassword[MAX_LEN];
    char line[MAX_LEN * 2];

    while (fgets(line, sizeof(line), fp)) {
        sscanf(line, "%[^,],%[^\n]", fileUsername, filePassword);
        if (strcmp(username, fileUsername) == 0 && strcmp(password, filePassword) == 0) {
            fclose(fp);
            return 1;
        }
    }

    fclose(fp);
    return 0;
}

void runQuizForUser(const char *username, UserStats *stats);

void startQuiz(const char *username) {
    UserStats stats;
    loadUserStats(username, &stats);

    while (1) {
        char choice;
        char buf[16];

        printf("Choose an option:\n");
        printf("1. Give Test\n");
        printf("2. Cumulative Performance\n");
        printf("3. View Leaderboard\n");
        printf("4. Logout\n");
        printf("Enter choice (1-4): ");
        if (scanf(" %c", &choice) != 1) {
            while (getchar()!='\n');
            continue;
        }
        while (getchar()!='\n');

        clearScreen();

        if (choice == '1') {
            runQuizForUser(username, &stats);
        }
        else if (choice == '2') {
            printf("\nYour all-time totals:\n");
            printf("  Correct:    %d\n", stats.total_correct);
            printf("  Incorrect:  %d\n", stats.total_incorrect);
            printf("  Skipped:    %d\n", stats.total_skipped);
            if (stats.total_correct == 0 && stats.total_incorrect == 0 && stats.total_skipped == 0){
                printf("  Accuracy:   Not Available.\n");
                printf("  Percentage: Not Available.\n");    
            }
            
            else if (stats.total_correct == 0 && stats.total_incorrect == 0){
                printf("Accuracy: Not Available.\n");
                printf("Percentage: Not Available.\n");
            }
            else {
                printf("  Accuracy:   %d\n", stats.total_correct*100/(stats.total_correct + stats.total_incorrect));
                printf("  Percentage: %d\n", stats.total_correct*100/(stats.total_correct + stats.total_incorrect + stats.total_skipped));
            }
            int rank = getUserRank(username);
            if (rank > 0)
                printf("  Your rank: %d\n", rank);
            else
                printf("  (You are not yet ranked.)\n");
            printf("\nPress Enter to return to menu...");
            fgets(buf, sizeof(buf), stdin);
            clearScreen();
        }
        else if (choice == '3') {
            showLeaderboard();
            printf("\nPress Enter to return to menu...");
            fgets(buf, sizeof buf, stdin);
            clearScreen();
        }
        else if (choice == '4') {
            saveUserStats(&stats);
            clearScreen();
            printf("Goodbye, %s! | Logged Out Successfuly.\n", username);
            break;
        }
        else {
            clearScreen();
            printf("Invalid choice, try again.\n");
            Sleep(1000);
        }
    }
}


void runQuizForUser(const char *username, UserStats *stats) {
    MCQ questions[MAX_QUESTIONS];
    int total = 0, numQuestions;
    char topic_choice, difficulty_choice;
    const char *topic, *diff;
    char filename[64];
    char buf[16];

    clearScreen();
    displayTopics();
    if (!fgets(buf, sizeof buf, stdin)) return;
    topic_choice = toupper(buf[0]);
    topic = getTopicName(topic_choice);
    if (!topic || buf[1] != '\n') {
        printf("Invalid topic.\n");
        return;
    }

    printf("\nSelect difficulty:\nA. Easy\nB. Medium\nC. Hard\nYour choice: ");
    if (!fgets(buf, sizeof buf, stdin)) return;
    difficulty_choice = toupper(buf[0]);
    diff = getDifficultyName(difficulty_choice);
    if (!diff || buf[1] != '\n') {
        printf("Invalid difficulty.\n");
        return;
    }

    switch (topic_choice) {
        case 'A': strcpy(filename, "epd_questions.csv"); break;
        case 'B': strcpy(filename, "c_questions.csv"); break;
        case 'C': strcpy(filename, "mental_ability_questions.csv"); break;
        case 'D': strcpy(filename, "python_questions.csv"); break;
        case 'E': strcpy(filename, "maths_questions.csv"); break;
        default:
            printf("Quiz for that topic not yet available.\n");
            return;
    }

    loadQuestions(filename, questions, &total, topic, diff);
    if (total == 0) {
        printf("No questions found for %s - %s.\n", topic, diff);
        return;
    }

    printf("Available questions: %d\nHow many do you want to attempt? ", total);
    if (scanf("%d", &numQuestions) != 1) {
        while (getchar() != '\n');
        printf("Invalid number.\n");
        return;
    }
    while (getchar() != '\n');
    if (numQuestions <= 0 || numQuestions > total) {
        printf("Using all %d questions.\n", total);
        numQuestions = total;
    }

    int perQ = strcmp(diff, "Easy") == 0 ? 30
               : strcmp(diff, "Medium") == 0 ? 60
               : 120;
    int totalQuizTime = perQ * numQuestions;
    time_t quizStart = time(NULL);
    printf("\nYou have %d seconds for %d questions.\n\n",
           totalQuizTime, numQuestions);
    sleep_ms(1000);
    clearScreen();

    int i;
    for (i = 0; i < numQuestions; i++) {
        if (difftime(time(NULL), quizStart) >= totalQuizTime) {
            printf("\nTime's up!\n");
            break;
        }
        askQuestion(&questions[i], quizStart, totalQuizTime);
    }

    for (int j = i; j < numQuestions; j++) {
        questions[j].user_option = 'S';
        questions[j].is_correct  = 0;
    }

    showResults(questions, numQuestions);

    int quiz_correct = 0, quiz_incorrect = 0, quiz_skipped = 0;
    for (int j = 0; j < numQuestions; j++) {
        if (questions[j].user_option == 'S') {
            quiz_skipped++;
        }
        else if (questions[j].is_correct) {
            quiz_correct++;
        }
        else {                              
            quiz_incorrect++;
        }
    }

    stats->total_correct   += quiz_correct;
    stats->total_incorrect += quiz_incorrect;
    stats->total_skipped   += quiz_skipped;
    saveUserStats(stats);

    printf("\nDo you want to review your answers? (Y/N): ");
    if (fgets(buf, sizeof buf, stdin) && toupper(buf[0]) == 'Y') {
        showAnswerReview(questions, numQuestions);
    }

    printf("\nPress Enter to return to menu...");
    fgets(buf, sizeof buf, stdin);
    clearScreen();
}