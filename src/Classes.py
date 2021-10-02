import sys
import struct
import io
import hashlib
from functools import partial
from copy import copy, deepcopy


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

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        for k, v in self.__dict__.items():
            try:
                setattr(result, k, deepcopy(v, memo))
            except:
                setattr(result, k, v) # Don't deepcopy the functions!
        return result


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

    def build(self, uasset):
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

    def build(self, uasset):
        tmp = self.getInt64(len(self.string))
        tmp += bytearray([0])
        tmp += self.string
        return tmp


class EnumProperty(TYPE):
    def __init__(self, file, uasset):
        self.dataType = 'EnumProperty'
        assert file.readInt64() == 8
        self.value0 = uasset.getName(file.readInt64())
        assert file.readInt8() == 0
        self.value = uasset.getName(file.readInt64())

    def build(self, uasset):
        tmp = self.getInt64(8)
        tmp += self.getInt64(uasset.getIndex(self.value0))
        tmp += bytearray([0])
        tmp += self.getInt64(uasset.getIndex(self.value))
        return tmp


class BoolProperty(TYPE):
    def __init__(self, file):
        self.dataType = 'BoolProperty'
        assert file.readInt64() == 0
        self.value = file.readInt8()
        file.data.seek(1, 1)

    def build(self, uasset):
        tmp = bytearray([0]*8)
        tmp += self.getInt8(self.value)
        tmp += bytearray([0])
        return tmp


class NameProperty(TYPE):
    def __init__(self, file, uasset):
        self.dataType = 'NameProperty'
        assert file.readInt64() == 8
        file.data.seek(1, 1)
        self.name = uasset.getName(file.readInt64())

    def build(self, uasset):
        tmp = self.getInt64(8)
        tmp += bytearray([0])
        tmp += self.getInt64(uasset.getIndex(self.name))
        return tmp


class IntProperty(TYPE):
    def __init__(self, file):
        self.dataType = 'IntProperty'
        assert file.readInt64() == 4
        file.data.seek(1, 1)
        self.value = file.readInt32()

    def build(self, uasset):
        tmp = self.getInt64(4)
        tmp += bytearray([0])
        tmp += self.getInt32(self.value)
        return tmp


class UInt32Property(TYPE):
    def __init__(self, file):
        self.dataType = 'UInt32Property'
        assert file.readInt64() == 4
        file.data.seek(1, 1)
        self.value = file.readUInt32()

    def build(self, uasset):
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

    def build(self, uasset):
        tmp = self.getInt64(1)
        tmp += self.getInt64(self.none)
        tmp += bytearray([0])
        tmp += self.getInt8(self.value)
        return tmp


class SoftObjectProperty(TYPE):
    def __init__(self, file):
        self.dataType = 'SoftObjectProperty'
        assert file.readInt64() == 0xc
        file.data.seek(1, 1)
        self.asset = file.data.read(0xc)

    def build(self, uasset):
        tmp = self.getInt64(0xc)
        tmp += bytearray([0])
        tmp += self.asset
        return tmp
        

# MonsterDataAsset: Include a bunch of floats I won't need to modify.
# Just lost struct as a bytearray
class StructProperty(TYPE):
    def __init__(self, file, uasset, callbackLoad, callbackBuild):
        self.none = uasset.getIndex('None')
        self.callbackBuild = callbackBuild
        self.dataType = 'StructProperty'
        self.structSize = file.readInt64()
        self.structType = uasset.getName(file.readInt64())
        file.data.seek(17, 1)
        # self.structData = file.data.read(self.size)
        if self.structType == 'Vector':
            self.x = file.readInt32()
            self.y = file.readInt32()
            self.z = file.readInt32()
        elif self.structType == 'LinearColor':
            self.r = file.readFloat()
            self.g = file.readFloat()
            self.b = file.readFloat()
            self.a = file.readFloat()
        else:
            self.structData = callbackLoad()

    def build(self, uasset):
        if self.structType == 'Vector':
            tmp = self.getInt64(self.structSize)
            tmp += self.getInt64(uasset.getIndex(self.structType))
            tmp += bytearray([0]*17)
            tmp += self.getInt32(self.x)
            tmp += self.getInt32(self.y)
            tmp += self.getInt32(self.z)
            return tmp
        elif self.structType == 'LinearColor':
            tmp = self.getInt64(self.structSize)
            tmp += self.getInt64(uasset.getIndex(self.structType))
            tmp += bytearray([0]*17)
            tmp += self.getFloat(self.r)
            tmp += self.getFloat(self.g)
            tmp += self.getFloat(self.b)
            tmp += self.getFloat(self.a)
            return tmp

        none = uasset.getIndex('None')
        tmp2 = self.callbackBuild(self.structData)
        tmp2 += self.getInt64(none)
        tmp = self.getInt64(len(tmp2))
        tmp += self.getInt64(uasset.getIndex(self.structType))
        tmp += bytearray([0]*17)
        return tmp + tmp2


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

    def build(self, uasset):
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
        self.none = uasset.getIndex('None')
        self.callbackBuild = callbackBuild
        self.dataType = 'ArrayProperty'
        self.size = file.readInt64()
        self.prop = uasset.getName(file.readInt64())
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
                self.array.append(uasset.getName(file.readInt64()))
            return

        if self.prop == 'StructProperty':
            self.name = uasset.getName(file.readInt64())
            assert uasset.getName(file.readInt64()) == 'StructProperty'
            self.structSize = file.readInt64()
            self.structType = uasset.getName(file.readInt64())
            file.data.seek(17, 1)
            for _ in range(num):
                self.array.append(callbackLoad())
            return

        sys.exit(f"Load array property does not allow for {prop} types!")

    def build(self, uasset):
        none = uasset.getIndex('None')
        tmp1 = self.getInt64(uasset.getIndex(self.prop))
        tmp1 += bytearray([0])

        tmp2 = self.getInt32(len(self.array))
        if self.prop == 'IntProperty':
            for ai in self.array:
                tmp2 += self.getInt32(ai)
        elif self.prop == 'EnumProperty':
            for ai in self.array:
                tmp2 += self.getInt64(uasset.getIndex(ai))
        elif self.prop == 'StructProperty':
            tmp2 += self.getInt64(uasset.getIndex(self.name))
            tmp2 += self.getInt64(uasset.getIndex('StructProperty'))
            tmp2 += self.getInt64(self.structSize)
            tmp2 += self.getInt64(uasset.getIndex(self.structType))
            tmp2 += bytearray([0]*17)
            for ai in self.array:
                tmp2 += self.callbackBuild(ai)
                tmp2 += self.getInt64(none)

        tmp = self.getInt64(len(tmp2))
        return tmp + tmp1 + tmp2


