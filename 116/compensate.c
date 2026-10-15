/* Replay CL3-0419's register dump through Bosch's reference API. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bme68x.c"
static unsigned char registers[256];
static BME68X_INTF_RET_TYPE rd(uint8_t reg,uint8_t *buf,uint32_t n,void *ptr){memcpy(buf,registers+reg,n);return 0;}
static BME68X_INTF_RET_TYPE wr(uint8_t reg,const uint8_t *buf,uint32_t n,void *ptr){return 0;}
static void delay(uint32_t us,void *ptr){}
int main(){
 FILE *boot=fopen("cl3_0419_boot.txt","r");char line[512];
 while(fgets(line,sizeof(line),boot)){
  if(strncmp(line,"REG ",4))continue;char *p=line+4;unsigned reg=strtoul(p,&p,0);
  while(*p){while(*p==' '||*p=='\t')p++;if(*p=='\n'||!*p)break;registers[reg++]=(unsigned char)strtoul(p,&p,16);}
 }
 fclose(boot);struct bme68x_dev d={0};d.intf=BME68X_I2C_INTF;d.read=rd;d.write=wr;d.delay_us=delay;
 if(get_calib_data(&d))return 2;
 fprintf(stderr,"T1=%u T2=%d T3=%d\nP1=%u P2=%d P3=%d P4=%d P5=%d P6=%d P7=%d P8=%d P9=%d P10=%u\nH1=%u H2=%u H3=%d H4=%d H5=%d H6=%u H7=%d\n",d.calib.par_t1,d.calib.par_t2,d.calib.par_t3,d.calib.par_p1,d.calib.par_p2,d.calib.par_p3,d.calib.par_p4,d.calib.par_p5,d.calib.par_p6,d.calib.par_p7,d.calib.par_p8,d.calib.par_p9,d.calib.par_p10,d.calib.par_h1,d.calib.par_h2,d.calib.par_h3,d.calib.par_h4,d.calib.par_h5,d.calib.par_h6,d.calib.par_h7);
 FILE *f=fopen("cl3_0419_env.csv","r");fgets(line,sizeof(line),f);printf("rec,ms,temperature_C,pressure_hPa,humidity_pct\n");
 unsigned rec,ms,t,p,h;
 while(fscanf(f,"%u,%u,%u,%u,%u\n",&rec,&ms,&t,&p,&h)==5){
  float temp=calc_temperature(t,&d),pres=calc_pressure(p,&d),hum=calc_humidity(h,&d);
  printf("%u,%u,%.8f,%.8f,%.8f\n",rec,ms,temp,pres/100,hum);
 }
 fclose(f);
}
