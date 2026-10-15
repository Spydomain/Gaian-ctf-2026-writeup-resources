from pathlib import Path
import struct,collections,numpy as np
b=Path('bbx_sd.img').read_bytes();area=164*512
start=b.index(b'START\n',area)+6
p=start;out=[];temps=[];blocks=[]
while p+7<len(b):
 if b[p:p+2]==b'\xa5F':
  tick,n=struct.unpack_from('<IB',b,p+2)
  if not 1<=n<=32:break
  end=p+7+12*n
  if end>len(b):break
  samples=np.frombuffer(b[p+7:end],dtype='<i2').reshape(n,6).copy()
  blocks.append((p,tick,n));out.extend((tick,*v) for v in samples);p=end
 elif b[p:p+2]==b'\xa5T':
  tick,temp=struct.unpack_from('<Ih',b,p+2);temps.append((tick,temp));p+=8
 else:break
print('continuous parse until',p,'relative',p-area,'next',b[p:p+32].hex())
print('F blocks',len(blocks),'samples',len(out),'temperatures',len(temps))
print('blocks first',blocks[:5]);print('blocks near declared end',[v for v in blocks if abs(v[0]-(area+446090))<400]);print('last blocks',blocks[-15:])
a=np.array(out,dtype='int64');np.save('samples_contiguous.npy',a)
print('ticks range',a[:,0].min(),a[:,0].max(),'negative jumps',[(blocks[i-1],blocks[i]) for i in range(1,len(blocks)) if blocks[i][1]<blocks[i-1][1]][:10])
for i in range(1,7):print('col',i,'range',a[:,i].min(),a[:,i].max(),'quantiles',np.percentile(a[:,i],[0,1,25,50,75,99,100]))
clipped=np.any((a[:,1:4]==-32768)|(a[:,1:4]==32767),axis=1)
print('clipped first',a[clipped][:10])
print('tempsfirstlast',temps[:5],temps[-5:])
