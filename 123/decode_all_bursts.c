#define _GNU_SOURCE
#include "lora.h"
#include <stdio.h>
#include <stdlib.h>
#include <complex.h>
#include <pthread.h>
#include <stdint.h>
#include <string.h>

pthread_mutex_t fftw_planner_mutex = PTHREAD_MUTEX_INITIALIZER;
int verbose = 0;

uint16_t jr_crc16(const uint8_t *data, size_t len) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int b = 0; b < 8; b++) {
            if (crc & 0x8000)
                crc = (crc << 1) ^ 0x1021;
            else
                crc = (crc << 1);
        }
    }
    return crc;
}

typedef struct {
    uint8_t payload[128];
    size_t len;
    int received;
    int crc_ok;
} frame_result_t;

static void on_frame(const uint8_t *payload, size_t payload_len,
                     const lora_frame_meta_t *meta, void *user)
{
    frame_result_t *res = (frame_result_t *)user;
    if (res->crc_ok) return;
    if (payload_len >= 73) {
        uint16_t expected_crc = (payload[71] << 8) | payload[72];
        uint16_t calc_crc = jr_crc16(payload, 71);
        if (calc_crc == expected_crc && payload[0] == 0x4a && payload[1] == 0x52 && payload[2] == 0x4d) {
            res->received = 1;
            res->len = payload_len;
            memcpy(res->payload, payload, 73);
            res->crc_ok = 1;
        }
    }
}

int main(int argc, char **argv)
{
    FILE *mf = fopen("shed_sdr_0930.sigmf-meta", "r");
    if (!mf) { perror("sigmf-meta"); return 1; }
    fseek(mf, 0, SEEK_END);
    long mlen = ftell(mf);
    fseek(mf, 0, SEEK_SET);
    char *meta_buf = malloc(mlen + 1);
    fread(meta_buf, 1, mlen, mf);
    fclose(mf);
    meta_buf[mlen] = 0;

    int max_caps = 2000;
    long *starts = malloc(sizeof(long) * max_caps);
    int num_caps = 0;

    char *p = meta_buf;
    while ((p = strstr(p, "\"core:sample_start\":")) != NULL) {
        p += strlen("\"core:sample_start\":");
        while (*p == ' ' || *p == '\t') p++;
        long s = atol(p);
        starts[num_caps++] = s;
        if (num_caps >= max_caps) break;
    }
    free(meta_buf);
    printf("Found %d captures in metadata\n", num_caps);

    FILE *df = fopen("shed_sdr_0930.sigmf-data", "rb");
    if (!df) { perror("sigmf-data"); return 1; }
    fseek(df, 0, SEEK_END);
    long total_bytes = ftell(df);
    long total_samples = total_bytes / 2;

    int num_to_decode = num_caps;
    if (argc > 1) num_to_decode = atoi(argv[1]);

    FILE *out_f = fopen("decoded_frames.bin", "wb");
    int pass_count = 0;
    int fail_count = 0;

    int max_buf = 120000;
    int8_t *raw_buf = malloc(max_buf * 2);
    float complex *samples = malloc(sizeof(float complex) * max_buf);

    int offsets[] = {0, -2000, -1000, -500, -1500, -2500, 500, 1000};
    int num_offsets = sizeof(offsets) / sizeof(offsets[0]);

    for (int i = 0; i < num_to_decode; i++) {
        long base_start = starts[i];
        long base_end = (i + 1 < num_caps) ? starts[i + 1] : total_samples;
        long nominal_len = base_end - base_start;
        if (nominal_len > 90000) nominal_len = 90000;

        frame_result_t res = {0};

        for (int o = 0; o < num_offsets; o++) {
            long cur_start = base_start + offsets[o];
            if (cur_start < 0) cur_start = 0;
            long cur_len = nominal_len - offsets[o];
            if (cur_len > max_buf) cur_len = max_buf;
            if (cur_start + cur_len > total_samples) cur_len = total_samples - cur_start;

            fseek(df, cur_start * 2, SEEK_SET);
            size_t rd = fread(raw_buf, 2, cur_len, df);

            for (size_t s = 0; s < rd; s++) {
                samples[s] = (float)raw_buf[2*s] + I * (float)raw_buf[2*s + 1];
            }

            lora_decoder_t *dec = lora_decoder_create_os(7, 5, 500000, 4);
            lora_decoder_set_callback(dec, on_frame, &res);
            lora_decoder_feed(dec, samples, rd);
            lora_decoder_destroy(dec);

            if (res.crc_ok) break;
        }

        if (res.crc_ok) {
            pass_count++;
            fwrite(res.payload, 1, 73, out_f);
        } else {
            fail_count++;
            uint8_t zeros[73] = {0};
            fwrite(zeros, 1, 73, out_f);
        }

        if ((i + 1) % 50 == 0 || i + 1 == num_to_decode) {
            printf("Progress: %d / %d (Passed: %d, Failed: %d)\n",
                   i + 1, num_to_decode, pass_count, fail_count);
            fflush(stdout);
        }
    }

    fclose(out_f);
    fclose(df);
    free(raw_buf);
    free(samples);
    free(starts);

    printf("Done! Total passed: %d / %d (%.1f%%)\n",
           pass_count, num_to_decode, (100.0 * pass_count) / num_to_decode);
    return 0;
}
