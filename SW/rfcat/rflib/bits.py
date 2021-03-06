import struct


def wtfo(string):
    outstr = []
    bitlen = len(outstr) * 8
    for x in range(8):
        outstr.append(shiftString(string, x))

    string = strBitReverse(string)
    for x in range(8):
        outstr.append(shiftString(string, x))

    return outstr

def strBitReverse(string):
    # FIXME: this is really dependent upon python's number system.  large strings will not convert well.  
    # FIXME: break up array of 8-bit numbers and bit-swap in the array
    num = 0
    bits = len(string)*8
    # convert to MSB number
    for x in range(len(string)):
        ch = string[x]
        #num |= (ord(ch)<<(8*x))        # this is LSB
        num <<= 8
        num |= ord(ch)

    print (hex(num))
    rnum = bitReverse(num, bits)
    print (hex(rnum))

    # convert back from MSB number to string
    out = []
    for x in range(len(string)):
        out.append(chr(rnum&0xff))
        rnum >>= 8
    out.reverse()
    print(''.join(out).encode('hex'))
    return ''.join(out)


        
        

def bitReverse(num, bitcnt):
    newnum = 0
    for idx in range(bitcnt):
        newnum <<= 1
        newnum |= num&1
        num    >>= 1
    return newnum

def shiftString(string, bits):
    carry = 0
    news = []
    for x in xrange(len(string)-1):
        newc = ((ord(string[x]) << bits) + (ord(string[x+1]) >> (8-bits))) & 0xff
        news.append("%c"%newc)
    newc = (ord(string[-1])<<bits) & 0xff
    news.append("%c"%newc)
    return "".join(news)

def getNextByte_feedbackRegister7bitsMSB():
    '''
    this returns a byte of a 7-bit feedback register stemming off bits 4 and 7
    the register is 7 bits long, but we return a more usable 8bits (ie. 
    '''
    global fbRegister

    retval = 0
    for x in range(8):      #MSB, 
        retval <<= 1
        retval |= (fbRegister >> 6)         # start with bit 7
        nb = ( ( fbRegister>>3) ^ (fbRegister>>6)) &1 
        fbRegister = ( ( fbRegister << 1 )   |   nb ) & 0x7f # do shifting
        #print "retval: %x  fbRegister: %x  bit7: %x  nb: %x" % (retval, fbRegister, (fbRegister>>6), nb)

    return retval

def getNextByte_feedbackRegister7bitsLSB():
    '''
    this returns a byte of a 7-bit feedback register stemming off bits 4 and 7
    the register is 7 bits long, but we return a more usable 8bits (ie. 
    '''
    global fbRegister

    retval = 0
    for x in range(8):      #MSB, 
        retval >>= 1
        retval |= ((fbRegister << 1)&0x80)         # start with bit 7

        nb = ( ( fbRegister>>3) ^ (fbRegister>>6)) &1 
        fbRegister = ( ( fbRegister << 1 )   |   nb ) & 0x7f # do shifting
        #print "retval: %x  fbRegister: %x  bit7: %x  nb: %x" % (retval, fbRegister, (fbRegister>>6), nb)

    return retval


def whitenData(data, seed=0xffff, getNextByte=getNextByte_feedbackRegister7bitsMSB):
    global fbRegister
    fbRegister = seed

    carry = 0
    news = []
    for x in xrange(len(data)-1):
        newc = ((ord(data[x]) ^ getNextByte() ) & 0xff)
        news.append("%c"%newc)
    return "".join(news)

def findSyncWord(byts, sensitivity=4, minpreamble=2): 
        '''
        seek SyncWords from a raw bitstream.  
        assumes we capture at least two (more likely 3 or more) preamble bytes
        '''
        possDwords = []
        # find the preamble (if any)
        while True:         # keep searching through string until we don't find any more preamble bits to pick on
            sbyts = byts
            pidx = byts.find("\xaa"*minpreamble)
            if pidx == -1:
                pidx = byts.find("\x55"*minpreamble)
                byts = shiftString(byts, 1)

            if pidx == -1:
                return possDwords
            
            # chop off the nonsense before the preamble
            sbyts = byts[pidx:]
            #print "sbyts: %s" % repr(sbyts)
            
            # find the definite end of the preamble (ie. it may be sooner, but we know this is the end)
            while (sbyts[0] == '\xaa' and len(sbyts)>2):
                sbyts = sbyts[1:]
            
            #print "sbyts: %s" % repr(sbyts)
            # now we look at the next 16 bits to narrow the possibilities to 8
            # at this point we have no hints at bit-alignment aside from 0xaa vs 0x55
            dwbits, = struct.unpack(">H", sbyts[:2])
            #print "sbyts: %s" % repr(sbyts)
            #print "dwbits: %s" % repr(dwbits)
            if len(sbyts)>=3:
                bitcnt = 0
                #  bits1 =      aaaaaaaaaaaaaaaabbbbbbbbbbbbbbbb
                #  bits2 =                      bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
                bits1, = struct.unpack(">H", sbyts[:2])
                bits1 = bits1 | (ord('\xaa') << 16)
                bits1 = bits1 | (ord('\xaa') << 24)
                bits1 <<= 8
                bits1 |= (ord(sbyts[2]) )
                #print "bits: %x" % (bits1)

                bit = (5 * 8) - 2  # bytes times bits/byte          #FIXME: MAGIC NUMBERS!?
                while (bits1 & (3<<bit) == (2<<bit)):
                    bit -= 2
                #print "bit = %d" % bit
                bits1 >>= (bit-16)
                #while (bits1 & 0x30000 != 0x20000): # now we align the end of the 101010 pattern with the beginning of the dword
                #    bits1 >>= 2
                #print "bits: %x" % (bits1)
                
                bitcount = min( 2 * sensitivity, 17 ) 
                for frontbits in xrange( bitcount ):            # with so many bit-inverted systems, let's not assume we know anything about the bit-arrangement.  \x55\x55 could be a perfectly reasonable preamble.
                    poss = (bits1 >> frontbits) & 0xffff
                    if not poss in possDwords:
                        possDwords.append(poss)
            byts = byts[pidx+1:]
        
        return possDwords

