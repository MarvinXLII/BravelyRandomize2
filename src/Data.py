import hjson
import sys
import random
import struct

class FILE:
    def __init__(self, data):
        self.data = data
        self.addr = 0

    def readInt(self, size=4):
        value = int.from_bytes(self.data[self.addr:self.addr+size], byteorder='little', signed=True)
        self.addr += size
        return value

    def readString(self, size):
        if size < 0:
            size *= -2
            string = self.data[self.addr:self.addr+size-2].decode(encoding='UTF-16')
        else:
            string = self.data[self.addr:self.addr+size-1].decode()
        self.addr += size
        return string

    def readSHA(self):
        sha = self.data[self.addr:self.addr+0x20].decode()
        assert self.data[self.addr+0x20] == 0
        self.addr += 0x21
        return sha
    
    def getInt(self, value, size=4):
        return value.to_bytes(size, byteorder='little', signed=True)

    def getString(self, string, utf16=False):
        if utf16:
            return string.encode(encoding='UTF-16')[2:] + b'\x00\x00'
        return string.encode() + b'\x00'

    def getSHA(self, sha):
        return sha.encode() + b'\x00'


class UASSET(FILE):
    def __init__(self, data):
        super().__init__(data)
        self.load()
        
    def load(self):
        self.entries = {}
        self.idxToName = {}
        self.nameToIdx = {}
        
        self.addr = 0x75
        count = self.readInt(size=4)
        self.addr = 0xbd
        addrFtr2 = self.readInt(size=4)
        # Store header
        self.header = self.data[:0xc1]
        # Load names
        self.addr = 0xc1
        for i in range(count):
            base = self.addr
            size = self.readInt()
            name = self.readString(size)
            key = self.readInt()
            self.nameToIdx[name] = i
            self.idxToName[i] = name
            self.entries[name] = self.data[base:self.addr]
        # Store footers (not sure what they're used for)
        self.footer1 = self.data[self.addr:addrFtr2]
        self.footer2 = self.data[addrFtr2:]

    def build(self):
        self.data = bytearray(self.header)
        count = len(self.idxToName)
        for entry in self.entries.values():
            self.data += entry
        self.data += self.footer1 + self.footer2

    def addToHeader(self, addr, valueToAdd):
        value = int.from_bytes(self.header[addr:addr+4], byteorder='little')
        value += valueToAdd
        self.header[addr:addr+4] = value.to_bytes(4, byteorder='little')
        
    def addToFooter1(self, addr, valueToAdd):
        value = int.from_bytes(self.footer1[addr:addr+8], byteorder='little')
        value += valueToAdd
        self.footer1[addr:addr+8] = value.to_bytes(8, byteorder='little')

    def addEntry(self, entry):
        # Update entry
        name = entry[4:-5].decode()
        if name in self.entries:
            return
        self.entries[name] = entry
        count = len(self.idxToName)
        self.idxToName[count] = name
        self.nameToIdx[name] = count
        # Update header
        length = len(entry)
        self.addToHeader(0x18, length)
        self.addToHeader(0x29, 1)
        self.addToHeader(0x3d, length)
        self.addToHeader(0x45, length)
        self.addToHeader(0x49, length)
        self.addToHeader(0x75, 1)
        self.addToHeader(0xa5, length)
        self.addToHeader(0xbd, length)
        # Update footer
        addr = len(self.footer1) - 0x4c
        self.addToFooter1(addr, length)

    def getName(self, index):
        return self.idxToName[index]
        
    def getIndex(self, name):
        return self.nameToIdx[name]

    def getEntry(self, name):
        return self.entries[name]


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
        self.table = {}
        self.header = bytearray([])
        self.uexp.addr = 0
        self.loadTable(self.table)

    def buildTable(self):
        data = bytearray([])
        for name in self.table:
            index = self.uasset.getIndex(name)
            data += self.uexp.getInt(index, size=8)
            prop = self.table[name]['prop']
            data += self.uexp.getInt(self.uasset.getIndex(prop), size=8)
            if prop == 'ArrayProperty':
                data += self.mergeArrayProperty(self.table[name]['data'])
            elif prop == 'MapProperty':
                size = self.table[name]['size']
                data += self.uexp.getInt(size, size=8)
                data += self.uexp.getInt(self.uasset.getIndex(self.table[name]['type1']), size=8)
                data += self.uexp.getInt(self.uasset.getIndex('StructProperty'), size=8)
                data += bytearray([0]*5)
                table = self.table[name]['data']
                data += self.uexp.getInt(len(table), size=4)
                for key in table: # For JOB in table
                    if self.table[name]['type1'] == 'EnumProperty':
                        data += self.uexp.getInt(self.uasset.getIndex(key), size=8)
                    elif self.table[name]['type1'] == 'IntProperty':
                        data += self.uexp.getInt(key, size=4)
                    for key2, d in table[key].items():
                        data += self.uexp.getInt(self.uasset.getIndex(key2), size=8)
                        data += self.uexp.getInt(self.uasset.getIndex(d['type']), size=8) ## ASSUMED FOR NOW
                        if d['type'] == 'EnumProperty':
                            data += self.mergeEnumProperty(d['entry'])
                        elif d['type'] == 'TextProperty':
                            data += self.mergeTextProperty(d['entry'])
                        elif d['type'] == 'IntProperty':
                            data += self.mergeIntProperty(d['entry'])
                        elif d['type'] == 'ArrayProperty':
                            data += self.mergeArrayProperty(d['entry'])
                        elif d['type'] == 'StrProperty':
                            data += self.mergeStrProperty(d['entry'])
                        elif d['type'] == 'BoolProperty':
                            data += self.mergeBoolProperty(d['entry'])
                        elif d['type'] == 'NameProperty':
                            data += self.mergeNameProperty(d['entry'])
                        elif d['type'] == 'StructProperty':
                            data += self.mergeStructProperty(d['entry'])
                        elif d['type'] == 'FloatProperty':
                            data += self.mergeFloatProperty(d['entry'])
                        else:
                            sys.exit(f"Property {d['type']} not yet included!")
                            
                    data += self.uexp.getInt(self.none, size=8)
        data += self.uexp.getInt(self.none, size=8)
        data += bytearray([0]*4)
        data += bytearray([0xc1, 0x83, 0x2a, 0x9e])
        self.uexp.data = data

    def loadFloatProperty(self):
        size = self.uexp.readInt(size=8)
        self.uexp.addr += 1
        data = self.uexp.data[self.uexp.addr:self.uexp.addr+4]
        self.uexp.addr += 4
        f = struct.unpack("<f", data)[0]
        return {'size': size, 'value': f}

    def mergeFloatProperty(self, entry):
        tmp = self.uexp.getInt(entry['size'], size=8)
        tmp += bytearray([0])
        tmp += struct.pack("<f", entry['value'])
        return tmp


    def loadStrProperty(self):
        size = self.uexp.readInt(size=8)
        self.uexp.addr += 1
        addr = self.uexp.addr
        string = self.uexp.data[addr:addr+size]
        self.uexp.addr += size
        return {'size': size, 'string': string}

    def mergeStrProperty(self, entry):
        tmp = self.uexp.getInt(entry['size'], size=8)
        tmp += bytearray([0])
        tmp += entry['string']
        return tmp
        
    def loadEnumProperty(self):
        size = self.uexp.readInt(size=8)
        assert size == 8, f"EnumProperty must always have a size of 8. Here size is {size}"
        value1 = self.uasset.getName(self.uexp.readInt(size=8))
        assert self.uexp.readInt(size=1) == 0, f"EnumProperty must have 0 before the full value."
        value2 = self.uasset.getName(self.uexp.readInt(size=8))
        return {'size': size, 'value1': value1, 'value2': value2}

    def mergeEnumProperty(self, entry):
        tmp = self.uexp.getInt(entry['size'], size=8)
        tmp += self.uexp.getInt(self.uasset.getIndex(entry['value1']), size=8)
        tmp += bytearray([0])
        tmp += self.uexp.getInt(self.uasset.getIndex(entry['value2']), size=8)
        return tmp

    def loadBoolProperty(self):
        assert self.uexp.readInt(size=8) == 0
        value = self.uexp.readInt(size=1)
        self.uexp.addr += 1
        return {'value': value}

    def mergeBoolProperty(self, entry):
        tmp = bytearray([0]*8)
        tmp += self.uexp.getInt(entry['value'], size=1)
        tmp += bytearray([0])
        return tmp
    
    def loadTextProperty(self):
        entrySize = self.uexp.readInt(size=8)
        self.uexp.addr += 5
        check = self.uexp.readInt(size=1)
        if check == -1:
            assert self.uexp.readInt(size=4) == 0
            return {'size': entrySize, 'namespace': "", 'sha': "", 'string': "", 'stringSize': ""}
        namespaceSize = self.uexp.readInt(size=4)
        namespace = self.uexp.readString(namespaceSize)
        shaSize = self.uexp.readInt(size=4)
        assert shaSize == 0x21
        sha = self.uexp.readSHA()
        stringSize = self.uexp.readInt(size=4)
        string = self.uexp.readString(stringSize)
        return {'size': entrySize, 'namespace': namespace, 'sha': sha, 'string': string, 'stringSize': stringSize}

    def mergeTextProperty(self, entry):
        tmp = bytearray([0]*4)
        if entry['string'] == "":
            tmp += bytearray([0xff]+[0]*4)
            return self.uexp.getInt(9, size=8) + bytearray([0]) + tmp
        else:
            tmp += bytearray([0])
        x = self.uexp.getString(entry['namespace'])
        tmp += self.uexp.getInt(len(x), size=4)
        tmp += x
        x = self.uexp.getSHA(entry['sha'])
        tmp += self.uexp.getInt(len(x), size=4)
        tmp += x
        if entry['stringSize'] < 0:
            x = self.uexp.getString(entry['string'], utf16=True)
            tmp += self.uexp.getInt(-int(len(x)/2), size=4)
        else:
            x = self.uexp.getString(entry['string'])
            tmp += self.uexp.getInt(len(x), size=4)
        tmp += x
        size = len(tmp)
        return self.uexp.getInt(size, size=8) + bytearray([0]) + tmp

    def loadNameProperty(self):
        size = self.uexp.readInt(size=8)
        self.uexp.addr += 1
        name = self.uasset.getName(self.uexp.readInt(size=8))
        return {'size': size, 'name': name}

    def mergeNameProperty(self, entry):
        tmp = self.uexp.getInt(entry['size'], size=8)
        tmp += bytearray([0])
        tmp += self.uexp.getInt(self.uasset.getIndex(entry['name']), size=8)
        return tmp
    
    def loadIntProperty(self):
        size = self.uexp.readInt(size=8)
        self.uexp.addr += 1
        value = self.uexp.readInt(size)
        return {'size': size, 'value': value}

    def mergeIntProperty(self, entry):
        tmp = self.uexp.getInt(entry['size'], size=8)
        tmp += bytearray([0])
        tmp += self.uexp.getInt(entry['value'], size=entry['size'])
        return tmp

    # MonsterDataAsset: Float I won't need to modify.
    def loadStructProperty(self):
        size = self.uexp.readInt(size=8)
        value = self.uexp.readInt(size=8)
        self.uexp.addr += 17
        structData = self.uexp.data[self.uexp.addr:self.uexp.addr+size]
        self.uexp.addr += size
        return {'size':size, 'value':value, 'struct':structData}

    def mergeStructProperty(self, entry):
        tmp = self.uexp.getInt(entry['size'], size=8)
        tmp += self.uexp.getInt(entry['value'], size=8)
        tmp += bytearray([0]*17)
        tmp += entry['struct']
        return tmp    
    
    def loadArrayProperty(self):
        size = self.uexp.readInt(size=8)
        prop = self.uasset.getName(self.uexp.readInt(size=8))
        self.uexp.addr += 1
        if prop == 'IntProperty':
            num = self.uexp.readInt(size=4)
            arr = []
            for _ in range(num):
                arr.append(self.uexp.readInt(size=4))
        elif prop == 'EnumProperty':
            num = self.uexp.readInt(size=4)
            arr = []
            for _ in range(num):
                value = self.uasset.getName(self.uexp.readInt(size=8))
                arr.append(value)
        else:
            sys.exit(f"Load array property does not allow for {prop} types!")    
        return {'size': size, 'prop': prop, 'arr': arr}

    def mergeArrayProperty(self, entry):
        tmp = bytearray(self.uexp.getInt(entry['size'], size=8)) # Sizes should not get modified!!!
        tmp += self.uexp.getInt(self.uasset.getIndex(entry['prop']), size=8)
        tmp += bytearray([0])
        tmp += self.uexp.getInt(len(entry['arr']), size=4)
        if entry['prop'] == 'IntProperty':
            for ai in entry['arr']:
                tmp += self.uexp.getInt(ai, size=4)
        elif entry['prop'] == 'EnumProperty':
            for ai in entry['arr']:
                tmp += self.uexp.getInt(self.uasset.getIndex(ai), size=8)
        else:
            sys.exit(f"Load array property does not allow for {prop} types!")
        return tmp

    def loadTable(self, table):
        nextValue = self.uexp.readInt(size=8)
        while nextValue != self.none:
            name = self.uasset.getName(nextValue)
            table[name] = {}
            
            propVal = self.uexp.readInt(size=8)
            propName = self.uasset.getName(propVal)
            table[name]['prop'] = propName

            if propName == 'ArrayProperty':
                table[name]['data'] = self.loadArrayProperty()
            elif propName == 'MapProperty':
                table[name]['size'] = self.uexp.readInt(size=8)
                type1 = self.uasset.getName(self.uexp.readInt(size=8))
                type2 = self.uasset.getName(self.uexp.readInt(size=8))
                assert type1 == 'EnumProperty' or type1 == 'IntProperty'
                assert type2 == 'StructProperty'
                table[name]['type1'] = type1
                self.uexp.addr += 1
                # self.uexp.addr += table[name]['size']
                self.uexp.addr += 4
                numEntries = self.uexp.readInt(size=4)
                table[name]['data'] = {}
                for _ in range(numEntries): # one entry per job
                    if type1 == 'EnumProperty':
                        key = self.uasset.getName(self.uexp.readInt(size=8))
                    elif type1 == 'IntProperty':
                        key = self.uexp.readInt(size=4)
                    table[name]['data'][key] = {}
                    nextValue = self.uexp.readInt(size=8)
                    while nextValue != self.none:
                        key2 = self.uasset.getName(nextValue)
                        prop = self.uasset.getName(self.uexp.readInt(size=8))
                        if prop == 'EnumProperty':
                            table[name]['data'][key][key2] = {
                                'type': prop,
                                'entry': self.loadEnumProperty(),
                            }
                        elif prop == 'TextProperty':
                            table[name]['data'][key][key2] = {
                                'type': prop,
                                'entry': self.loadTextProperty(),
                            }
                        elif prop == 'IntProperty':
                            table[name]['data'][key][key2] = {
                                'type': prop,
                                'entry': self.loadIntProperty(),
                            }
                        elif prop == 'ArrayProperty':
                            table[name]['data'][key][key2] = {
                                'type': prop,
                                'entry': self.loadArrayProperty(),
                            }
                        elif prop == 'StrProperty':
                            table[name]['data'][key][key2] = {
                                'type': prop,
                                'entry': self.loadStrProperty(),
                            }
                        elif prop == 'BoolProperty':
                            table[name]['data'][key][key2] = {
                                'type': prop,
                                'entry': self.loadBoolProperty(),
                            }
                        elif prop == 'NameProperty':
                            table[name]['data'][key][key2] = {
                                'type': prop,
                                'entry': self.loadNameProperty(),
                            }
                        elif prop == 'StructProperty':
                            table[name]['data'][key][key2] = {
                                'type': prop,
                                'entry': self.loadStructProperty(),
                            }
                        elif prop == 'FloatProperty':
                            table[name]['data'][key][key2] = {
                                'type': prop,
                                'entry': self.loadFloatProperty(),
                            }
                        else:
                            sys.exit(f"{prop} not yet included")
                        nextValue = self.uexp.readInt(size=8)
            nextValue = self.uexp.readInt(size=8)
        return


    def update(self):
        # Build uexp first -- need total size for uasset
        self.buildTable()
        ## Update uasset footer to account for size changes in uexp
        address = len(self.uasset.footer1) - 0x54
        length = len(self.uexp.data) - 4
        self.uasset.footer1[address:address+8] = length.to_bytes(8, byteorder='little')
        # Build uasset
        self.uasset.build()
        # Patch ROM
        self.rom.patchFile(self.uasset.data, f"{self.fileName}.uasset")
        self.rom.patchFile(self.uexp.data, f"{self.fileName}.uexp")



