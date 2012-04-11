#!/usr/bin/env python
#
# Copyright 2012 Andy Isaacson <adi@hexapodia.org>
#
# This program is free software, licensed under the GNU GPL version 2.
# Please see the file COPYING for additional information.

import os, sys, time, getopt

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

def read_cpu_stats():
    '''Returns a tuple of integers denoting CPU statistics from /proc/stat.
    The list consists of:

     0 CPU user centiseconds
     1 CPU nice centiseconds
     2 CPU system centiseconds
     3 CPU idle centiseconds
     4 CPU iowait centiseconds
     5 CPU steal centiseconds
     6 interrupts
     7 context switches
     8 processes created
     9 processes currently running
    10 processes currently blocked
    '''
    v = [x.split() for x in open('/proc/stat')]
    v = dict([(x[0], x[1:]) for x in v])
    f = lambda k: int(v[k][0])
    cpu = map(int, v['cpu'])
    return (cpu[0], cpu[1], cpu[2], cpu[3], cpu[4], cpu[5],
            f('intr'), f('ctxt'), f('processes'),
            f('procs_running'), f('procs_blocked'))

def read_mem_stats():
    '''Returns a tuple of integers denoting memory statistics from
    /proc/meminfo.  The list consists of:

    0 Free
    1 Buffers
    2 Cached
    3 SwapCached
    4 Active
    5 Mlocked
    6 Dirty
    7 Writeback
    8 PageTables
    9 Bounce
    10 WritebackTmp
    '''
    keys = str.split('''MemFree Buffers Cached SwapCached Active Mlocked Dirty
                        Writeback PageTables Bounce WritebackTmp''')
    v = [x.split() for x in open('/proc/meminfo')]
    v = dict([(x[0][:-1], x[1]) for x in v])
    return map(lambda k: int(v[k]), keys)

def enumerate_blockdevs():
    '''Returns a list of strings naming block devices in /sys/class/block.
    Partitions (which contain a 'partition' pseudofile) are not included.
    '''
    d = '/sys/class/block'
    r = []
    for b in os.listdir(d):
        try:
            os.stat('%s/%s/partition' % (d, b))
        except OSError, e:
            # found a non-partition blockdev!
            r.append(b)
    return r

def read_blockdev_stats(b):
    '''Given the name of a blockdev, returns a list of integers denoting IO
    statistics from /sys/class/block/<b>/stat.  If the blockdev does not
    exist (perhaps due to hotunplug), returns None.

    The list consists of:

     0 reads completed
     1 reads merged
     2 sectors read
     3 time spent reading (ms)
     4 writes completed
     5 writes merged
     6 sectors written
     7 time spent writing (ms)
     8 IOs currently in progress
     9 time spent doing IOs (ms)
    10 weighted time spent doing IOs (ms)
    '''
    try:
        f = open('/sys/class/block/%s/stat' % b)
    except IOError, e:
        return None
    return [int(i) for i in f.read().split()]

delay = 1

(opts, args) = getopt.getopt(sys.argv[1:], 'w:')
for (o, v) in opts:
    if o == '-w':
        delay = float(v)

if len(args) == 0:
    blockdevs = sorted(enumerate_blockdevs())
else:
    blockdevs = [i.split('/')[-1] for i in args]

lastcpu = None
lastblkdev = {}

cpuhdr = 'ru bl intr ctxsw usr nic sys idl iow stl   free buff cach actv mlck drty wrbk'
cpufmt = '%2d %2d %4d %5d %3d %3d %3d %3d %3d %3d   %4d %4d %4d %4d %4d %4d %4d'
bdhdr = 'dev     rd rMB   wr wMB  io% avgms depth'
bdfmt = '%-5s %4d %3d %4d %3d %3d%% %5d %3d'
print cpuhdr
while True:
    t0 = time.time()
    cpu = read_cpu_stats()
    mem = read_mem_stats()
    if lastcpu:
        cpud = map(lambda a,b: a-b, cpu, lastcpu)
    else:
        cpud = cpu
    lastcpu = cpu
    bd = [(b, read_blockdev_stats(b)) for b in blockdevs]
    o=[]
    o.append('')
    o.append(cpuhdr)
                  #     ru       bl     intr    ctxsw      usr      nic
    o.append(cpufmt % (cpu[9], cpu[10], cpud[6], cpud[7], cpud[0], cpud[1],
                  # sys      idl      iow      stl
                    cpud[2], cpud[3], cpud[4], cpud[5],
                  # free           buff           cach           actv
                    mem[0] / 1024, mem[1] / 1024, mem[2] / 1024, mem[4] / 1024,
                  # mlck           drty           wrbk
                    mem[5] / 1024, mem[6] / 1024, mem[7] / 1024))

    if len(bd) > 0 and bd[0][1]:
        o.append(bdhdr)
        for d,v in bd:
            if v:
                x = v
                prev = lastblkdev.get(d)
                if prev:
                    x = map(lambda a,b:a-b, v, prev)
                numio = x[0] + x[4]
                o.append(bdfmt % (d[-5:], x[0], x[2] / 1024, x[4], x[6] / 1024,
                               round(x[9] / 10.), x[10] / (numio or 1), v[8]))
                lastblkdev[d] = v
    sys.stdout.write('\n'.join(o) + '\n')
    sys.stdout.flush()

    ts = ' [%.0f]' % (1e6 * (time.time() - t0))

    time.sleep(delay)
