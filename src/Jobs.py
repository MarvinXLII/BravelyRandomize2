import random
import hjson
import sys
sys.path.append("..")


## TODO
# - Should Benediction be included with healing? NO if it works with items!
#   --> White mage cures only!!!!
# - does Magic Critical only affect spells or also physical attacks with an element? e.g. Sky Slicer of thief
#   --> These attack can get critical without Magic Critical (allows magic crits)
# - weapon lores should probably end up on jobs with weapon-specific attacks???
# - should job sampling for weapon-based attacks be biased towards jobs with strong weapons affinities (S, A, .. maybe B?)
# - How does "In One's Element" work if spell cost become BP or HP?
# - Do Supports work properly as Traits? (and vice versa?)
#   --> Yes, they seem to work just fine! (though not each and every one tested)
# - Do bosses fight the same way with skills and support swapped? (presumably)
#   --> Yes, it seems like Dag uses its vanilla skills

# OFFTOPIC
# - Test swapping cutscenes for asterisks earned.
# - How about items collected, eg. map, stones?
# - Healing in the main menu
#   --> Didn't work a while back but works fine now. Not sure what the issue was before.

# What if a job is all supports?
# Is there a max number of supports allowed?


def randomActionCosts(jobData):

    actionDict = {a.Name:a for a in jobData.actionsDict.values()}
    done = {}
    for i, job in enumerate(jobData.jobs):
        for action in job.Actions:
            if action:
                done[action.Name] = False

    # Load groups
    groups = hjson.load(open("json/groups.json", 'r'))
    costData = hjson.load(open("json/costs.json", 'r'))

    # Update groups all at once with the same costs
    weightDict = {
        'ECommandCostEnum::CCE_HP': 40,  # 29
        'ECommandCostEnum::CCE_MP': 170, # 188
        'ECommandCostEnum::CCE_BP': 40,  # 32
        'ECommandCostEnum::CCE_pq': 20,  # 12
    }
    costTypes = list(weightDict.keys())
    weights = list(weightDict.values())
    idx = {t:i for i, t in enumerate(costTypes)}

    def randomCost(t, action):
        # Update weights
        i = idx[t]
        weights[i] = max(weights[i]-1, 0)

        # Keep original
        if actionDict[action].Cost == t:
            return

        # Update cost
        actionDict[action].Cost = t
        if t == 'ECommandCostEnum::CCE_pq':
            actionDict[action].CostValue = 10 * costData[action]['ECommandCostEnum::CCE_MP'] * costData[action]['ECommandCostEnum::CCE_BP']
        else:
            actionDict[action].CostValue = costData[action][t]

        # Update CostType
        if t == 'ECommandCostEnum::CCE_HP':
            actionDict[action].CostType = 'ECommandCostTypeEnum::CCTE_Maximum_Percent'
        else:
            actionDict[action].CostType = 'ECommandCostTypeEnum::CCTE_Value'

    
    for group in groups.values():
        # pick cost type from weights
        t = random.choices(costTypes, weights)[0]
        
        # Loop over actions in the group
        for action in group:
            # Don't try this again later!
            done[action] = True
            
            # Skip in not included in the cost data
            if action not in costData:
                continue

            # Pick and set a random cost
            randomCost(t, action)

    # Update all the rests of the actions
    for job in jobData.jobs:
        for action in job.Actions:
            if not action:
                continue
            if done[action.Name]:
                continue
            ### DO STUFF
            done[action.Name] = True
            if action.Name not in costData:
                continue
            # pick cost type from weights
            t = random.choices(costTypes, weights)[0]
            randomCost(t, action.Name)
                


