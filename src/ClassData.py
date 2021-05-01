from dataclasses import dataclass, field
from typing import List
from Classes import EnumProperty
import random
from copy import deepcopy

@dataclass
class ACTIONSKILL:
    Id: int
    Job: int
    Cost: str
    CostValue: int
    CostType: str
    Name: str
    Description: str

@dataclass
class SUPPORTSKILL:
    Id: int
    Cost: int
    Name: str
    Description: str

@dataclass
class MAGIC:
    FireResistance: EnumProperty
    WaterResistance: EnumProperty
    LightningResistance: EnumProperty
    EarthResistance: EnumProperty
    WindResistance: EnumProperty
    LightResistance: EnumProperty
    DarknessResistance: EnumProperty

@dataclass
class WEAPONS:
    ShortSwordResistance: EnumProperty
    SwordResistance: EnumProperty
    AxeResistance: EnumProperty
    SpearResistance: EnumProperty
    BowResistance: EnumProperty
    StaffResistance: EnumProperty

@dataclass
class EFFECTS:
    ResistancePoison: EnumProperty
    ResistanceLevelPoison: EnumProperty
    ResistanceDark: EnumProperty
    ResistanceLevelDark: EnumProperty
    ResistanceSilence: EnumProperty
    ResistanceLevelSilence: EnumProperty
    ResistanceSleep: EnumProperty
    ResistanceLevelSleep: EnumProperty
    ResistanceParalysis: EnumProperty
    ResistanceLevelParalysis: EnumProperty
    ResistanceFear: EnumProperty
    ResistanceLevelFear: EnumProperty
    ResistanceBerzerk: EnumProperty
    ResistanceLevelBerzerk: EnumProperty
    ResistanceConfusion: EnumProperty
    ResistanceLevelConfusion: EnumProperty
    ResistanceSeduction: EnumProperty
    ResistanceLevelSeduction: EnumProperty
    ResistanceInstantDeath: EnumProperty
    ResistanceLevelInstantDeath: EnumProperty
    ResistanceDeathTimer: EnumProperty
    ResistanceLevelDeathTimer: EnumProperty
    ResistanceStop: EnumProperty
    ResistanceLevelStop: EnumProperty
    ResistanceFreeze: EnumProperty
    ResistanceLevelFreeze: EnumProperty
    ResistanceBattleExclusion: EnumProperty
    ResistanceLevelBattleExclusion: EnumProperty
    ResistanceTransparent: EnumProperty
    ResistanceLevelTransparent: EnumProperty
    ResistancePaint: EnumProperty
    ResistanceLevelPaint: EnumProperty
    ResistanceEpidemic: EnumProperty
    ResistanceLevelEpidemic: EnumProperty
    ResistanceSlow: EnumProperty
    ResistanceLevelSlow: EnumProperty
    ResistanceWeakPoint: EnumProperty
    ResistanceLevelWeakPoint: EnumProperty

@dataclass
class ITEM:
    Id: int
    Count: int = 1
    Name: str = ''

    def isMoney(self):
        return self.Id == -1 and self.Count > 1

    def canShuffle(self):
        return self.isMoney() or self.Name is not None

    def setItem(self, newItem):
        for attr, value in newItem.__dict__.items():
            setattr(self, attr, value)

    def getItem(self):
        return deepcopy(self)

    def getString(self):
        if self.isMoney():
            return f"{self.Count} pg"
        if self.Count > 1:
            return f"{self.Name} x{self.Count}"
        return self.Name

@dataclass
class ITEMENEMY(ITEM):

    def setItem(self, newItem):
        assert not newItem.isMoney()   # Enemy drops and steals must be items; they can never be money!
        super().setItem(newItem)
        self.Count = 1

    def getItem(self):
        item = deepcopy(self)
        if item.canShuffle(): # otherwise keep the Count that the default value of 1
            item.Count = random.choices([1, 2, 3], [0.85, 0.10, 0.05])[0]
        return item

@dataclass
class CHEST:
    Key: str
    Chapter: int
    Item: ITEM
    EventType: int
    EnemyPartyId: int
    Location: str

    def __post_init__(self):
        self.Vanilla = self.Item.getString()

    def getString(self):
        return ''.join([
            self.Location.ljust(40, ' '),
            self.Vanilla.ljust(35, ' '),
            " <-- ",
            self.Item.getString(),
        ])

