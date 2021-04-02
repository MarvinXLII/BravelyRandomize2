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

    def getEntry(self, name):
        if name in self.entries:
            return self.entries[name]
        # Get name base
        index = self.getIndex(name)
        name = self.idxToName[index & 0xFFFFFFFF]
        # Return entry for the name base
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
                    if self.table[name]['type1'] == 'IntProperty':
                        data += self.uexp.getInt(key, size=4)
                    else: # EnumProperty, NameProperty
                        data += self.uexp.getInt(self.uasset.getIndex(key), size=8)
                    data += self.buildEntry(table[key])
                    data += self.uexp.getInt(self.none, size=8)
        data += self.uexp.getInt(self.none, size=8)
        data += bytearray([0]*4)
        data += bytearray([0xc1, 0x83, 0x2a, 0x9e])
        self.uexp.data = data

    def buildEntry(self, entry):
        data = bytearray([])
        for key, d in entry.items():
            data += self.uexp.getInt(self.uasset.getIndex(key), size=8)
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
            elif d['type'] == 'ByteProperty':
                data += self.mergeByteProperty(d['entry'])
            else:
                sys.exit(f"Property {d['type']} not yet included!")
        return data


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
        assert size == 8, f"EnumProperty must always have a size of 8."
        value0 = self.uasset.getName(self.uexp.readInt(size=8))
        assert self.uexp.readInt(size=1) == 0, f"EnumProperty must have 0 before the full value."
        value = self.uasset.getName(self.uexp.readInt(size=8))
        return {'size': size, 'value0': value0, 'value': value}

    def mergeEnumProperty(self, entry):
        tmp = self.uexp.getInt(entry['size'], size=8)
        tmp += self.uexp.getInt(self.uasset.getIndex(entry['value0']), size=8)
        tmp += bytearray([0])
        tmp += self.uexp.getInt(self.uasset.getIndex(entry['value']), size=8)
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
        return {'size': size, 'value': name}

    def mergeNameProperty(self, entry):
        tmp = self.uexp.getInt(entry['size'], size=8)
        tmp += bytearray([0])
        tmp += self.uexp.getInt(self.uasset.getIndex(entry['value']), size=8)
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

    def loadByteProperty(self):
        size = self.uexp.readInt(size=8)
        assert size == 1
        assert self.uexp.readInt(size=8) == self.none
        self.uexp.addr += 1
        value = self.uexp.readInt(size=1)
        return {'size': size, 'value': value}

    def mergeByteProperty(self, entry):
        tmp = self.uexp.getInt(entry['size'], size=8)
        tmp += self.uexp.getInt(self.none, size=8)
        tmp += bytearray([0])
        tmp += self.uexp.getInt(entry['value'], size=1)
        return tmp

    # MonsterDataAsset: Float I won't need to modify.
    def loadStructProperty(self):
        size = self.uexp.readInt(size=8)
        value = self.uexp.readInt(size=8)
        self.uexp.addr += 17
        structData = self.uexp.data[self.uexp.addr:self.uexp.addr+size]
        self.uexp.addr += size
        return {'size': size, 'value': value, 'struct': structData}

    def mergeStructProperty(self, entry):
        tmp = self.uexp.getInt(entry['size'], size=8)
        tmp += self.uexp.getInt(entry['value'], size=8)
        tmp += bytearray([0]*17)
        tmp += entry['struct']
        return tmp    
    
    def loadArrayProperty(self, name=None):
        size = self.uexp.readInt(size=8)
        prop = self.uasset.getName(self.uexp.readInt(size=8))
        self.uexp.addr += 1
        if prop == 'IntProperty':
            num = self.uexp.readInt(size=4)
            arr = []
            for _ in range(num):
                arr.append(self.uexp.readInt(size=4))
            return {'size': size, 'prop': prop, 'arr': arr}
        elif prop == 'EnumProperty':
            num = self.uexp.readInt(size=4)
            arr = []
            for _ in range(num):
                value = self.uasset.getName(self.uexp.readInt(size=8))
                arr.append(value)
            return {'size': size, 'prop': prop, 'arr': arr}
        elif prop == 'StructProperty':
            num = self.uexp.readInt(size=4)
            ## Ensure names are the same
            name2Val = self.uexp.readInt(size=8)
            name2 = self.uasset.getName(name2Val)
            assert name2 == name
            ## Ensure still a struct
            typeVal = self.uexp.readInt(size=8)
            typeName = self.uasset.getName(typeVal)
            assert typeName == 'StructProperty'
            ## Rest of the prep stuff
            size2 = self.uexp.readInt(size=8)
            dataType = self.uasset.getName(self.uexp.readInt(size=8))
            for _ in range(17):
                assert self.uexp.readInt(size=1) == 0
            ## Load the array
            arr = []
            for _ in range(num):
                arr.append(self.loadEntry())
            return {'size': size, 'size2': size2, 'dataType': dataType, 'prop': prop, 'arr': arr, 'name': name2}
        else:
            sys.exit(f"Load array property does not allow for {prop} types!")    

    def mergeArrayProperty(self, entry):
        tmp = bytearray(self.uexp.getInt(entry['size'], size=8)) # Assumes sizes are not modified!!!
        tmp += self.uexp.getInt(self.uasset.getIndex(entry['prop']), size=8)
        tmp += bytearray([0])
        tmp += self.uexp.getInt(len(entry['arr']), size=4)
        if entry['prop'] == 'IntProperty':
            for ai in entry['arr']:
                tmp += self.uexp.getInt(ai, size=4)
        elif entry['prop'] == 'EnumProperty':
            for ai in entry['arr']:
                tmp += self.uexp.getInt(self.uasset.getIndex(ai), size=8)
        elif entry['prop'] == 'StructProperty':
            tmp += self.uexp.getInt(self.uasset.getIndex(entry['name']), size=8)
            tmp += self.uexp.getInt(self.uasset.getIndex('StructProperty'), size=8)
            tmp += self.uexp.getInt(entry['size2'], size=8)
            tmp += self.uexp.getInt(self.uasset.getIndex(entry['dataType']), size=8)
            tmp += bytearray([0]*17)
            for ai in entry['arr']:
                tmp += self.buildEntry(ai)
                tmp += self.uexp.getInt(self.none, size=8)
        else:
            sys.exit(f"Load array property does not allow for {prop} types!")
        return tmp

    def loadEntry(self):
        dic = {}
        nextValue = self.uexp.readInt(size=8)
        while nextValue != self.none:
            key2 = self.uasset.getName(nextValue)
            prop = self.uasset.getName(self.uexp.readInt(size=8))
            if prop == 'EnumProperty':
                dic[key2] = {
                    'type': prop,
                    'entry': self.loadEnumProperty(),
                }
            elif prop == 'TextProperty':
                dic[key2] = {
                    'type': prop,
                    'entry': self.loadTextProperty(),
                }
            elif prop == 'IntProperty':
                dic[key2] = {
                    'type': prop,
                    'entry': self.loadIntProperty(),
                }
            elif prop == 'ArrayProperty':
                dic[key2] = {
                    'type': prop,
                    'entry': self.loadArrayProperty(key2),
                }
            elif prop == 'StrProperty':
                dic[key2] = {
                    'type': prop,
                    'entry': self.loadStrProperty(),
                }
            elif prop == 'BoolProperty':
                dic[key2] = {
                    'type': prop,
                    'entry': self.loadBoolProperty(),
                }
            elif prop == 'NameProperty':
                dic[key2] = {
                    'type': prop,
                    'entry': self.loadNameProperty(),
                }
            elif prop == 'StructProperty':
                dic[key2] = {
                    'type': prop,
                    'entry': self.loadStructProperty(),
                }
            elif prop == 'FloatProperty':
                dic[key2] = {
                    'type': prop,
                    'entry': self.loadFloatProperty(),
                }
            elif prop == 'ByteProperty':
                dic[key2] = {
                    'type': prop,
                    'entry': self.loadByteProperty(),
                }
            else:
                sys.exit(f"{prop} not yet included")
            nextValue = self.uexp.readInt(size=8)

        return dic
        

    def loadTable(self, table):
        nextValue = self.uexp.readInt(size=8)
        while nextValue != self.none:
            name = self.uasset.getName(nextValue)
            table[name] = {}
            
            propVal = self.uexp.readInt(size=8)
            propName = self.uasset.getName(propVal)
            table[name]['prop'] = propName

            if propName == 'ArrayProperty':
                table[name]['data'] = self.loadArrayProperty(name)
            elif propName == 'MapProperty':
                table[name]['size'] = self.uexp.readInt(size=8)
                type1 = self.uasset.getName(self.uexp.readInt(size=8))
                type2 = self.uasset.getName(self.uexp.readInt(size=8))
                assert type1 == 'EnumProperty' or type1 == 'IntProperty' or type1 == 'NameProperty'
                assert type2 == 'StructProperty'
                table[name]['type1'] = type1
                self.uexp.addr += 5
                numEntries = self.uexp.readInt(size=4)
                table[name]['data'] = {}
                for _ in range(numEntries): # one entry per job
                    if type1 == 'EnumProperty':
                        key = self.uasset.getName(self.uexp.readInt(size=8))
                    elif type1 == 'IntProperty':
                        key = self.uexp.readInt(size=4)
                    elif type1 == 'NameProperty':
                        key = self.uasset.getName(self.uexp.readInt(size=8))
                    table[name]['data'][key] = self.loadEntry()
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
        


