"""Summarise what a container tried to reach, from a pcap taken inside its network namespace.
Counts new outbound TCP connections (SYN without ACK), UDP flows and DNS questions sent by the
container's own addresses. Host-originated multicast (IPv6 RA/mDNS from the bridge) is ignored.
Usage: python3 egress_summary.py OWN_IP_PREFIX file.pcap [...]  (runs tcpdump -r; needs read access)"""
import collections, re, subprocess, sys
prefix, files = sys.argv[1], sys.argv[2:]
syn, udp, dns = collections.Counter(), collections.Counter(), collections.Counter()
for f in files:
    out = subprocess.run(['tcpdump', '-nn', '-r', f], capture_output=True, text=True).stdout
    for line in out.splitlines():
        m = re.search(r' IP6? (\S+) > (\S+?):? (.*)$', line)
        if not m: continue
        src, dst, rest = m.groups()
        if dst.startswith('127.0.0.11.'): dns['(query to Docker resolver; name not decoded)'] += 1; continue
        if not src.startswith(prefix): continue
        dhost, _, dport = dst.rpartition('.')
        if rest.startswith('Flags [S]'): syn[f'{dhost}:{dport}'] += 1
        elif 'UDP' in rest or re.match(r'\d+\+? ', rest): 
            udp[f'{dhost}:{dport}'] += 1
            q = re.search(r' (A|AAAA)\? (\S+) ', rest)
            if q: dns[q.group(2)] += 1
print('new TCP connections by destination:', dict(syn) or 'none')
print('UDP packets by destination:', dict(udp) or 'none')
print('DNS query packets:', dict(dns) or 'none')
