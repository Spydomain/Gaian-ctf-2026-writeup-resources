#include "lora.h"
#include <stdio.h>
#include <stdlib.h>
#include <complex.h>
#include <pthread.h>

pthread_mutex_t fftw_planner_mutex = PTHREAD_MUTEX_INITIALIZER;
int verbose = 0;

void on_frame(const uint8_t *payload, size_t payload_len,
              const lora_frame_meta_t *meta, void *user)
{
    printf("FRAME DELIVERED! len=%zu, crc_ok=%d\n", payload_len, meta->payload_crc_ok);
    for (size_t i = 0; i < payload_len; i++) {
        printf("%02x ", payload[i]);
    }
    printf("\nASCII: ");
    for (size_t i = 0; i < payload_len; i++) {
        char c = payload[i];
        putchar((c >= 32 && c < 127) ? c : '.');
    }
    printf("\n");
}

int main(int argc, char **argv)
{
    FILE *fp = fopen("shed_sdr_0930.sigmf-data", "rb");
    if (!fp) { perror("fopen"); return 1; }

    int num_samples = 81959 * 5; // read first 5 bursts
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

    printf("Feeding %zu samples...\n", rd);
    lora_decoder_feed(dec, samples, rd);

    lora_demod_stats_dump(stdout);
    lora_decoder_destroy(dec);
    free(samples);
    return 0;
}