class MONSTERPARTY(DATA):
    def __init__(self, rom):
        super().__init__(rom, 'MonsterPartyAsset')
        self.data = self.table['MonsterPartyMap']['data']
        self.levels = {}
        for party in self.data.values():
            for i in range(1, 7):
                Id = party[f"Monster{i}Id"]['entry']['value']
                Level = party[f"Monster{i}Level"]['entry']['value']
                if Id < 0: continue
                if Id not in self.levels:
                    self.levels[Id] = set()
                self.levels[Id].add(Level)

    # NOTE: This is a crude estimate of chapter based on the enemy's level!
    def getChapter(self, Id):
        try:
            chapter = int(min(self.levels[Id].difference([1])) / 10)
            return min(chapter, 7)
        except:
            pass
        if Id == 105506: # Might be part of a boss battle???
            return 5
        if Id == 106407: # Might be part of a boss battle???
            return 2


class MONSTERS(DATA):
    def __init__(self, rom, monster, items, party):
        super().__init__(rom, 'MonsterDataAsset')
        self.data = self.table['MonsterDataMap']['data']
        self.monster = monster
        self.items = items
        self.party = party

        self.steals = {}
        for d in self.data.values():
            Id = d['Id']['entry']['value']
            try:
                name = self.monster.getName(Id)
            except:
                name = ''
            stealRate = d['StealRate']['entry']['value']
            stealItem = d['StealItem']['entry']['value']
            stealRareItem = d['StealRareItem']['entry']['value']

            self.steals[Id] = {
                'shuffle': name != '' and stealRate != 50, ## INCLUDE IN SWAPPING
                'chapter': self.party.getChapter(Id), # For grouping by "chapters" (TODO: do this accurately)
                'steal': {
                    # I'll probably just shuffle items and rare items separately.....
                    'StealRate': stealRate,
                    'StealItem': stealItem,
                    'StealRareItem': stealRareItem,
                }
            }

        self.resistance = {}
        for d in self.data.values():
            Id = d['Id']['entry']['value']
            self.resistance[Id] = {
                'isBoss': d['MonsterRank']['entry']['value'] == 'EMonsterRankEnum::MRE_Boss',
                # MAGIC
                'Magic': {
                    'FireResistance': d['FireResistance']['entry']['value'],
                    'WaterResistance': d['WaterResistance']['entry']['value'],
                    'LightningResistance': d['LightningResistance']['entry']['value'],
                    'EarthResistance': d['EarthResistance']['entry']['value'],
                    'WindResistance': d['WindResistance']['entry']['value'],
                    'LightResistance': d['LightResistance']['entry']['value'],
                    'DarknessResistance': d['DarknessResistance']['entry']['value'],
                },
                # WEAPONS
                'Weapon': {
                    'ShortSwordResistance': d['ShortSwordResistance']['entry']['value'],
                    'SwordResistance': d['AxeResistance']['entry']['value'],
                    'AxeResistance': d['AxeResistance']['entry']['value'],
                    'SpearResistance': d['SpearResistance']['entry']['value'],
                    'BowResistance': d['BowResistance']['entry']['value'],
                    'StaffResistance': d['StaffResistance']['entry']['value'],
                },
                # # STATS -- include????
                # 'BuffDebuffResistance': d['BuffDebuffResistance']['entry']['value'],
                # STATUS EFFECTS
                'Effects': {
                    'ResistancePoison': (d['ResistancePoison']['entry']['value'], d['ResistanceLevelPoison']['entry']['value']),
                    'ResistanceDark': (d['ResistanceDark']['entry']['value'], d['ResistanceLevelDark']['entry']['value']),
                    'ResistanceSilence': (d['ResistanceSilence']['entry']['value'], d['ResistanceLevelSilence']['entry']['value']),
                    'ResistanceSleep': (d['ResistanceSleep']['entry']['value'], d['ResistanceLevelSleep']['entry']['value']),
                    'ResistanceParalysis': (d['ResistanceParalysis']['entry']['value'], d['ResistanceLevelParalysis']['entry']['value']),
                    'ResistanceFear': (d['ResistanceFear']['entry']['value'], d['ResistanceLevelFear']['entry']['value']),
                    'ResistanceBerzerk': (d['ResistanceBerzerk']['entry']['value'], d['ResistanceLevelBerzerk']['entry']['value']),
                    'ResistanceConfusion': (d['ResistanceConfusion']['entry']['value'], d['ResistanceLevelConfusion']['entry']['value']),
                    'ResistanceSeduction': (d['ResistanceSeduction']['entry']['value'], d['ResistanceLevelSeduction']['entry']['value']),
                    'ResistanceInstantDeath': (d['ResistanceInstantDeath']['entry']['value'], d['ResistanceLevelInstantDeath']['entry']['value']),
                    'ResistanceDeathTimer': (d['ResistanceDeathTimer']['entry']['value'], d['ResistanceLevelDeathTimer']['entry']['value']),
                    'ResistanceStop': (d['ResistanceStop']['entry']['value'], d['ResistanceLevelStop']['entry']['value']),
                    'ResistanceFreeze': (d['ResistanceFreeze']['entry']['value'], d['ResistanceLevelFreeze']['entry']['value']),
                    'ResistanceBattleExclusion': (d['ResistanceBattleExclusion']['entry']['value'], d['ResistanceLevelBattleExclusion']['entry']['value']),
                    'ResistanceTransparent': (d['ResistanceTransparent']['entry']['value'], d['ResistanceLevelTransparent']['entry']['value']),
                    'ResistancePaint': (d['ResistancePaint']['entry']['value'], d['ResistanceLevelPaint']['entry']['value']),
                    'ResistanceEpidemic': (d['ResistanceEpidemic']['entry']['value'], d['ResistanceLevelEpidemic']['entry']['value']),
                    'ResistanceSlow': (d['ResistanceSlow']['entry']['value'], d['ResistanceLevelSlow']['entry']['value']),
                    'ResistanceWeakPoint': (d['ResistanceWeakPoint']['entry']['value'], d['ResistanceLevelWeakPoint']['entry']['value']),
                },
            }

    def update(self):
        for d in self.data.values():
            Id = d['Id']['entry']['value']
            for key, value in self.resistance[Id]['Magic'].items():
                d[key]['entry']['value'] = value
            for key, value in self.resistance[Id]['Weapon'].items():
                d[key]['entry']['value'] = value
            for key, (res, level) in self.resistance[Id]['Effects'].items():
                key2 = 'ResistanceLevel' + key[10:]
                d[key]['entry']['value'] = res
                d[key2]['entry']['value'] = level
            try:
                self.monster.getName(Id)
                steals = self.steals[Id]['steal']
            except:
                # Reuse stealable items (they are kept the same as their predecessor in almost every case)
                assert steals
            for key, value in steals.items():
                d[key]['entry']['value'] = value

        super().update()

    # "PQ" in the code, "PG" in the game
    def scalePG(self, scale):
        assert scale > 0
        for d in self.data.values():
            pg = int(scale * d['pq']['entry']['value'])
            d['pq']['entry']['value'] = min(pg, 99999)

    def scaleEXP(self, scale):
        assert scale > 0
        for d in self.data.values():
            exp = int(scale * d['Exp']['entry']['value'])
            d['Exp']['entry']['value'] = min(exp, 99999)

    def scaleJP(self, scale):
        assert scale > 0
        for d in self.data.values():
            jp = int(scale * d['Jp']['entry']['value'])
            d['Jp']['entry']['value'] = min(jp, 9999)

    def spoilers(self, filename):
        with open(filename, 'w') as sys.stdout:
            for Id, data in self.data.items():
                steal = self.steals[Id]['steal']
                try:
                    name = self.monster.getName(Id)
                except:
                    name = '          '
                if steal['StealRate'] == 50:
                    assert steal['StealItem'] == -1
                    assert steal['StealRareItem'] == -1
                    print(', '.join([name, str(steal['StealRate']), "NONE", "NONE"]))
                else:
                    if steal['StealItem'] > 0:
                        stealItem = self.items.getName(steal['StealItem'])
                    else:
                        stealItem = "NONE"
                    if steal['StealRareItem'] > 0:
                        stealRareItem = self.items.getName(steal['StealRareItem'])
                    else:
                        stealRareItem = "NONE"
                    print(', '.join([name, str(self.steals[Id]['chapter']), stealItem, stealRareItem]))

        sys.stdout = sys.__stdout__


