#include <stddef.h>

// Edit a const char *'s underlying data in place - YOLO
// (Seriously, an easter egg isn't worth reallocating lots of strings, and we don't care about this leaking to other places)
const char *remove_spider_leg(char *str) {
    static int do_replace = -1;
    if (do_replace == -1)
        do_replace = (rand() % 8 == 0);
    if (!do_replace)
        return str;

    for (size_t i = 0; str[i] && str[i + 1] && str[i + 2]; i++) {
        if (str[i] == 0xE8 && str[i + 1] == 0x87 && str[i + 2] == 0xA9) {
            str[i] = 0xE7;
            i += 2;
        }
    }
    return str;
}