## INPUT DATA COMES FROM THE JOBDATA OBJECT
def shuffleJobAbilities(jobData):
    # Job skills objects
    jobs = jobData.jobs
    
    # Candidate lists
    actions = list(jobData.actionsDict)
    support = list(jobData.supportDict)

    # Store assignments for easy job lookup
    assignments = {} # Maps Skill Id -> Job Id

    # Reset skills and vacant slots
    for job in jobs:
        job.resetSkills()

    def fillGroup(skills):
        # Pick a job
        i = random.randint(0, 23)
        while jobs[i].vacantActionSlots() < len(skills):
            i = random.randint(0, 23)
            
        # Fill slots
        objs = [jobData.actionsDict[Id] for Id in skills]
        jobs[i].fillActionSlots(objs)

        # Filter candidates and fill assignments
        for skill in skills:
            assignments[skill] = i
            actions.remove(skill)

    # def fillSupport(skills):
    #     # Pick a job
    #     i = random.randint(0, 23)
    #     while jobs[i].vacantSupportSlots() < len(skills):
    #         i = random.randint(0, 23)

    #     # Fill slots
    #     objs = [jobData.supportDict[Id] for Id in skills]
    #     jobs[i].fillSupportSlots(objs)

    #     # Filter candidates and fill assignments
    #     for skill in skills:
    #         assignments[skill] = i
    #         support.remove(skill)

    def addActions(skills, targets):
        random.shuffle(skills) # Order doesn't matter!
        random.shuffle(targets)
        for target in targets:
            i = assignments[target]
            if jobs[i].vacantActionSlots() >= len(skills):
                objs = [jobData.actionsDict[Id] for Id in skills]
                jobs[i].fillActionSlots(objs)
                for skill in skills:
                    assignments[skill] = i
                    actions.remove(skill)
                return True
        return False

    def addSupport(skills, targets):
        random.shuffle(skills) # Order doesn't matter!
        random.shuffle(targets)
        for target in targets:
            i = assignments[target]
            if jobs[i].vacantSupportSlots() >= len(skills):
                objs = [jobData.supportDict[Id] for Id in skills]
                jobs[i].fillSupportSlots(objs)
                for skill in skills:
                    assignments[skill] = i
                    support.remove(skill)
                return True
        return False
        

    

            


# def shuffleJobAbilities(data):
#     candidates = {
#         'skills': list(data.skills),
#         'support': list(data.support),
#     }
#     assignments = {} # Skill/Support ID -> Job ID
    
#     ## Build weights to keep track of slots
#     # 15 skills/supports + trait1 + trait2
#     vacant = [[True]*17 for i in range(24)]

#     # Job names
#     names = list(data.job.keys())

#     # GROUP OF SKILLS up to slot 15
#     def fillGroup(skills):

#         # Pick a job
#         i = random.randint(0, 23)
#         while sum(vacant[i][:15]) < len(skills): # Ensures enough room for skills
#             i = random.randint(0, 23)

#         # Setup slots for the remaining skills
#         slots = []
#         for _ in enumerate(skills):
#             j = random.choices(range(15), vacant[i][:15])[0]
#             vacant[i][j] = False
#             slots.append(j)
#         slots.sort()

#         # Assign skills to the slots
#         for slot, skill in zip(slots, skills):
#             data.job[names[i]][slot] = skill
#             assignments[skill] = i

#         # Remove skills from candidates
#         candidates['skills'] = list(filter(lambda x: x not in skills, candidates['skills']))

#     # GROUP OF SUPPORT up to slot 17 (includes traits!)
#     def fillSupport(skills):

#         # Pick a job
#         i = random.randint(0, 23)
#         while sum(vacant[i][:17]) < len(skills): # Ensures enough room for skills
#             i = random.randint(0, 23)

#         # Setup slots for the remaining skills
#         slots = []
#         for _ in enumerate(skills):
#             j = random.choices(range(17), vacant[i][:17])[0]
#             vacant[i][j] = False
#             slots.append(j)
#         slots.sort()

#         # Assign skills to the slots
#         for slot, skill in zip(slots, skills):
#             data.job[names[i]][slot] = skill
#             assignments[skill] = i

#         # Remove skills from candidates
#         candidates['support'] = list(filter(lambda x: x not in skills, candidates['support']))

#     def addSkills(skills, targets):
#         random.shuffle(skills) # Order not required for these!

#         target = random.sample(targets, 1)[0]
#         i = assignments[target]
#         if sum(vacant[i]) < len(skills):
#             return False

#         for s in skills:
#             j = random.choices(range(17), vacant[i])[0]
#             vacant[i][j] = False
#             data.job[names[i]][j] = s

#         # Remove skills from candidates
#         candidates['skills'] = list(filter(lambda x: x not in skills, candidates['skills']))

#         return True
        

#     def addSupport(supports, targets):
#         random.shuffle(supports) # Order not required for these!
        