class QUESTS(DATA):
    def __init__(self, rom, text, locations):
        super().__init__(rom, 'QuestAsset')
        self.text = text
        self.locations = locations
        self.questArray = self.table['QuestArray']['data']['arr']
        with open('json/quests.json','r') as file:
            self.json = hjson.load(file)

        ## Organize data for shuffling
        self.questRewards = {i:[] for i in range(8)}
        for i, quest in enumerate(self.questArray[148:]):
            if quest['RewardType']['entry']['value'] != 'EQuestRewardType::None':
                rewardId = quest['RewardID']['entry']['value']
                rewardCount = quest['RewardCount']['entry']['value']
                subQuestIndex = quest['SubQuestIndex']['entry']['value']
                chapter = self.getChapter(quest['SubQuestIndex']['entry']['value'])
                self.questRewards[chapter].append({
                    'Index': 148+i,
                    'RewardId': rewardId,
                    'RewardCount': rewardCount,
                    'Vanilla': self.getReward(rewardId, rewardCount),
                    'Swap': '',
                    'SubQuestID': str(subQuestIndex).zfill(3),
                    'Location': self.getLocation(subQuestIndex),
                    'Name': self.getName(subQuestIndex),
                })
        # Sort chapters (mainly for printouts)
        for i in range(8):
            self.questRewards[i] = sorted(self.questRewards[i], key=lambda x: x['SubQuestID'])

    def update(self):
        for chapterQuests in self.questRewards.values():
            for quest in chapterQuests:
                i = quest['Index']
                self.questArray[i]['RewardID']['entry']['value'] = quest['RewardId']
                self.questArray[i]['RewardCount']['entry']['value'] = quest['RewardCount']
                if quest['RewardId'] == -1 and quest['RewardCount'] > 0:
                    self.questArray[i]['RewardType']['entry']['value'] = "EQuestRewardType::Money"
                else:
                    self.questArray[i]['RewardType']['entry']['value'] = "EQuestRewardType::Item"

        super().update()

    def getReward(self, rewardId, rewardCount):
        if rewardId < 0 and rewardCount > 0:
            return f"{rewardCount} pg"
        if rewardId > 0:
            item = self.text.getName(rewardId)
            if rewardCount > 1:
                item += f" x{rewardCount}"
            return item

    def getChapter(self, index):
        return self.json[str(index)]['Chapter']

    def getLocation(self, index):
        return self.json[str(index)]['Location']

    def getName(self, index):
        return self.json[str(index)]['Name']

    def spoilers(self, filename):
        with open(filename, 'w') as sys.stdout:
            for i in range(7):
                print('')
                print('')
                if i == 0:
                    print('--------')
                    print('Prologue')
                    print('--------')
                else:
                    print('---------')
                    print(f'Chapter {i}')
                    print('---------')
                print('')
                for quest in self.questRewards[i]:
                    print('   ', quest['SubQuestID'].ljust(5, ' '), quest['Location'].ljust(20, ' '), quest['Name'].ljust(35, ' '), quest['Vanilla'].ljust(35, ' '), ' <-- ', quest['Swap'].ljust(35, ' '))

        sys.stdout = sys.__stdout__

    def print(self, fileName):
        with open(fileName, 'w') as sys.stdout:
            for i, q in enumerate(self.questArray):
                reward = self.getReward(q['RewardID']['entry']['value'], q['RewardCount']['entry']['value'])
                if reward:
                    print(', '.join([str(i), q['QuestID']['entry']['value'], str(q['Chapter']['entry']['value']), str(self.getChapter(q['QuestID']['entry']['value'])), reward]))
                else:
                    print(', '.join([str(i), q['QuestID']['entry']['value'], str(q['Chapter']['entry']['value']), str(self.getChapter(q['QuestID']['entry']['value'])), "NONE"]))

        sys.stdout = sys.__stdout__

