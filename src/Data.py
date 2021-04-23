import hjson
import sys
import random
import struct
import io
import hashlib
from functools import partial
from Classes import TYPE, FILE, FloatProperty, StrProperty, EnumProperty, BoolProperty, NameProperty, IntProperty, UInt32Property, ByteProperty, StructProperty, TextProperty, ArrayProperty

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
        addrUexp = self.readInt32() - 0x54
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
        self.addrUexp = addrUexp - self.data.tell()
        self.footer = bytearray(self.data.read())

    def build(self, sizeUEXP=None):
        # Update size of uexp if needed
        if sizeUEXP:
            self.footer[self.addrUexp:self.addrUexp+8] = self.getUInt64(sizeUEXP-4)
        # Build uasset
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
        self.switcher = {
            'EnumProperty': partial(EnumProperty, self.uexp, self.uasset),
            'TextProperty': partial(TextProperty, self.uexp),
            'IntProperty': partial(IntProperty, self.uexp),
            'UInt32Property': partial(UInt32Property, self.uexp),
            'ArrayProperty': partial(ArrayProperty, self.uexp, self.uasset, self.loadEntry, self.buildEntry),
            'StrProperty': partial(StrProperty, self.uexp),
            'BoolProperty': partial(BoolProperty, self.uexp),
            'NameProperty': partial(NameProperty, self.uexp, self.uasset),
            'StructProperty': partial(StructProperty, self.uexp),
            'FloatProperty': partial(FloatProperty, self.uexp),
            'ByteProperty': partial(ByteProperty, self.uexp),
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
                data += self.table[name]['data'].build()
            elif prop == 'MapProperty':
                size = self.table[name]['size']
                data += self.uexp.getInt64(size)
                data += self.uexp.getInt64(self.uasset.getIndex(self.table[name]['type']))
                data += self.uexp.getInt64(self.uasset.getIndex('StructProperty'))
                data += bytearray([0]*5)
                table = self.table[name]['data']
                data += self.uexp.getInt32(len(table))
                for key in table: # For JOB in table
                    if self.table[name]['type'] == 'IntProperty':
                        data += self.uexp.getInt32(key)
                    else: # EnumProperty, NameProperty
                        data += self.uexp.getInt64(self.uasset.getIndex(key))
                    data += self.buildEntry(table[key])
                    data += self.uexp.getInt64(self.none)
        data += self.uexp.getInt64(self.none)
        data += bytearray([0]*4)
        data += bytearray([0xc1, 0x83, 0x2a, 0x9e])
        return data

    def buildEntry(self, entry):
        data = bytearray([])
        for key, d in entry.items():
            data += self.uexp.getInt64(self.uasset.getIndex(key))
            data += self.uexp.getInt64(self.uasset.getIndex(d.dataType))
            data += d.build()
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
                    self.table[name]['data'][key] = self.loadEntry()
            nextValue = self.uexp.readInt64()

    def update(self):
        # Build uexp
        dataUEXP = self.buildTable()
        self.rom.patchFile(dataUEXP, f"{self.fileName}.uexp")
        # Build uasset
        size = len(dataUEXP)
        dataUASSET = self.uasset.build(sizeUEXP=size)
        self.rom.patchFile(dataUASSET, f"{self.fileName}.uasset")


class FLAGS(DATA):
    def __init__(self, rom):
        super().__init__(rom, 'FlagDataAsset')
        self.bools = self.table['BoolFlagDataArray']['data'].array
        self.ints = self.table['IntegerFlagDataArray']['data'].array

        self.boolsDict = {}
        for entry in self.bools:
            f = entry['FlagID']
            v = entry['InitialValue']
            self.boolsDict[f] = v

        self.intsDict = {}
        for entry in self.ints:
            f = entry['FlagID']
            v = entry['InitialValue']
            self.intsDict[f] = v

    def update(self):
        ### DON'T SEEM TO DO ANYTHING
        # self.boolsDict['LIMITATION_TELEPO'] = True
        # self.boolsDict['RELEASE_FASTTRAVEL'] = True
        # self.boolsDict['NPC_JBS01_J00_ON'] = True
        # self.boolsDict['BF_EV00_TUTORIAL_01_END'] = True
        # self.boolsDict['BF_EV00_TUTORIAL_02_END'] = True
        # self.boolsDict['BF_EV00_TUTORIAL_03_END'] = True
        # self.boolsDict['BF_EX_TUTORIAL_END'] = True
        # self.boolsDict['EX01_VICTORY'] = True
        # self.boolsDict['EX02_VICTORY'] = True
        # self.boolsDict['EX03_VICTORY'] = True
        # self.boolsDict['EX04_VICTORY'] = True
        # self.boolsDict['EX05_VICTORY'] = True
        # self.boolsDict['EX06_VICTORY'] = True
        # self.boolsDict['EX07_VICTORY'] = True
        # self.intsDict['ASTERISK_NUMBER'] = 2
        # self.intsDict['INT_CHAPTER_NUMBER'] = 5
        # self.intsDict['RELEASE_MENU_JOBABI'] = 1
        
        for i, value in enumerate(self.boolsDict.values()):
            self.bools[i]['InitialValue'] = value
        
        for i, value in enumerate(self.intsDict.values()):
            self.ints[i]['InitialValue'] = value

        super().update()
            

class ACTIONS(DATA):
    def __init__(self, rom, text):
        super().__init__(rom, 'ActionAbilityAsset')
        self.data = self.table['ActionAbilityDataMap']['data']
        self.text = text

        self.skills = {}
        for Id, skill in self.data.items():
            name = self.text.getName(Id)
            if not name:
                continue
            description = self.text.getDescription(Id)
            job = skill['JobId'].value
            cost = skill['Cost'].value
            costValue = skill['CostValue'].value
            costType = skill['CostType'].value
            self.skills[Id] = {
                'Job': job,
                'Cost': cost,
                'CostValue': costValue,
                'CostType': costType,
                'Name': name,
                'Description': description,
            }

    def update(self):
        for Id, skill in self.skills.items():
            self.data[Id]['JobId'].value = skill['Job']
            self.data[Id]['Cost'].value = skill['Cost']
            self.data[Id]['CostValue'].value = skill['CostValue']
            self.data[Id]['CostType'].value = skill['CostType']
        super().update()


class SUPPORT(DATA):
    def __init__(self, rom, text):
        super().__init__(rom, 'SupportAbilityAsset')
        self.data = self.table['SupportAbilityDataMap']['data']
        self.text = text

        self.skills = {}
        for Id, skill in self.data.items():
            name = self.text.getName(Id)
            if not name:
                continue
            description = self.text.getDescription(Id)
            cost = skill['AbilityCost'].value
            self.skills[Id] = {
                'AbilityCost': cost,
                'Name': name,
                'Description': description,
            }

    def update(self):
        for Id, skill in self.skills.items():
            self.data[Id]['AbilityCost'].value = skill['AbilityCost']
        super().update()


class JOBSTATS(DATA):
    def __init__(self, rom):
        super().__init__(rom, 'JobCorrectionAsset')
        self.data = self.table['JobLevelMap']['data']

    # Shuffles jobs
    def shuffleStats(self):
        keys = list(self.data.keys())
        for i, ki in enumerate(self.data):
            kj = random.sample(keys[i:], 1)[0]
            self.data[ki], self.data[kj] = self.data[kj], self.data[ki]
            self.data[ki]['_id'], self.data[kj]['_id'] = self.data[kj]['_id'], self.data[ki]['_id'] # SWAP ID BACK

    # Unbiased shuffling
    def randomStats(self):
        stats = list(self.data['EJobEnum::JE_Sobriety'].keys())[1:] # omit _id
        keys = list(self.data.keys())
        for stat in stats: # HP, MP, ...
            for i, ki in enumerate(self.data): # Freelancer, ...
                kj = random.sample(keys[i:], 1)[0]
                self.data[ki][stat], self.data[kj][stat] = self.data[kj][stat], self.data[ki][stat]


class JOBDATA(DATA):
    def __init__(self, rom, actionText, supportText):
        super().__init__(rom, 'JobDataAsset')
        self.data = self.table['JobDataMap']['data']
        self.job = {}
        self.skills = []
        self.support = []
        for name, data in self.data.items():
            skills = data['ActionAbilityArray'].array
            support = data['SupportAbilityArray'].array
            jobTraitId1 = data['JobTraitId1'].value
            jobTraitId2 = data['JobTraitId2'].value
            self.job[name] = [k if k > 0 else u for k,u in zip(skills, support)]
            self.job[name] += [jobTraitId1, jobTraitId2]
            self.skills += list(filter(lambda x: x > 0, skills))
            self.support += list(filter(lambda x: x > 0, support))
            self.support += [jobTraitId1, jobTraitId2]

        self.nameToId = {}
        for skill in self.skills:
            name = actionText.getName(skill)
            assert name
            assert name not in self.nameToId
            self.nameToId[name] = skill
        for support in self.support:
            name = supportText.getName(support)
            assert name
            assert name not in self.nameToId
            self.nameToId[name] = support

    def getIds(self, *names):
        return [self.nameToId[n] for n in names]

    def pickIds(self, num, *names):
        assert num <= len(names)
        count = random.randint(num, len(names))
        return [self.nameToId[n] for n in random.sample(names, count)]

    def pickGroup(self, groups):
        group = random.sample(groups, 1)[0]
        return self.getIds(*group)

    def update(self):
        for name, data in self.data.items():
            data['ActionAbilityArray'].array = [s if s < 200000 else -1 for s in self.job[name][:15]]
            data['SupportAbilityArray'].array = [s if s >= 200000 else -1 for s in self.job[name][:15]]
            data['JobTraitId1'].value = self.job[name][15]
            data['JobTraitId2'].value = self.job[name][16]
        super().update()


class MONSTERPARTY(DATA):
    def __init__(self, rom):
        super().__init__(rom, 'MonsterPartyAsset')
        self.data = self.table['MonsterPartyMap']['data']
        self.levels = {}
        for party in self.data.values():
            for i in range(1, 7):
                Id = party[f"Monster{i}Id"].value
                Level = party[f"Monster{i}Level"].value
                if Id < 0:
                    continue
                if Id not in self.levels:
                    self.levels[Id] = set()
                self.levels[Id].add(Level)

    # NOTE: This is a crude estimate of chapter based on the enemy's level!
    def getChapter(self, Id):
        if Id not in self.levels:
            return

        levels = self.levels[Id].difference([1])
        if levels == set():
            return

        chapter = int(min(levels) / 10)
        return min(chapter, 7)

    def update(self):
        # 300201 Selene
        # 300401 Dag
        # 300101 Horten
        # self.data[700001]['Monster1Id']['value'] = 300101

        # Originally "EV30_0110" for Selene & Dag
        # Messed with cutscene (Killed Selene; custscene with her started AFTER)
        # self.data[700001]['BattleEventId']['value'] = "EV30_0210"
        
        super().update()


class MONSTERS(DATA):
    def __init__(self, rom, monster, items, party):
        super().__init__(rom, 'MonsterDataAsset')
        self.data = self.table['MonsterDataMap']['data']
        self.monster = monster
        self.items = items
        self.party = party

        self.steals = {}
        self.stealsRare = {}
        self.drops = {}
        self.dropsRare = {}
        for d in self.data.values():
            Id = d['Id'].value
            # Skip monster with no distinguishable chapter (i.e. level)
            chapter = self.party.getChapter(Id)
            if not chapter:
                continue
            # Skip monster without a name
            name = self.monster.getName(Id)
            if not name:
                continue

            stealItem = d['StealItem'].value
            self.steals[Id] = {
                'shuffle': stealItem != -1,
                'chapter': self.party.getChapter(Id), # For grouping by "chapters" (TODO: do this accurately)
                'item': stealItem,
            }

            stealRareItem = d['StealRareItem'].value
            self.stealsRare[Id] = {
                'shuffle': stealRareItem != -1,
                'chapter': self.party.getChapter(Id),
                'item': stealRareItem,
            }

            dropItem = d['DropItemId'].value
            self.drops[Id] = {
                'shuffle': dropItem != -1,
                'chapter': self.party.getChapter(Id),
                'item': dropItem,
            }

            dropRareItem = d['DropRareItemId'].value
            self.dropsRare[Id] = {
                'shuffle': dropRareItem != -1,
                'chapter': self.party.getChapter(Id),
                'item': dropRareItem,
            }

        self.resistance = {}
        for d in self.data.values():
            Id = d['Id'].value
            self.resistance[Id] = {
                'isBoss': d['MonsterRank'].value == 'EMonsterRankEnum::MRE_Boss',
                # MAGIC
                'Magic': {
                    'FireResistance': d['FireResistance'].value,
                    'WaterResistance': d['WaterResistance'].value,
                    'LightningResistance': d['LightningResistance'].value,
                    'EarthResistance': d['EarthResistance'].value,
                    'WindResistance': d['WindResistance'].value,
                    'LightResistance': d['LightResistance'].value,
                    'DarknessResistance': d['DarknessResistance'].value,
                },
                # WEAPONS
                'Weapon': {
                    'ShortSwordResistance': d['ShortSwordResistance'].value,
                    'SwordResistance': d['SwordResistance'].value,
                    'AxeResistance': d['AxeResistance'].value,
                    'SpearResistance': d['SpearResistance'].value,
                    'BowResistance': d['BowResistance'].value,
                    'StaffResistance': d['StaffResistance'].value,
                },
                # # STATS -- include????
                # 'BuffDebuffResistance': d['BuffDebuffResistance'].value,
                # STATUS EFFECTS
                'Effects': {
                    'ResistancePoison': (d['ResistancePoison'], d['ResistanceLevelPoison']),
                    'ResistanceDark': (d['ResistanceDark'], d['ResistanceLevelDark']),
                    'ResistanceSilence': (d['ResistanceSilence'], d['ResistanceLevelSilence']),
                    'ResistanceSleep': (d['ResistanceSleep'], d['ResistanceLevelSleep']),
                    'ResistanceParalysis': (d['ResistanceParalysis'], d['ResistanceLevelParalysis']),
                    'ResistanceFear': (d['ResistanceFear'], d['ResistanceLevelFear']),
                    'ResistanceBerzerk': (d['ResistanceBerzerk'], d['ResistanceLevelBerzerk']),
                    'ResistanceConfusion': (d['ResistanceConfusion'], d['ResistanceLevelConfusion']),
                    'ResistanceSeduction': (d['ResistanceSeduction'], d['ResistanceLevelSeduction']),
                    'ResistanceInstantDeath': (d['ResistanceInstantDeath'], d['ResistanceLevelInstantDeath']),
                    'ResistanceDeathTimer': (d['ResistanceDeathTimer'], d['ResistanceLevelDeathTimer']),
                    'ResistanceStop': (d['ResistanceStop'], d['ResistanceLevelStop']),
                    'ResistanceFreeze': (d['ResistanceFreeze'], d['ResistanceLevelFreeze']),
                    'ResistanceBattleExclusion': (d['ResistanceBattleExclusion'], d['ResistanceLevelBattleExclusion']),
                    'ResistanceTransparent': (d['ResistanceTransparent'], d['ResistanceLevelTransparent']),
                    'ResistancePaint': (d['ResistancePaint'], d['ResistanceLevelPaint']),
                    'ResistanceEpidemic': (d['ResistanceEpidemic'], d['ResistanceLevelEpidemic']),
                    'ResistanceSlow': (d['ResistanceSlow'], d['ResistanceLevelSlow']),
                    'ResistanceWeakPoint': (d['ResistanceWeakPoint'], d['ResistanceLevelWeakPoint']),
                },
            }

        # Store vanilla sword resistance for early bosses
        self.selene = self.resistance[300201]['Weapon']['SwordResistance']
        self.dag = self.resistance[300401]['Weapon']['SwordResistance']
        self.horten = self.resistance[300101]['Weapon']['SwordResistance']

    def update(self):

        # Ensure vanilla weakness to Sir Sloan's attack, just a safety precaution
        self.resistance[300201]['Weapon']['SwordResistance'] = self.selene
        self.resistance[300401]['Weapon']['SwordResistance'] = self.dag
        self.resistance[300101]['Weapon']['SwordResistance'] = self.horten

        for d in self.data.values():
            Id = d['Id'].value
            # Stats and weaknesses
            for key, value in self.resistance[Id]['Magic'].items():
                d[key].value = value
            for key, value in self.resistance[Id]['Weapon'].items():
                d[key].value = value
            for key, (res, level) in self.resistance[Id]['Effects'].items():
                key2 = 'ResistanceLevel' + key[10:]
                d[key] = res
                d[key2] = level
            # Stealable items
            if Id in self.steals:
                d['StealItem'].value = self.steals[Id]['item']
            if Id in self.stealsRare:
                d['StealItem'].value = self.steals[Id]['item']
            # Dropped items
            if Id in self.drops:
                d['DropItemId'].value = self.drops[Id]['item']
            if Id in self.dropsRare:
                d['DropRareItemId'].value = self.dropsRare[Id]['item']

        super().update()

    # "PQ" in the code, "PG" in the game
    def scalePG(self, scale):
        assert scale > 0
        for d in self.data.values():
            pg = int(scale * d['pq'].value)
            d['pq'].value = min(pg, 99999)

    def scaleEXP(self, scale):
        assert scale > 0
        for d in self.data.values():
            exp = int(scale * d['Exp'].value)
            d['Exp'].value = min(exp, 99999)

    def scaleJP(self, scale):
        assert scale > 0
        for d in self.data.values():
            jp = int(scale * d['Jp'].value)
            d['Jp'].value = min(jp, 9999)

    def spoilers(self, filename):
        with open(filename, 'w') as sys.stdout:
            for Id, data in self.data.items():
                if Id in self.steals or Id in self.stealsRare or Id in self.drops or Id in self.dropsRare:
                    name = self.monster.getName(Id)
                    assert name
                else:
                    continue

                if name == "Bandit A":
                    print('here')
                items = []

                item = self.drops[Id]['item']
                if item > 0:
                    items.append(self.items.getName(self.drops[Id]['item']))
                    chapter = self.drops[Id]['chapter']
                else:
                    items.append("NONE")

                item = self.dropsRare[Id]['item']
                if item > 0:
                    items.append(self.items.getName(self.dropsRare[Id]['item']))
                    chapter = self.dropsRare[Id]['chapter']
                else:
                    items.append("NONE")

                item = self.steals[Id]['item']
                if item > 0:
                    items.append(self.items.getName(self.steals[Id]['item']))
                    chapter = self.steals[Id]['chapter']
                else:
                    items.append("NONE")

                item = self.stealsRare[Id]['item']
                if item > 0:
                    items.append(self.items.getName(self.stealsRare[Id]['item']))
                    chapter = self.stealsRare[Id]['chapter']
                else:
                    items.append("NONE")

                print(', '.join([name, str(chapter)] + items))

        sys.stdout = sys.__stdout__


class QUESTS(DATA):
    def __init__(self, rom, text, locations):
        super().__init__(rom, 'QuestAsset')
        self.text = text
        self.locations = locations
        self.questArray = self.table['QuestArray']['data'].array
        with open('json/quests.json','r') as file:
            self.json = hjson.load(file)

        ## Organize data for shuffling
        self.questRewards = {i:[] for i in range(8)}
        for i, quest in enumerate(self.questArray[148:]):
            if quest['RewardType'].value != 'EQuestRewardType::None':
                rewardId = quest['RewardID'].value
                rewardCount = quest['RewardCount'].value
                subQuestIndex = quest['SubQuestIndex'].value
                chapter = self.getChapter(quest['SubQuestIndex'].value)
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
                self.questArray[i]['RewardID'].value = quest['RewardId']
                self.questArray[i]['RewardCount'].value = quest['RewardCount']
                if quest['RewardId'] == -1 and quest['RewardCount'] > 0:
                    self.questArray[i]['RewardType'].value = "EQuestRewardType::Money"
                else:
                    self.questArray[i]['RewardType'].value = "EQuestRewardType::Item"

        # ### TEMPORARY: ONLY SEEMS TO UPDATE THE TRACKER ICON, NOT ACTUALLY SKIPPING SCENES
        # questID = []
        # for i, quest in enumerate(self.questArray):
        #     questID.append(quest['QuestID']['value'])

        # index = 0
        # for quest in self.questArray:
        #     # quest['NextQuestID']['value'] = questID[index]
        #     quest['NextQuestID']['value'] = "MAIN_S020610"

        super().update()

    def getReward(self, rewardId, rewardCount):
        if rewardId < 0 and rewardCount > 0:
            return f"{rewardCount} pg"
        if rewardId > 0:
            item = self.text.getName(rewardId)
            assert item
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
                itemId = value['ItemId'].value
                itemCount = value['ItemCount'].value
                enemyPartyId = value['EnemyPartyId'].value
                eventType = value['EventType'].value
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
                data['ItemId'].value = box['ItemId']
                data['ItemCount'].value = box['ItemCount']
                data['EnemyPartyId'].value = box['EnemyPartyId']
                data['EventType'].value = box['EventType']
                # TEMPORARY TESTING: NO BATTLES FROM CHESTS IN TOWNS!!!
                # if box['key'][:3] == 'MAP' or box['key'][:5] == 'Field':
                #     data['EnemyPartyId'] = 2000
                #     data['EventType'] = 3
                # Must update type for money or item
                if box['ItemId'] == -1 and box['ItemCount'] > 0:
                    data['TreasureType'].value = "ETreasureType::Money"
                else:
                    data['TreasureType'].value = "ETreasureType::Item"
        super().update()

    def getContents(self, itemId, itemCount):
        if itemId < 0:
            return f"{itemCount} pg"

        item = self.text.getName(itemId)
        assert item
        if itemCount > 1:
            item += f" x{itemCount}"
        return item

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
        descKey = self.nameKey.replace('Name', 'Description')
        if descKey in keys:
            self.descKey = descKey
        else:
            self.descKey = None

    def getName(self, key):
        if key in self.data:
            return self.data[key][self.nameKey].string

    def getDescription(self, key):
        if self.descKey:
            return self.data[key][self.descKey].string
