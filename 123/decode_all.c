#include "lora.h"
#include <stdio.h>
#include <stdlib.h>
#include <complex.h>
#include <pthread.h>
#include <string.h>
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

void on_frame(const uint8_t *payload, size_t payload_len,
              const lora_frame_meta_t *meta, void *user) {
    FILE *fp = (FILE*)user;
    // Check application CRC (last 2 bytes)
    uint16_t frame_crc = 0;
    uint16_t calc_crc = 0;
    int crc_ok = 0;
    if (payload_len >= 2) {
        frame_crc = (payload[payload_len - 2] << 8) | payload[payload_len - 1];
        calc_crc = jr_crc16(payload, payload_len - 2);
        crc_ok = (frame_crc == calc_crc);
    }
    fprintf(fp, "FRAME: len=%zu, phy_crc_ok=%d, app_crc_ok=%d, app_crc=%04x/%04x\n",
            payload_len, meta->payload_crc_ok, crc_ok, frame_crc, calc_crc);
    for (size_t i = 0; i < payload_len; i++) {
        fprintf(fp, "%02x ", payload[i]);
    }
    fprintf(fp, "\n");
}

int main(int argc, char **argv) {
    FILE *fp = fopen("shed_sdr_0930.sigmf-data", "rb");
    if (!fp) { perror("fopen"); return 1; }

    fseek(fp, 0, SEEK_END);
    long file_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    int num_samples = file_size / 2;
    
    int8_t *raw = malloc(num_samples * 2);
    size_t rd = fread(raw, 2, num_samples, fp);
    fclose(fp);

    float complex *samples = malloc(sizeof(float complex) * rd);
    for (size_t i = 0; i < rd; i++) {
        samples[i] = (float)raw[2*i] + I * (float)raw[2*i + 1];
    }
    free(raw);

    lora_decoder_t *dec = lora_decoder_create_os(7, 5, 500000, 4);
    lora_decoder_set_callback(dec, on_frame, stdout);

    printf("Feeding %zu samples...\n", rd);
    lora_decoder_feed(dec, samples, rd);

    lora_demod_stats_dump(stdout);
    lora_decoder_destroy(dec);
    free(samples);
    return 0;
}