class TREASURES(DATA):
    def __init__(self, rom, text, locations):
        super().__init__(rom, 'TreasureBoxDataAsset')
        self.text = text
        self.locations = locations
        self.data = list(self.table.values())[0]['data']
        with open('json/treasures.json','r') as file:
            self.json = hjson.load(file)

        self.boxes = {i:[] for i in range(8)}
        for key, value in self.data.items():
            if key in self.json:
                chapter = self.json[key]['Chapter']
                itemId = value['ItemId']['entry']['value']
                itemCount = value['ItemCount']['entry']['value']
                enemyPartyId = value['EnemyPartyId']['entry']['value']
                eventType = value['EventType']['entry']['value']
                self.boxes[chapter].append({
                    'key': key,
                    'ItemId': itemId,
                    'ItemCount': itemCount,
                    'EnemyPartyId': enemyPartyId,
                    'EventType': eventType,
                    'Vanilla': self.getContents(itemId, itemCount),
                    'Swap': '',
                    'Location': self.json[key]['Location'],
                })
        # Sort by location
        for boxes in self.boxes.values():
            boxes.sort(key=lambda x: x['Location'])

    def update(self):
        for chapterBoxes in self.boxes.values():
            for box in chapterBoxes:
                data = self.data[box['key']]
                data['ItemId']['entry']['value'] = box['ItemId']
                data['ItemCount']['entry']['value'] = box['ItemCount']
                data['EnemyPartyId']['entry']['value'] = box['EnemyPartyId']
                data['EventType']['entry']['value'] = box['EventType']
                # TEMPORARY TESTING: NO BATTLES FROM CHESTS IN TOWNS!!!
                if box['key'][:3] == 'MAP' or box['key'][:5] == 'Field':
                    data['EnemyPartyId']['entry']['value'] = 2000
                    data['EventType']['entry']['value'] = 3
                # Must update type for money or item
                if box['ItemId'] == -1 and box['ItemCount'] > 0:
                    data['TreasureType']['entry']['value'] = "ETreasureType::Money"
                else:
                    data['TreasureType']['entry']['value'] = "ETreasureType::Item"
        super().update()

    def getContents(self, itemId, itemCount):
        if itemId < 0:
            return f"{itemCount} pg"
        else:
            item = self.text.getName(itemId)
            if itemCount > 1:
                item += f" x{itemCount}"
            return item

    def print(self, fileName):
        keys = list(self.data.keys()) # TW_0010_TN_1
        headers = self.data[keys[0]].keys()
        with open(fileName, 'w') as sys.stdout:
            print(',,'+','.join(headers))
            for key in keys:
                t = []
                for hi in headers:
                    t.append(self.data[key][hi]['entry']['value'])
                t = list(map(str, t))
                try:
                    count = self.data[key]['ItemCount']['entry']['value']
                    if self.data[key]['TreasureType']['entry']['value'] == 'ETreasureType::Item':
                        item = self.text.getName(self.data[key]['ItemId']['entry']['value'])
                        if count > 1:
                            item = f"{count}x {item}"
                    elif self.data[key]['TreasureType']['entry']['value'] == 'ETreasureType::Money':
                        item = f"{count} pg"
                except:
                    item = ''
                try:
                    location = self.getLocation(key)
                except:
                    location = ''
                print(location + ',' + item + ',' + ','.join(t))

        sys.stdout = sys.__stdout__

    def spoilers(self, filename):
        with open(filename, 'w') as sys.stdout:
            for i in range(8):
                if i == 0:
                    print('')
                    print('')
                    print('--------')
                    print('Prologue')
                    print('--------')
                else:
                    print('')
                    print('')
                    print('----------')
                    print(f'Chapter {i}')
                    print('----------')
                print('')
                for box in self.boxes[i]:
                    print('   ', box['Location'].ljust(40, ' '), box['Vanilla'].ljust(35, ' '), ' <-- ', box['Swap'].ljust(35, ' '))

        sys.stdout = sys.__stdout__


class TEXT(DATA):
    def __init__(self, rom, baseName):
        super().__init__(rom, baseName)
        self.data = list(self.table.values())[0]['data']
        keys = list(self.data[next(iter(self.data))].keys())
        self.nameKey = list(filter(lambda key: 'Name' in key, keys))[0]
        try:
            self.descKey = list(filter(lambda key: 'Description' in key, keys))[0]
        except:
            self.descKey = None

    def getName(self, key):
        return self.data[key][self.nameKey]['entry']['string']

    def getDescription(self, key):
        if self.descKey:
            return self.data[key][self.descKey]['entry']['string']



