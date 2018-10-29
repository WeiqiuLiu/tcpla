from split import *
import os


flag_retransmission = 0x001
flag_likely_retransmission = 0x002
flag_reordering = 0x004
flag_dupack = 0x008
flag_loss = 0x010
flag_probably_loss = 0x020
flag_detected = 0x040
flag_previous_loss = 0x080

def readflow(flowname):
  flowlist = []
  ff = open(flowname+".txt","rb")
  while os.path.getsize(flowname+".txt")!=ff.tell():
    flowlist.extend(cPickle.load(ff))
  ff.close()
  os.remove(flowname+".txt")
  return flowlist


def new_flow_flag_list(flow):
  ffl = []
  for i in range(len(flow)):
    ffl.append(0x000)
  return ffl

def setflag(ffl,num,flag):
  ffl[num] = ffl[num]|flag

def estimate_RTT(flow):
  forward_rtt = []
  backward_rtt = []
  for n in range(len(flow)-1):
    if len(forward_rtt)==0 and flow[n].direction == 1 and flow[n+1].direction == 0 and (flow[n+1].seglen == 0 or flow[n+1].flag == 1) and ((flow[n].seq+1==flow[n+1].ack and flow[n].flag == 2) or (flow[n].seq+flow[n].seglen==flow[n+1].ack and flow[n].seglen != 0)):
      temp_rtt = flow[n+1].time - flow[n].time
      forward_rtt.append(temp_rtt)
    elif len(backward_rtt)==0 and flow[n].direction == 0 and flow[n+1].direction == 1 and flow[n+1].seglen == 0 and ((flow[n].seq+1==flow[n+1].ack and flow[n].flag == 1) or (flow[n].seq+flow[n].seglen==flow[n+1].ack and flow[n].seglen != 0)):
      temp_rtt = flow[n+1].time - flow[n].time
      backward_rtt.append(temp_rtt)
  if len(forward_rtt)>0 and len(backward_rtt)>0:
    forward_average_rtt = float(sum(forward_rtt))/len(forward_rtt)
    backward_average_rtt = float(sum(backward_rtt))/len(backward_rtt)
    return forward_average_rtt + backward_average_rtt
  else:
    return 0

