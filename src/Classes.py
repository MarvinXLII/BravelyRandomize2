import sys
import struct
import io
import hashlib

class TYPE:
    def getInt8(self, value):
        return struct.pack("<b", value)

    def getUInt8(self, value):
        return struct.pack("<B", value)

    def getInt32(self, value):
        return struct.pack("<l", value)

    def getUInt32(self, value):
        return struct.pack("<L", value)

    def getInt64(self, value):
        return struct.pack("<q", value)

    def getUInt64(self, value):
        return struct.pack("<Q", value)

    def getFloat(self, value):
        return struct.pack("<f", value)

    def getString(self, string):
        tmp = string.encode() + b'\x00'
        for t in tmp:
            if t & 0x80:
                st = string.encode(encoding='UTF-16')[2:] + b'\x00\x00'
                size = self.getInt32(-int(len(st)/2))
                return st, size
        return tmp, self.getInt32(len(tmp))

    def getSHA(self, sha):
        return sha.encode() + b'\x00'



class FILE(TYPE):
    def __init__(self, data):
        self.data = io.BytesIO(data)

    def readInt8(self):
        return struct.unpack("<b", self.data.read(1))[0]

    def readUInt8(self):
        return struct.unpack("<B", self.data.read(1))[0]

    def readInt32(self):
        return struct.unpack("<l", self.data.read(4))[0]

    def readUInt32(self):
        return struct.unpack("<L", self.data.read(4))[0]

    def readInt64(self):
        return struct.unpack("<q", self.data.read(8))[0]

    def readUInt64(self):
        return struct.unpack("<Q", self.data.read(8))[0]

    def readFloat(self):
        return struct.unpack("<f", self.data.read(4))[0]

    def readString(self, size):
        if size < 0:
            string = self.data.read(-2*size).decode(encoding='UTF-16')
        else:
            string = self.data.read(size).decode()
        return string[:-1]

    def readSHA(self):
        sha = self.data.read(0x20).decode()
        assert self.data.read(1) == b'\x00'
        return sha


class FloatProperty(TYPE):
    def __init__(self, file):
        self.dataType = 'FloatProperty'
        assert file.readInt64() == 4
        file.data.seek(1, 1)
        self.value = file.readFloat()

    def build(self):
        tmp = self.getInt64(4)
        tmp += bytearray([0])
        tmp += self.getFloat(self.value)
        return tmp


class StrProperty(TYPE):
    def __init__(self, file):
        self.dataType = 'StrProperty'
        size = file.readInt64()
        file.data.seek(1, 1)
        self.string = file.data.read(size)
        assert size == len(self.string)

    def build(self):
        tmp = self.getInt64(len(self.string))
        tmp += bytearray([0])
        tmp += self.string
        return tmp


class EnumProperty(TYPE):
    def __init__(self, file, uasset):
        self.dataType = 'EnumProperty'
        self.uasset = uasset
        assert file.readInt64() == 8
        self.value0 = uasset.getName(file.readInt64())
        assert file.readInt8() == 0
        self.value = uasset.getName(file.readInt64())

    def build(self):
        tmp = self.getInt64(8)
        tmp += self.getInt64(self.uasset.getIndex(self.value0))
        tmp += bytearray([0])
        tmp += self.getInt64(self.uasset.getIndex(self.value))
        return tmp


class BoolProperty(TYPE):
    def __init__(self, file):
        self.dataType = 'BoolProperty'
        assert file.readInt64() == 0
        self.value = file.readInt8()
        file.data.seek(1, 1)

    def build(self):
        tmp = bytearray([0]*8)
        tmp += self.getInt8(self.value)
        tmp += bytearray([0])
        return tmp


class NameProperty(TYPE):
    def __init__(self, file, uasset):
        self.dataType = 'NameProperty'
        self.uasset = uasset
        assert file.readInt64() == 8
        file.data.seek(1, 1)
        self.name = self.uasset.getName(file.readInt64())

    def build(self):
        tmp = self.getInt64(8)
        tmp += bytearray([0])
        tmp += self.getInt64(self.uasset.getIndex(self.name))
        return tmp


class IntProperty(TYPE):
    def __init__(self, file):
        self.dataType = 'IntProperty'
        assert file.readInt64() == 4
        file.data.seek(1, 1)
        self.value = file.readInt32()

    def build(self):
        tmp = self.getInt64(4)
        tmp += bytearray([0])
        tmp += self.getInt32(self.value)
        return tmp


