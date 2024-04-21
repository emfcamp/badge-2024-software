#include "st3m_counter.h"

#include <string.h>

#include "esp_log.h"
#include "esp_timer.h"

void st3m_counter_rate_init(st3m_counter_rate_t *rate) {
    memset(rate, 0, sizeof(st3m_counter_rate_t));
}

void st3m_counter_rate_sample(st3m_counter_rate_t *rate) {
    rate->sample_us[rate->write_offs] = esp_timer_get_time();
    rate->write_offs = (rate->write_offs + 1) % 10;
    if (rate->read_offs == rate->write_offs) {
        rate->read_offs = (rate->write_offs + 1) % 10;
    }
}

int64_t st3m_counter_rate_average(st3m_counter_rate_t *rate) {
    int start = rate->read_offs - 1;
    int end = rate->write_offs - 1;
    if (start < 0) start = 9;
    if (end < 0) end = 9;

    int i = start;
    int64_t sum = 0;
    int64_t count = 0;
    while (i != end) {
        int j = (i + 1) % 10;
        int64_t diff = rate->sample_us[j] - rate->sample_us[i];
        sum += diff;
        count++;

        i = j;
    }

    if (count == 0) {
        return INT64_MAX;
    }
    return sum / count;
}

uint8_t st3m_counter_rate_report(st3m_counter_rate_t *rate, int seconds) {
    int64_t now = esp_timer_get_time();
    if ((now - rate->last_report) > seconds * 1000000) {
        rate->last_report = now;
        return 1;
    }
    return 0;
}

void st3m_counter_timer_init(st3m_counter_timer_t *timer) {
    memset(timer, 0, sizeof(st3m_counter_timer_t));
}

void st3m_counter_timer_sample(st3m_counter_timer_t *timer, int64_t val) {
    timer->sample[timer->write_offs] = val;
    timer->write_offs = (timer->write_offs + 1) % 10;
    if (timer->read_offs == timer->write_offs) {
        timer->read_offs = (timer->write_offs + 1) % 10;
    }
}

int64_t st3m_counter_timer_average(st3m_counter_timer_t *timer) {
    int start = timer->read_offs - 1;
    int end = timer->write_offs - 1;
    if (start < 0) start = 9;
    if (end < 0) end = 9;

    int i = start;
    int64_t sum = 0;
    int64_t count = 0;
    while (i != end) {
        int j = (i + 1) % 10;
        sum += timer->sample[i];
        count++;
        i = j;
    }

    if (count == 0) {
        return INT64_MAX;
    }
    return sum / count;
}

uint8_t st3m_counter_timer_report(st3m_counter_timer_t *timer, int seconds) {
    int64_t now = esp_timer_get_time();
    if ((now - timer->last_report) > seconds * 1000000) {
        timer->last_report = now;
        return 1;
    }
    return 0;
}