def process(flow,flowname):
  flow_flag_list = new_flow_flag_list(flow)
  number = 0
  estimateRTT = estimate_RTT(flow)
  forward_rs = -1
  backward_rs = -1
  forward_ra = -1
  backward_ra = -1
  forward_ack=-1
  backward_ack=-1
  #print estimateRTT
  forward_seq = [[-1,-1]]
  backward_seq = [[-1,-1]]
  for packet in flow:
    #print packet
    if packet.flag == 1 or packet.flag == 2:
      packet.seglen = 1

    seglen = packet.seglen
    rs = packet.seq
    ra = packet.ack
    if packet.flag == 2 and ((packet.direction==1 and forward_seq[0][0]!=packet.seq)or(packet.direction==0 and backward_seq[0][0]!=packet.seq)):
      forward_seq=[[-1,-1]]
      forward_ack=0
      backward_seq=[[-1,-1]]
      backward_ack=0
      fwd_window = 0
      bwd_window = 0
      
    #print seglen
    if packet.direction == 1:
      if forward_rs != -1:
        if packet.seq - forward_rs>=0:
          packet.seq -= forward_rs
        else:
          packet.seq = 4294967296 + packet.seq - forward_rs
      else:
        forward_rs = packet.seq
        packet.seq = 0

      if backward_rs != -1:
        if packet.ack - backward_rs >= 0:
          packet.ack -= backward_rs
        else:
          packet.ack = 4294967296 + packet.ack - backward_rs
      else:
        if packet.ack != 0:
          backward_rs = packet.ack
          packet.ack = 0
        
      rs = packet.seq
      ra = packet.ack
      
      if rs>forward_seq[-1][1] and seglen!=0:
        #print 'normal packet'
        if rs==forward_seq[-1][1]+1:
          forward_seq[-1][1] = rs + seglen - 1
        elif forward_seq == [[-1,-1]]:
          forward_seq[0] = [rs,rs + seglen - 1]
        else: 
          forward_seq.append([rs,rs+seglen-1])
      elif rs<=forward_seq[-1][1] and seglen!=0:
        #print 'out-of-order packet'
        retran_detection(flow,forward_seq,rs,seglen,flow_flag_list,number,estimateRTT);

      if forward_ack<ra:
        forward_ack = ra
        #print forward_ack
      elif forward_ack == ra and packet.flag == 0 and seglen == 0 and packet.window == fwd_window:
        #print 'dup ack'
        setflag(flow_flag_list,number,flag_dupack)
        #print ra

      fwd_window = packet.window
          
    else:#backward
      if backward_rs != -1:
        if packet.seq - backward_rs>=0:
          packet.seq -= backward_rs
        else:
          packet.seq = 4294967296 + packet.seq - backward_rs
      else:
        backward_rs = packet.seq
        packet.seq = 0

      if forward_rs != -1:
        if packet.ack - forward_rs >= 0:
          packet.ack -= forward_rs
        else:
          packet.ack = 4294967296 + packet.ack - forward_rs
      else:
        if packet.ack != 0:
          forward_rs = packet.ack
          packet.ack = 0
        
      rs = packet.seq
      ra = packet.ack

      if rs>backward_seq[-1][1] and seglen!=0:
        #print 'normal packet'
        if rs==backward_seq[-1][1]+1:
          backward_seq[-1][1] = rs + seglen - 1
        elif backward_seq == [[-1,-1]]:
          backward_seq[0] = [rs,rs + seglen - 1]
        else:
          backward_seq.append([rs,rs+seglen-1])
      elif rs<=backward_seq[-1][1] and seglen!=0:
        #print 'out-of-order packet'
        retran_detection(flow,backward_seq,rs,seglen,flow_flag_list,number,estimateRTT)
        
      if backward_ack<ra:
        backward_ack = ra
        #print backward_ack
      elif backward_ack == ra and packet.flag == 0 and seglen == 0 and bwd_window == packet.window:
        #print 'dup ack'
        setflag(flow_flag_list,number,flag_dupack)
        #print ra

      bwd_window = packet.window
      
    number += 1
  loss_detection(flow,flow_flag_list)
  #print forward_ack
  #print forward_seq
  #print backward_ack
  #print backward_seq
  output_log(flow,flow_flag_list,flowname,estimateRTT)

def loss_detection(flow,ffl):
  l = len(ffl)
  n = 0
  while n<l:
    if islikelyRetran(ffl[n]):
      setflag(ffl,n,flag_previous_loss)
    elif isRetran(ffl[n]):
      highest_ack_before,ack_location = find_highest_ack_before(flow,n)
      if (highest_ack_before >= flow[n].seq + flow[n].seglen):
        previous_pkt_location = find_previous_pkt(flow,n)
        if previous_pkt_location>ack_location:
          setflag(ffl,previous_pkt_location,flag_probably_loss)#loss
      else:
        previous_pkt_location = find_previous_pkt(flow,n)
        previous_pkt = flow[previous_pkt_location]
        next_greater_ack_location = find_next_greater_ack(flow,n,previous_pkt)
        next_greater_ack = flow[next_greater_ack_location]
        if connection_detection(n,next_greater_ack_location,flow,previous_pkt_location,ffl):
          if has_lower_ack_detection(n,next_greater_ack_location,flow,previous_pkt,ffl):
            setflag(ffl,previous_pkt_location,flag_loss)#loss
            #print 'loss'
          else:
            setflag(ffl,previous_pkt_location,flag_probably_loss)#probably loss
            #print 'probably loss'
        #else:
          #print 'no loss'
    n += 1

def has_lower_ack_detection(n,m,flow,pkt,ffl):
  nn = n
  mm = m
  while nn < mm:
    if flow[nn].direction != flow[n].direction:
      if flow[nn].ack > pkt.seq and flow[nn].ack < pkt.seq+pkt.seglen:
        return True
    nn += 1
  return False

