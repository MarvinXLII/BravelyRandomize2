import random

## TODO
# - Should Benediction be included with healing? NO if it works with items!
# - does Freehand work for all abilities???


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

    def fillSkills(skills, targets):
        random.shuffle(skills) # Order not required for these!
        
        i = assignments[targets[0]]
        if sum(vacant[i]) < len(skills):
            return False

        for s in skills:
            j = random.choices(range(17), vacant[i])[0]
            vacant[i][j] = False
            data.job[names[i]][j] = s

        # Remove skills from candidates
        candidates['skills'] = list(filter(lambda x: x not in skills, candidates['skills']))

        return True
        

    def fillSupport(supports, targets):
        random.shuffle(supports) # Order not required for these!
        
        i = assignments[targets[0]]
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

    # MONK SKILLS & SUPPORT
    skills = data.pickIds(1, "Inner Alchemy", "Invigorate", "Mindfulness")
    fillGroup(skills)
    supports = data.getIds("Concentration")
    assert fillSupport(supports, skills)
    
    # WHITE MAGE SUPPORT
    # HOW WILL I ADD THE OTHER GROUPS? MAYBE JUST ADD GROUPS, THEN PICK A JOB TO ADD HOLISTIC MEDICINE TO?
    skills = [
        data.getIds("Cure", "Cura", "Curaga"),
    ]
    for skillSet in skills:
        fillGroup(skillSet)
    supports = data.getIds("Holistic Medicine")
    assert fillSupport(supports, random.sample(skills, 1)[0])

    # WHITE MAGE -- revives
    skills = data.getIds("Raise", "Arise", "Raise All")
    fillGroup(skills)

    # WHITE MAGE -- statuses
    skills = data.getIds("Basuna", "Esuna")
    fillGroup(skills)

    # DARK MAGE
    skills = data.getIds("Fire", "Fira", "Firaga", "Flare")
    fillGroup(skills)
    
    skills = data.getIds("Blizzard", "Blizzara", "Blizzaga", "Freeze")
    fillGroup(skills)
    
    skills = data.getIds("Thunder", "Thundara", "Thundaga", "Burst")
    fillGroup(skills)

    # VANGUARD
    skills = data.getIds("Aggravate", "Infuriate")
    fillGroup(skills)

    skills = data.getIds("Sword of Stone", "Quake Blade")
    fillGroup(skills)

    skills = data.getIds("Shield Bash", "Ultimatum")
    fillGroup(skills)
    supports = data.getIds("Attention Seeker")
    assert fillSupport(supports, skills)

    # TROUBADOR -- Born Entertainor support also works for Artist skills
    troubador = data.pickIds(4, "Don't Let 'Em Get To You", "Don't Let 'Em Trick You", "Step into the Spotlight",
                          "(Won't) Be Missing You", "Right Through Your Fingers", "Hurts So Bad",
                          "Work Your Magic", "All Killer No Filler")
    fillGroup(troubador)
    supports = data.getIds("Encore", "Extended Outro")
    assert fillSupport(supports, troubador)

    # PICTOMANCER
    pictomancer = data.pickIds(3, "Disarming Scarlet", "Disenchanting Mauve", "Incurable Coral", "Indefensible Teal", "Zappable Chartreuse", )
    fillGroup(pictomancer)
    skills = data.getIds("Mass Production")
    assert fillSkills(skills, pictomancer)
    supports = data.getIds("Self-Expression")
    assert fillSupport(supports, pictomancer)

    # BORN ENTERTAINOR (TROUBADOR + PICTOMANCER)
    supports = data.getIds("Born Entertainer")
    skills = random.sample([troubador, pictomancer], 1)[0]
    assert fillSupport(supports, skills)

    # TAMER
    skills = data.getIds("Capture", "Off the Leash", "Off the Chain")
    fillGroup(skills)
    supports = data.getIds("Beast Whisperer", "Animal Rescue", "Creature Comforts")
    assert fillSupport(supports, skills)


    # THIEF
    skills = data.getIds("Steal")
    fillGroup(skills)
    supports = data.getIds("Mug", "Magpie", "Rob Blind")
    assert fillSupport(supports, skills)

    skills = data.pickIds(1, "Steal Breath", "Steal Spirit", "Steal Courage")
    fillGroup(skills)
    supports = data.getIds("Sleight of Hand", "Up to No Good")
    assert fillSupport(supports, skills)

    skills = data.getIds("Sky Slicer", "Tornado's Edge")
    fillGroup(skills)

    # GAMBLER
    elementals = data.getIds("Elemental Wheel", "Real Elemental Wheel")
    fillGroup(elementals)
    wheels = data.pickIds(3, "Odds or Evens", "Life or Death", "Spin the Wheel", "Triples", "Bold Gambit", "Unlucky Eight")
    fillGroup(wheels)
    skills = random.sample([elementals, wheels], 1)[0]
    supports = data.getIds("Born Lucky")
    assert fillSupport(supports, skills)

    # BERZERK
    skills = data.getIds("Vent Fury")
    fillGroup(skills)
    supports = data.getIds("Rage and Reason", "Free-for-All")
    assert fillSupport(supports, skills)

    skills = data.getIds("Crescent Moon", "Level Slash", "Death's Door")
    fillGroup(skills)
    skills = data.getIds("Double Damage", "Amped Strike")
    fillGroup(skills)
    skills = data.getIds("Water Damage", "Flood Damage")
    fillGroup(skills)

    # RED MAGE
    
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