def findSyncWordDoubled(byts):
        possDwords = []
        # find the preamble (if any)
        bitoff = 0
        pidx = byts.find("\xaa\xaa")
        if pidx == -1:
            pidx = byts.find("\55\x55")
            bitoff = 1
        if pidx == -1:
            return []

        # chop off the nonsense before the preamble
        byts = byts[pidx:]

        # find the definite end of the preamble (ie. it may be sooner, but we know this is the end)
        while (byts[0] == ('\xaa', '\x55')[bitoff] and len(byts)>2):
            byts = byts[1:]

        # now we look at the next 16 bits to narrow the possibilities to 8
        # at this point we have no hints at bit-alignment
        dwbits, = struct.unpack(">H", byts[:2])
        if len(byts)>=5:
            bitcnt = 0
            #  bits1 =      aaaaaaaaaaaaaaaabbbbbbbbbbbbbbbb
            #  bits2 =                      bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
            bits1, = struct.unpack(">H", byts[:2])
            bits1 = bits1 | (ord(('\xaa','\x55')[bitoff]) << 16)
            bits1 = bits1 | (ord(('\xaa','\x55')[bitoff]) << 24)
            bits1 <<= 8
            bits1 |= (ord(byts[2]) )
            bits1 >>= bitoff

            bits2, = struct.unpack(">L", byts[:4])
            bits2 <<= 8
            bits2 |= (ord(byts[4]) )
            bits2 >>= bitoff
            

            frontbits = 0
            for frontbits in xrange(16, 40, 2):    #FIXME: if this doesn't work, try 16, then 18+frontbits
                dwb1 = (bits1 >> (frontbits)) & 3
                dwb2 = (bits2 >> (frontbits)) & 3
                print "\tfrontbits: %d \t\t dwb1: %s dwb2: %s" % (frontbits, bin(bits1 >> (frontbits)), bin(bits2 >> (frontbits)))
                if dwb2 != dwb1:
                    break

            # frontbits now represents our unknowns...  let's go from the other side now
            for tailbits in xrange(16, -1, -2):
                dwb1 = (bits1 >> (tailbits)) & 3
                dwb2 = (bits2 >> (tailbits)) & 3
                print "\ttailbits: %d\t\t dwb1: %s dwb2: %s" % (tailbits, bin(bits1 >> (tailbits)), bin(bits2 >> (tailbits)))
                if dwb2 != dwb1:
                    tailbits += 2
                    break

            # now, if we have a double syncword, iinm, tailbits + frontbits >= 16
            print "frontbits: %d\t\t tailbits: %d, bits: %s " % (frontbits, tailbits, bin((bits2>>tailbits & 0xffffffff)))
            if (frontbits + tailbits >= 16):
                tbits = bits2 >> (tailbits&0xffff)
                tbits &= (0xffffffff)
                print "tbits: %x" % tbits

                poss = tbits&0xffffffff
                if poss not in possDwords:
                    possDwords.append(poss)
            else:
                pass
                # FIXME: what if we *don't* have a double-sync word?  then we stop at AAblah or 55blah and take the next word?

            possDwords.reverse()
        return possDwords

#def test():

def visBits(data):
    pass



def getBit(data, bit):
    idx = bit / 8
    bidx = bit % 8
    char = data[idx]
    return (ord(char)>>(7-bidx)) & 1



