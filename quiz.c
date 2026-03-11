#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <windows.h>
#include <conio.h>
#include <time.h>
#include "quiz.h"
#define STATS_FILE "user_stats.csv"

#define MAX_LINE 1024

void displayTopics()
{
    printf("\n\nChoose a topic:\n");
    printf("A. EPD\n");
    printf("B. C-Programming\n");
    printf("C. Mental Ability\n");
    printf("D. Python\n");
    printf("E. Triple Integration\n");
    printf("\tEnter your choice (A-E): ");
}

const char* getTopicName(char choice)
{
    switch (toupper(choice))
    {
        case 'A': return "EPD";
        case 'B': return "C Programming";
        case 'C': return "Mental Ability";
        case 'D': return "Python";
        case 'E': return "Triple Integration";
        default:  return NULL;
    }
}

const char* getDifficultyName(char choice)
{
    switch (toupper(choice))
    {
        case 'A': return "Easy";
        case 'B': return "Medium";
        case 'C': return "Hard";
        default:  return NULL;
    }
}

void loadQuestions(const char *filename, MCQ questions[], int *count, const char *chosenTopic, const char *chosenDifficulty)
{
    FILE *file = fopen(filename, "r");
    if (!file)
    {
        printf("Error opening file: %s\n", filename);
        *count = 0;
        return;
    }

    unsigned char bom[3];
    fread(bom,1,3,file);
    if (!(bom[0]==0xEF && bom[1]==0xBB && bom[2]==0xBF))
    {
        rewind(file);
    }

    char line[MAX_LINE];
    int i = 0;
    fgets(line, MAX_LINE, file);

    while (fgets(line, MAX_LINE, file) && i < MAX_QUESTIONS)
    {
        MCQ q; char correct[2];
        sscanf(line,"%d|%49[^|]|%19[^|]|%255[^|]|%127[^|]|%127[^|]|%127[^|]|%127[^|]|%1s",
               &q.id, q.topic, q.difficulty, q.question,
               q.option_a, q.option_b, q.option_c, q.option_d, correct);

        if (strcmp(q.topic, chosenTopic)==0 && strcmp(q.difficulty, chosenDifficulty)==0)
        {
            q.correct_option = toupper(correct[0]);
            q.user_option = ' ';
            q.is_correct = 0;
            questions[i++] = q;
        }
    }

    *count = i;
    fclose(file);
}


void askQuestion(MCQ *q, time_t quizStart, int totalQuizTime) {
    char input = '\0';
    int answered = 0;

    printf("\nQ%d: %s\n", q->id, q->question);
    printf("  A. %s\n", q->option_a);
    printf("  B. %s\n", q->option_b);
    printf("  C. %s\n", q->option_c);
    printf("  D. %s\n", q->option_d);
    printf("\nChoose Option A-D, 'S' to skip: ");

    while (1) {
        time_t now = time(NULL);
        int elapsed = (int)difftime(now, quizStart);
        int remaining = totalQuizTime - elapsed;

        if (remaining <= 0) {
            q->user_option = 'S';
            q->is_correct = 0;
            printf("\nTime's up for the quiz!\n");
            break;
        }
        printf("\r\t\t\t\t\t\t\t\t\tTime left: %02d:%02d", remaining / 60, remaining % 60);
        fflush(stdout);

        if (_kbhit()) {
            char ch = _getch();

            if (ch == 8) {
                if (input != '\0') {
                    printf("\b \b");
                    input = '\0';
                }
                continue;
            }

            ch = toupper(ch);
            if (ch == 'A' || ch == 'B' || ch == 'C' || ch == 'D' || ch == 'S') {
                if (input != '\0') {
                    printf("\b \b");
                }
                input = ch;
                printf("\n%c", input);
            }

            if (input != '\0') {
                char confirm = _getch();
                if (confirm == 13) {
                    q->user_option = input;
                    q->is_correct = (input == q->correct_option);
                    answered = 1;
                    break;
                } else if (confirm == 8) {
                    printf("\b \b");
                    input = '\0';
                }
            }
        }

        Sleep(200);
    }

    if (answered) {
        printf("\nYou chose: %c\n", q->user_option);
        Sleep(500);
    }
}


void showResults(MCQ questions[], int total)
{
    int c=0, w=0, s=0;
    for(int i=0;i<total;i++)
    {
        if (questions[i].user_option=='S')
            s++;
        
        else if (questions[i].is_correct)
            c++;

        else
            w++;
    }
    printf("\nQuiz Completed!\n");
    printf(" Correct: %d\n Incorrect: %d\n Skipped: %d\n",c,w,s);
}

void showAnswerReview(MCQ questions[], int total)
{
    printf("\nAnswer Review:\n");
    for(int i=0;i<total;i++)
    {
        printf("\nQ%d: %s\n",questions[i].id,questions[i].question);
        if (questions[i].user_option=='S') 
        {
            printf(" You skipped. | Correct: %c\n",questions[i].correct_option);
        } 
        else 
        {
            printf(" Your: %c | Correct: %c \n %s\n",
                   questions[i].user_option,
                   questions[i].correct_option,
                   questions[i].is_correct ? "Correct":"Incorrect");
        }
    }
}

