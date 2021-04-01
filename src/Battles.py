import random

def shuffleResistance(monsters, separate):

    keys = list(monsters.resistance.keys())

    def shuffle(weights):
        for i, key in enumerate(keys):
            if not weights[i]: continue
            key2 = random.choices(keys[i:], weights[i:])[0]
            assert weights[keys.index(key2)]
            monsters.resistance[key]['Magic'], monsters.resistance[key2]['Magic'] = monsters.resistance[key2]['Magic'], monsters.resistance[key]['Magic']
        for i, key in enumerate(keys):
            if not weights[i]: continue
            keys2 = random.choices(keys[i:], weights[i:])[0]
            assert weights[keys.index(key2)]
            monsters.resistance[key]['Weapon'], monsters.resistance[key2]['Weapon'] = monsters.resistance[key2]['Weapon'], monsters.resistance[key]['Weapon']
        for i, key in enumerate(keys):
            if not weights[i]: continue
            keys2 = random.choices(keys[i:], weights[i:])[0]
            assert weights[keys.index(key2)]
            monsters.resistance[key]['Effects'], monsters.resistance[key2]['Effects'] = monsters.resistance[key2]['Effects'], monsters.resistance[key]['Effects']
    
    if separate:
        # Do bosses and monsters separately
        bossWeights = [m['isBoss'] for m in monsters.resistance.values()]
        enemyWeights = [not m['isBoss'] for m in monsters.resistance.values()]
        shuffle(bossWeights)
        shuffle(enemyWeights)

    else:
        weights = [True]*len(keys)
        shuffle(weights)
