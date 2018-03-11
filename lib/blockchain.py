# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@ecdsa.org
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import os
import threading

from . import util
from . import bitcoin
from .bitcoin import *

MAX_TARGET = 0x00000000FFFF0000000000000000000000000000000000000000000000000000

'''
global info
'''
BITCOINX_FORK_HEIGHT = 494784
BITCOINX_HDR_SIZE = 141
BITCOINX_HDR_EXT_SIZE = 140 + 1347

# (245 + 1) *2016 = 495936 this chunk contains first forked header
BITCOINX_CHUNK_FORK_INDEX = 245


def get_header_size(height):
    if (height >= BITCOINX_FORK_HEIGHT):
        return (BITCOINX_HDR_EXT_SIZE)
    else:
        return (BITCOINX_HDR_SIZE)

# now all are fixed header size
def get_total_hdr_size(start_height, end_height):
    '''
    if (start_height >= BITCOINX_FORK_HEIGHT):
        return ((end_height - start_height) * BITCOINX_HDR_EXT_SIZE)

    if (end_height < BITCOINX_FORK_HEIGHT):
        return ((end_height - start_height) * BITCOINX_HDR_SIZE)

    return (((BITCOINX_FORK_HEIGHT - start_height) * BITCOINX_HDR_SIZE) +
            (end_height - BITCOINX_FORK_HEIGHT) * BITCOINX_HDR_EXT_SIZE)
    '''
    return ((end_height - start_height) * BITCOINX_HDR_SIZE)

#  XXX nonce is 32 bytes and reversed. tried to be the same with server electrumx
def serialize_header(res):
    print_error("height " + str(res.get('block_height')) + " nonce " + str(res.get('nonce')))
    nonce = res.get('nonce')
    if len(nonce) < 64:
        if (len(nonce) % 2 != 0):
            nonce = "0" + nonce

        while (len(nonce) <= 64):
            nonce = "00" + nonce

    '''
    we ignore the solution here. it is too long. electrum header doesn't 
    field. But can not calculate header hash without it.
    '''
    if (res.get('block_height') >= BITCOINX_FORK_HEIGHT):
        s = int_to_hex(res.get('version'), 4) \
            + rev_hex(res.get('prev_block_hash')) \
            + rev_hex(res.get('merkle_root')) \
            + int_to_hex(int(res.get('block_height')),4) \
            + '00000000000000000000000000000000000000000000000000000000' \
            + int_to_hex(int(res.get('timestamp')), 4) \
            + int_to_hex(int(res.get('bits')), 4) \
            + rev_hex(res.get('nonce')) \
            + '00'
    else:
        s = int_to_hex(res.get('version'), 4) \
            + rev_hex(res.get('prev_block_hash')) \
            + rev_hex(res.get('merkle_root')) \
            + '0000000000000000000000000000000000000000000000000000000000000000' \
            + int_to_hex(int(res.get('timestamp')), 4) \
            + int_to_hex(int(res.get('bits')), 4) \
            + rev_hex(res.get('nonce')) \
            + '00'

    return s

def deserialize_header(s, height, from_disk):
    hex_to_int = lambda s1: int('0x' + bh2u(s1[::-1]), 16)
    h = {}
    h['version'] = hex_to_int(s[0:4])
    h['prev_block_hash'] = hash_encode(s[4:36])
    h['merkle_root'] = hash_encode(s[36:68])

    h['timestamp'] = hex_to_int(s[100:104])
    h['bits'] = hex_to_int(s[104:108])

    nonce = hash_encode(s[108:140])
    if len(nonce) < 64:
        if (len(nonce) % 2 != 0):
            nonce = "0" + nonce

        while (len(nonce) <= 64):
            nonce = "00" + nonce

    h['nonce'] = nonce

    solution = ""
    h['solution'] = solution
    h['block_height'] = height
    print_error("Deserialize header " + str(h))
    return h


