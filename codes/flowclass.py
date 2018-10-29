class pkt:
  def __init__(self,seq,seglen,ack,time,direction,flag,window):
    self.seq = seq
    self.seglen = seglen
    self.ack = ack
    self.time = time
    self.direction = direction
    self.flag = flag
    self.window = window
