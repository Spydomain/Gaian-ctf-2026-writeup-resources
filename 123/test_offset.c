#include "lora.h"
#include <stdio.h>
#include <stdlib.h>
#include <complex.h>
#include <pthread.h>
#include <stdint.h>

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

static int got_pass = 0;

void on_frame(const uint8_t *payload, size_t payload_len,
              const lora_frame_meta_t *meta, void *user)
{
    if (payload_len >= 73) {
        uint16_t expected_crc = (payload[71] << 8) | payload[72];
        uint16_t calc_crc = jr_crc16(payload, 71);
        if (calc_crc == expected_crc) {
            printf("  OFFSET MATCH! hdr: %02x%02x%02x%02x%02x%02x%02x CRC=%04x\n",
                   payload[0], payload[1], payload[2], payload[3], payload[4], payload[5], payload[6],
                   calc_crc);
            got_pass = 1;
        }
    }
}

int main(int argc, char **argv)
{
    int burst_idx = 4;
    long start = 333833;
    long num_samples = 81959;

    FILE *fp = fopen("shed_sdr_0930.sigmf-data", "rb");
    fseek(fp, (start - 2000) * 2, SEEK_SET);
    int total_to_read = num_samples + 4000;
    int8_t *raw = malloc(total_to_read * 2);
    fread(raw, 2, total_to_read, fp);
    fclose(fp);

    float complex *all_samples = malloc(sizeof(float complex) * total_to_read);
    for (int i = 0; i < total_to_read; i++) {
        all_samples[i] = (float)raw[2*i] + I * (float)raw[2*i + 1];
    }

    for (int off = -2000; off <= 2000; off += 100) {
        got_pass = 0;
        lora_decoder_t *dec = lora_decoder_create_os(7, 5, 500000, 4);
        lora_decoder_set_callback(dec, on_frame, NULL);
        lora_decoder_feed(dec, &all_samples[2000 + off], num_samples);
        lora_decoder_destroy(dec);
        if (got_pass) {
            printf("Found working offset for burst 4: %d\n", off);
            break;
        }
    }
    return 0;
}