# XXX after height BITCOINX_FORK_HEIGHT, without solution, can not calculate hash  
def hash_header(header):
    if header is None:
        return '0' * 64
    if header.get('prev_block_hash') is None:
        header['prev_block_hash'] = '00' * 32

    serialized_hdr = serialize_header(header);
    print_error(" serialized header " + str(serialized_hdr))
    if int(header.get('block_height')) >= BITCOINX_FORK_HEIGHT:
        #hash is meaningless because we can not calculate hash
        #return hash_encode(Hash(bfh(serialized_hdr)))
        return hash_encode(bfh(serialized_hdr[136:200]))
    else:
        # version + pre_hash + merkle_root + ts + bits + nonce
        # return hash_encode(Hash(bfh(serialized_hdr)))
        return hash_encode(Hash(bfh(serialized_hdr[:136] + serialized_hdr[200:216] +
                                    serialized_hdr[216:224])))

blockchains = {}

def read_blockchains(config):
    blockchains[0] = Blockchain(config, 0, None)
    fdir = os.path.join(util.get_headers_dir(config), 'forks')
    if not os.path.exists(fdir):
        os.mkdir(fdir)
    l = filter(lambda x: x.startswith('fork_'), os.listdir(fdir))
    l = sorted(l, key=lambda x: int(x.split('_')[1]))
    for filename in l:
        checkpoint = int(filename.split('_')[2])
        parent_id = int(filename.split('_')[1])
        b = Blockchain(config, checkpoint, parent_id)
        blockchains[b.checkpoint] = b
    return blockchains


def check_header(header):
    if type(header) is not dict:
        return False
    for b in blockchains.values():
        if b.check_header(header):
            return b
    return False


def can_connect(header):
    for b in blockchains.values():
        if b.can_connect(header):
            return b
    return False


