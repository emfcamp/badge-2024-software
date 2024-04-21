#pragma once

#include <stdint.h>

typedef struct {
    int64_t sample_us[10];
    int64_t last_report;

    int write_offs;
    int read_offs;
} st3m_counter_rate_t;

void st3m_counter_rate_init(st3m_counter_rate_t *rate);
void st3m_counter_rate_sample(st3m_counter_rate_t *rate);
int64_t st3m_counter_rate_average(st3m_counter_rate_t *rate);
uint8_t st3m_counter_rate_report(st3m_counter_rate_t *rate, int seconds);

typedef struct {
    int64_t sample[10];
    int64_t last_report;

    int write_offs;
    int read_offs;
} st3m_counter_timer_t;

void st3m_counter_timer_init(st3m_counter_timer_t *rate);
void st3m_counter_timer_sample(st3m_counter_timer_t *timer, int64_t val);
int64_t st3m_counter_timer_average(st3m_counter_timer_t *rate);
uint8_t st3m_counter_timer_report(st3m_counter_timer_t *rate, int seconds);