def connection_detection(n,m,flow,pkt_location,ffl):#pkt_location shi previous
  nn = n#pkt location
  mm = m#ack location
  pkt = flow[pkt_location]
  retran_temp_list=[]
  #print pkt.time-flow[0].time
  while nn <= mm:
    if flow[nn].direction == flow[n].direction:
      s = flow[nn].seq
      sl = flow[nn].seglen
      if isRetran(ffl[nn]) and hasNewseq(retran_temp_list,s,sl) and (not hasRepeatseq(retran_temp_list,s,sl)) and pkt_location == find_previous_pkt(flow,nn):#
        addrange(retran_temp_list,s,sl)
        #setflag(ffl,nn,flag_detected)
      elif isRetran(ffl[nn]) and hasNewseq(retran_temp_list,s,sl) and hasRepeatseq([[flow[pkt_location].seq,flow[pkt_location].seq+flow[pkt_location].seglen-1]],s,sl):
        update_seqlist(retran_temp_list,s,sl)
        #setflag(ffl,nn,flag_detected)
    nn += 1
    
  if len(retran_temp_list)==1 and retran_temp_list[0][0] <= pkt.seq and retran_temp_list[0][1] >= (pkt.seq+pkt.seglen-1):
    return True
  else:
    return False

def addrange(seqlist,s,l):
  temp = 0
  
  if len(seqlist) == 0:
    seqlist.append([s,s+l-1])
  elif s == seqlist[-1][1]+1:
    seqlist[-1][1] = s+l-1
  elif s < seqlist[-1][0]:
    temp = len(seqlist)-1
    if temp == 0:
      seqlist.insert(temp,[s,s+l-1])
    elif temp > 0:
      while temp >= 1:
        temp -= 1
        if s > seqlist[temp][1]:
          seqlist.insert(temp+1,[s,s+l-1])
          break
        elif temp == 0:
          seqlist.insert(temp,[s,s+l-1])
  simplify_seqlist(seqlist)

def find_next_greater_ack(flow,n,previous_pkt):
  temp = n
  while temp<len(flow)-1:
    temp += 1
    if previous_pkt.direction != flow[temp].direction:
      if flow[temp].ack >= (previous_pkt.seq+previous_pkt.seglen):
        break
  return temp

def find_previous_pkt(flow,n):
  temp = n
  while temp>0:
    temp -= 1
    if flow[temp].seq <= flow[n].seq and flow[temp].seq+flow[temp].seglen>flow[n].seq:
      return temp

def find_highest_ack_before(flow,n):
  temp = n-1
  highest_ack = 0
  number = temp
  while temp >= 0:
    if flow[n].direction!=flow[temp].direction: #and isACK(flow[temp]):
      if highest_ack < flow[temp].ack:
        highest_ack = flow[temp].ack
        number = temp
    temp -= 1
  return highest_ack,number

def output_log(flow,ffl,flowname,rtt):
  outlog.write('\r\n'+flowname+':\r\n')
  outlog.write('estimate RTT: '+str(rtt)+'\r\n\r\n')
  j = 0
  datapktnum = 0
  for i in range(len(ffl)):
    if flow[i].seglen > 0:
      if not isRetran(ffl[i]):
        datapktnum += 1
    if isinnormal(ffl[i]):
      s = 'packet ' + str(i+1)+': '
      
      if isRetran(ffl[i]):
        s += 'retransmission, '
      elif islikelyRetran(ffl[i]):
        s += 'likely retransmission, '
      elif isdupack(ffl[i]):
        s += 'dup ack, '
      elif isreordering(ffl[i]):
        s += 'reordering, '
      if isloss(ffl[i]):
        s += 'this packet lost after captured, '
        j+=1
      elif isprobablyloss(ffl[i]):
        s += 'this packet probably lost after captured, '
        j+=1
      if ispreviousloss(ffl[i]):
        s += 'previous packet probably lost before captured'
        j+=1

      s += '\r\n'
      outlog.write(s)
  #print "In "+str(datapktnum)+" packets, "+str(j)+" packets lost, loss rate: "+str((j+0.0)*100/datapktnum)[0:6]+'%'
  if datapktnum>0:
    outlog.write("\r\nIn "+str(datapktnum)+" packets, "+str(j)+" packets lost, loss rate: "+str((j+0.0)*100/datapktnum)[0:6]+'%\r\n')

