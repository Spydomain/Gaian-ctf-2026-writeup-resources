#include "lora.h"
#include <stdio.h>
#include <stdlib.h>
#include <complex.h>
#include <pthread.h>
#include <stdint.h>
pthread_mutex_t fftw_planner_mutex = PTHREAD_MUTEX_INITIALIZER;
int verbose=0;
static int capture=0,found=0;
static void frame(const uint8_t *p,size_t n,const lora_frame_meta_t *m,void *u){
 found++;
 printf("{\"capture\":%d,\"length\":%zu,\"header_ok\":%s,\"crc_present\":%s,\"crc_ok\":%s,\"cr\":%d,\"payload\":\"",capture,n,m->header_crc_ok?"true":"false",m->has_crc?"true":"false",m->payload_crc_ok?"true":"false",m->cr);
 for(size_t i=0;i<n;i++)printf("%02x",p[i]);printf("\"}\n");fflush(stdout);
}
int main(){
 FILE *f=fopen("coop_sdr_1205.sigmf-data","rb"),*b=fopen("capture_bounds.txt","r");
 if(!f||!b)return 2;
 int8_t *raw=malloc(1000000);float complex *iq=malloc(500000*sizeof(*iq));long a,z;
 while(fscanf(b,"%ld %ld",&a,&z)==2){
  size_t n=(size_t)(z-a);fseek(f,2*a,SEEK_SET);n=fread(raw,2,n,f);
  for(size_t i=0;i<n;i++)iq[i]=(float)raw[2*i]+I*(float)raw[2*i+1];
  int before=found;lora_decoder_t *d=lora_decoder_create_os(9,5,125000,8);
  lora_decoder_set_callback(d,frame,NULL);lora_decoder_feed(d,iq,n);lora_decoder_destroy(d);
  if(found==before)fprintf(stderr,"No frame in capture %d\n",capture);capture++;
 }
 fprintf(stderr,"%d frames in %d captures\n",found,capture);fclose(f);fclose(b);free(raw);free(iq);
}
