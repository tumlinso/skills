#!/usr/bin/env python3
"""CPU identities for the atlas. Does NOT emulate GPU rounding or synchronization."""
from __future__ import annotations
import argparse,json,math,random
from fractions import Fraction
from pathlib import Path
MASK=(1<<32)-1

def lop3(a:int,b:int,c:int,lut:int)->int:
    out=0
    for i in range(8):
        if (lut>>i)&1:
            out|=(a if i&4 else ~a)&(b if i&2 else ~b)&(c if i&1 else ~c)
    return out&MASK

def planes(xs:list[int],width:int)->list[int]:
    return [sum(((x>>j)&1)<<i for i,x in enumerate(xs)) for j in range(width)]

def unpack_planes(ps:list[int],n:int)->list[int]:
    return [sum(((p>>i)&1)<<j for j,p in enumerate(ps)) for i in range(n)]

def byte_perm_reference(a:int,b:int,sel:int,sign_mode:bool=False)->int:
    data=a|(b<<32);out=0
    for i in range(4):
        nib=(sel>>(4*i))&15
        v=(data>>(8*(nib&7)))&255
        if sign_mode and nib&8:v=255 if v&128 else 0
        out|=v<<(8*i)
    return out

def dot4(a:int,b:int,signed:bool)->int:
    aa=[(a>>(8*i))&255 for i in range(4)]
    bb=[(b>>(8*i))&255 for i in range(4)]
    if signed:
        aa=[x-256 if x&128 else x for x in aa]
        bb=[x-256 if x&128 else x for x in bb]
    return sum(x*y for x,y in zip(aa,bb))

def carry_save(words:list[int])->dict[int,int]:
    buckets={0:list(words)};j=0
    while j<=max(buckets,default=0):
        q=buckets.setdefault(j,[])
        while len(q)>=2:
            a=q.pop();b=q.pop();c=q.pop() if q else 0
            q.append((a^b^c)&MASK)
            buckets.setdefault(j+1,[]).append(((a&b)|(a&c)|(b&c))&MASK)
        j+=1
    return {k:v[0] for k,v in buckets.items() if v}

