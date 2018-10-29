import datetime
import cPickle
from flowclass import *
from PcapReader import *


def hasFlags(flags,seglen):
  if seglen!=0:
    return 0
  else:
    if flags&0x012==0x012 or flags&0x001==0x001 or flags&0x004==0x004:
      return 1
    elif flags&0x012==0x002:
      return 2  
    else:
      return 0

  
def writefiles(flowdict,temp_time):
  poplist = []
  
  for flowname in flowdict:
    if flowdict[flowname][-1].time <= temp_time:
      poplist.append(flowname)
      ff = open(flowname+".txt","ab")
      cPickle.dump(flowdict[flowname],ff)
      ff.close()

  for flowname in poplist:
    flowdict.pop(flowname)

  poplist = []

def split(pcapfile):
  f = PcapReader(pcapfile)
  j = 0
  p = f.read_packet()
  flownamelist = []
  flowdict = {}
  underline = '_'
  
  while(p!=None):

    time, seq, ack, seglen, flags, src, dst, sport, dport, win = p
    j += 1
    
    flowname = underline.join([src,dst,str(sport),str(dport)])
        
    if flowname in flowdict:
      flowdict[flowname].append(pkt(seq,seglen,ack,time,1,hasFlags(flags,seglen),win))
    else:
      flowname_rev = underline.join([dst,src,str(dport),str(sport)])
      if flowname_rev in flowdict:
        flowdict[flowname_rev].append(pkt(seq,seglen,ack,time,0,hasFlags(flags,seglen),win))
      else:
        if flowname in flownamelist:
          flowdict[flowname] = [pkt(seq,seglen,ack,time,1,hasFlags(flags,seglen),win)]
        elif flowname_rev in flownamelist:
          flowdict[flowname_rev] = [pkt(seq,seglen,ack,time,0,hasFlags(flags,seglen),win)]
        else:
          flownamelist.append(flowname)
          flowdict[flowname] = [pkt(seq,seglen,ack,time,1,hasFlags(flags,seglen),win)]
        
    if j == 900000:
      temp_time = time
      
    if j == 1000000:
      writefiles(flowdict,temp_time)
      j = 0
      
    p = f.read_packet()

  f.close()
  
  writefiles(flowdict,time)
  flowdict = {}
  return flownamelist

