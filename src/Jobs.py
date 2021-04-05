import random

## TODO
# - Should Benediction be included with healing? NO if it works with items!


def shuffleJobAbilities(data):
    candidates = {
        'skills': list(data.skills),
        'support': list(data.support),
    }
    
    ## Build weights to keep track of slots
    # 15 skills/supports + trait1 + trait2
    vacant = [[True]*17 for i in range(24)]

    # Job names
    names = list(data.job.keys())

    def fillGroup(skills, support):

        # Pick a job
        total = len(skills) + len(support)
        i = random.randint(0, 23)
        while sum(vacant[i][:15]) < total: # Ensures enough room for skills
            i = random.randint(0, 23)

        # Add support
        candidates['support'] = list(filter(lambda x: x not in support, candidates['support']))
        while support:
            j = random.choices(range(17), vacant[i])[0]
            vacant[i][j] = False
            if j == 15:
                data.job[names[i]][15] = support.pop()
            elif j == 16:
                data.job[names[i]][16] = support.pop()
            else:
                data.job[names[i]][j] = support.pop()

        # Setup slots for the remaining skills
        slots = []
        for _ in enumerate(skills):
            j = random.choices(range(15), vacant[i][:15])[0]
            slots.append(j)
            vacant[i][j] = False
        slots.sort()

        # Assign skills to the slots
        candidates['skills'] = list(filter(lambda x: x not in skills, candidates['skills']))
        for slot, skill in zip(slots, skills):
            data.job[names[i]][slot] = skill
            vacant[i][slot] = False

    #### FIRST: FILL ALL GROUPINGS

    # MONK SKILLS & SUPPORT
    skills = data.pickIds(1, "Inner Alchemy", "Invigorate", "Mindfulness")
    supports = data.getIds("Concentration")
    fillGroup(skills, supports)

    # WHITE MAGE SUPPORT
    # HOW WILL I ADD THE OTHER GROUPS? MAYBE JUST ADD GROUPS, THEN PICK A JOB TO ADD HOLISTIC MEDICINE TO?
    skills = data.pickGroup([
        ["Cure", "Cura", "Curaga"],
        # RED MAGE
        # ANYTHING FROM SALVE MAKER?
        # ANYTHING ELSE?
    ])
    supports = data.getIds("Holistic Medicine")
    fillGroup(skills, supports)

    # WHITE MAGE -- revives
    skills = data.getIds("Raise", "Arise", "Raise All")
    fillGroup(skills, [])

    # WHITE MAGE -- statuses
    skills = data.getIds("Basuna", "Esuna")
    fillGroup(skills, [])

    # DARK MAGE
    skills = data.getIds("Fire", "Fira", "Firaga", "Flare")
    fillGroup(skills, [])
    
    skills = data.getIds("Blizzard", "Blizzara", "Blizzaga", "Freeze")
    fillGroup(skills, [])
    
    skills = data.getIds("Thunder", "Thundara", "Thundaga", "Burst")
    fillGroup(skills, [])

    # VANGUARD
    skills = data.getIds("Aggravate", "Infuriate")
    fillGroup(skills, [])

    skills = data.getIds("Sword of Stone", "Quake Blade")
    fillGroup(skills, [])

    skills = data.getIds("Shield Bash", "Ultimatum")
    supports = data.getIds("Attention Seeker")
    fillGroup(skills, [])

    

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
