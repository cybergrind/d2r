/* One hotkey request to the service, from a process that starts in about a millisecond.
 *
 *     d2r-send "<prefix>" <socket path>
 *
 * The same datagram as request.py sends: the prefix, the monotonic clock, then how long this
 * process took to start (ms, to a clock tick) and the CPU it used (ms). request.py's own start took
 * 31 to 57 ms of every press with the game running (2026-10-11); the teleport key is bound to this
 * instead (input/compositor.py builds it when `make serve` starts and falls back to request.py).
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <time.h>
#include <unistd.h>

static double now(clockid_t clock) {
    struct timespec t;
    clock_gettime(clock, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

/* Seconds since this process started; negative when /proc does not say. */
static double age(void) {
    char text[1024];
    FILE *stat = fopen("/proc/self/stat", "r");
    if (!stat) return -1;
    size_t size = fread(text, 1, sizeof text - 1, stat);
    fclose(stat);
    text[size] = 0;
    char *field = strrchr(text, ')');
    if (!field) return -1;
    for (int skipped = 0; skipped < 20 && field; skipped++) field = strchr(field + 1, ' ');
    if (!field) return -1;
    return now(CLOCK_BOOTTIME) - strtod(field + 1, NULL) / sysconf(_SC_CLK_TCK);
}

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: d2r-send \"<prefix>\" <socket path>\n");
        return 2;
    }
    struct sockaddr_un address = {.sun_family = AF_UNIX};
    if (strlen(argv[2]) >= sizeof address.sun_path) return 2;
    strcpy(address.sun_path, argv[2]);
    int client = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (client < 0) return 1;
    double started = age(), cpu = now(CLOCK_PROCESS_CPUTIME_ID);
    char message[256];
    int length = started < 0
        ? snprintf(message, sizeof message, "%s%.6f", argv[1], now(CLOCK_MONOTONIC))
        : snprintf(message, sizeof message, "%s%.6f %.1f %.1f", argv[1], now(CLOCK_MONOTONIC), started * 1e3, cpu * 1e3);
    if (length < 0 || length >= (int)sizeof message) return 2;
    return sendto(client, message, length, 0, (struct sockaddr *)&address, sizeof address) == length ? 0 : 1;
}