def isinnormal(flag):
  if flag&0x0BF!=0x000:
    return True
  else:
    return False

def retran_detection(flow,seqlist,rs,sl,ffl,number,estimateRTT):

  if hasRepeatseq(seqlist,rs,sl):
    setflag(ffl,number,flag_retransmission)
    if hasNewseq(seqlist,rs,sl):
      #print 'retransmission and new seq'
      update_seqlist(seqlist,rs,sl)
    #else:
      #print 'retransmission'
  else:
    #timegapdetection
    timegapdetection(flow,number,estimateRTT,ffl)
    update_seqlist(seqlist,rs,sl)

def update_seqlist(seqlist,rs,sl):
  for n in range(len(seqlist)):
    down = seqlist[n][0]
    up = seqlist[n][1]
    if rs >= down and rs <= up+1:
      seqlist[n][1] = rs + sl - 1
      simplify_seqlist(seqlist)
      break
    elif rs > up+1 and n < len(seqlist)-1:
      if rs < seqlist[n+1][0]:
        seqlist.insert(n+1,[rs,rs+sl-1])
        simplify_seqlist(seqlist)
        break

def simplify_seqlist(sl):
  #for seqrange in seqlist
  l = len(sl)-1
  n = 0
  while n<l:
    if sl[n][1] >= sl[n+1][0]-1:
      if sl[n][1] <= sl[n+1][1]:
        sl[n][1] = sl[n+1][1]
        sl.pop(n+1)
      else:
        sl.pop(n+1)
      l = l-1
    else:
      n = n+1

def timegapdetection(flow,number,rtt,ffl):
  timegap = find_time_gap(flow,number,ffl)
  if timegap <= rtt:
    #print 'reordering'
    setflag(ffl,number,flag_reordering)
  else:
    #print 'likely retransmission'
    setflag(ffl,number,flag_likely_retransmission)

def find_time_gap(flow,number,ffl):
  time1 = flow[number].time
  for i in range(number)[::-1]:
    if flow[i].direction==flow[number].direction and (not isRetran(ffl[i]) and (not isreordering(ffl[i]))and (not islikelyRetran(ffl[i]))):
      time2 = flow[i].time
      break
  return time1-time2

def isRetran(flag):
  if flag&flag_retransmission==flag_retransmission:
    return True
  else:
    return False

def islikelyRetran(flag):
  if flag&flag_likely_retransmission==flag_likely_retransmission:
    return True
  else:
    return False

def isreordering(flag):
  if flag&flag_reordering==flag_reordering:
    return True
  else:
    return False

def isdupack(flag):
  if flag&flag_dupack==flag_dupack:
    return True
  else:
    return False

def isloss(flag):
  if flag&flag_loss==flag_loss:
    return True
  else:
    return False

def isprobablyloss(flag):
  if flag&flag_probably_loss==flag_probably_loss:
    return True
  else:
    return False

def isdetected(flag):
  if flag&flag_detected==flag_detected:
    return True
  else:
    return False

def ispreviousloss(flag):
  if flag&flag_previous_loss==flag_previous_loss:
    return True
  else:
    return False
  
def hasNewseq(seqlist,rs,sl):
  for seqrange in seqlist:
    down = seqrange[0]
    up = seqrange[1]
    if down<=rs and rs+sl-1<=up:
      return False
  return True

def hasRepeatseq(seqlist,rs,sl):
  for seqrange in seqlist:
    down = seqrange[0]
    up = seqrange[1]
    if down<=rs and up>=rs:
      return True
    elif down>rs and rs+sl-1>=down:
      return True
  return False
try:
  flownamelist = split(sys.argv[1])
  #flownamelist = sp[0]
  outlog = open(sys.argv[1].split('.',1)[0]+".log","w")

  for flowname in flownamelist:
    #try:
    #print flowname
    process(readflow(flowname),flowname)
  
    #except:
      #print 'Error occured in '+flowname
  
  outlog.close()
except:
  print 'Error! please check the input'
  print 'Usage: python tcpla.py filename.pcap'

