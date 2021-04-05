import random

## TODO
# - Should Benediction be included with healing? NO if it works with items!
# - does Freehand work for all abilities???
# - does Magic Critical only affect spells or also physical attacks with an element? e.g. Sky Slicer of thief
# - weapon lores should probably end up on jobs with weapon-specific attacks
# - should job sampling for weapon-based attacks be biased towards jobs with strong weapons affinities (S, A, .. maybe B?)


def shuffleJobAbilities(data):
    candidates = {
        'skills': list(data.skills),
        'support': list(data.support),
    }
    assignments = {} # Skill/Support ID -> Job ID
    
    ## Build weights to keep track of slots
    # 15 skills/supports + trait1 + trait2
    vacant = [[True]*17 for i in range(24)]

    # Job names
    names = list(data.job.keys())

    # GROUP OF SKILLS up to slot 15
    def fillGroup(skills):

        # Pick a job
        i = random.randint(0, 23)
        while sum(vacant[i][:15]) < len(skills): # Ensures enough room for skills
            i = random.randint(0, 23)

        # Setup slots for the remaining skills
        slots = []
        for _ in enumerate(skills):
            j = random.choices(range(15), vacant[i][:15])[0]
            vacant[i][j] = False
            slots.append(j)
        slots.sort()

        # Assign skills to the slots
        for slot, skill in zip(slots, skills):
            data.job[names[i]][slot] = skill
            assignments[skill] = i

        # Remove skills from candidates
        candidates['skills'] = list(filter(lambda x: x not in skills, candidates['skills']))

    # GROUP OF SUPPORT up to slot 17 (includes traits!)
    def fillSupport(skills):

        # Pick a job
        i = random.randint(0, 23)
        while sum(vacant[i][:17]) < len(skills): # Ensures enough room for skills
            i = random.randint(0, 23)

        # Setup slots for the remaining skills
        slots = []
        for _ in enumerate(skills):
            j = random.choices(range(17), vacant[i][:17])[0]
            vacant[i][j] = False
            slots.append(j)
        slots.sort()

        # Assign skills to the slots
        for slot, skill in zip(slots, skills):
            data.job[names[i]][slot] = skill
            assignments[skill] = i

        # Remove skills from candidates
        candidates['support'] = list(filter(lambda x: x not in skills, candidates['support']))

    def addSkills(skills, targets):
        random.shuffle(skills) # Order not required for these!

        target = random.sample(targets, 1)[0]
        i = assignments[target]
        if sum(vacant[i]) < len(skills):
            return False

        for s in skills:
            j = random.choices(range(17), vacant[i])[0]
            vacant[i][j] = False
            data.job[names[i]][j] = s

        # Remove skills from candidates
        candidates['skills'] = list(filter(lambda x: x not in skills, candidates['skills']))

        return True
        

    def addSupport(supports, targets):
        random.shuffle(supports) # Order not required for these!
        
        target = random.sample(targets, 1)[0]
        i = assignments[target]
        if sum(vacant[i]) < len(supports):
            return False

        for s in supports:
            j = random.choices(range(17), vacant[i])[0]
            vacant[i][j] = False
            data.job[names[i]][j] = s

        # Remove support skills from candidates
        candidates['support'] = list(filter(lambda x: x not in supports, candidates['support']))

        return True
        

    #### FIRST: FILL ALL GROUPINGS

    # MONK SKILLS
    monk = data.pickIds(1, "Inner Alchemy", "Invigorate", "Mindfulness")
    fillGroup(monk)
    
    # Healing spells
    wm_cure = data.getIds("Cure", "Cura", "Curaga")
    fillGroup(wm_cure)

    # WHITE MAGE -- revives
    wm_raise = data.getIds("Raise", "Arise", "Raise All")
    fillGroup(wm_raise)

    # WHITE MAGE -- statuses
    wm_basuna = data.getIds("Basuna", "Esuna")
    fillGroup(wm_basuna)

    # BLACK MAGE
    bm_fire = data.getIds("Fire", "Fira", "Firaga", "Flare")
    fillGroup(bm_fire)
    
    bm_blizzard = data.getIds("Blizzard", "Blizzara", "Blizzaga", "Freeze")
    fillGroup(bm_blizzard)
    
    bm_thunder = data.getIds("Thunder", "Thundara", "Thundaga", "Burst")
    fillGroup(bm_thunder)

    # VANGUARD
    vg_target = data.getIds("Aggravate", "Infuriate")
    fillGroup(vg_target)

    vg_earth = data.getIds("Sword of Stone", "Quake Blade")
    fillGroup(vg_earth)

    vg_delay = data.getIds("Shield Bash", "Ultimatum")
    fillGroup(vg_delay)

    # TROUBADOR -- Born Entertainor support also works for Artist skills
    bard = data.pickIds(4, "Don't Let 'Em Get To You", "Don't Let 'Em Trick You", "Step into the Spotlight",
                          "(Won't) Be Missing You", "Right Through Your Fingers", "Hurts So Bad",
                          "Work Your Magic", "All Killer No Filler")
    fillGroup(bard)

    # PICTOMANCER
    pictomancer = data.pickIds(3, "Disarming Scarlet", "Disenchanting Mauve", "Incurable Coral", "Indefensible Teal", "Zappable Chartreuse", )
    fillGroup(pictomancer)

    # TAMER
    tamer = data.getIds("Capture", "Off the Leash", "Off the Chain")
    fillGroup(tamer)

    # THIEF
    thief_steal_items = data.getIds("Steal")
    fillGroup(thief_steal_items)

    thief_steal_other = data.pickIds(1, "Steal Breath", "Steal Spirit", "Steal Courage")
    fillGroup(thief_steal_other)

    thief_wind = data.getIds("Sky Slicer", "Tornado's Edge")
    fillGroup(thief_wind)

    # GAMBLER
    gambler_elem = data.getIds("Elemental Wheel", "Real Elemental Wheel")
    fillGroup(gambler_elem)

    gambler_wheels = data.pickIds(3, "Odds or Evens", "Life or Death", "Spin the Wheel", "Triples", "Bold Gambit", "Unlucky Eight")
    fillGroup(gambler_wheels)

    # BERZERKER
    berz_berzerk = data.getIds("Vent Fury")
    fillGroup(berz_berzerk)

    berz_attack_all = data.getIds("Crescent Moon", "Level Slash", "Death's Door")
    fillGroup(berz_attack_all)

    berz_attack_one = data.getIds("Double Damage", "Amped Strike")
    fillGroup(berz_attack_one)

    berz_water_attack = data.getIds("Water Damage", "Flood Damage")
    fillGroup(berz_water_attack)

    # RED MAGE
    rm_earth = data.getIds("Stone", "Stonera", "Stonega", "Quake")
    rm_wind = data.getIds("Aero", "Aerora", "Aeroga", "Tornado")
    if random.random() > 0.5:
        rm_earth += data.getIds("Disaster")
    else:
        rm_wind += data.getIds("Disaster")
    fillGroup(rm_earth)
    fillGroup(rm_wind)

    rm_heal = data.getIds("Heal", "Healara", "Healaga")
    fillGroup(rm_heal)

    # HUNTER
    hunter_random = data.getIds("Quickfire Flurry", "Grand Barrage")
    fillGroup(hunter_random)

    # SHIELDMASTER
    shield = data.getIds("Bodyguard", "Defender of the People")
    fillGroup(shield)

    shield_protect = data.getIds("Protect Ally")
    fillSupport(shield_protect)

    shield_hitter = data.getIds("Heavy Hitter", "Super Heavy Hitter")
    fillGroup(shield_hitter)

    shield_reprisal = data.getIds("Reprisal", "Harsh Reprisal")
    fillGroup(shield_reprisal)

    
    assert len(candidates['support']) + len(candidates['skills']) == sum([sum(v) for v in vacant])


    ##########
    # SKILLS #
    ##########

    # Pictomancer
    skills = data.getIds("Mass Production")
    assert addSkills(skills, pictomancer)

    ###########
    # SUPPORT #
    ###########

    # Monk
    supports = data.getIds("Concentration")
    assert addSupport(supports, monk)

    # Healing Spells
    supports = data.getIds("Holistic Medicine")
    assert addSupport(supports, wm_cure + rm_heal)

    # Vanguard -- attack and crit rate scale with target chance
    supports = data.getIds("Attention Seeker")
    assert addSupport(supports, vg_target)

    # Bard -- singing-specific supports
    supports = data.getIds("Encore", "Extended Outro")
    assert addSupport(supports, bard)

    # Pictomancer
    supports = data.getIds("Self-Expression")
    assert addSupport(supports, pictomancer)

    # Bard + Pictomancer
    supports = data.getIds("Born Entertainer")
    assert addSupport(supports, bard + pictomancer)

    # Tamer
    supports = data.getIds("Beast Whisperer", "Animal Rescue", "Creature Comforts")
    assert addSupport(supports, tamer)

    # Thief
    supports = data.getIds("Mug", "Magpie", "Rob Blind")
    assert addSupport(supports, thief_steal_items)

    supports = data.getIds("Sleight of Hand", "Up to No Good")
    assert addSupport(supports, thief_steal_other)

    # Gambler
    supports = data.getIds("Born Lucky")
    assert addSupport(supports, gambler_elem + gambler_wheels)

    # Berzerker
    supports = data.getIds("Rage and Reason", "Free-for-All")
    assert addSupport(supports, berz_berzerk)

    # Red Mage -- attacking magic
    supports = data.getIds("Magic Critical")
    assert addSupport(supports, bm_fire + bm_blizzard + bm_thunder + rm_earth + rm_wind) # INCLUDE ATTACKS? e.g. Sky Slicer (thief_wind)

    supports = data.getIds("Nuisance")
    assert addSupport(supports, bm_fire + bm_blizzard + bm_thunder + rm_earth + rm_wind) # INCLUDE ATTACKS? e.g. Sky Slicer (thief_wind)

    # Reg Mage -- magic spells
    supports = data.getIds("Chainspell")
    assert addSupport(supports, bm_fire + bm_blizzard + bm_thunder + rm_earth + rm_wind
                       + rm_heal + wm_cure) # INCLUDE ATTACKS? e.g. Sky Slicer (thief_wind)
    
    # Shieldmaster -- protect
    supports = data.getIds("Chivalrous Spirit")
    assert addSupport(supports, shield + shield_protect)
    
    assert len(candidates['support']) + len(candidates['skills']) == sum([sum(v) for v in vacant])

    #### SECOND: FILL ALL TRAITS
    random.shuffle(candidates['support'])
    for i in range(24):
        if vacant[i][15]:
            data.job[names[i]][15] = candidates['support'].pop()
            vacant[i][15] = False
        if vacant[i][16]:
            data.job[names[i]][16] = candidates['support'].pop()
            vacant[i][16] = False

    #### THIRD: FILL THE REMAINING VACANT SLOTS
    remaining = candidates['skills'] + candidates['support']
    random.shuffle(remaining)
    for i in range(24):
        for j in range(15):
            if vacant[i][j]:
                data.job[names[i]][j] = remaining.pop()
                vacant[i][j] = False

    for v in vacant:
        assert not sum(v)