int loadUserStats(const char *username, UserStats *stats) {
    FILE *f = fopen(STATS_FILE, "r");
    if (!f) {
        strcpy(stats->username, username);
        stats->total_correct = stats->total_incorrect = stats->total_skipped = 0;
        return 0;
    }
    char line[128];
    while (fgets(line, sizeof line, f)) {
        char user[50];
        int c,i,s;
        if (sscanf(line, "%49[^,],%d,%d,%d", user, &c,&i,&s)==4) {
            if (strcmp(user, username)==0) {
                strcpy(stats->username, user);
                stats->total_correct = c;
                stats->total_incorrect = i;
                stats->total_skipped = s;
                fclose(f);
                return 0;
            }
        }
    }
    strcpy(stats->username, username);
    stats->total_correct = stats->total_incorrect = stats->total_skipped = 0;
    fclose(f);
    return 0;
}

int saveUserStats(const UserStats *stats) {
    FILE *f = fopen(STATS_FILE, "r");
    FILE *tmp = fopen("stats.tmp", "w");
    char line[128];
    int found = 0;
    if (f) {
        while (fgets(line, sizeof line, f)) {
            char user[50];
            int c,i,s;
            if (sscanf(line, "%49[^,],%d,%d,%d", user,&c,&i,&s)==4) {
                if (strcmp(user, stats->username)==0) {
                    fprintf(tmp, "%s,%d,%d,%d\n",
                            stats->username,
                            stats->total_correct,
                            stats->total_incorrect,
                            stats->total_skipped);
                    found = 1;
                } else {
                    fputs(line, tmp);
                }
            }
        }
        fclose(f);
    }
    if (!found) {
        fprintf(tmp, "%s,%d,%d,%d\n",
                stats->username,
                stats->total_correct,
                stats->total_incorrect,
                stats->total_skipped);
    }
    fclose(tmp);
    remove(STATS_FILE);
    rename("stats.tmp", STATS_FILE);
    return 0;
}

void fullQuizLogic(const char *username) {
    char more;
    do {
        MCQ questions[MAX_QUESTIONS];
        int total = 0, numQuestions;
        char topic_choice, difficulty_choice;
        char filename[64];
        char buf[16];

        displayTopics();
        fgets(buf, sizeof(buf), stdin);
        topic_choice = toupper(buf[0]);
        const char *topic = getTopicName(topic_choice);
        if (!topic || buf[1] != '\n') {
            printf("Invalid topic.\n\n");
            continue;
        }

        printf("\nSelect difficulty:\nA. Easy\nB. Medium\nC. Hard\nYour choice: ");
        fgets(buf, sizeof(buf), stdin);
        difficulty_choice = toupper(buf[0]);
        const char *diff = getDifficultyName(difficulty_choice);
        if (!diff || buf[1] != '\n') {
            printf("Invalid difficulty.\n\n");
            continue;
        }

        switch (topic_choice) {
            case 'A': strcpy(filename, "epd_questions.csv"); break;
            case 'B': strcpy(filename, "cprog_questions.csv"); break;
            case 'C': strcpy(filename, "mental_ability_questions.csv"); break;
            case 'D': strcpy(filename, "python_questions.csv"); break;
            case 'E': strcpy(filename, "maths_questions.csv"); break;
            default:
                printf("Quiz for that topic not yet available.\n\n");
                continue;
        }

        loadQuestions(filename, questions, &total, topic, diff);
        if (total == 0) {
            printf("No questions found for %s - %s.\n\n", topic, diff);
            continue;
        }

        printf("Available questions: %d\nHow many do you want to attempt? ", total);
        scanf("%d", &numQuestions);
        while (getchar() != '\n');
        if (numQuestions <= 0 || numQuestions > total) {
            printf("Invalid number; using all %d questions.\n", total);
            numQuestions = total;
        }

        int perQ;
        if (strcmp(diff, "Easy") == 0)      perQ = 30;
        else if (strcmp(diff, "Medium") == 0) perQ = 60;
        else                                 perQ = 120;
        int totalQuizTime = perQ * numQuestions;
        time_t quizStart = time(NULL);

        printf("\n You have %d seconds total to answer %d questions.\n\n",
               totalQuizTime, numQuestions);
        Sleep(1500);

        for (int i = 0; i < numQuestions; i++) {
            askQuestion(&questions[i], quizStart, totalQuizTime);
        }

        showResults(questions, numQuestions);

        printf("\nDo you want to review your answers? (Y/N): ");
        fgets(buf, sizeof(buf), stdin);
        if (toupper(buf[0]) == 'Y') {
            showAnswerReview(questions, numQuestions);
        }

        printf("\nTake another quiz? (Y/N): ");
        fgets(buf, sizeof(buf), stdin);
        more = toupper(buf[0]);

    } while (more == 'Y');

    printf("\n[QUIZ] Completed. Goodbye, %s!\n", username);
}