@dataclass
class QUESTREWARD:
    Index: int
    Chapter: int
    Item: ITEM
    Location: str
    SubQuestIndex: int
    SubQuestName: str

    def __post_init__(self):
        self.Vanilla = self.Item.getString()

    def getString(self):
        return ''.join([
            str(self.SubQuestIndex).ljust(5, ' '),
            self.Location.ljust(20, ' '),
            self.SubQuestName.ljust(35, ' '),
            self.Vanilla.ljust(35, ' '),
            " <-- ",
            self.Item.getString(),
        ])

@dataclass
class DROP:
    Chapter: int
    EnemyId: int
    Item: ITEMENEMY
    RareItem: ITEMENEMY
    Name: str

    def getString(self):
        itemString = self.Item.getString()
        if not itemString:
            itemString = '-'*5
        rareItemString = self.RareItem.getString()
        if not rareItemString:
            rareItemString = '-'*5
        return ' '.join([
            itemString.ljust(35, ' '),
            rareItemString.ljust(35, ' '),
        ])

@dataclass
class STEAL:
    Chapter: int
    EnemyId: int
    Item: ITEMENEMY
    RareItem: ITEMENEMY
    Name: str

    def getString(self):
        itemString = self.Item.getString()
        if not itemString:
            itemString = '-'*5
        rareItemString = self.RareItem.getString()
        if not rareItemString:
            rareItemString = '-'*5
        return ' '.join([
            itemString.ljust(35, ' '),
            rareItemString.ljust(35, ' '),
        ])

        
@dataclass
class JOB:
    Name: str
    # Stats: dict
    Actions: List[ACTIONSKILL] = field(default_factory=lambda: [None]*15)
    Support: List[SUPPORTSKILL] = field(default_factory=lambda: [None]*17)
    Vacant: List[bool] = field(default_factory=lambda: [True]*17)

    def __post_init__(self):
        self.numActionSlots = 15
        self.numSupportSlots = 17
        self.numSupport = 0

    def resetSkills(self):
        self.Actions = [None]*15
        self.Support = [None]*17
        self.Vacant = [True]*17
        self.numActionSlots = 15
        self.numSupportSlots = 17
        self.numSupport = 0

    def getActions(self):
        return [-1 if not a else a.Id for a in self.Actions]

    def getSupport(self):
        return [-1 if not s else s.Id for s in self.Support[:15]]

    def getTrait1(self):
        return self.Support[15].Id

    def getTrait2(self):
        return self.Support[16].Id

    def setActions(self, lst):
        for i, li in enumerate(lst):
            self.Actions[i] = li

    def setSupport(self, lst):
        for i, li in enumerate(lst):
            self.Support[i] = li

    def setTrait1(self, trait):
        self.Support[15] = trait
        self.Vacant[15] = False
        self.numSupportSlots -= 1

    def setTrait2(self, trait):
        self.Support[16] = trait
        self.Vacant[16] = False
        self.numSupportSlots -= 1

    def isTrait1Empty(self):
        return self.Vacant[15]

    def isTrait2Empty(self):
        return self.Vacant[16]

    def roomForSupport(self):
        return (self.numSupport < 8) and (self.numSupportSlots > 0)

    def roomForAction(self):
        return self.numActionSlots > 0
        
    def vacantActionSlots(self):
        return self.numActionSlots

    def vacantSupportSlots(self):
        return self.numSupportSlots

    def fillActionSlots(self, skills):
        # Sample without replacement
        slots = []
        indices = list(range(15))
        for _ in enumerate(skills):
            j = random.choices(indices, self.Vacant[:15])[0]
            self.Vacant[j] = False
            slots.append(j)
        slots.sort()

        # Fill slots
        for slot, skill in zip(slots, skills):
            self.Actions[slot] = skill
            self.numActionSlots -= 1
            self.numSupportSlots -= 1

    def fillSupportSlots(self, skills):
        # Sample without replacement
        slots = []
        indices = list(range(17))
        for _ in enumerate(skills):
            j = random.choices(indices, self.Vacant)[0]
            self.Vacant[j] = False
            slots.append(j)
        slots.sort()

        # Fill slots
        for slot, skill in zip(slots, skills):
            self.Support[slot] = skill
            self.numActionSlots -= slot < 15
            self.numSupportSlots -= 1
            self.numSupport += slot < 15    