class UInt32Property(TYPE):
    def __init__(self, file):
        self.dataType = 'UInt32Property'
        assert file.readInt64() == 4
        file.data.seek(1, 1)
        self.value = self.readUInt32()

    def build(self):
        tmp = self.getInt64(4)
        tmp += bytearray([0])
        tmp += self.getUInt32(self.value)
        return tmp


class ByteProperty(TYPE):
    def __init__(self, file):
        self.dataType = 'ByteProperty'
        assert file.readInt64() == 1
        self.none = file.readInt64()
        file.data.seek(1, 1)
        self.value = file.readInt8()

    def build(self):
        tmp = self.getInt64(1)
        tmp += self.getInt64(self.none)
        tmp += bytearray([0])
        tmp += self.getInt8(self.value)
        return tmp

# MonsterDataAsset: Include a bunch of floats I won't need to modify.
# Just lost struct as a bytearray
class StructProperty(TYPE):
    def __init__(self, file):
        self.dataType = 'StructProperty'
        self.size = file.readInt64()
        self.value = file.readInt64()
        file.data.seek(17, 1)
        self.structData = file.data.read(self.size)

    def build(self):
        tmp = self.getInt64(self.size)
        tmp += self.getInt64(self.value)
        tmp += bytearray([0]*17)
        tmp += self.structData
        return tmp


class TextProperty(TYPE):
    def __init__(self, file):
        self.dataType = 'TextProperty'
        self.size = file.readInt64()
        file.data.seek(5, 1)
        if file.readInt8() == -1:
            assert file.readInt32() == 0
            self.string = ''
        else:
            size = file.readInt32()
            self.namespace = file.readString(size)
            assert file.readInt32() == 0x21
            self.sha = file.readSHA()
            size = file.readInt32()
            self.string = file.readString(size)

    def build(self):
        tmp = bytearray([0]*4)
        if not self.string:
            tmp += bytearray([0xff]+[0]*4)
            return self.getInt64(9) + bytearray([0]) + tmp

        tmp += bytearray([0])
        string, size = self.getString(self.namespace)
        tmp += size + string
        tmp += self.getInt32(0x21)
        tmp += self.getSHA(self.sha)
        string, size = self.getString(self.string)
        tmp += size + string

        size = len(tmp)
        return self.getInt64(size) + bytearray([0]) + tmp


class ArrayProperty(TYPE):
    def __init__(self, file, uasset, callbackLoad, callbackBuild):
        self.uasset = uasset
        self.none = uasset.getIndex('None')
        self.callbackBuild = callbackBuild
        self.dataType = 'ArrayProperty'
        self.size = file.readInt64()
        self.prop = self.uasset.getName(file.readInt64())
        file.data.seek(1, 1)
        num = file.readInt32()
        self.array = []

        if self.prop == 'IntProperty':
            assert self.size == 4 + 4*num
            for _ in range(num):
                self.array.append(file.readInt32())
            return

        if self.prop == 'EnumProperty':
            assert self.size == 4 + 8*num
            for _ in range(num):
                self.array.append(self.uasset.getName(file.readInt64()))
            return

        if self.prop == 'StructProperty':
            self.name = self.uasset.getName(file.readInt64())
            assert self.uasset.getName(file.readInt64()) == 'StructProperty'
            self.structSize = file.readInt64()
            self.structType = self.uasset.getName(file.readInt64())
            file.data.seek(17, 1)
            for _ in range(num):
                self.array.append(callbackLoad())
            return

        sys.exit(f"Load array property does not allow for {prop} types!")

    def build(self):
        tmp = bytearray(self.getInt64(self.size))
        tmp += self.getInt64(self.uasset.getIndex(self.prop))
        tmp += bytearray([0])
        tmp += self.getInt32(len(self.array))
        if self.prop == 'IntProperty':
            for ai in self.array:
                tmp += self.getInt32(ai)
        elif self.prop == 'EnumProperty':
            for ai in self.array:
                tmp += self.getInt64(self.uasset.getIndex(ai))
        elif self.prop == 'StructProperty':
            tmp += self.getInt64(self.uasset.getIndex(self.name))
            tmp += self.getInt64(self.uasset.getIndex('StructProperty'))
            tmp += self.getInt64(self.structSize)
            tmp += self.getInt64(self.uasset.getIndex(self.structType))
            tmp += bytearray([0]*17)
            for ai in self.array:
                tmp += self.callbackBuild(ai)
                tmp += self.getInt64(self.none)
        return tmp


