#include <time.h>
#ifndef QUIZ_H
#define QUIZ_H

#define MAX_QUESTIONS 100

typedef struct {
    int id;
    char topic[50];
    char difficulty[20];
    char question[256];
    char option_a[100];
    char option_b[100];
    char option_c[100];
    char option_d[100];
    char correct_option;
    char user_option;
    int is_correct;
} MCQ;

typedef struct {
    char username[50];
    int total_correct;
    int total_incorrect;
    int total_skipped;
} UserStats;

void displayTopics();
const char* getTopicName(char choice);
const char* getDifficultyName(char choice);
void loadQuestions(const char *filename, MCQ questions[], int *total, const char *topic, const char *difficulty);
int loadUserStats(const char *username, UserStats *stats);
int saveUserStats(const UserStats *stats);
void askQuestion(MCQ *q, time_t quizStart, int totalQuizTime);
void showResults(MCQ questions[], int total);
void showAnswerReview(MCQ questions[], int total);
void fullQuizLogic(const char *username);

#endif