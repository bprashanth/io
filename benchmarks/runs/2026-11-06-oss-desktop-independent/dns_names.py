"""List DNS question names (and answers' A records) in a pcap, including queries Docker's
embedded resolver receives on a remapped loopback port, which tcpdump does not decode.
Pure stdlib pcap reader (Linux cooked v2 or Ethernet). Usage: python3 dns_names.py file.pcap"""
import collections, struct, sys
def qname(b, off):
    labels = []
    while True:
        n = b[off]
        if n == 0: return '.'.join(labels), off + 1
        if n & 0xC0 == 0xC0:
            ptr = struct.unpack('!H', b[off:off+2])[0] & 0x3FFF
            name, _ = qname(b, ptr); labels.append(name); return '.'.join(labels), off + 2
        labels.append(b[off+1:off+1+n].decode('ascii', 'replace')); off += 1 + n
def packets(path):
    f = open(path, 'rb'); gh = f.read(24)
    endian = '<' if gh[:4] == b'\xd4\xc3\xb2\xa1' else '>'
    link = struct.unpack(endian + 'I', gh[20:24])[0]
    while (h := f.read(16)) and len(h) == 16:
        ts, _, incl, _ = struct.unpack(endian + 'IIII', h); data = f.read(incl)
        off = 20 if link == 276 else 14 if link == 1 else 16
        proto = struct.unpack('!H', data[0:2])[0] if link == 276 else struct.unpack('!H', data[12:14])[0] if link == 1 else struct.unpack('!H', data[14:16])[0]
        if proto != 0x0800: continue
        ip = data[off:]; ihl = (ip[0] & 15) * 4
        if ip[9] != 17: continue
        udp = ip[ihl:]; yield ts, udp[8:], struct.unpack('!HH', udp[:4])
qs, ans = collections.Counter(), collections.defaultdict(set)
for ts, p, ports in packets(sys.argv[1]):
    if len(p) < 12: continue
    flags, qd, an = struct.unpack('!HHH', p[2:8])
    if qd != 1: continue
    try:
        name, off = qname(p, 12); off += 4
        if not flags & 0x8000: qs[name] += 1; continue
        for _ in range(an):
            _, off2 = qname(p, off); typ, _, _, rdl = struct.unpack('!HHIH', p[off2:off2+10])
            if typ == 1: ans[name].add('.'.join(map(str, p[off2+10:off2+14])))
            off = off2 + 10 + rdl
    except Exception: pass
for n, c in sorted(qs.items(), key=lambda x: -x[1]):
    print(f'{c:4d}  {n}  {sorted(ans.get(n, []))[:4]}')