#         target = random.sample(targets, 1)[0]
#         i = assignments[target]
#         if sum(vacant[i]) < len(supports):
#             return False

#         for s in supports:
#             j = random.choices(range(17), vacant[i])[0]
#             vacant[i][j] = False
#             data.job[names[i]][j] = s

#         # Remove support skills from candidates
#         candidates['support'] = list(filter(lambda x: x not in supports, candidates['support']))

#         return True
        

    #### FIRST: FILL ALL GROUPINGS
    groups = hjson.load(open("json/groups.json", 'r'))

    # MONK SKILLS
    monk = jobData.pickIds(1, groups['monk']) #"Inner Alchemy", "Invigorate", "Mindfulness")
    fillGroup(monk)
    
    # Healing spells
    wm_cure = jobData.getIds(groups['cure']) #"Cure", "Cura", "Curaga")
    fillGroup(wm_cure)

    # WHITE MAGE -- revives
    wm_raise = jobData.getIds(groups['raise']) #"Raise", "Arise", "Raise All")
    fillGroup(wm_raise)

    # WHITE MAGE -- statuses
    wm_basuna = jobData.getIds(groups['basuna']) #"Basuna", "Esuna")
    fillGroup(wm_basuna)

    # BLACK MAGE
    bm_fire = jobData.getIds(groups['fire']) #"Fire", "Fira", "Firaga", "Flare")
    fillGroup(bm_fire)
    
    bm_blizzard = jobData.getIds(groups['blizzard']) #"Blizzard", "Blizzara", "Blizzaga", "Freeze")
    fillGroup(bm_blizzard)
    
    bm_thunder = jobData.getIds(groups['thunder']) #"Thunder", "Thundara", "Thundaga", "Burst")
    fillGroup(bm_thunder)

    # VANGUARD
    vg_target = jobData.getIds(groups['target']) #"Aggravate", "Infuriate")
    fillGroup(vg_target)

    vg_earth = jobData.getIds(groups['earth']) #"Sword of Stone", "Quake Blade")
    fillGroup(vg_earth)

    vg_delay = jobData.getIds(groups['delay']) #"Shield Bash", "Ultimatum")
    fillGroup(vg_delay)

    # TROUBADOR -- Born Entertainor support also works for Artist skills
    bard = jobData.pickIds(4, groups['bard']) #"Don't Let 'Em Get to You", "Don't Let 'Em Trick You", "Step into the Spotlight",
                          #"(Won't) Be Missing You", "Right Through Your Fingers", "Hurts So Bad",
                          #"Work Your Magic", "All Killer No Filler")
    fillGroup(bard)

    # PICTOMANCER
    pictomancer = jobData.pickIds(3, groups['pictomancer']) #"Disarming Scarlet", "Disenchanting Mauve", "Incurable Coral", "Indefensible Teal", "Zappable Chartreuse", )
    fillGroup(pictomancer)

    # TAMER
    tamer = jobData.getIds(groups['tamer']) #"Capture", "Off the Leash", "Off the Chain")
    fillGroup(tamer)

    # THIEF
    thief_steal_items = jobData.getIds(groups['steal_items'])#"Steal")
    fillGroup(thief_steal_items)

    thief_steal_other = jobData.pickIds(1, groups['steal_other'])#"Steal Breath", "Steal Spirit", "Steal Courage")
    fillGroup(thief_steal_other)

    thief_wind = jobData.getIds(groups['wind'])#"Sky Slicer", "Tornado's Edge")
    fillGroup(thief_wind)

    # GAMBLER
    gambler_elem = jobData.getIds(groups['gambler'])#"Elemental Wheel", "Real Elemental Wheel")
    fillGroup(gambler_elem)

    gambler_wheels = jobData.pickIds(3, groups['wheels'])#"Odds or Evens", "Life or Death", "Spin the Wheel", "Triples", "Bold Gambit", "Unlucky Eight")
    fillGroup(gambler_wheels)

    # BERZERKER
    berz_berzerk = jobData.getIds(groups['berzerk'])#"Vent Fury")
    fillGroup(berz_berzerk)

    berz_attack_all = jobData.getIds(groups['berz_all'])#"Crescent Moon", "Level Slash", "Death's Door")
    fillGroup(berz_attack_all)

    berz_attack_one = jobData.getIds(groups['berz_one'])#"Double Damage", "Amped Strike")
    fillGroup(berz_attack_one)

    berz_water_attack = jobData.getIds(groups['water'])#"Water Damage", "Flood Damage")
    fillGroup(berz_water_attack)

    # RED MAGE
    rm_earth = jobData.getIds(groups['stone'])#"Stone", "Stonera", "Stonega", "Quake", "Disaster")
    rm_wind = jobData.getIds(groups['aero'])#"Aero", "Aerora", "Aeroga", "Tornado", "Disaster")
    if random.random() > 0.5:
        rm_earth.append(jobData.getIds(groups["disaster"])[0])
    else:
        rm_wind.append(jobData.getIds(groups["disaster"])[0])
    fillGroup(rm_earth)
    fillGroup(rm_wind)

    rm_heal = jobData.getIds(groups['heal'])#"Heal", "Healara", "Healaga")
    fillGroup(rm_heal)

    # HUNTER
    hunter_random = jobData.getIds(groups['hunter'])#"Quickfire Flurry", "Grand Barrage")
    fillGroup(hunter_random)

    hunter_slayer = jobData.pickIds(4, groups['slayer'])#"Bug Slayer","Plant Slayer","Beast Slayer","Aquatic Slayer","Humanoid Slayer","Undead Slayer","Demon Slayer","Spirit Slayer")
    random.shuffle(hunter_slayer)
    fillGroup(hunter_slayer)

    # SHIELDMASTER
    shield = jobData.getIds(groups['shield'])#"Bodyguard", "Defender of the People")
    fillGroup(shield)

    shield_hitter = jobData.getIds(groups['hitter'])#"Heavy Hitter", "Super Heavy Hitter")
    fillGroup(shield_hitter)

    shield_reprisal = jobData.getIds(groups['reprisal'])#"Reprisal", "Harsh Reprisal")
    fillGroup(shield_reprisal)

    # DRAGOON WARRIOR
    dragoon_jump = jobData.getIds(groups['jump'])#"Jump", "Super Jump", "Soul Jump")
    fillGroup(dragoon_jump)

    dragoon_lightning = jobData.getIds(groups['lightning'])#"Thunder Thrust", "Bolt Blast")
    fillGroup(dragoon_lightning)

    # SPIRITMASTER
    spm_spirits = jobData.getIds(groups['spirits'])#"Healthbringer", "Basunabringer", "Spiritbringer", "Lifebringer", "Bravebringer", "Purebringer")
    random.shuffle(spm_spirits)
    fillGroup(spm_spirits)

    spm_light = jobData.getIds(groups['light'])#"Banish", "Banishra", "Banishga", "Holy")
    fillGroup(spm_light)

    spm_regen = jobData.getIds(groups['regen'])#"Regeneration", "Reraise")
    fillGroup(spm_regen)

    # SWORDMASTER
    swm_flurry = jobData.getIds(groups['flurry'])#"Fourfold Flurry", "Ninefold Flurry")
    fillGroup(swm_flurry)

    swm_stance1 = jobData.getIds(groups['stance1'])#"Fluid Stance", "Solid Stance")
    swm_stance2 = jobData.getIds(groups['stance2'])#"Solid Right Style", "Fluid Left Style", "Solid Slash", "Fluid Flow", "Solid Smash", "Fluid Frenzy")
    random.shuffle(swm_stance1)
    random.shuffle(swm_stance2)
    fillGroup(swm_stance1 + swm_stance2)

    # ORACLE
    oracle_quick = jobData.getIds(groups['quick'])#"Quick", "Quickga")
    fillGroup(oracle_quick)

    oracle_slow = jobData.getIds(groups['slow'])#"Slow", "Slowga")
    fillGroup(oracle_slow)

    oracle_haste = jobData.getIds(groups['haste'])#"Haste", "Hastega")
    fillGroup(oracle_haste)

    oracle_triple = jobData.getIds(groups['triple'])#"Triple", "Triplara", "Triplaga")
    fillGroup(oracle_triple)

    # SALVE-MAKER
    svm_survey = jobData.getIds(groups['survey'])#"Survey", "Analysis")
    fillGroup(svm_survey)

    svm_tonic = jobData.getIds(groups['tonic'])#"BP Tonic", "Double BP Tonic")
    fillGroup(svm_tonic)

    svm_philtre = jobData.getIds(groups['philtre'])#"Philtre", "Heartbreak")
    fillGroup(svm_philtre)

    svm_compounding = jobData.getIds(groups['compounding'])#"Compounding", "Advanced Compounding")
    fillGroup(svm_compounding)

    # ARCANIST
    arc_dark = jobData.getIds(groups['dark'])#"Dark", "Darkra", "Darkga", "Doomsday")
    fillGroup(arc_dark)

    arc_comet = jobData.getIds(groups['comet'])#"Comet", "Meteor")
    fillGroup(arc_comet)

    arc_pairs1 = jobData.getIds(groups['ardour'])#"Ardour", "Electon")
    arc_pairs2 = jobData.getIds(groups['meltdown'])#"Meltdown", "Apocalypse")
    arc_pairs = arc_pairs1 + arc_pairs2
    fillGroup(arc_pairs)

    # Bastion
    bast_light = jobData.getIds(groups['bastion'])#"Light of Justice", "Holy Light")
    fillGroup(bast_light)

    # Phantom
    phan_shroud = jobData.getIds(groups['shroud'])#"Shroud", "Burial Shroud")
    fillGroup(phan_shroud)

    phan_nightmare = jobData.getIds(groups['nightmare'])#"Recurring Nightmare", "Never-Ending Nightmare")
    fillGroup(phan_nightmare)

    # Hellblade
    hell_dread = jobData.getIds(groups['dread'])#"Dread Blade", "Terrorise")
    fillGroup(hell_dread)

    # Brave
    brave_gravity = jobData.getIds(groups['gravity'])#"Supergravity", "Hypergravity", "Gigagravity")
    fillGroup(brave_gravity)

    brave_bp = jobData.getIds(groups['brave'])#"Wall of Woe", "Dawn of Odyssey")
    random.shuffle(brave_bp)
    fillGroup(brave_bp)

    assert len(support) + len(actions) == sum([job.vacantSupportSlots() for job in jobs])

    ##########
    # SKILLS #
    ##########

    check = True
    
    # White Mage
    skills = jobData.getIds(["Benediction"]) # Only works with Cure!
    check *= addActions(skills, wm_cure)

    # Pictomancer
    skills = jobData.getIds(["Mass Production"])
    check *= addActions(skills, pictomancer)

    if not check:
        return False

    ###########
    # SUPPORT #
    ###########

    check = True
    
    # Monk
    sup = jobData.getIds(["Concentration"])
    check *=  addSupport(sup, monk)

    # Healing Spells
    sup = jobData.getIds(["Holistic Medicine"])
    check *= addSupport(sup, wm_cure + rm_heal)

    # Vanguard -- attack and crit rate scale with target chance
    sup = jobData.getIds(["Attention Seeker"])
    check *= addSupport(sup, vg_target)

    # Bard -- singing-specific sup
    sup = jobData.getIds(["Encore", "Extended Outro"])
    check *= addSupport(sup, bard)

    # Pictomancer
    sup = jobData.getIds(["Self-Expression"])
    check *= addSupport(sup, pictomancer)

    # Bard + Pictomancer
    sup = jobData.getIds(["Born Entertainer"])
    check *= addSupport(sup, bard + pictomancer)

    # Tamer
    sup = jobData.getIds(["Beast Whisperer", "Animal Rescue", "Creature Comforts"])
    check *= addSupport(sup, tamer)

    # Thief
    sup = jobData.getIds(["Mug", "Magpie", "Rob Blind"])
    check *= addSupport(sup, thief_steal_items)

    sup = jobData.getIds(["Sleight of Hand", "Up to No Good"])
    check *= addSupport(sup, thief_steal_other)

    # Gambler
    sup = jobData.getIds(["Born Lucky"])
    check *= addSupport(sup, gambler_elem + gambler_wheels)

    # Berzerker
    sup = jobData.getIds(["Rage and Reason", "Free-for-All"])
    check *= addSupport(sup, berz_berzerk)

    # Red Mage -- attacking magic
    sup = jobData.getIds(["Magic Critical"])
    check *= addSupport(sup, bm_fire + bm_blizzard + bm_thunder + rm_earth + rm_wind + arc_pairs + arc_dark + arc_comet + oracle_triple + spm_light) # INCLUDE ATTACKS? e.g. Sky Slicer (thief_wind)

    sup = jobData.getIds(["Nuisance"])
    check *= addSupport(sup, bm_fire + bm_blizzard + bm_thunder + rm_earth + rm_wind + arc_pairs + arc_dark + arc_comet + oracle_triple + spm_light) # INCLUDE ATTACKS? e.g. Sky Slicer (thief_wind)

    # Reg Mage -- magic spells
    sup = jobData.getIds(["Chainspell"])
    check *= addSupport(sup, bm_fire + bm_blizzard + bm_thunder + rm_earth + rm_wind + arc_pairs + arc_dark + arc_comet + oracle_triple + spm_light
                       + rm_heal + wm_cure) # INCLUDE ATTACKS? e.g. Sky Slicer (thief_wind)

    # Hunter
    sup = jobData.getIds(["Apex Predator"])
    check *= addSupport(sup, hunter_slayer)
    
    # Shieldmaster -- protect
    sup = jobData.getIds(["Protect Ally", "Chivalrous Spirit"])
    check *= addSupport(sup, shield)

    # Dragoon Warrior
    sup = jobData.getIds(["Momentum", "Highwind"])
    check *= addSupport(sup, dragoon_jump)

    # Spiritmaster
    sup = jobData.getIds(["Spirited Defence", "There in Spirit"])
    check *= addSupport(sup, spm_spirits)

    # Swordmaster
    sup = jobData.getIds(["Redoubled Effort"])
    check *= addSupport(sup, swm_stance1)

    # Salve Maker
    sup = jobData.getIds(["Master Medic"])
    check *= addSupport(sup, svm_compounding)

    # Arcanist
    sup = jobData.getIds(["All In"])
    check *= addSupport(sup, bm_fire + bm_blizzard + bm_thunder + rm_earth + rm_wind + arc_pairs + arc_dark + arc_comet + oracle_triple + spm_light) # INCLUDE ATTACKS? e.g. Sky Slicer (thief_wind)

    sup = jobData.getIds(["Wild Wizardry"])
    check *= addSupport(sup, bm_fire + bm_blizzard + bm_thunder + rm_earth + rm_wind + arc_pairs + arc_dark + arc_comet + oracle_triple + spm_light) # INCLUDE ATTACKS? e.g. Sky Slicer (thief_wind)

    sup = jobData.getIds(["Magic Amp"])
    check *= addSupport(sup, bm_fire + bm_blizzard + bm_thunder + rm_earth + rm_wind + arc_pairs + arc_dark + arc_comet + oracle_triple + spm_light) # INCLUDE ATTACKS? e.g. Sky Slicer (thief_wind)

    if not check:
        return check
    
    assert len(support) + len(actions) == sum([job.vacantSupportSlots() for job in jobs])

    #### SECOND: FILL ALL TRAITS
    random.shuffle(support)
    for i in range(24):
        if jobs[i].isTrait1Empty():
            obj = jobData.supportDict[support.pop()]
            jobs[i].setTrait1(obj)
        if jobs[i].isTrait2Empty():
            obj = jobData.supportDict[support.pop()]
            jobs[i].setTrait2(obj)

    #### THIRD: Finish filling with supports
    w = [job.roomForSupport() for job in jobs]
    r = list(range(len(w)))
    c = sum(w)
    while support:
        if c == 0:
            return False
        i = random.choices(r, w)[0]
        obj = jobData.supportDict[support.pop()]
        jobs[i].fillSupportSlots([obj])
        if not jobs[i].roomForSupport():
            w[i] = False
            c -= 1

    #### FOURTH: Finish filling actions
    random.shuffle(actions)
    w = [job.roomForAction() for job in jobs]
    r = list(range(len(w)))
    c = sum(w)
    while actions:
        if c == 0:
            return False
        i = random.choices(r, w)[0]
        obj = jobData.actionsDict[actions.pop()]
        jobs[i].fillActionSlots([obj])
        if not jobs[i].roomForAction():
            w[i] = False
            c -= 1
        
    return True
