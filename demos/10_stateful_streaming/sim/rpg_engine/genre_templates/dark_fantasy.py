"""
Dark Fantasy — The Witcher / Annihilation style.

Grim, low-magic, folk horror. Branching forest paths, isolated settlements,
things in the dark that don't have names yet.
"""

TEMPLATE = {
    "genre": "dark-fantasy",
    "display_name": "Dark Fantasy",
    "description": "Grim low-magic. Folk horror, dangerous wilderness, people who know more than they say.",
    "register_preset": "dark-fantasy",
    "default_name": "The Dark Between Trees",
    "topology": "branching_paths",

    "location_count": {"min": 8, "max": 14},
    "location_types": [
        {
            "type": "tavern",
            "weight": 2,
            "tags": ["safe", "social", "rest"],
            "is_start": True,
            "name_patterns": ["The {adj} {noun}", "The {noun} and {noun2}", "{name}'s Rest"],
            "sensory": {
                "sight": [
                    "Firelight through warped glass. Smoke curling from the chimney.",
                    "Low beams, stained tables, a bar worn smooth by decades of elbows.",
                    "A haze of pipe smoke. Shadows that move with the draft.",
                ],
                "sound": [
                    "Muffled voices. A chair scraping. The clink of mugs.",
                    "Someone humming badly. The creak of old wood.",
                    "The fire popping. A dog sighing in its sleep.",
                ],
                "smell": [
                    "Woodsmoke, roasting meat, spilled ale.",
                    "Wet wool, tallow candles, yesterday's bread.",
                    "Old beer and older wood. Something roasting in the kitchen.",
                ],
                "touch": [
                    "Warm inside. The bench is worn smooth.",
                    "Sticky table. The ale is room temperature.",
                    "Heat from the hearth on one side, draft from the door on the other.",
                ],
            },
            "atmosphere": [
                "Weary sanctuary. People stop here because they have to, not because they want to.",
                "The kind of warmth that makes you forget what's outside. Temporarily.",
                "Tired but alive. The hearth holds the dark at bay.",
            ],
        },
        {
            "type": "village_square",
            "weight": 2,
            "tags": ["social", "commerce"],
            "name_patterns": ["{name} Market", "The Square", "{name} Commons"],
            "sensory": {
                "sight": [
                    "Faded awnings, a few people moving between stalls. Crows on the rooftops.",
                    "Shuttered windows. A well at the center, rope frayed.",
                    "Cobblestones dark with rain. Buildings lean inward.",
                ],
                "sound": [
                    "Haggling. A hammer on metal from the smithy. Crows.",
                    "Cart wheels on stone. Someone arguing about prices.",
                    "The well rope creaking. Footsteps on wet stone.",
                ],
                "smell": [
                    "Fish, tanned leather, something sweet from the baker's.",
                    "Wet stone, horse manure, bread baking.",
                    "Iron from the smithy. Rotting vegetables in the gutter.",
                ],
                "touch": [
                    "Uneven cobblestones underfoot. The air is damp.",
                    "Cold wind between buildings. Puddles in the ruts.",
                    "The stone well rim is smooth and cold.",
                ],
            },
            "atmosphere": [
                "A town holding its breath. Busy enough to seem normal, quiet enough to feel wrong.",
                "People going through the motions. Nobody makes eye contact for too long.",
                "Commerce as ritual. Nobody's getting rich. They're just surviving.",
            ],
        },
        {
            "type": "forest",
            "weight": 3,
            "tags": ["dangerous", "wilderness"],
            "name_patterns": ["The Edge of {name}", "{adj} {name}", "The {adj} Path"],
            "sensory": {
                "sight": [
                    "Twisted branches. Moss on everything. The path splits ahead.",
                    "Green-dark canopy. Shapes that might be stumps or might not be.",
                    "Trees too close together. The light doesn't reach the ground.",
                ],
                "sound": [
                    "Dripping water. Something moving in the undergrowth. No birdsong.",
                    "Branches cracking. Your own breathing, too loud.",
                    "Wind through leaves that sounds like whispering.",
                ],
                "smell": [
                    "Rot, wet bark, mushrooms.",
                    "Damp earth. Something sweet and wrong underneath.",
                    "Pine resin, mold, the copper tang of standing water.",
                ],
                "touch": [
                    "The air is colder here. Damp seeps through clothing.",
                    "Branches grab at your pack. The ground is soft, uncertain.",
                    "Cobwebs across your face. The bark is slick.",
                ],
            },
            "atmosphere": [
                "The forest doesn't want you here. Not hostile — indifferent.",
                "Something watching. Not malicious. Just aware.",
                "Old. The trees were here first and they'll be here after.",
            ],
        },
        {
            "type": "chapel",
            "weight": 1,
            "tags": ["sacred", "mystery"],
            "name_patterns": ["The Chapel of {name}", "The {adj} Shrine", "The Old Temple"],
            "sensory": {
                "sight": [
                    "Candlelight on stone walls. Faded paintings. Dust motes.",
                    "Empty pews. An altar with offerings nobody claims.",
                    "Stained glass so old the images have melted into color.",
                ],
                "sound": [
                    "Silence. The town sounds cut off at the threshold.",
                    "Your footsteps echo wrong. Too many surfaces.",
                    "A faint hum you can't locate. Maybe the walls.",
                ],
                "smell": [
                    "Beeswax, old incense, dust.",
                    "Cold stone and something floral, very faint.",
                    "Candlesmoke and time.",
                ],
                "touch": [
                    "Cool stone. The air is still, almost thick.",
                    "The pew wood is cold. The floor is uneven.",
                    "Something vibrating in the walls. Sub-audible.",
                ],
            },
            "atmosphere": [
                "Something is listening. Not threatening — patient.",
                "Sacred in a way that predates the religion.",
                "The silence has weight. It's holding something.",
            ],
        },
        {
            "type": "clearing",
            "weight": 1,
            "tags": ["dangerous", "mystery", "magical"],
            "name_patterns": ["The Clearing", "The {adj} Circle", "The {name} Stone"],
            "sensory": {
                "sight": [
                    "Dead trees in a perfect circle. Scorch marks on the ground.",
                    "A stone marker at the center, carved with symbols you don't recognize.",
                    "Nothing grows here. The ground is bare and dark.",
                ],
                "sound": [
                    "Nothing. Not even wind. The forest sounds stop at the treeline.",
                    "A ringing in your ears. Maybe it was always there.",
                    "Silence so complete it feels like pressure.",
                ],
                "smell": [
                    "Ozone. Ash. Something sweet and wrong.",
                    "Burnt air. Like after lightning, but stale.",
                    "Nothing. The absence of smell. Which is wrong.",
                ],
                "touch": [
                    "The air vibrates faintly, like standing near a struck bell.",
                    "Static on your skin. Your hair lifts.",
                    "Cold that has nothing to do with temperature.",
                ],
            },
            "atmosphere": [
                "Wrong. Beautiful and wrong. The silence is a held breath.",
                "This place shouldn't exist. But it does, and it's waiting.",
                "Power. Old and patient and not for you.",
            ],
        },
        {
            "type": "bridge",
            "weight": 1,
            "tags": ["transitional", "dangerous"],
            "name_patterns": ["The Old Bridge", "The {name} Crossing", "{adj} Bridge"],
            "sensory": {
                "sight": [
                    "Stone arch over dark water. Half the railing missing.",
                    "Mist rising from the river. Can't see the other bank clearly.",
                    "The bridge stones are cracked. Something has tested them.",
                ],
                "sound": [
                    "Rushing water. Loud enough to cover footsteps.",
                    "The bridge groaning with your weight.",
                    "Water breaking around pilings. A hollow sound underneath.",
                ],
                "smell": [
                    "Wet stone, river mud, something metallic.",
                    "Clean water and rot. The river carries both.",
                    "Fish. Damp wood. The mineral tang of rapids.",
                ],
                "touch": [
                    "The bridge stones are slick. Spray from the river.",
                    "Wind off the water. Colder than expected.",
                    "The railing — what's left of it — wobbles.",
                ],
            },
            "atmosphere": [
                "Liminal. Between here and there. The kind of place things happen.",
                "Don't stop on the bridge. Keep moving.",
                "The river doesn't care about you. That's the most honest thing here.",
            ],
        },
        {
            "type": "ruin",
            "weight": 1,
            "tags": ["dangerous", "mystery"],
            "name_patterns": ["The {adj} Ruins", "{name} Keep", "The Fallen {noun}"],
            "sensory": {
                "sight": [
                    "Walls half-standing. Doorways that open onto sky.",
                    "Stone stairs leading up to nothing. Carvings worn smooth.",
                    "Rubble overgrown with vine. Something was important here.",
                ],
                "sound": [
                    "Wind through empty windows. Stones settling.",
                    "Pigeons. Dripping water. Your own echoes.",
                    "A distant grinding. Maybe just the ruin settling.",
                ],
                "smell": [
                    "Dust, old mortar, wildflowers growing in the cracks.",
                    "Bat guano. Wet stone. The ghost of a cooking fire.",
                    "Rain-washed stone. Clean decay.",
                ],
                "touch": [
                    "Rough stone under your fingers. Carved letters you can't read.",
                    "The floor is uneven. Watch your step.",
                    "Cold draft from somewhere below.",
                ],
            },
            "atmosphere": [
                "A place that remembers being important.",
                "Nothing here anymore. Probably. Don't go below ground.",
                "Time won. The stones are patient about it.",
            ],
        },
    ],

    "name_pools": {
        "adj": ["Dark", "Hollow", "Crimson", "Old", "Quiet", "Iron",
                "Ashen", "Silent", "Blighted", "Crooked", "Grey",
                "Thornbound", "Bitter", "Dead", "Pale"],
        "noun": ["Wood", "Bridge", "Tower", "Market", "Chapel", "Gate",
                 "Stone", "Well", "Hearth", "Crown", "Path", "Hill"],
        "noun2": ["Raven", "Hound", "Oak", "Thorn", "Candle", "Blade",
                  "Bone", "Crow", "Ember", "Root"],
        "name": ["Ashwick", "Thornmere", "Grimholt", "Ravenmoor",
                 "Dunhaven", "Blackhollow", "Fenwick", "Ironmarch",
                 "Greypine", "Coldwater", "Stillreed", "Rootham",
                 "Mudwick", "Harrowfield", "Duskmere"],
        "forest_name": ["Thornwood", "Darkhollow", "Blightveil",
                        "Greycanopy", "Rotmire", "Whisperoak",
                        "Blackbriar", "Deadvein"],
    },

    "npc_count": {"min": 5, "max": 10},
    "npc_archetypes": [
        {
            "role": "innkeeper",
            "voice": "innkeeper",
            "weight": 2,
            "location_type": "tavern",
            "names": ["Maren", "Edda", "Brynn", "Olk", "Hild", "Gareth",
                      "Berta", "Thom", "Wren", "Coll"],
            "personalities": [
                "Practical, guarded, dry humor. Reads people fast. Generous to those who earn it.",
                "Tired but sharp. Speaks in clipped sentences. Trusts actions, not words.",
                "Warm on the surface, calculating underneath. Knows everything that happens in this town.",
            ],
            "knowledge_topics": ["local gossip", "travelers", "the forest", "missing people"],
            "secret_types": ["personal loss", "hidden identity", "knows more than they say"],
            "default_disposition": "cautious",
        },
        {
            "role": "merchant",
            "voice": "merchant",
            "weight": 2,
            "location_type": "village_square",
            "names": ["Davan", "Syl", "Pek", "Ren", "Lura", "Voss",
                      "Kemp", "Tira", "Aldric", "Fenn"],
            "personalities": [
                "Charming, calculating. Trades in oddities and information. Smiles too easily.",
                "Quiet, precise. Values things others overlook. Patient as a spider.",
                "Boisterous, friendly, sharp. Everybody's friend, nobody's fool.",
            ],
            "knowledge_topics": ["trade routes", "rare items", "who's buying what"],
            "secret_types": ["hidden employer", "smuggling", "debts"],
            "default_disposition": "friendly",
        },
        {
            "role": "chapel keeper",
            "voice": "mystic",
            "weight": 1,
            "location_type": "chapel",
            "names": ["Sister Vale", "Brother Ash", "The Listener",
                      "Mother Cinder", "Father Dusk", "Sister Moss"],
            "personalities": [
                "Serene to the point of unsettling. Speaks simply but with weight. Knows things she shouldn't.",
                "Gentle, distant. Speaks as if translating from a language you can't hear.",
                "Calm, direct, slightly otherworldly. Answers the question you meant to ask.",
            ],
            "knowledge_topics": ["the old ways", "the seal", "what sleeps beneath"],
            "secret_types": ["amnesia", "not entirely human", "bound to the place"],
            "default_disposition": "open",
        },
        {
            "role": "guard",
            "voice": "soldier",
            "weight": 1,
            "location_type": "village_square",
            "names": ["Warden Cress", "Halric", "Dane", "Mira", "Kol",
                      "Sergeant Fell"],
            "personalities": [
                "Tired, dutiful, haunted. Has seen things in the forest he doesn't talk about.",
                "By-the-book, frustrated. Underfunded, understaffed, outmatched.",
                "Pragmatic, gruff, secretly caring. Does the job because nobody else will.",
            ],
            "knowledge_topics": ["patrols", "the perimeter", "what's been happening at night"],
            "secret_types": ["cowardice", "lost patrol", "bribery"],
            "default_disposition": "neutral",
        },
        {
            "role": "herbalist",
            "voice": "healer",
            "weight": 1,
            "location_type": "tavern",
            "names": ["Old Nettie", "Rue", "Sorrel", "Moss",
                      "Hemlock", "Yarrow"],
            "personalities": [
                "Sharp-tongued, kind-hearted. Treats wounds and asks uncomfortable questions.",
                "Quiet, methodical. Smells like herbs and knows your ailment before you describe it.",
                "Grumpy, effective. Doesn't suffer fools but will save your life complaining the whole time.",
            ],
            "knowledge_topics": ["injuries", "poisons", "what the forest does to people"],
            "secret_types": ["forbidden knowledge", "uses the old ways", "treated someone they shouldn't have"],
            "default_disposition": "neutral",
        },
    ],

    "quest_patterns": [
        {
            "type": "investigation",
            "name_templates": ["The Missing {noun}", "What {name} Knows", "The {adj} Truth"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Learn about the {subject}.", "location_type": "tavern"},
                {"objective": "Investigate {location}.", "location_type": "forest"},
                {"objective": "Reach the {destination}.", "location_type": "clearing"},
                {"objective": "Understand what you found.", "location_type": "chapel"},
            ],
        },
        {
            "type": "fetch",
            "name_templates": ["The {adj} Commission", "{name}'s Request", "Retrieving the {noun}"],
            "stages": 3,
            "stage_templates": [
                {"objective": "Learn what {npc} needs.", "location_type": "village_square"},
                {"objective": "Find the {item} in {location}.", "location_type": "ruin"},
                {"objective": "Return to {npc}.", "location_type": "village_square"},
            ],
        },
        {
            "type": "faction_conflict",
            "name_templates": ["Choosing Sides", "The {adj} Divide", "Between {name} and {name2}"],
            "stages": 3,
            "stage_templates": [
                {"objective": "Learn what each side wants.", "location_type": "village_square"},
                {"objective": "Investigate {npc}'s claims.", "location_type": "forest"},
                {"objective": "Make your choice.", "location_type": "any"},
            ],
        },
    ],

    "item_types": [
        {"category": "weapon", "tags": ["weapon"],
         "items": [
             {"name": "a rusted iron sword", "desc": "Pitted, heavy, functional. It'll cut."},
             {"name": "a hunting bow", "desc": "Yew wood, well-used. The string is new."},
             {"name": "a wood axe", "desc": "Meant for trees. Works on other things."},
             {"name": "a long knife", "desc": "More than a tool, less than a sword."},
         ]},
        {"category": "tool", "tags": ["tool"],
         "items": [
             {"name": "an iron lantern", "desc": "Heavy, dented. The glass is cracked but holds."},
             {"name": "a coil of rope", "desc": "Hemp. Fifty feet, roughly."},
             {"name": "a set of lockpicks", "desc": "Worn leather roll. Three picks, one tension wrench."},
             {"name": "a tinderbox", "desc": "Flint, steel, and a wad of charcloth."},
         ]},
        {"category": "consumable", "tags": ["consumable", "medical"],
         "items": [
             {"name": "a healing poultice", "desc": "Crushed herbs and honey. Dulls pain, fights infection."},
             {"name": "a vial of antidote", "desc": "Bitter. Works on most common poisons. Probably."},
             {"name": "dried rations", "desc": "Hard bread, salt meat, dried fruit. Two days' worth."},
         ]},
        {"category": "clue", "tags": ["clue", "quest_item"],
         "items": [
             {"name": "a faded notice", "desc": "Rain-warped paper. Someone's handwriting, hurried."},
             {"name": "a charcoal rubbing", "desc": "Spirals within spirals. A language you don't know."},
             {"name": "a torn journal page", "desc": "Ink blurred with water. Dates that don't match up."},
             {"name": "a hand-drawn map", "desc": "Rough charcoal on hide. An X marks something bad."},
         ]},
    ],

    "faction_types": [
        {
            "type": "townsfolk",
            "name_templates": ["{name} Townsfolk", "The People of {name}"],
            "goals": ["Survive the season.", "Pretend everything is normal.", "Hope someone else deals with it."],
            "default_reputation": "neutral",
        },
        {
            "type": "order",
            "name_templates": ["The {adj}", "The Order of {name}", "The {noun} Keepers"],
            "goals": ["Maintain the seal.", "Find someone who can strengthen it."],
            "default_reputation": "unknown",
        },
        {
            "type": "outsiders",
            "name_templates": ["The {adj} Company", "{name}'s People", "The Travelers"],
            "goals": ["Profit.", "Information.", "Get out before things go bad."],
            "default_reputation": "neutral",
        },
    ],

    "encounter_types": [
        {
            "type": "combat",
            "weight": 2,
            "location_tags": ["dangerous", "wilderness"],
            "enemy_templates": [
                {"name": "a forest-twisted thing", "desc": "It was an animal once. Now it's branches and teeth.",
                 "stats": {"health": 6, "damage": 3, "speed": "fast"},
                 "behavior": "Ambush predator. Strikes and retreats."},
                {"name": "a hollow man", "desc": "A figure made of bark and old clothes. No face.",
                 "stats": {"health": 4, "damage": 2, "speed": "slow"},
                 "behavior": "Shambles forward. Doesn't stop."},
                {"name": "something in the dark", "desc": "You can't see it clearly. That's deliberate.",
                 "stats": {"health": 8, "damage": 4, "speed": "fast"},
                 "behavior": "Hunts from darkness. Retreats from light."},
            ],
            "tone_templates": [
                "Sudden, visceral, disorienting. The player shouldn't fully understand what attacked them.",
                "Slow buildup. The sounds first, then movement, then contact.",
            ],
        },
        {
            "type": "discovery",
            "weight": 3,
            "location_tags": ["mystery", "sacred"],
            "tone_templates": [
                "Quiet, eerie, significant. A turning point — play it slow.",
                "Build the reveal gradually. Let the player piece things together.",
            ],
        },
        {
            "type": "dialogue",
            "weight": 2,
            "location_tags": ["social"],
            "tone_templates": [
                "Shift from casual to real stakes. Drop the social mask, briefly.",
                "Tension under politeness. What's not being said matters.",
            ],
        },
    ],

    "world_rules_template": {
        "setting": "Low-fantasy medieval. Magic exists but is rare, dangerous, and poorly understood. No one calls it magic — it's 'the old ways' or 'what the forest does.'",
        "tone": "Grim but not nihilistic. Dark, atmospheric, with moments of warmth and dark humor. Folk horror with heart.",
        "era": "Roughly medieval. No gunpowder, no printing press. Iron and steel, horses and carts, candles and hearths.",
        "magic_system": "Magic is ambient, environmental, mostly beyond human control. The forest does things. Candles burn without being lit. People don't cast spells — they stumble into zones of effect, or carry objects that resonate with old forces. Magic is more like weather than a tool.",
        "combat_rules": {
            "style": "Realistic and consequential. Injuries matter.",
            "lethality": "high — one bad hit can end things",
            "healing": "slow without herbs or rest",
            "note": "Combat should feel like a failure state, not a power fantasy.",
        },
        "exploration_rules": {
            "style": "Environmental storytelling. The world shows its history through details.",
            "discovery": "Reward observation and curiosity.",
            "danger": "The wilderness is genuinely dangerous. Preparation matters.",
        },
        "dialogue_rules": {
            "style": "NPCs have their own agendas. They don't exist to serve the player.",
            "trust": "Built through actions, not dialogue choices.",
            "information": "Nobody gives everything away. Information is currency.",
        },
    },

    "player_defaults": {
        "name": "the traveler",
        "stats": {"health": 10, "stamina": 8, "perception": 6, "persuasion": 4},
        "starting_items": [
            {"id": "worn_pack", "name": "a worn leather pack",
             "description": "Cracked leather, one strap repaired with cord."},
            {"id": "waterskin", "name": "a half-empty waterskin",
             "description": "Lukewarm water. Enough for a day."},
            {"id": "belt_knife", "name": "a short knife",
             "description": "Not a weapon — a tool. Good for rope, bread, and bluffing."},
            {"id": "silver_coins", "name": "a pouch with a few silver coins",
             "description": "Enough for a room and a meal. Maybe two if you're careful."},
        ],
    },
}
