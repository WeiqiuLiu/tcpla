import sys  
import socket  
import struct  
import pcap


class PcapReader:

    def __init__(self, filename):
        
        # Read 24-bytes pcap header
        try:
            self.f = pcap.pcapObject(filename)
        except:
            self.f = pcap.pcap(filename)
          
    def __iter__(self):
        return self

    def read_packet(self):
        
        
        try:
            t = self.f.next()
            # read IP header  
            data = t[1][14:34]
            (vl, tos, tot_len, id, frag_off, ttl, protocol, check, saddr, daddr) = struct.unpack(">ssHHHssHLL", data)  
            iphdrlen1 = ord(vl) & 0x0F   
            iphdrlen1 *= 4
          
            # read TCP standard header  
            tcpdata = t[1][14+iphdrlen1:34+iphdrlen1]
            (sport, dport, seq, ack, pad1, win, check, urgp) = struct.unpack(">HHLLHHHH", tcpdata)  
            tcphdrlen = pad1 & 0xF000  
            tcphdrlen = tcphdrlen >> 12  
            tcphdrlen = tcphdrlen*4
            
            flags = pad1 & 0x0FFF
            seglen = tot_len-iphdrlen1-tcphdrlen
            
            src = socket.inet_ntoa(struct.pack('I',socket.htonl(saddr)))
            dst = socket.inet_ntoa(struct.pack('I',socket.htonl(daddr)))

            return t[0], seq, ack, seglen, flags, src, dst, sport, dport, win
        except:
            return None
        
    def close(self):
        return self.f.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tracback):
        self.close()
