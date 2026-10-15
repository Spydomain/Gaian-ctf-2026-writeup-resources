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

void on_frame(const uint8_t *payload, size_t payload_len,
              const lora_frame_meta_t *meta, void *user)
{
    printf("FRAME DELIVERED! len=%zu\n", payload_len);
    for (size_t i = 0; i < payload_len; i++) {
        printf("%02x ", payload[i]);
    }
    printf("\n");
    if (payload_len >= 73) {
        uint16_t expected_crc = (payload[71] << 8) | payload[72];
        uint16_t calc_crc = jr_crc16(payload, 71);
        printf("CRC check: calc=%04x expected=%04x -> %s\n",
               calc_crc, expected_crc, (calc_crc == expected_crc) ? "PASS!" : "FAIL");
    }
}

int main(int argc, char **argv)
{
    int burst_idx = 1;
    if (argc > 1) burst_idx = atoi(argv[1]);

    long starts[] = {0, 81959, 165917, 249875, 333833};
    long lens[] = {81959, 83958, 83958, 83958, 81959};

    FILE *fp = fopen("shed_sdr_0930.sigmf-data", "rb");
    if (!fp) { perror("fopen"); return 1; }

    fseek(fp, starts[burst_idx] * 2, SEEK_SET);
    int num_samples = lens[burst_idx];
    int8_t *raw = malloc(num_samples * 2);
    size_t rd = fread(raw, 2, num_samples, fp);
    fclose(fp);

    float complex *samples = malloc(sizeof(float complex) * rd);
    for (size_t i = 0; i < rd; i++) {
        samples[i] = (float)raw[2*i] + I * (float)raw[2*i + 1];
    }
    free(raw);

    lora_decoder_t *dec = lora_decoder_create_os(7, 5, 500000, 4);
    lora_decoder_set_callback(dec, on_frame, NULL);

    printf("Decoding burst %d (%zu samples)...\n", burst_idx, rd);
    lora_decoder_feed(dec, samples, rd);

    lora_decoder_destroy(dec);
    free(samples);
    return 0;
}