class JOBS(DATA):
    def __init__(self, rom):
        super().__init__(rom, 'JobCorrectionAsset')

    # Shuffles jobs
    def shuffleStats(self):
        data = self.table['JobLevelMap']['data']
        keys = list(data.keys())
        for i, ki in enumerate(data):
            kj = random.sample(keys[i:], 1)[0]
            data[ki], data[kj] = data[kj], data[ki]
            data[ki]['_id'], data[kj]['_id'] = data[kj]['_id'], data[ki]['_id'] # SWAP ID BACK

    # Unbiased shuffling
    def randomStats(self):
        data = self.table['JobLevelMap']['data']
        stats = list(data['EJobEnum::JE_Sobriety'].keys())[1:] # omit _id
        keys = list(data.keys())
        for stat in stats: # HP, MP, ...
            for i, ki in enumerate(data): # Freelancer, ...
                kj = random.sample(keys[i:], 1)[0]
                data[ki][stat], data[kj][stat] = data[kj][stat], data[ki][stat]


class JOBDATA(DATA):
    def __init__(self, rom):
        super().__init__(rom, 'JobDataAsset')

    def shuffleSupport(self):
        data = self.table['JobDataMap']['data']
        jobs = data.keys()
        support = []
        for job in jobs:
            support += list(filter(lambda x: x > 0, data[job]['SupportAbilityArray']['entry']['arr']))
        random.shuffle(support)
        for job in jobs:
            array = data[job]['SupportAbilityArray']['entry']['arr']
            for i, a in enumerate(array):
                if a > 0:
                    array[i] = support.pop()

    def shuffleSkills(self):
        data = self.table['JobDataMap']['data']
        jobs = data.keys()
        action = []
        for job in jobs:
            action += list(filter(lambda x: x > 0, data[job]['ActionAbilityArray']['entry']['arr']))
        random.shuffle(action)
        for job in jobs:
            array = data[job]['ActionAbilityArray']['entry']['arr']
            for i, a in enumerate(array):
                if a > 0:
                    array[i] = action.pop()

    def shuffleAll(self):
        data = self.table['JobDataMap']['data']
        jobs = data.keys()
        pairs = []
        for job in jobs:
            pairs += list(zip(data[job]['ActionAbilityArray']['entry']['arr'], data[job]['SupportAbilityArray']['entry']['arr']))
        random.shuffle(pairs)
        for job in jobs:
            action = data[job]['ActionAbilityArray']['entry']['arr']
            support = data[job]['SupportAbilityArray']['entry']['arr']
            for i in range(len(action)):
                action[i], support[i] = pairs.pop()

    def shuffleTraits(self):
        data = self.table['JobDataMap']['data']
        traits = []
        for job in data.values():
            traits.append(job['JobTraitId1'])
            traits.append(job['JobTraitId2'])
        random.shuffle(traits)
        for job in data.values():
            job['JobTraitId1'] = traits.pop()
            job['JobTraitId2'] = traits.pop()
        

