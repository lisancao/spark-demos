"""
High Fantasy — Middle Earth / classic epic fantasy.

Multiple races, ancient evil, quests of cosmic importance.
The kind of world where a farmer's kid can save everything.
"""

TEMPLATE = {
    "genre": "high-fantasy",
    "display_name": "High Fantasy",
    "description": "Epic fantasy. Ancient evil, noble quests, multiple races, and magic that shapes the fate of kingdoms.",
    "register_preset": "high-fantasy",
    "default_name": "The Last Alliance",
    "topology": "hub_and_spoke",

    "location_count": {"min": 8, "max": 14},
    "location_types": [
        {
            "type": "castle_hall",
            "weight": 1,
            "tags": ["social", "authority", "safe"],
            "is_start": True,
            "name_patterns": ["The Hall of {name}", "{name} Keep", "The {adj} Throne"],
            "sensory": {
                "sight": [
                    "Banners hanging from vaulted ceilings. Torchlight on polished stone. A throne at the far end, occupied or empty — it matters which.",
                    "Tapestries depicting battles you half-remember from songs. Stained glass throwing colored light across the floor.",
                    "Long tables, cleared. The hall echoes. Guards at every door, standing too still.",
                ],
                "sound": [
                    "Boots on stone. The clink of armor. Voices that carry whether you want them to or not.",
                    "A herald calling names. The scratch of a quill. Whispered counsel behind pillars.",
                    "The fire in the great hearth, loud as weather. Doors closing with finality.",
                ],
                "smell": [
                    "Cold stone, beeswax, roasting meat from the kitchens below.",
                    "Polished wood, old tapestry, the iron tang of the braziers.",
                    "Incense and authority. The particular staleness of a room that's always occupied.",
                ],
                "touch": [
                    "Smooth flagstones underfoot. The bannister is carved oak, worn by centuries of hands.",
                    "The cold coming off the walls. Even near the fire, the stone remembers winter.",
                    "Heavy doors. You push with both hands. The hinges are silent — well-oiled.",
                ],
            },
            "atmosphere": [
                "Power wearing a crown. Every conversation here is a negotiation.",
                "History in every stone. The weight of decisions made in this room.",
                "Grand and cold. The architecture was designed to make you feel small.",
            ],
        },
        {
            "type": "market_district",
            "weight": 2,
            "tags": ["social", "commerce"],
            "name_patterns": ["{name} Market", "The Grand Bazaar", "The {adj} Quarter"],
            "sensory": {
                "sight": [
                    "Awnings in every color. Carts piled with grain, cloth, pottery. A puppet show drawing children.",
                    "Smiths, bakers, herbalists, a cartographer arguing about borders. The city in miniature.",
                    "Cobblestone streets worn to grooves. A fountain at the center, coins glinting at the bottom.",
                ],
                "sound": [
                    "Haggling in three languages. A blacksmith's hammer. Someone playing a fiddle, badly.",
                    "Cart wheels, braying donkeys, the slap of fish on a counter.",
                    "The fountain splashing. Children chasing a dog. A merchant's pitch, well-rehearsed.",
                ],
                "smell": [
                    "Spices, leather, fresh bread, manure, and flowers — all at once.",
                    "Roasting chestnuts, tanned hides, the sharp green of herbs crushed underfoot.",
                    "Rain on hot stone. Wet wool. The sweetness of a baker's second batch.",
                ],
                "touch": [
                    "The crowd presses. Elbows and shoulders. Your coin purse needs watching.",
                    "Cobblestones uneven underfoot. A vendor pushes fabric into your hands.",
                    "Warm sun on one side of the street, cool shade on the other.",
                ],
            },
            "atmosphere": [
                "Life. Loud, messy, alive. The city at its most honest.",
                "Everyone selling something. Goods, gossip, loyalty, lies.",
                "The place where races mix. Dwarven steel next to elven silk next to halfling cheese.",
            ],
        },
        {
            "type": "temple",
            "weight": 1,
            "tags": ["sacred", "safe", "mystery"],
            "name_patterns": ["The Temple of {name}", "The {adj} Sanctum", "The {name} Cathedral"],
            "sensory": {
                "sight": [
                    "Marble columns. An altar with a flame that never dims. Priests in white moving like currents.",
                    "Stained glass telling the creation story. Light falls in patterns that shift with the hours.",
                    "Reliquaries behind glass. Offerings of wheat and silver. The silence has architecture.",
                ],
                "sound": [
                    "Chanting, low and continuous, like the building is breathing.",
                    "Footsteps that echo for too long. A bell, somewhere high, marking the hour.",
                    "Pages turning. Prayer murmured. The flame on the altar hissing faintly.",
                ],
                "smell": [
                    "Frankincense, beeswax, old stone, and the particular cleanness of consecrated space.",
                    "Dried flowers on the altar. Candle smoke. Something ancient in the walls.",
                    "Ink and parchment from the scriptorium. Holy water — just water, but colder somehow.",
                ],
                "touch": [
                    "The marble floor is cold through boot soles. The holy water font is smooth as glass.",
                    "Wooden pews, centuries old, warm where others have sat before.",
                    "The air is cool and still. It presses gently, like a held breath.",
                ],
            },
            "atmosphere": [
                "Sacred in a way you feel in your chest. Whether you believe or not.",
                "The divine, organized. Power channeled through ritual and architecture.",
                "Peace. Or the enforcement of it. Hard to tell from inside.",
            ],
        },
        {
            "type": "tavern",
            "weight": 2,
            "tags": ["social", "rest", "safe"],
            "name_patterns": ["The {adj} {noun}", "The {noun} and {noun2}", "{name}'s Hearth"],
            "sensory": {
                "sight": [
                    "Warm light, long tables, a bard in the corner. Ale flowing, laughter flowing faster.",
                    "Mounted antlers, a shield above the mantle, initials carved into every surface.",
                    "A roaring fire. Travelers in road-stained cloaks. The innkeeper watching everything.",
                ],
                "sound": [
                    "A bard singing off-key about a dragon. Dice on wood. Chairs scraping.",
                    "Laughter, argument, the clink of mugs. A song you know, sung by strangers.",
                    "The fire crackling. A serving girl calling orders. The door banging open.",
                ],
                "smell": [
                    "Ale, stew, woodsmoke, and the honest sweat of people at rest.",
                    "Roast mutton, spilled wine, pipe smoke, wet wool drying by the fire.",
                    "Bread baking, tallow candles, and the particular warmth of a room full of bodies.",
                ],
                "touch": [
                    "The bench is worn smooth. The ale is cold, the stew is hot, the bread is fresh.",
                    "Warmth from the fire. A draft from the door. The table rocks on uneven legs.",
                    "Sticky mug handle. The floor creaks underfoot. The chair fits your back.",
                ],
            },
            "atmosphere": [
                "Where every quest begins. The last warm place before the road.",
                "Strangers becoming companions over ale and a shared enemy.",
                "Refuge. Brief, imperfect, essential.",
            ],
        },
        {
            "type": "elven_glade",
            "weight": 1,
            "tags": ["sacred", "magical", "wilderness"],
            "name_patterns": ["The {adj} Glade", "{name} Wood", "The Elven {noun}"],
            "sensory": {
                "sight": [
                    "Trees that glow faintly. Platforms in the canopy. Bridges of living wood between them.",
                    "Light filtering through leaves that are green-gold even in winter. Carvings in every trunk.",
                    "A clearing where the grass is impossibly soft. Flowers that open at your approach.",
                ],
                "sound": [
                    "Birdsong that sounds arranged, not random. Running water you can't locate.",
                    "Wind in the leaves — musical, deliberate. Silence between notes.",
                    "An elven voice, singing. Far away, or very close. Hard to tell in the trees.",
                ],
                "smell": [
                    "Honey, wildflowers, clean rain, and something beneath — old and green and alive.",
                    "Pine and starlight. It shouldn't have a smell, but it does.",
                    "The particular sweetness of air that hasn't been breathed in centuries.",
                ],
                "touch": [
                    "The bark is warm. The grass doesn't bend under your feet — it moves aside.",
                    "Air like silk. Temperature perfect, as if the forest is choosing it.",
                    "The bridge sways but holds. The living wood pulses faintly under your hand.",
                ],
            },
            "atmosphere": [
                "Beauty that makes you ache. And a quiet warning that you don't belong here.",
                "Time moves differently. You've been here an hour. Or a day. The light hasn't changed.",
                "Ancient. Patient. Watching you the way a mountain watches a cloud.",
            ],
        },
        {
            "type": "dwarven_mine",
            "weight": 1,
            "tags": ["dangerous", "commerce", "underground"],
            "name_patterns": ["{name} Deep", "The {adj} Mine", "The Halls of {name}"],
            "sensory": {
                "sight": [
                    "Torch-lit tunnels carved with geometric precision. Veins of ore glinting in the walls.",
                    "A vast chamber. Pillars carved from the living rock. Bridges over a darkness that has no bottom.",
                    "Forges glowing orange in alcoves. Dwarven runes above every doorway. Dust motes in torchlight.",
                ],
                "sound": [
                    "Hammers on stone. Hammers on metal. Hammers on everything. The mountain rings.",
                    "Mine carts on rails, distant. Dripping water. The deep groan of stone settling.",
                    "Dwarven voices echoing — gruff, purposeful. A bellows pumping. Metal singing on the anvil.",
                ],
                "smell": [
                    "Hot metal, stone dust, lamp oil, and the mineral tang of underground water.",
                    "Coal smoke, iron filings, sweat, and the cold breath of deep places.",
                    "Something sulfurous from below. And the clean smell of freshly cut stone.",
                ],
                "touch": [
                    "The walls vibrate with industry. The floor is perfectly level — dwarven engineering.",
                    "Warm near the forges, cold everywhere else. The air is dry and tastes of dust.",
                    "Rough-hewn railings. The heat from a forge, fierce even at ten paces.",
                ],
            },
            "atmosphere": [
                "Industry and pride carved into stone. Every surface is a monument to craft.",
                "Deep. The weight of the mountain above you. Comforting or crushing, depending.",
                "The dwarves didn't find this place. They made it. Every inch, by hand.",
            ],
        },
        {
            "type": "wizard_tower",
            "weight": 1,
            "tags": ["magical", "mystery", "dangerous"],
            "name_patterns": ["The Tower of {name}", "The {adj} Spire", "{name}'s Observatory"],
            "sensory": {
                "sight": [
                    "Spiraling stairs. Books on every surface. Astrolabes and crystals catching light that has no source.",
                    "A window showing stars, though it's midday outside. Maps of places that don't exist yet.",
                    "Jars of things you can't identify. Chalk circles on the floor. A cat watching you with too much intelligence.",
                ],
                "sound": [
                    "The scratch of a quill that writes by itself. Bubbling from somewhere. Whispered equations.",
                    "Wind at the top, always. The creak of the tower in a breeze that isn't there.",
                    "Pages turning without hands. A clock with too many hands, ticking at different speeds.",
                ],
                "smell": [
                    "Old paper, ozone, dried herbs, and something that smells like the color blue.",
                    "Ink, candle wax, sulfur, and the particular dryness of preserved knowledge.",
                    "Burnt amber. Star anise. Something from the cauldron that makes your eyes water.",
                ],
                "touch": [
                    "The banister is warm on one side, cold on the other. The stairs shift underfoot.",
                    "Static in the air. Your hair lifts. The books hum when you touch them.",
                    "The door opens before you knock. The chair adjusts to fit you.",
                ],
            },
            "atmosphere": [
                "Knowledge that costs. Every answer here comes with a price or a warning.",
                "Power, barely contained. The walls are thinner than they look.",
                "A mind made architecture. Brilliant, cluttered, dangerous to the uninvited.",
            ],
        },
        {
            "type": "battlefield",
            "weight": 1,
            "tags": ["dangerous", "transitional"],
            "name_patterns": ["The {adj} Field", "The Battle of {name}", "{name} Plains"],
            "sensory": {
                "sight": [
                    "Churned earth. Broken standards. Crows picking at what's left.",
                    "Trenches and barricades, some still standing. Arrows bristling from the ground like dead grass.",
                    "A vast flat field. Cairns marking the fallen. The grass growing back, not quite covering the scars.",
                ],
                "sound": [
                    "Wind. Nothing else. The silence of a place that's used up all its noise.",
                    "Crows arguing. The flutter of a torn banner. Your footsteps, too loud.",
                    "The grass hissing in the wind. A distant hammer — someone building a memorial.",
                ],
                "smell": [
                    "Turned earth. Rust. The particular flatness of aftermath.",
                    "Grass and iron. Rain-washed, but the ground remembers.",
                    "Nothing. The wind has scoured it clean. Almost.",
                ],
                "touch": [
                    "The ground is soft, disturbed. Your boots sink slightly.",
                    "Wind that cuts. Cold metal half-buried. The earth gives under your weight.",
                    "A broken sword hilt in the dirt. Still sharp enough to cut.",
                ],
            },
            "atmosphere": [
                "The cost of heroism, laid out in mud and markers.",
                "History written in the ground. The dead are patient teachers.",
                "Glory, in the stories. Here, just the aftermath.",
            ],
        },
        {
            "type": "shire_village",
            "weight": 2,
            "tags": ["safe", "social", "rest"],
            "name_patterns": ["{name} Village", "The {adj} Hamlet", "{name}'s Hollow"],
            "sensory": {
                "sight": [
                    "Round doors in hillsides. Smoke from chimneys. Gardens that put the elves to shame.",
                    "A village green with a party tree. Washing lines and children and somebody's prize pig.",
                    "Thatched roofs, stone walls, window boxes full of color. Everything at halfling scale.",
                ],
                "sound": [
                    "Laughter. A hammer on a barrel. Children screaming with joy. Birds, everywhere.",
                    "A fiddle and a drum. Someone singing about pie. The splash of the village stream.",
                    "Chickens. A dog barking at nothing. The creak of a gate. Comfortable sounds.",
                ],
                "smell": [
                    "Fresh bread, pipe smoke, grass cuttings, and something baking that you can't resist.",
                    "Honey, apples, wood shavings, and the clean smell of hung laundry.",
                    "Autumn leaves, roasting chestnuts, cider, and the particular warmth of a well-kept home.",
                ],
                "touch": [
                    "Soft grass underfoot. The sun is warm. The bench by the green fits perfectly.",
                    "A mug of cider pressed into your hand before you ask. The chair is too small but welcoming.",
                    "The gate latch is smooth wood. The path is swept clean. Everything here is maintained with love.",
                ],
            },
            "atmosphere": [
                "What you're fighting to protect. Simple, good, worth it.",
                "Peace that doesn't know it's precious. Not yet.",
                "Home. Or what home should feel like. The kind of place heroes come from.",
            ],
        },
        {
            "type": "mountain_pass",
            "weight": 1,
            "tags": ["dangerous", "wilderness", "transitional"],
            "name_patterns": ["The {adj} Pass", "{name} Gap", "The {name} Stairs"],
            "sensory": {
                "sight": [
                    "Stone switchbacks carved into the cliff. Cloud below you. The path narrows to nothing.",
                    "Snow on the peaks. The trail is a thread between two drops. Eagles circling.",
                    "A bridge of stone and hope across a chasm. The wind tries to make decisions for you.",
                ],
                "sound": [
                    "Wind. Relentless. Conversation is impossible. Your own heartbeat in your ears.",
                    "Rocks falling somewhere. The crack of ice. The mountain settling, indifferent.",
                    "Your breathing, labored. The scrape of boots on stone. Nothing else survives up here.",
                ],
                "smell": [
                    "Cold. That's a smell up here. Clean, empty, thin.",
                    "Ice, rock dust, and the faint sulfur of distant volcanic vents.",
                    "Nothing. The air is too thin to carry much. Your lungs notice.",
                ],
                "touch": [
                    "Cold that finds every gap in your clothing. Stone under your fingers, rough and certain.",
                    "The wind pushing you sideways. Ice on the path. Every step deliberate.",
                    "Your hands numb. The rope is stiff with frost. The stone is the only friend you have.",
                ],
            },
            "atmosphere": [
                "The world made vertical. Every step earned. No shortcuts in the mountains.",
                "Beautiful and lethal. The view is the last thing you see if you're careless.",
                "Between here and there. The hard way. The only way.",
            ],
        },
    ],

    "name_pools": {
        "adj": ["Golden", "Fallen", "Ancient", "Silver", "Iron", "Misty",
                "Shadowed", "White", "High", "Lost", "Starlit", "Broken",
                "Emerald", "Crimson", "Eternal", "Thunder"],
        "noun": ["Crown", "Shield", "Flame", "Oak", "Stone", "Gate",
                 "Tower", "Bridge", "Horn", "Sword", "Haven", "Hammer"],
        "noun2": ["Dragon", "Eagle", "Wolf", "Stag", "Lion", "Bear",
                  "Raven", "Fox", "Serpent", "Phoenix"],
        "name": ["Thalindor", "Oakenheim", "Silvermere", "Ironforge",
                 "Ravenhill", "Goldenhall", "Stormwatch", "Duskhollow",
                 "Brightwater", "Thornfield", "Deepholm", "Starfall",
                 "Kingsreach", "Eldergrove", "Windmere", "Ashenmoor"],
    },

    "npc_count": {"min": 5, "max": 12},
    "npc_archetypes": [
        {
            "role": "king",
            "voice": "noble",
            "weight": 1,
            "location_type": "castle_hall",
            "names": ["King Aldric", "Queen Elara", "Lord Regent Thane",
                      "King Beren", "Queen Morwen", "The High King"],
            "personalities": [
                "Burdened, wise, aging. Carries the crown like a penance. Makes hard choices and sleeps badly.",
                "Young, idealistic, untested. Inherited a kingdom at war and a court full of serpents.",
                "Stern, just, lonely. Rules by law because trust is too expensive.",
            ],
            "knowledge_topics": ["kingdom politics", "the ancient threat", "alliances", "the prophecy"],
            "secret_types": ["failing health", "doubt", "forbidden alliance", "the heir's true parentage"],
            "default_disposition": "formal",
        },
        {
            "role": "wizard",
            "voice": "sage",
            "weight": 1,
            "location_type": "wizard_tower",
            "names": ["Aldanor", "Mirathis", "The Grey Wanderer",
                      "Seren", "Thalorin", "Old Elm"],
            "personalities": [
                "Cryptic, kind, infuriating. Answers questions with better questions. Knows more than anyone alive and shares half of it.",
                "Direct, gruff, tired of fools. Power sits on him like weather. He's old enough to remember when the dark last rose.",
                "Gentle, scattered, terrifyingly powerful when focused. Talks to birds. The birds talk back.",
            ],
            "knowledge_topics": ["ancient history", "the dark power", "magic theory", "what the stars say"],
            "secret_types": ["immortality's cost", "a past failure", "knows the ending", "isn't what he appears"],
            "default_disposition": "enigmatic",
        },
        {
            "role": "ranger",
            "voice": "ranger",
            "weight": 2,
            "location_type": "mountain_pass",
            "names": ["Strider", "Kael", "Thornwood", "Ashlyn",
                      "Dain", "The Warden", "Lirael", "Fenris"],
            "personalities": [
                "Quiet, competent, haunted. Knows the wild better than any map. Fights alone because he's lost everyone who followed.",
                "Laconic, watchful, dry humor. Speaks in short sentences and long silences. Trusts the forest more than people.",
                "Fierce, protective, scarred. Guards the borders because she's seen what gets through when nobody watches.",
            ],
            "knowledge_topics": ["wilderness routes", "enemy movements", "tracking", "the old roads"],
            "secret_types": ["exiled nobility", "failed oath", "the thing in the forest", "lost love"],
            "default_disposition": "reserved",
        },
        {
            "role": "bard",
            "voice": "performer",
            "weight": 1,
            "location_type": "tavern",
            "names": ["Lyric", "Tam", "Goldfinch", "Melody",
                      "The Songbird", "Pip", "Rhyme", "Cadence"],
            "personalities": [
                "Charming, clever, collecting stories. Every conversation is material. Every smile is genuine and strategic.",
                "Flamboyant, sharp, hiding pain behind performance. The songs are funny until you listen to the words.",
                "Quiet offstage, electric on. Watches everything, remembers everything, sings it all back transformed.",
            ],
            "knowledge_topics": ["legends", "court gossip", "who's traveling where", "the old songs"],
            "secret_types": ["spy for a faction", "witnessed something terrible", "the song that's forbidden", "noble in hiding"],
            "default_disposition": "friendly",
        },
        {
            "role": "elf_lord",
            "voice": "ancient",
            "weight": 1,
            "location_type": "elven_glade",
            "names": ["Lord Celeborn", "Lady Nimloth", "Thanduil",
                      "Aerin", "The Eldest", "Star-keeper"],
            "personalities": [
                "Ancient, beautiful, sad. Has watched civilizations rise and fall. Cares deeply but from a great distance.",
                "Formal, precise, wary of mortals. Not cruel — just aware that human lives are seasons to elven years.",
                "Warm, surprising, curious about mortals. Old enough to find short-lived passions fascinating rather than tragic.",
            ],
            "knowledge_topics": ["ancient history", "elvish magic", "the enemy's origins", "the fading"],
            "secret_types": ["choosing to leave", "ancient wrong", "a mortal they loved", "the price of immortality"],
            "default_disposition": "courteous",
        },
        {
            "role": "dwarf_smith",
            "voice": "craftsman",
            "weight": 1,
            "location_type": "dwarven_mine",
            "names": ["Thorin", "Gimla", "Durin's Heir", "Brokk",
                      "Helga Ironhand", "Forge-master Krag"],
            "personalities": [
                "Blunt, proud, skilled beyond measure. Judges people by their hands — rough means honest, soft means trouble.",
                "Gruff, loyal, stubborn as the stone he works. Once a friend, always a friend. Once an enemy, forever.",
                "Loud, generous, competitive. Every piece must be his best yet. Takes failure personally.",
            ],
            "knowledge_topics": ["metallurgy", "mining", "dwarven history", "underground routes"],
            "secret_types": ["a masterwork gone wrong", "a sealed tunnel", "dwarven politics", "a grudge from centuries ago"],
            "default_disposition": "gruff",
        },
        {
            "role": "thief",
            "voice": "rogue",
            "weight": 1,
            "location_type": "market_district",
            "names": ["Quickfingers", "Shade", "Pip", "Raven",
                      "The Sparrow", "Silk", "Nix", "Dart"],
            "personalities": [
                "Quick, charming, untrustworthy — but with a code. Steals from those who can afford it. Mostly.",
                "Street-smart, defensive, young. Grew up with nothing and learned that taking is easier than asking.",
                "Smooth, sophisticated, amoral. Not a pickpocket — an artist with a flexible relationship to property.",
            ],
            "knowledge_topics": ["the underworld", "secret passages", "who has what", "escape routes"],
            "secret_types": ["heart of gold", "stealing for someone else", "knows the castle's secrets", "former nobility"],
            "default_disposition": "evasive",
        },
    ],

    "quest_patterns": [
        {
            "type": "epic_quest",
            "name_templates": ["The {adj} Quest", "The {noun} of {name}", "The Last {noun}"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Learn of the threat from {npc}.", "location_type": "castle_hall"},
                {"objective": "Seek counsel at {location}.", "location_type": "wizard_tower"},
                {"objective": "Journey through {destination} to reach the goal.", "location_type": "mountain_pass"},
                {"objective": "Face the challenge at {destination}.", "location_type": "battlefield"},
            ],
        },
        {
            "type": "diplomacy",
            "name_templates": ["The {adj} Alliance", "Uniting {name}", "The Council of {name}"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Receive the king's charge from {npc}.", "location_type": "castle_hall"},
                {"objective": "Win the elves' trust at {location}.", "location_type": "elven_glade"},
                {"objective": "Negotiate with the dwarves at {location}.", "location_type": "dwarven_mine"},
                {"objective": "Unite the forces at {destination}.", "location_type": "castle_hall"},
            ],
        },
        {
            "type": "investigation",
            "name_templates": ["The {adj} Conspiracy", "Traitors in {name}", "The {noun}'s Shadow"],
            "stages": 3,
            "stage_templates": [
                {"objective": "Hear rumors from {npc}.", "location_type": "tavern"},
                {"objective": "Investigate the evidence at {location}.", "location_type": "market_district"},
                {"objective": "Confront the traitor at {destination}.", "location_type": "castle_hall"},
            ],
        },
        {
            "type": "rescue",
            "name_templates": ["Saving {name}", "The {adj} Prison", "Into the {noun}"],
            "stages": 3,
            "stage_templates": [
                {"objective": "Learn who was taken from {npc}.", "location_type": "shire_village"},
                {"objective": "Track the captors through {location}.", "location_type": "mountain_pass"},
                {"objective": "Free the captive at {destination}.", "location_type": "any"},
            ],
        },
    ],

    "item_types": [
        {"category": "weapon", "tags": ["weapon"],
         "items": [
             {"name": "a dwarven-forged sword", "desc": "Runes along the blade. It hums faintly near danger."},
             {"name": "an elven longbow", "desc": "Pale wood, impossibly light. The string sings when drawn."},
             {"name": "a battle axe", "desc": "Heavy iron, leather-wrapped haft. Dwarven make — built to last."},
             {"name": "a short sword", "desc": "Simple, balanced, practical. A soldier's weapon."},
         ]},
        {"category": "tool", "tags": ["tool"],
         "items": [
             {"name": "a rope of elven make", "desc": "Thin as twine, strong as chain. Fifty feet, weightless."},
             {"name": "a tinderbox", "desc": "Dwarven flint. Sparks in any weather."},
             {"name": "a map of the realm", "desc": "Hand-drawn on vellum. Some borders are already wrong."},
             {"name": "a healer's kit", "desc": "Herbs, bandages, a needle, and a prayer."},
         ]},
        {"category": "consumable", "tags": ["consumable", "medical"],
         "items": [
             {"name": "a vial of healing draught", "desc": "Elvish recipe. Tastes of starlight and regret. Works fast."},
             {"name": "lembas bread", "desc": "Elven waybread. A single cake sustains for a day's march."},
             {"name": "a flask of miruvor", "desc": "Cordial of the elves. Warmth and strength in every sip."},
         ]},
        {"category": "clue", "tags": ["clue", "quest_item"],
         "items": [
             {"name": "a fragment of prophecy", "desc": "Ancient script on crumbling parchment. Three lines. Two are legible."},
             {"name": "a signet ring", "desc": "House crest you recognize. Found where it shouldn't be."},
             {"name": "a charcoal rubbing", "desc": "Elvish script from a standing stone. Warning or invitation."},
             {"name": "a captain's journal", "desc": "Water-stained. The last entry is unfinished."},
         ]},
    ],

    "faction_types": [
        {
            "type": "kingdom",
            "name_templates": ["The Kingdom of {name}", "The {adj} Realm", "The Free Peoples"],
            "goals": ["Defend the realm.", "Unite against the darkness.", "Preserve what's good."],
            "default_reputation": "friendly",
        },
        {
            "type": "dark_power",
            "name_templates": ["The {adj} Host", "The Shadow of {name}", "The Enemy"],
            "goals": ["Dominion.", "Corruption.", "The end of all free things."],
            "default_reputation": "hostile",
        },
        {
            "type": "neutral_power",
            "name_templates": ["The {adj} Council", "The Guild of {name}", "The {noun} League"],
            "goals": ["Survive.", "Profit from both sides.", "Maintain independence."],
            "default_reputation": "neutral",
        },
    ],

    "encounter_types": [
        {
            "type": "combat",
            "weight": 2,
            "location_tags": ["dangerous", "wilderness"],
            "enemy_templates": [
                {"name": "an orc war-band", "desc": "Five, armored in black iron. Yellow eyes, crude weapons, organized.",
                 "stats": {"health": 7, "damage": 3, "speed": "medium"},
                 "behavior": "Pack tactics. Flanking. They've done this before."},
                {"name": "a cave troll", "desc": "Massive. Skin like stone. Stupid but strong enough that it doesn't matter.",
                 "stats": {"health": 15, "damage": 6, "speed": "slow"},
                 "behavior": "Charges. Swings. Doesn't stop until dead or bored."},
                {"name": "a wraith", "desc": "A shape in the dark. Cold radiates from it. Your sword feels heavy.",
                 "stats": {"health": 10, "damage": 4, "speed": "fast"},
                 "behavior": "Fear first, then the blade. Retreats from light and fire."},
            ],
            "tone_templates": [
                "Heroic but costly. Victory comes with bruises and lessons. Every fight matters.",
                "Desperate, outnumbered, turning the tide through courage or cleverness.",
            ],
        },
        {
            "type": "discovery",
            "weight": 3,
            "location_tags": ["magical", "mystery", "sacred"],
            "tone_templates": [
                "Wonder. The world is bigger and older than you knew. Let the player feel small in a good way.",
                "A piece of the puzzle. History speaking through ruins, relics, or living memory.",
            ],
        },
        {
            "type": "dialogue",
            "weight": 3,
            "location_tags": ["social", "safe"],
            "tone_templates": [
                "Counsel. Wisdom offered freely but hard to hear. The right choice isn't the easy one.",
                "Debate between allies. Everyone wants the same thing but disagrees on how to get it.",
            ],
        },
    ],

    "world_rules_template": {
        "setting": "High fantasy. A world of multiple races, ancient magic, and a rising darkness that threatens all free peoples.",
        "tone": "Epic, hopeful beneath the danger. Tolkien's moral clarity with room for gray. The ordinary matters as much as the grand.",
        "era": "Medieval to early Renaissance. Swords, horses, castles. Technology varies by race — dwarven engineering, elven artistry, human adaptability.",
        "magic_system": "Magic is real, powerful, and rare. Wizards study it for lifetimes. Elves breathe it. Dwarves forge it into metal. Dark magic corrupts. All power has a cost.",
        "combat_rules": {
            "style": "Heroic but grounded. Skill and courage matter, but so does armor and numbers.",
            "lethality": "moderate — heroes are tougher than average, but not invulnerable",
            "healing": "magic and herbs — faster than nature, slower than instant",
            "note": "Combat should feel earned. Every victory has weight. Every loss has meaning.",
        },
        "exploration_rules": {
            "style": "A world rich with history. Every ruin tells a story. The landscape is a character.",
            "discovery": "Wonder and danger in equal measure. The beautiful places can kill you.",
            "danger": "The wild is wild. Roads exist for a reason. Leave them at your peril.",
        },
        "dialogue_rules": {
            "style": "Weight and warmth. Characters speak with purpose. Even casual speech reveals character.",
            "trust": "Earned through deeds. Words matter, but actions define.",
            "information": "Shared freely among allies. Hoarded by the wise when the enemy might be listening.",
        },
    },

    "player_defaults": {
        "name": "the wanderer",
        "stats": {"health": 12, "stamina": 10, "wisdom": 5, "charisma": 5},
        "starting_items": [
            {"id": "travel_cloak", "name": "a travel-worn cloak",
             "description": "Grey-green. Good for blending with the road. Keeps the rain off. Mostly."},
            {"id": "waterskin", "name": "a leather waterskin",
             "description": "Full. Cool water from the last stream."},
            {"id": "short_sword", "name": "a short sword",
             "description": "Plain hilt, keen edge. Not legendary — reliable."},
            {"id": "coin_purse", "name": "a purse of mixed coin",
             "description": "Silver and copper. Enough for lodging and supplies. Spend carefully."},
        ],
    },
}