def detectRepeatPatterns(data, size=64, minEntropy=.07):
    #FIXME: convert strings to bit arrays before comparing.
    c1 = 0
    c2 = 0
    d1 = 0
    p1 = 0
    mask = (1<<size) - 1
    bitlen = 8*len(data)

    while p1 < (bitlen-size-8):
        d1 <<= 1
        d1 |= getBit(data, p1)
        d1 &= mask
        #print bin(d1)

        if c1 < (size):
            p1 += 1
            c1 += 1
            continue

        d2 = 0
        p2 = p1+size
        while p2 < (bitlen):
            d2 <<= 1
            d2 |= getBit(data, p2)
            d2 &= mask
            #print bin(d2)

            if c2 < (size):
                p2 += 1
                c2 += 1
                continue

            if d1 == d2 and d1 > 0:
                s1 = p1 - size
                s2 = p2 - size
                print "s1: %d\t  p1: %d\t  " % (s1, p1)
                print "s2: %d\t  p2: %d\t  " % (s2, p2)
                # complete the pattern until the numbers differ or meet
                while True:
                    p1 += 1
                    p2 += 1
                    #print "s1: %d\t  p1: %d\t  " % (s1, p1)
                    #print "s2: %d\t  p2: %d\t  " % (s2, p2)
                    if p2 >= bitlen:
                        break

                    b1 = getBit(data,p1)
                    b2 = getBit(data,p2)

                    if p1 == s2 or b1 != b2:
                        break

                length = p1 - s1
                c2 = 0
                p2 -= size

                bitSection, ent = bitSectString(data, s1, s1+length)
                if ent > minEntropy:
                    print "success:"
                    print "  * bit idx1: %4d (%4d bits) - '%s' %s" % (s1, length, bin(d1), bitSection.encode("hex"))
                    print "  * bit idx2: %4d (%4d bits) - '%s'" % (s2, length, bin(d2))
            #else:
            #    print "  * idx1: %d - '%s'  * idx2: %d - '%s'" % (p1, d1, p2, d2)
            p2 += 1
        p1 += 1


def bitSectString(string, startbit, endbit):
    '''
    bitsects a string... ie. chops out the bits from the middle of the string
    returns the new string and the entropy (ratio of 0:1)
    '''
    ones = 0
    zeros = 0
    entropy = [zeros, ones]

    s = ''
    bit = startbit

    Bidx = bit / 8
    bidx = (bit % 8)

    while bit < endbit:

        byte1 = ord( string[Bidx] )
        try:
            byte2 = ord( string[Bidx+1] )
        except IndexError:
            byte2 = 0

        byte = (byte1 << bidx) & 0xff
        byte |= (byte2 >> (8-bidx))
        #calculate entropy over the byte
        for bi in range(8):
            b = (byte>>bi) & 1
            entropy[b] += 1

        bit += 8
        Bidx += 1

        if bit > endbit:
            diff = bit-endbit
            mask = ~ ( (1<<diff) - 1 )
            byte &= mask

        s += chr(byte)
    
    ent = (min(entropy)+1.0) / (max(entropy)+1)
    #print "entropy: %f" % ent
    return (s, ent)


        
def genBitArray(string, startbit, endbit):
    '''
    bitsects a string... ie. chops out the bits from the middle of the string
    returns the new string and the entropy (ratio of 0:1)
    '''
    binStr, ent = bitSectString(string, startbit, endbit)

    s = []
    for byte in binStr:
        byte = ord(byte)
        for bitx in range(7, -1, -1):
            bit = (byte>>bitx) & 1
            s.append(bit)

    return (s, ent)


chars_top = [
        " ", #000
        " ", #001
        "^", #010
        "/", #011
        " ", #100
        " ", #101
        "\\",#110
        "-", #111
        ]

chars_mid = [
        " ", #000
        "|", #001
        "#", #010
        " ", #011
        "|", #100
        "#", #101
        " ", #110
        " ", #110
        ]

chars_bot = [
        "-", #000
        "/", #001
        " ", #010
        " ", #011
        "\\",#100
        "V", #101
        " ", #110
        " ", #110
        ]


def reprBitArray(bitAry, width=194):
    top = []
    mid = []
    bot = []

    arylen = len(bitAry)
    # top line
    #FIXME: UGGGGLY and kinda broken.
    fraction = 1.0 * arylen/width
    expand = [bitAry[int(x*fraction)] for x in xrange(width)]

    for bindex in xrange(width):
        bits = 0
        if bindex>0:
            bits += (expand[bindex-1]) << (2)
        bits += (expand[bindex]) << (1)
        if bindex < width-1:
            bits += (expand[bindex+1])

        top.append( chars_top[ bits ] )
        mid.append( chars_mid[ bits ] )
        bot.append( chars_bot[ bits ] )

    tops = "".join(top)
    mids = "".join(mid)
    bots = "".join(bot)
    return "\n".join([tops, mids, bots])

def invertBits(data):
    output = []
    ldata = len(data)
    off = 0

    if ldata&1:
        output.append( chr( ord( data[0] ) ^ 0xff) )
        off = 1

    if ldata&2:
        output.append( struct.pack( "<H", struct.unpack( "<H", data[off:off+2] )[0] ^ 0xffff) )
        off += 2

    #method 1
    #for idx in xrange( off, ldata, 4):
    #    output.append( struct.pack( "<I", struct.unpack( "<I", data[idx:idx+4] )[0] & 0xffff) )

    #method2
    count = ldata / 4
    #print ldata, count
    numlist = struct.unpack( "<%dI" % count, data[off:] )
    modlist = [ struct.pack("<L", (x^0xffffffff) ) for x in numlist ]
    output.extend(modlist)

    return ''.join(output)