class MONSTERS(DATA):
    def __init__(self, rom):
        super().__init__(rom, 'MonsterDataAsset')

    # "PQ" in the code, "PG" in the game
    def scalePG(self, scale):
        assert scale > 0
        data = self.table['MonsterDataMap']['data']
        for d in data.values():
            pg = int(scale * d['pq']['entry']['value'])
            d['pq']['entry']['value'] = min(pg, 99999)
            
    def scaleEXP(self, scale):
        assert scale > 0
        data = self.table['MonsterDataMap']['data']
        for d in data.values():
            exp = int(scale * d['Exp']['entry']['value'])
            d['Exp']['entry']['value'] = min(exp, 99999)
            
    def scaleJP(self, scale):
        assert scale > 0
        data = self.table['MonsterDataMap']['data']
        for d in data.values():
            jp = int(scale * d['Jp']['entry']['value'])
            d['Jp']['entry']['value'] = min(jp, 9999)


class TEXT(DATA):
    def __init__(self, rom, baseName):
        super().__init__(rom, baseName)
        self.data = list(self.table.values())[0]['data']
        keys = list(self.data[next(iter(self.data))].keys())
        self.nameKey = list(filter(lambda key: 'Name' in key, keys))[0]
        self.descKey = list(filter(lambda key: 'Description' in key, keys))[0]

    def getName(self, key):
        return self.data[key][self.nameKey]['entry']['string']

    def getDescription(self, key):
        return self.data[key][self.descKey]['entry']['string']