def run()->dict:
    rng=random.Random(10070);groups=[];count=0
    def check(name:str,fn):
        nonlocal count
        before=count
        def ok(value:bool):
            nonlocal count
            if not value:raise AssertionError(name)
            count+=1
        fn(ok)
        groups.append({'name':name,'assertions':count-before,'passed':True})
    def truth(ok):
        for a in (0,1):
            for b in (0,1):
                for c in (0,1):
                    ok((lop3(a,b,c,0x96)&1)==(a^b^c))
                    ok((lop3(a,b,c,0xe8)&1)==((a+b+c)>=2))
                    ok((lop3(a,b,c,0xca)&1)==(b if a else c))
        for _ in range(1000):
            a,b,c=[rng.getrandbits(32) for _ in range(3)]
            s=lop3(a,b,c,0x96);carry=lop3(a,b,c,0xe8)
            ok(s+2*carry==a+b+c)
            ok(lop3(a,b,c,0xca)==((a&b)|(~a&c))&MASK)
    check('LOP3 truth tables and word full-adder',truth)
    def transpose(ok):
        for k in (1,2,3,5,8,16):
            for n in range(33):
                xs=[rng.randrange(1<<k) for _ in range(n)]
                ok(unpack_planes(planes(xs,k),n)==xs)
    check('Bitplane transpose including empty and partial groups',transpose)
    def sequence(ok):
        for n in range(33):
            for _ in range(12):
                x=[rng.randrange(4) for _ in range(n)];y=[rng.randrange(4) for _ in range(n)]
                x0,x1=planes(x,2);y0,y1=planes(y,2);valid=(1<<n)-1
                eq=~((x0^y0)|(x1^y1))&valid
                ok(eq==sum((a==b)<<i for i,(a,b) in enumerate(zip(x,y))))
    check('Two-plane sequence equality and valid masks',sequence)
    def rank(ok):
        for _ in range(300):
            m=rng.getrandbits(32);members=[i for i in range(32) if m>>i&1]
            for k,l in enumerate(members):ok((m&((1<<l)-1)).bit_count()==k)
            # Abstract rank/select only: not a model of CUDA __fns base/offset semantics.
            for k in range(len(members)):ok([i for i in range(32) if m>>i&1][k]==members[k])
    check('Abstract mask rank/select (not __fns emulation)',rank)
    def bytecheck(ok):
        a=0x03020100;b=0x87868584
        for i in range(8):
            sel=sum(i<<(4*j) for j in range(4));v=((a|(b<<32))>>(8*i))&255
            ok(byte_perm_reference(a,b,sel)==v*0x01010101)
            ssel=sum((i|8)<<(4*j) for j in range(4))
            ok(byte_perm_reference(a,b,ssel,True)==(MASK if v&128 else 0))
        for _ in range(100):
            table=[rng.randrange(256) for _ in range(128)]
            packed=[sum(table[4*l+j]<<(8*j) for j in range(4)) for l in range(32)]
            for i in range(128):ok(((packed[i>>2]>>(8*(i&3)))&255)==table[i])
    check('Byte selection,distinct sign mode,and warp lookup algebra',bytecheck)
    def dp(ok):
        for signed in (False,True):
            for _ in range(500):
                xs=[rng.randrange(-20,21) if signed else rng.randrange(41) for _ in range(4)]
                ys=[rng.randrange(-20,21) if signed else rng.randrange(41) for _ in range(4)]
                a=sum((x&255)<<(8*i) for i,x in enumerate(xs));b=sum((x&255)<<(8*i) for i,x in enumerate(ys))
                ok(dot4(a,b,signed)==sum(x*y for x,y in zip(xs,ys)))
    check('Packed signed/unsigned short-dot identity',dp)
    def convolution(ok):
        for _ in range(500):
            a=[rng.randrange(4) for _ in range(4)];b=[rng.randrange(4) for _ in range(4)];g=6
            prod=sum(x<<(g*i) for i,x in enumerate(a))*sum(x<<(g*i) for i,x in enumerate(b))
            expected=[sum(a[i]*b[k-i] for i in range(4) if 0<=k-i<4) for k in range(7)]
            ok(all(v<64 for v in expected))
            ok([(prod>>(g*k))&63 for k in range(7)]==expected)
            ok(prod<1<<64)
        a=b=[7,7];g=3;prod=sum(x<<(g*i) for i,x in enumerate(a))*sum(x<<(g*i) for i,x in enumerate(b))
        ok([(prod>>(g*k))&7 for k in range(3)]!=[49,98,49])
    check('Guard-digit convolution and deliberate carry-failure control',convolution)
    def mapping(ok):
        for group in range(4):
            lanes=list(range(4*group,4*group+4))+list(range(16+4*group,20+4*group))
            A=[((l%4)+4*(l>=16),i) for l in lanes for i in range(4)]
            B=[(i,(l%4)+4*(l>=16)) for l in lanes for i in range(4)]
            C=[((l&1)+(i&2)+4*(l>=16),(i&4)+(l&2)+(i&1)) for l in lanes for i in range(8)]
            ok(len(set(A))==32 and set(A)=={(r,c) for r in range(8) for c in range(4)})
            ok(len(set(B))==32 and set(B)=={(r,c) for r in range(4) for c in range(8)})
            ok(len(set(C))==64 and set(C)=={(r,c) for r in range(8) for c in range(8)})
    check('Explicit sm70 m8n8k4 coordinate bijections',mapping)
    def matrices(ok):
        for _ in range(100):
            x=[rng.randrange(-8,9) for _ in range(8)]
            ok([sum((j<=i)*x[j] for j in range(8)) for i in range(8)]==[sum(x[:i+1]) for i in range(8)])
            a=[rng.getrandbits(12) for _ in range(8)];b=[rng.getrandbits(12) for _ in range(8)]
            ok(all(sum(((u>>k)&1)*((v>>k)&1) for k in range(12))==(u&v).bit_count() for u in a for v in b))
        H=[[1 if (i&j).bit_count()%2==0 else -1 for j in range(8)] for i in range(8)]
        ok(all(sum(H[i][k]*H[j][k] for k in range(8))==(8 if i==j else 0) for i in range(8) for j in range(8)))
    check('Prefix,binary intersection,and Hadamard identities',matrices)
    def graph(ok):
        for _ in range(100):
            ns=[rng.getrandbits(32) for _ in range(32)];f=rng.getrandbits(32)
            nxt=sum(bool(n&f)<<i for i,n in enumerate(ns))
            ref=sum(any(((ns[i]>>j)&1) and ((f>>j)&1) for j in range(32))<<i for i in range(32))
            ok(nxt==ref)
    check('Incoming-neighbor register graph',graph)
    def fsm(ok):
        for _ in range(200):
            xs=[rng.randrange(4) for _ in range(32)];u=rng.getrandbits(32);q0,q1=planes(xs,2)
            s0=q0^u;carry=q0&u;s1=q1^carry;overflow=q1&carry
            out=unpack_planes([s0|overflow,s1|overflow],32)
            ok(out==[min(3,x+((u>>i)&1)) for i,x in enumerate(xs)])
    check('Two-bit saturating state machine',fsm)
    def csa(ok):
        for n in (0,1,2,3,7,17,33):
            for _ in range(30):
                ws=[rng.getrandbits(32) for _ in range(n)];out=carry_save(ws)
                ok(all(sum(((w>>i)&1) for w in ws)==sum(((v>>i)&1)*(1<<j) for j,v in out.items()) for i in range(32)))
                ok(sum(w.bit_count() for w in ws)==sum((1<<j)*v.bit_count() for j,v in out.items()))
    check('Carry-save per-bit multiplicity and total population',csa)
    def monotone(ok):
        for _ in range(200):
            ws=[rng.getrandbits(32) for _ in range(10)];ref=0
            for w in ws:ref|=w
            shuffled=ws+ws[::2];rng.shuffle(shuffled);out=0
            for w in shuffled:out|=w
            ok(out==ref)
    check('Idempotent OR with reordered duplicate proposals',monotone)
    def expansion(ok):
        for _ in range(200):
            ah,al,bh,bl=[Fraction(rng.randrange(-30,31),8) for _ in range(4)]
            approx=ah*bh+ah*bl+al*bh
            ok((ah+al)*(bh+bl)-approx==al*bl)
            ok(abs((ah+al)*(bh+bl)-approx)<=abs(al)*abs(bl))
    check('Exact high/low algebra and omitted residual',expansion)
    def approx(ok):
        for _ in range(1000):
            a=rng.uniform(-5,5);h=rng.uniform(.01,.3);t=rng.random();x=a+t*h
            interpolated=(1-t)*math.sin(a)+t*math.sin(a+h)
            ok(abs(interpolated-math.sin(x))<=h*h/8+1e-14)
            true=rng.uniform(-10,10);eps=rng.uniform(0,1);est=true+rng.uniform(-eps,eps);tau=rng.uniform(-10,10)
            if est-eps>=tau:ok(true>=tau)
            elif est+eps<tau:ok(true<tau)
            else:ok(True) # Explicit exact-refinement branch.
    check('Ideal interpolation bound and certified interval decisions',approx)
    return {'status':'PASS','seed':10070,'groups':groups,'assertions':count,'gpu_measured':False,'cuda_compiled':False,'limitations':['CPU identities only.','No simulation of Volta tensor rounding.','No GPU participation,memory-model or progress validation.','Abstract rank/select is not __fns emulation.','PTX sign permutation is separated from CUDA byte_perm semantics.']}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'ledger'/'CPU_TEST_RESULTS.json');args=p.parse_args()
    result=run();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'test_groups':len(result['groups']),'assertions':result['assertions'],'gpu_measured':False}))
if __name__=='__main__':main()