class UASSET(FILE):
    def __init__(self, data):
        super().__init__(data)
        self.load()
        
    def load(self):
        self.entries = {}
        self.idxToName = {}
        self.nameToIdx = {}

        self.data.seek(0x75)
        count = self.readInt32()
        self.data.seek(0xbd)
        self.addrUexp = self.readInt32() - 0x54
        self.data.seek(self.addrUexp)
        self.size1 = self.readInt64()
        self.data.seek(0xa9)
        self.size2 = self.readInt64()
        # Store header
        self.data.seek(0)
        self.header = bytearray(self.data.read(0xc1))
        # Load names
        self.data.seek(0xc1)
        for i in range(count):
            base = self.data.tell()
            size = self.readInt32()
            name = self.readString(size)
            key = self.readInt32()
            self.nameToIdx[name] = i
            self.idxToName[i] = name
            # Store chunk of data 
            size = self.data.tell() - base
            self.data.seek(base)
            self.entries[name] = bytearray(self.data.read(size))
        # Store footers (not sure what they're used for)
        # self.addrUexp = addrUexp - self.data.tell()
        self.footer = bytearray(self.data.read())

    def build(self):
        data = bytearray([])
        for entry in self.entries.values():
            data += entry
        return self.header + data + self.footer

    def getName(self, index):
        name = self.idxToName[index & 0xFFFFFFFF]
        index >>= 32
        if index:
            return f"{name}_{index-1}"
        return name    
        
    def getIndex(self, name):
        if name in self.nameToIdx:
            return self.nameToIdx[name]
        nameBase = '_'.join(name.split('_')[:-1])
        if nameBase not in self.nameToIdx:
            sys.exit(f"{nameBase} does not exist in this uasset")
        value = int(name.split('_')[-1]) + 1
        value <<= 32
        value += self.nameToIdx[nameBase]
        return value