class Blockchain(util.PrintError):
    """
    Manages blockchain headers and their verification
    """

    def __init__(self, config, checkpoint, parent_id):
        self.config = config
        self.catch_up = None  # interface catching up
        self.checkpoint = checkpoint
        self.parent_id = parent_id
        self.lock = threading.Lock()
        with self.lock:
            self.update_size()

    def parent(self):
        return blockchains[self.parent_id]

    def get_max_child(self):
        children = list(filter(lambda y: y.parent_id == self.checkpoint, blockchains.values()))
        return max([x.checkpoint for x in children]) if children else None

    def get_checkpoint(self):
        mc = self.get_max_child()
        return mc if mc is not None else self.checkpoint

    def get_branch_size(self):
        return self.height() - self.get_checkpoint() + 1

    def get_name(self):
        return self.get_hash(self.get_checkpoint()).lstrip('00')[0:10]

    def check_header(self, header):
        print_error("check_header:  header " + str(header))

        # XXX sometimes server does not send solution within header
        header_hash = hash_header(header)
        height = header.get('block_height')
        if (height >= BITCOINX_FORK_HEIGHT):
            return (self.header_in_disk(height))

        print_error("header_hash:" + str(header_hash) + "get_hash:" + str(self.get_hash(height)))
        return header_hash == self.get_hash(height)

    def fork(parent, header):
        checkpoint = header.get('block_height')
        self = Blockchain(parent.config, checkpoint, parent.checkpoint)
        open(self.path(), 'w+').close()
        self.save_header(header)
        return self

    def height(self):
        return self.checkpoint + self.size() - 1

    def size(self):
        with self.lock:
            return self._size

    def update_size(self):
        p = self.path()
        self._size = os.path.getsize(p) // BITCOINX_HDR_SIZE if os.path.exists(p) else 0

    def verify_header(self, header, prev_header, bits, target):
        if bitcoin.NetworkConstants.TESTNET:
            return

        if(header.get('block_height') >= BITCOINX_FORK_HEIGHT) :
            # XXX: blocks are already consensused. just need light verification. 
            # TBD: can not get hash now, verify?
            return

        prev_hash = hash_header(prev_header)
        _hash = hash_header(header)

        if prev_hash != header.get('prev_block_hash'):
            raise BaseException("prev hash mismatch: %s vs %s" % (prev_hash, header.get('prev_block_hash')))
        if bits != header.get('bits'):
            raise BaseException("bits mismatch: %s vs %s" % (bits, header.get('bits')))
        print_error("hash: " + _hash + " prev_hash: " + prev_hash)
        if int('0x' + _hash, 16) > target:
            raise BaseException("insufficient proof of work: %s vs target %s" % (int('0x' + _hash, 16), target))

    def verify_chunk(self, index, data):
        check_bits = True
        prev_header = None
        print_error("verify chunk: index " + str(index))
        if index != 0:
            prev_header = self.read_header(index * 2016 - 1)
        print_error("prev_hash: " + str(prev_header))

        bits, target = self.get_target(index)
        print_error("target: " + str(target) + " bits: " + str(bits))

        pos = 0
        count = 0
        while (pos + get_header_size(index * 2016 + count)) <= len(data):
            header_size = get_header_size(index * 2016 + count)
            print_error("header_size: " + str(header_size) + " pos " + str(pos))
            # header_size = BITCOINX_HDR_SIZE
            raw_header = data[pos: pos + header_size]

            header = deserialize_header(raw_header, index * 2016 + count, False)

            self.verify_header(header, prev_header, bits, target)

            prev_header = header
            count = count + 1
            pos = pos + header_size

    def path(self):
        d = util.get_headers_dir(self.config)
        filename = 'blockchain_headers' if self.parent_id is None else os.path.join('forks', 'fork_%d_%d' % (
        self.parent_id, self.checkpoint))
        return os.path.join(d, filename)

    def save_chunk(self, index, chunk):
        filename = self.path()
        d = get_total_hdr_size(self.checkpoint, (index) * 2016)
        print_error("save_chunk: filename" + filename + " index " + str(index) + " check_point " + str(
            self.checkpoint) + " d " + str(d))
        if d < 0:
            chunk = chunk[-d:]
            d = 0

        if (index < BITCOINX_CHUNK_FORK_INDEX) :
            self.write(chunk, d)
        else :

            pos = 0
            count = 0
            while (pos + get_header_size(index * 2016 + count)) <= len(chunk):
                header_size = get_header_size(index * 2016 + count)
                print_error("header_size: " + str(header_size) + " pos " + str(pos))

                raw_header = chunk[pos: pos + BITCOINX_HDR_SIZE]
                d = get_total_hdr_size(self.checkpoint, index * 2016 + count)
                self.write(raw_header, d)

                count = count + 1
                pos = pos + header_size

    def swap_with_parent(self):
        if self.parent_id is None:
            return
        parent_branch_size = self.parent().height() - self.checkpoint + 1
        if parent_branch_size >= self.size():
            return
        self.print_error("swap", self.checkpoint, self.parent_id)
        parent_id = self.parent_id
        checkpoint = self.checkpoint
        parent = self.parent()
        with open(self.path(), 'rb') as f:
            my_data = f.read()
        with open(parent.path(), 'rb') as f:
            f.seek(get_total_hdr_size(parent.checkpoint, checkpoint))
            parent_data = f.read(self.checkpoint, self.parent().height())
        self.write(parent_data, 0)
        parent.write(my_data, get_total_hdr_size(parent.checkpoint, checkpoint))
        # store file path
        for b in blockchains.values():
            b.old_path = b.path()
        # swap parameters
        self.parent_id = parent.parent_id;
        parent.parent_id = parent_id
        self.checkpoint = parent.checkpoint;
        parent.checkpoint = checkpoint
        self._size = parent._size;
        parent._size = parent_branch_size
        # move files
        for b in blockchains.values():
            if b in [self, parent]: continue
            if b.old_path != b.path():
                self.print_error("renaming", b.old_path, b.path())
                os.rename(b.old_path, b.path())
        # update pointers
        blockchains[self.checkpoint] = self
        blockchains[parent.checkpoint] = parent

    def write(self, data, offset):
        filename = self.path()
        with self.lock:
            with open(filename, 'rb+') as f:
                if offset != get_total_hdr_size(0, self._size):
                    f.seek(offset)
                    f.truncate()
                f.seek(offset)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            self.update_size()

    def save_header(self, header):
        delta = header.get('block_height') - self.checkpoint
        data = bfh(serialize_header(header))
        assert delta == self.size()
        assert len(data) == BITCOINX_HDR_SIZE

        self.write(data, get_total_hdr_size(0, delta))

        self.swap_with_parent()

    # XXX This is alter way to check header in file.
    def header_in_disk(self, height) :

        if (height < self.checkpoint) :
            return True

        offset = get_total_hdr_size(self.checkpoint, height + 1);
        name = self.path()
        if (offset <= os.path.getsize(name)) :
            return True
        else :
            return False 

    def read_header(self, height):
        assert self.parent_id != self.checkpoint
        if height < 0:
            return
        if height < self.checkpoint:
            return self.parent().read_header(height)
        if height > self.height():
            return

        if not self.header_in_disk(height) :
            return

        delta = height - self.checkpoint
        name = self.path()
        if os.path.exists(name):
            with open(name, 'rb') as f:
                f.seek(get_total_hdr_size(self.checkpoint, height))
                h = f.read(get_header_size(height))
        return deserialize_header(h, height, True)

    def get_hash(self, height):
        return hash_header(self.read_header(height))

    def BIP9(self, height, flag):
        v = self.read_header(height)['version']
        return ((v & 0xE0000000) == 0x20000000) and ((v & flag) == flag)

    def segwit_support(self, N=144):
        h = self.local_height
        return sum([self.BIP9(h - i, 2) for i in range(N)]) * 10000 / N / 100.

    def get_target(self, index):
        if bitcoin.NetworkConstants.TESTNET:
            return 0, 0
        if index == 0:
            return 0x1d00ffff, MAX_TARGET

        first = self.read_header((index - 1) * 2016)
        last = self.read_header(index * 2016 - 1)
        print_error("first: " + str(first) + " last: " + str(last))

        # bits to target
        bits = last.get('bits')
        bitsN = (bits >> 24) & 0xff

        if (last.get('block_height') <= BITCOINX_FORK_HEIGHT) :
            if not (bitsN >= 0x03 and bitsN <= 0x1d):
                raise BaseException("First part of bits should be in [0x03, 0x1d]")
            bitsBase = bits & 0xffffff
            if not (bitsBase >= 0x8000 and bitsBase <= 0x7fffff):
                raise BaseException("Second part of bits should be in [0x8000, 0x7fffff]")
        bitsBase = bits & 0xffffff


        target = bitsBase << (8 * (bitsN - 3))
        # new target
        nActualTimespan = last.get('timestamp') - first.get('timestamp')
        nTargetTimespan = 14 * 24 * 60 * 60
        nActualTimespan = max(nActualTimespan, nTargetTimespan // 4)
        nActualTimespan = min(nActualTimespan, nTargetTimespan * 4)
        new_target = min(MAX_TARGET, (target * nActualTimespan) // nTargetTimespan)
        # convert new target to bits
        c = ("%064x" % new_target)[2:]
        while c[:2] == '00' and len(c) > 6:
            c = c[2:]
        bitsN, bitsBase = len(c) // 2, int('0x' + c[:6], 16)
        if bitsBase >= 0x800000:
            bitsN += 1
            bitsBase >>= 8
        new_bits = bitsN << 24 | bitsBase
        return new_bits, bitsBase << (8 * (bitsN - 3))

    def can_connect(self, header, check_height=True):
        height = header['block_height']
        print_error("can_connect: header " + str(header))
        if check_height and self.height() != height - 1:
            return False
        if height == 0:
            #print_error("genesis hash: " + hash_header(header))
            return hash_header(header) == bitcoin.NetworkConstants.GENESIS
        previous_header = self.read_header(height - 1)
        if not previous_header:
            return False

        prev_hash = hash_header(previous_header)

        #print_error("height:" + str(height) + "hash from prev_header:" + str(prev_hash) + "current header prev hash:" + str(header.get('prev_block_hash')))

        if (height < BITCOINX_FORK_HEIGHT) :
            if prev_hash != header.get('prev_block_hash'):
                return False
        else :
            print_error("block height " + str(height) + " no prev hash comparsion")

        index = height // 2016
        bits, target = self.get_target(index)

        try:
            self.verify_header(header, previous_header, bits, target)
        except:
            return False
        return True

    def connect_chunk(self, idx, hexdata):
        try:
            data = bfh(hexdata)
            self.print_error("validate chunk %d" % idx)
            self.verify_chunk(idx, data)
            self.print_error("validated chunk %d" % idx)
            self.save_chunk(idx, data)
            return True
        except BaseException as e:
            self.print_error('verify_chunk failed', str(e))
            return False