# NB: This is written specifically for the files used.
class DATA:
    def __init__(self, rom, fileName):
        self.rom = rom
        self.fileName = fileName
        print(f'Loading data from {fileName}')
        # Load data
        self.uasset = UASSET(self.rom.extractFile(f"{self.fileName}.uasset"))
        self.uexp = FILE(self.rom.extractFile(f"{self.fileName}.uexp"))
        # Store none index
        self.none = self.uasset.getIndex('None')
        # Organize/"parse" uexp data
        self.switcher = {  # REPLACE WITH MATCH IN py3.10????
            'EnumProperty': partial(EnumProperty, self.uexp, self.uasset),
            'TextProperty': partial(TextProperty, self.uexp),
            'IntProperty': partial(IntProperty, self.uexp),
            'UInt32Property': partial(UInt32Property, self.uexp),
            'ArrayProperty': partial(ArrayProperty, self.uexp, self.uasset, self.loadEntry, self.buildEntry),
            'StrProperty': partial(StrProperty, self.uexp),
            'BoolProperty': partial(BoolProperty, self.uexp),
            'NameProperty': partial(NameProperty, self.uexp, self.uasset),
            'StructProperty': partial(StructProperty, self.uexp, self.uasset, self.loadEntry, self.buildEntry),
            'FloatProperty': partial(FloatProperty, self.uexp),
            'ByteProperty': partial(ByteProperty, self.uexp),
            'SoftObjectProperty': partial(SoftObjectProperty, self.uexp),
        }
        self.loadTable()

    def buildTable(self):
        data = bytearray([])
        for name in self.table:
            index = self.uasset.getIndex(name)
            data += self.uexp.getInt64(index)
            prop = self.table[name]['prop']
            data += self.uexp.getInt64(self.uasset.getIndex(prop))
            if prop == 'ArrayProperty':
                data += self.table[name]['data'].build(self.uasset)
            if prop == 'IntProperty':
                data += self.table[name]['data'].build(self.uasset)
            elif prop == 'MapProperty':
                tmp1 = self.uexp.getInt64(self.uasset.getIndex(self.table[name]['type']))
                tmp1 += self.uexp.getInt64(self.uasset.getIndex('StructProperty'))
                tmp1 += bytearray([0])

                tmp2 = bytearray([0]*4)
                table = self.table[name]['data']
                tmp2 += self.uexp.getInt32(len(table))
                for key in table: # For JOB in table
                    if self.table[name]['type'] == 'IntProperty':
                        tmp2 += self.uexp.getInt32(key)
                    else: # EnumProperty, NameProperty
                        tmp2 += self.uexp.getInt64(self.uasset.getIndex(key))
                    tmp2 += self.buildEntry(table[key])
                    tmp2 += self.uexp.getInt64(self.none)
                tmp = self.uexp.getInt64(len(tmp2))
                data += tmp + tmp1 + tmp2

        data += self.uexp.getInt64(self.none)
        data += bytearray([0]*4)
        data += bytearray([0xc1, 0x83, 0x2a, 0x9e])
        return data

    def buildEntry(self, entry):
        data = bytearray([])
        for key, d in entry.items():
            data += self.uexp.getInt64(self.uasset.getIndex(key))
            data += self.uexp.getInt64(self.uasset.getIndex(d.dataType))
            data += d.build(self.uasset)
        return data

    def loadEntry(self):
        dic = {}
        nextValue = self.uexp.readInt64()
        while nextValue != self.none:
            key = self.uasset.getName(nextValue)
            prop = self.uasset.getName(self.uexp.readInt64())
            try:
                dic[key] = self.switcher[prop]()
            except KeyError:
                sys.exit(f"{prop} not yet included")
            nextValue = self.uexp.readInt64()
        return dic

    def loadTable(self):
        self.table = {}
        nextValue = self.uexp.readInt64()
        while nextValue != self.none:
            name = self.uasset.getName(nextValue)
            self.table[name] = {}
            
            propVal = self.uexp.readInt64()
            propName = self.uasset.getName(propVal)
            self.table[name]['prop'] = propName

            if propName == 'ArrayProperty':
                self.table[name]['data'] = ArrayProperty(self.uexp, self.uasset, self.loadEntry, self.buildEntry)
            elif propName == 'IntProperty':
                self.table[name]['data'] = IntProperty(self.uexp)
            elif propName == 'MapProperty':
                self.table[name]['size'] = self.uexp.readInt64()
                dataType = self.uasset.getName(self.uexp.readInt64())
                assert dataType == 'EnumProperty' or dataType == 'IntProperty' or dataType == 'NameProperty'
                assert self.uasset.getName(self.uexp.readInt64()) == 'StructProperty'
                self.table[name]['type'] = dataType
                self.uexp.data.seek(5, 1)
                numEntries = self.uexp.readInt32()
                self.table[name]['data'] = {}
                for _ in range(numEntries): # one entry per job
                    if dataType == 'EnumProperty':
                        key = self.uasset.getName(self.uexp.readInt64())
                    elif dataType == 'IntProperty':
                        key = self.uexp.readInt32()
                    elif dataType == 'NameProperty':
                        key = self.uasset.getName(self.uexp.readInt64())
                    else:
                        sys.exit(f"loadTable MapProperty not setup for {dataType}")
                    self.table[name]['data'][key] = self.loadEntry()
            else:
                sys.exit(f"loadTable not setup for {propName}")
            nextValue = self.uexp.readInt64()

    def update(self):
        # Build uexp
        dataUEXP = self.buildTable()
        # Build uasset
        dataUASSET = self.uasset.build()
        # Update sizes in uasset
        uexpSize = len(dataUEXP) - 4
        totalSize = uexpSize + len(dataUASSET)
        dataUASSET[self.uasset.addrUexp:self.uasset.addrUexp+8] = self.uasset.getUInt64(uexpSize)
        dataUASSET[0xa9:0xa9+8] = self.uasset.getUInt64(totalSize)
        # Patch files
        self.rom.patchFile(dataUEXP, f"{self.fileName}.uexp")
        self.rom.patchFile(dataUASSET, f"{self.fileName}.uasset")    
