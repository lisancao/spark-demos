"""
Post-Apocalyptic — Fallout style.

Wasteland, scavengers, mutants, bunkers. The world ended.
What's left is trying to figure out what comes next.
"""

TEMPLATE = {
    "genre": "post-apocalyptic",
    "display_name": "Post-Apocalyptic",
    "description": "The world ended. Now there's the wasteland, scavengers, and the slow work of building something from nothing.",
    "register_preset": "post-apocalyptic",
    "default_name": "Dust and Echoes",
    "topology": "branching_paths",

    "location_count": {"min": 8, "max": 14},
    "location_types": [
        {
            "type": "trading_post",
            "weight": 2,
            "tags": ["social", "commerce", "safe"],
            "is_start": True,
            "name_patterns": ["{name} Trading Post", "The {adj} Market", "{name}'s Store"],
            "sensory": {
                "sight": [
                    "A shipping container cut open and roofed with corrugated tin. Shelves of salvage, bartered and priced in caps.",
                    "Tarps and rope, tables made of car hoods. Everything for sale has been something else first.",
                    "Hand-painted signs. A guard with a shotgun on a lawn chair. A line of people with things to trade.",
                ],
                "sound": [
                    "Haggling. A generator chugging. The clink of bottle caps changing hands.",
                    "Wind snapping the tarps. Someone testing a radio. A dog tied to a post, not barking.",
                    "A woman counting caps. A man arguing about water prices. The generator, always the generator.",
                ],
                "smell": [
                    "Diesel exhaust, cured meat, the chemical tang of water purification tablets.",
                    "Gun oil, leather, something cooking — jerky, maybe. Or rat. Best not to ask.",
                    "Dust and barter. The smell of people who walk a long way to trade.",
                ],
                "touch": [
                    "Everything is rough. Wood, metal, fabric — nothing has been manufactured in your lifetime.",
                    "The counter is a car door laid flat. It wobbles. The caps are warm from someone's pocket.",
                    "Dust on everything. It gets in your teeth. The water costs extra if it's filtered.",
                ],
            },
            "atmosphere": [
                "Civilization, rebuilt one barter at a time. Fragile, essential, human.",
                "The only law here is trade. Fair or not depends on your leverage.",
                "Where people remember how to be people. For a few hours, at least.",
            ],
        },
        {
            "type": "bunker",
            "weight": 1,
            "tags": ["safe", "mystery", "underground"],
            "name_patterns": ["Vault {noun}", "The {adj} Bunker", "Shelter {noun}"],
            "sensory": {
                "sight": [
                    "Blast doors, three feet thick, hanging open. Fluorescent lights — most working, some flickering.",
                    "Corridors of concrete and steel. Faded government posters about preparedness. A water stain shaped like a map.",
                    "Rows of bunks, some still made. A common area with a table, cards scattered. People lived here. Maybe still do.",
                ],
                "sound": [
                    "The ventilation system, laboring. Water in the pipes. Your footsteps, too loud on the metal floor.",
                    "A Geiger counter clicking slowly. The blast door groaning as it moves. Silence between the machines.",
                    "Dripping. The hum of whatever's still powered. A radio playing static on a loop.",
                ],
                "smell": [
                    "Recycled air, machine oil, the faint must of sealed spaces.",
                    "Concrete dust. Stale water. The preserved nothing-smell of a place designed to outlast the world.",
                    "Old food storage — grain, canned goods, preservatives. The ghost of meals from before.",
                ],
                "touch": [
                    "Cold metal. Cold concrete. The air is cool and dry and hasn't seen sunlight since the bombs.",
                    "The walls vibrate with the generator. The door handles are industrial — built to last, not to comfort.",
                    "Everything is sealed, bolted, redundant. Built for survival, not living.",
                ],
            },
            "atmosphere": [
                "A time capsule. The old world's last bet. Whether it paid off depends on who's inside.",
                "Safety, at a cost. The walls keep everything out. Including the future.",
                "Answers to questions nobody alive was around to ask. Maybe a working shower.",
            ],
        },
        {
            "type": "wasteland",
            "weight": 3,
            "tags": ["dangerous", "wilderness"],
            "name_patterns": ["The {adj} Wastes", "{name} Flats", "The Dead {noun}"],
            "sensory": {
                "sight": [
                    "Flat to the horizon. Cracked earth, dead trees, a rusted highway overpass in the distance.",
                    "Dust devils. The skeleton of a suburb — foundations and chimneys. A billboard advertising something extinct.",
                    "Bleached concrete, twisted rebar, a car half-buried in sand. The sky is too big.",
                ],
                "sound": [
                    "Wind. Just wind. It carries dust and nothing else.",
                    "Your boots on gravel. A distant rumble — thunder or something worse. Metal creaking in the heat.",
                    "The ping of your Geiger counter. Steady. You learn to listen for changes.",
                ],
                "smell": [
                    "Dust, hot metal, ozone. The air tastes like a coin left in the sun.",
                    "Nothing alive. The wind smells like distance and old fire.",
                    "Alkali dust, sun-baked plastic, and the faintest sulfur from somewhere underground.",
                ],
                "touch": [
                    "Heat radiating from the ground. Even through boot soles. Sweat evaporates before it forms.",
                    "Grit in every fold of your clothing. The wind sandpapers exposed skin.",
                    "The metal of the car hood — hot enough to cook on. People do.",
                ],
            },
            "atmosphere": [
                "The world's corpse, drying in the sun. Beautiful in the way only dead things can be.",
                "Empty. Miles of nothing between something. The distance will kill you before anything else.",
                "What's left. Not nothing — just less. Every mile, a reminder of what there was.",
            ],
        },
        {
            "type": "raider_camp",
            "weight": 1,
            "tags": ["dangerous", "criminal"],
            "name_patterns": ["The {adj} Camp", "{name}'s Turf", "The {noun} Nest"],
            "sensory": {
                "sight": [
                    "Sharpened car doors as barricades. Skulls on poles. Graffiti in spray paint and blood.",
                    "A compound of scrap metal and aggression. Fires burning in oil drums. Sentries with makeshift weapons.",
                    "Trophies from raids — clothes, gear, things that belonged to people. Wire fences topped with glass.",
                ],
                "sound": [
                    "Shouting. Metal music from a car battery speaker. Someone sharpening something.",
                    "Dogs — or something that used to be dogs. Engines revving. Gunfire, recreational.",
                    "Laughter that isn't friendly. The clank of chains. Someone crying, quietly.",
                ],
                "smell": [
                    "Smoke, sweat, gasoline, and the sour tang of people who've stopped caring about hygiene.",
                    "Burning plastic. Cooked meat you don't want identified. Motor oil and gunpowder.",
                    "Fear. It has a smell — sharp, metallic, underneath the fire and the fuel.",
                ],
                "touch": [
                    "Everything here is sharp. The barricades, the people, the air between them.",
                    "Heat from the fire drums. Cold metal in your hands if they let you keep your weapon.",
                    "The ground is littered. Glass, metal, shell casings. Watch where you step.",
                ],
            },
            "atmosphere": [
                "The end of civility. What happens when people decide the rules died with the old world.",
                "Strength is the only currency. Everything else is taken.",
                "Not evil. Just survival without the parts that make it worth surviving.",
            ],
        },
        {
            "type": "ruins",
            "weight": 2,
            "tags": ["dangerous", "mystery"],
            "name_patterns": ["The {adj} Ruins", "Old {name}", "The {name} Remains"],
            "sensory": {
                "sight": [
                    "A city block, collapsed inward. Office buildings with their skin blown off, showing floors like shelves.",
                    "A library. Roof gone. Books pulped by rain. A staircase leading to a second floor that isn't there.",
                    "Houses in rows, each one damaged differently. Nature reclaiming — vines through windows, trees through roofs.",
                ],
                "sound": [
                    "Creaking. The ruins shift and settle. Somewhere, water dripping into a basement.",
                    "Pigeons. Glass crunching underfoot. The wind playing the buildings like instruments.",
                    "Your Geiger counter, ticking faster. Then slower. The hotspots move with the wind.",
                ],
                "smell": [
                    "Wet concrete, mold, rust. The particular smell of a building dying slowly.",
                    "Old paper, rat droppings, rain-washed ash. The ghost of what burned.",
                    "Plaster dust, standing water, something chemical from the cracked foundation.",
                ],
                "touch": [
                    "Concrete crumbles under your hand. The rebar is warm from the sun. Everything shifts.",
                    "Glass on every surface. The doorframe flexes when you lean on it. Don't lean.",
                    "Damp in the lower levels. Dry and hot above. The building can't regulate itself anymore.",
                ],
            },
            "atmosphere": [
                "Memory, crumbling. Every room was someone's. Every desk had a name.",
                "The old world, pickable. Salvage is archaeology with less reverence.",
                "Ghosts without the supernatural. Just the weight of what used to be here.",
            ],
        },
        {
            "type": "water_source",
            "weight": 1,
            "tags": ["safe", "commerce", "contested"],
            "name_patterns": ["The {adj} Spring", "{name} Well", "The Clean {noun}"],
            "sensory": {
                "sight": [
                    "A pipe sticking from rock, dripping clear water into a concrete basin. People waiting with containers.",
                    "A covered well with a hand pump. Guard posted. The line is long and nobody cuts.",
                    "Green. Actual green — plants growing near the water. The first color you've seen in miles.",
                ],
                "sound": [
                    "Water trickling. The pump squeaking. People talking in the patient way of those who wait.",
                    "Containers filling. Children splashing. An argument about rations, quickly settled.",
                    "The spring bubbling. Birdsong — actual birds, drawn by the water.",
                ],
                "smell": [
                    "Clean water. After the wasteland, it smells like a miracle.",
                    "Wet earth, green growth, the mineral tang of groundwater. Life.",
                    "Chlorine from purification. Clean, sharp, reassuring.",
                ],
                "touch": [
                    "Cool water on cracked hands. The basin rim is smooth, worn by a thousand reaching hands.",
                    "Wet grass underfoot. After the wasteland, the softness is almost painful.",
                    "The pump handle is worn smooth. The water is cold. You drink and it reaches your bones.",
                ],
            },
            "atmosphere": [
                "The most valuable thing in the wasteland. Everything else is negotiable.",
                "Life, concentrated. Where water is, people are. Where people are, trouble follows.",
                "Hope, liquid. Every settlement starts with water. Every war, too.",
            ],
        },
        {
            "type": "settlement",
            "weight": 2,
            "tags": ["social", "safe", "rest"],
            "name_patterns": ["{name} Settlement", "New {name}", "The {adj} Hold"],
            "sensory": {
                "sight": [
                    "Walls of stacked cars and corrugated metal. Inside, gardens, laundry lines, children. A town.",
                    "Salvaged buildings with new roofs. A water tower, hand-painted with the settlement name. Sentries on the walls.",
                    "Market stalls, a clinic, a bar. People with jobs, routines, hope. Fragile and real.",
                ],
                "sound": [
                    "Conversation. A hammer on nails. A child laughing. Sounds of building, not surviving.",
                    "The gate closing behind you — heavy, reassuring. A bell for mealtimes. A generator, steady.",
                    "Music from the bar. Someone teaching — actually teaching, to actual students.",
                ],
                "smell": [
                    "Cooking — real cooking, with spices and patience. Woodsmoke. Growing things.",
                    "Sweat from honest work. Laundry drying. The particular smell of people who've stopped running.",
                    "Garden soil. Bread baking. Something fermenting. Humanity, trying again.",
                ],
                "touch": [
                    "The walls are solid. The gate locks. For the first time in days, your shoulders drop.",
                    "A chair. An actual chair, with a back. The luxury of sitting without watching for threats.",
                    "A bed with blankets. Clean water in a cup. The profound comfort of safety.",
                ],
            },
            "atmosphere": [
                "The argument for going on. People rebuilding because the alternative is nothing.",
                "Community, earned. Every wall was raised together. Every meal is shared.",
                "Home. Or as close as the wasteland allows. Worth defending.",
            ],
        },
        {
            "type": "radiation_zone",
            "weight": 1,
            "tags": ["dangerous", "mystery", "contaminated"],
            "name_patterns": ["The {adj} Zone", "The Glow", "{name} Crater"],
            "sensory": {
                "sight": [
                    "Everything glows faintly. The ground is glass where the sand fused. Shapes in the distance that might be buildings.",
                    "A crater. Vast. The center is still hot — heat shimmer rises. Nothing grows for a mile.",
                    "Mutated vegetation — too big, too many leaves, wrong colors. Beautiful and deeply wrong.",
                ],
                "sound": [
                    "Your Geiger counter screaming. The wind sounds different here — thicker, charged.",
                    "Nothing living makes sound here. The silence is chemical.",
                    "A hum from the ground. Sub-audible. Your fillings vibrate.",
                ],
                "smell": [
                    "Ozone, hot metal, something sweet that your body knows means danger.",
                    "The air tastes electric. Your nose burns slightly. Time to check your dosimeter.",
                    "Nothing. Your nose stops working in the hot zones. That's a bad sign.",
                ],
                "touch": [
                    "Tingling skin. The warmth isn't from the sun — it's from the ground. Your Geiger counter confirms.",
                    "Static. Everything you touch sparks. Your hair stands up.",
                    "The air itself feels thicker. Pressure on your skin. Your body knows before your mind.",
                ],
            },
            "atmosphere": [
                "Ground zero for the end of the world. The scar that won't heal.",
                "Deadly, fascinating, tempting. The best salvage is in the places that kill you.",
                "A reminder. This is what happened. This is what we did.",
            ],
        },
        {
            "type": "overpass",
            "weight": 1,
            "tags": ["transitional", "dangerous"],
            "name_patterns": ["The {adj} Overpass", "Highway {noun}", "The Bridge"],
            "sensory": {
                "sight": [
                    "A concrete ribbon across the wasteland. Cars frozen in the last traffic jam. Rust and sun.",
                    "Gaps in the road where sections collapsed. You can see the ground far below.",
                    "Graffiti from survivors. Dates, names, arrows pointing somewhere safer. A sniper's paradise.",
                ],
                "sound": [
                    "Wind through car windows. Metal groaning. The overpass sways in strong gusts.",
                    "Your footsteps echo on concrete. Something scuttling under a car. A distant engine.",
                    "The creak of a car door, swinging. Wind through rebar. Silence between gusts.",
                ],
                "smell": [
                    "Old rubber, rust, sun-baked upholstery. The particular death of machines.",
                    "Concrete dust, bird droppings, and the empty smell of abandonment.",
                    "Wind from the wasteland below — dust, alkali, distance.",
                ],
                "touch": [
                    "The guardrail is hot metal. The concrete is cracked and shifting. Watch the gaps.",
                    "Wind tries to push you sideways. The surface is gritty — sand blown up from below.",
                    "A car door handle, sun-warm. The glove compartment might have something. Probably doesn't.",
                ],
            },
            "atmosphere": [
                "A road to nowhere, suspended above nothing. The view is excellent and dangerous.",
                "The old world's arteries, drained dry. Now just geography for the walking.",
                "High ground. Good for seeing. Also good for being seen.",
            ],
        },
        {
            "type": "scrapyard",
            "weight": 1,
            "tags": ["commerce", "dangerous"],
            "name_patterns": ["{name}'s Scrapyard", "The {adj} Heap", "The Boneyard"],
            "sensory": {
                "sight": [
                    "Mountains of metal. Car bodies stacked five high. A crane that somehow still works.",
                    "Organized chaos — the owner knows where everything is. Sorted by vehicle, by era, by usefulness.",
                    "A workshop under a tarp. Tools hung on pegboard. Parts laid out like surgery.",
                ],
                "sound": [
                    "Metal on metal. The grind of a hand-crank drill. Someone hammering shape into salvage.",
                    "The crane groaning. A cutting torch hissing. Dogs barking — the yard's security system.",
                    "Wind through the stacks — a low moan, shifting pitch. The scrapyard sings.",
                ],
                "smell": [
                    "Rust, motor oil, cutting fluid, and the hot metal smell of fabrication.",
                    "Rubber, battery acid, paint thinner. The smell of making things work again.",
                    "Grease and ambition. Someone here is building something.",
                ],
                "touch": [
                    "Everything has an edge. Gloves are mandatory. The metal is hot in the sun, cold in the shade.",
                    "Oil on every surface. The tools are worn smooth. The workbench vibrates with the generator.",
                    "Rough. Everything here was broken once. The good ones got fixed. The rest are parts.",
                ],
            },
            "atmosphere": [
                "Where the old world gets recycled into the new. Alchemy with a wrench.",
                "The mechanic is the most important person in the wasteland. This is their kingdom.",
                "Hope in metal form. If it can be fixed, it can be useful. If it's useful, it's alive.",
            ],
        },
    ],

    "name_pools": {
        "adj": ["Rusted", "Burnt", "Dead", "Dry", "Last", "Broken",
                "Hollow", "Ash", "Dust", "Iron", "Salt", "Scorch",
                "Bleached", "Cracked", "Silent", "Red"],
        "noun": ["Mile", "Road", "Tower", "Bridge", "Wells", "Gate",
                 "Wall", "Fork", "Ridge", "Flats", "Bones", "Pipe"],
        "noun2": ["Coyote", "Crow", "Rust", "Sand", "Bullet", "Wire",
                  "Tin", "Bone", "Ash", "Glass"],
        "name": ["Dusthollow", "Ironside", "Ashfall", "Drywell",
                 "Rustburg", "Saltmere", "Scorchfield", "Breakwater",
                 "Graystone", "Burnside", "Deadoak", "Tintown",
                 "Rattlespring", "Bonemarch", "Capstone", "Lastwell"],
    },

    "npc_count": {"min": 5, "max": 10},
    "npc_archetypes": [
        {
            "role": "warlord",
            "voice": "tyrant",
            "weight": 1,
            "location_type": "raider_camp",
            "names": ["Slag", "The General", "Iron Meg", "Ashmouth",
                      "Warlord Krest", "Queen Diesel", "The Colonel"],
            "personalities": [
                "Brutal, strategic, charismatic in the way of people who give certainty in uncertain times.",
                "Quiet, terrifying, rational. Violence is a tool, not a hobby. The most dangerous kind.",
                "Loud, theatrical, genuinely believes might makes right. Has built a kingdom from nothing and rules it with a fist.",
            ],
            "knowledge_topics": ["territory", "rivals", "pre-war tech locations", "who has what"],
            "secret_types": ["came from a bunker", "losing control", "has a code they won't admit to", "dying of radiation"],
            "default_disposition": "hostile",
        },
        {
            "role": "scavenger",
            "voice": "survivor",
            "weight": 2,
            "location_type": "ruins",
            "names": ["Picks", "Finder", "Junker", "Loot", "Salvage Sam",
                      "The Drifter", "Rust", "Magpie", "Wire", "Kit"],
            "personalities": [
                "Cautious, knowledgeable, trades in things and information. Knows the ruins better than anyone alive.",
                "Twitchy, fast, friendly once you earn it. Talks to themselves — the wasteland does that to people.",
                "Methodical, quiet, practical. Every piece of salvage is catalogued. Every route is mapped.",
            ],
            "knowledge_topics": ["ruins locations", "salvage values", "hidden caches", "what's dangerous where"],
            "secret_types": ["found something big", "knows a bunker location", "running from raiders", "sitting on a cache"],
            "default_disposition": "cautious",
        },
        {
            "role": "doctor",
            "voice": "healer",
            "weight": 1,
            "location_type": "settlement",
            "names": ["Doc", "Dr. Mercer", "The Surgeon", "Needle",
                      "Old Bones", "Medic Roan", "The Pharmacist"],
            "personalities": [
                "Exhausted, capable, running on fumes and obligation. Can't save everyone. Tries anyway.",
                "Gruff, efficient, doesn't waste words or supplies. Both are too scarce.",
                "Gentle, patient, haunted by the ones lost. Trades medical care for whatever people can spare.",
            ],
            "knowledge_topics": ["radiation sickness", "injuries", "pre-war medicine", "water quality"],
            "secret_types": ["limited supplies", "experimental treatment", "mercy killing", "addiction"],
            "default_disposition": "compassionate",
        },
        {
            "role": "mechanic",
            "voice": "craftsman",
            "weight": 1,
            "location_type": "scrapyard",
            "names": ["Wrench", "Gears", "Spark", "Crank", "Rivet",
                      "Old Chrome", "Axle", "Piston"],
            "personalities": [
                "Obsessive, brilliant, talks to machines. Genuinely happier with an engine than a person.",
                "Practical, fair, protective of their yard. Trades in repairs and respect.",
                "Grumpy, skilled, secretly generous. Will fix your water filter and complain about it the whole time.",
            ],
            "knowledge_topics": ["pre-war tech", "vehicle repair", "power generation", "water purification"],
            "secret_types": ["building something big", "found working tech", "hoarding fuel", "can't fix everything"],
            "default_disposition": "gruff",
        },
        {
            "role": "trader",
            "voice": "merchant",
            "weight": 2,
            "location_type": "trading_post",
            "names": ["Barter Bob", "Silk", "Fair Deal", "Profit",
                      "Mama Cap", "The Caravan Boss", "Nickel", "Trade"],
            "personalities": [
                "Shrewd, fair-ish, knows the value of everything including your desperation.",
                "Cheerful, connected, surprisingly well-informed. The trade routes are information highways.",
                "Cautious, armed, professional. Survived by being useful to everyone and threatening to none.",
            ],
            "knowledge_topics": ["prices", "supply routes", "settlement news", "what's scarce"],
            "secret_types": ["hoarding", "trading with raiders", "knows about a supply cache", "running from debts"],
            "default_disposition": "friendly",
        },
        {
            "role": "cult_leader",
            "voice": "prophet",
            "weight": 1,
            "location_type": "radiation_zone",
            "names": ["The Radiant", "Mother Glow", "Prophet Ash",
                      "The Illuminated", "Father Fusion", "The Seer"],
            "personalities": [
                "Serene, mad, magnetic. Sees the radiation as divine. The followers believe, and belief is power.",
                "Intellectual, twisted, charismatic. Built a theology from atomic physics and desperation. Makes sense if you don't think too hard.",
                "Gentle, delusional, genuinely caring. Leads the flock into the glow because they truly believe it saves.",
            ],
            "knowledge_topics": ["radiation zones", "pre-war history", "the glow", "the faithful"],
            "secret_types": ["isn't affected by radiation", "knows it's killing them", "protects followers in secret", "the visions are real"],
            "default_disposition": "welcoming",
        },
    ],

    "quest_patterns": [
        {
            "type": "salvage_run",
            "name_templates": ["The {adj} Run", "{name}'s Cache", "Into the {noun}"],
            "stages": 3,
            "stage_templates": [
                {"objective": "Get the salvage location from {npc}.", "location_type": "trading_post"},
                {"objective": "Navigate to {location} and recover the salvage.", "location_type": "ruins"},
                {"objective": "Return the salvage to {npc}.", "location_type": "trading_post"},
            ],
        },
        {
            "type": "settlement_defense",
            "name_templates": ["Holding {name}", "The {adj} Siege", "Raiders at the Gate"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Learn about the threat from {npc}.", "location_type": "settlement"},
                {"objective": "Scout the raider force at {location}.", "location_type": "wasteland"},
                {"objective": "Prepare defenses at {destination}.", "location_type": "settlement"},
                {"objective": "Survive the attack.", "location_type": "settlement"},
            ],
        },
        {
            "type": "water_quest",
            "name_templates": ["The {adj} Source", "Finding {noun}", "Water Wars"],
            "stages": 3,
            "stage_templates": [
                {"objective": "Learn about the water crisis from {npc}.", "location_type": "settlement"},
                {"objective": "Find the water source at {location}.", "location_type": "water_source"},
                {"objective": "Decide who gets the water.", "location_type": "any"},
            ],
        },
        {
            "type": "bunker_expedition",
            "name_templates": ["Vault {noun}", "The {adj} Bunker", "What's Below"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Get the bunker location from {npc}.", "location_type": "scrapyard"},
                {"objective": "Navigate the wasteland to {location}.", "location_type": "wasteland"},
                {"objective": "Enter and explore the bunker at {destination}.", "location_type": "bunker"},
                {"objective": "Return with what you found.", "location_type": "settlement"},
            ],
        },
    ],

    "item_types": [
        {"category": "weapon", "tags": ["weapon"],
         "items": [
             {"name": "a pipe rifle", "desc": "Plumbing parts and violence. Loud, inaccurate, effective at close range."},
             {"name": "a machete", "desc": "Car leaf spring, ground sharp. The handle is wrapped in electrical tape."},
             {"name": "a sawed-off shotgun", "desc": "Two barrels, both short. Stops arguments."},
             {"name": "a hunting rifle", "desc": "Pre-war, maintained with love. The scope is cracked but functional."},
         ]},
        {"category": "tool", "tags": ["tool"],
         "items": [
             {"name": "a Geiger counter", "desc": "Pre-war surplus. The needle jumps before you feel anything. Essential."},
             {"name": "a water filter", "desc": "Charcoal and ceramic. Makes puddle water into drinking water. Slowly."},
             {"name": "a multi-tool", "desc": "Pliers, screwdriver, knife, can opener. The one thing you never trade."},
             {"name": "a length of chain", "desc": "Eight feet. For locking, climbing, or reminding someone of their place."},
         ]},
        {"category": "consumable", "tags": ["consumable", "medical"],
         "items": [
             {"name": "a rad-away dose", "desc": "Pre-war pharmaceutical. Flushes radiation. Tastes like metal and regret."},
             {"name": "purified water", "desc": "One bottle. Worth more than ammo. Drink carefully."},
             {"name": "canned food", "desc": "Pre-war surplus. The label's gone. Dinner is a mystery."},
         ]},
        {"category": "clue", "tags": ["clue", "quest_item"],
         "items": [
             {"name": "a hand-drawn map", "desc": "Charcoal on hide. X marks something. The route is annotated with skull symbols."},
             {"name": "a pre-war ID badge", "desc": "Government facility. Level 5 clearance. The face is faded but the barcode might work."},
             {"name": "a distress signal recording", "desc": "Static, then a voice. Coordinates. A date. Then nothing."},
             {"name": "a mechanic's notebook", "desc": "Diagrams of something. Not a vehicle. Something bigger. Something that still works."},
         ]},
    ],

    "faction_types": [
        {
            "type": "settlement",
            "name_templates": ["The People of {name}", "{name} Settlement", "The {adj} Hold"],
            "goals": ["Survive.", "Grow.", "Protect what we've built."],
            "default_reputation": "neutral",
        },
        {
            "type": "raiders",
            "name_templates": ["The {adj} Horde", "{name}'s Gang", "The {noun} Raiders"],
            "goals": ["Take what we need.", "Expand territory.", "Rule through strength."],
            "default_reputation": "hostile",
        },
        {
            "type": "brotherhood",
            "name_templates": ["The {adj} Brotherhood", "The Order of {name}", "The Keepers"],
            "goals": ["Preserve pre-war knowledge.", "Control dangerous technology.", "Rebuild on their terms."],
            "default_reputation": "unknown",
        },
    ],

    "encounter_types": [
        {
            "type": "combat",
            "weight": 2,
            "location_tags": ["dangerous", "criminal"],
            "enemy_templates": [
                {"name": "a raider patrol", "desc": "Three, armed with junk weapons and bad intentions. Desperate enough to be dangerous.",
                 "stats": {"health": 5, "damage": 3, "speed": "fast"},
                 "behavior": "Rush tactics. Intimidation first. Violence second."},
                {"name": "a mutant creature", "desc": "Something that used to be recognizable. Bigger now, and hungry.",
                 "stats": {"health": 10, "damage": 4, "speed": "medium"},
                 "behavior": "Territorial. Charges if you're in its space. Doesn't chase far."},
                {"name": "a scavenger robot", "desc": "Pre-war maintenance model, malfunctioning. Identifies everything as 'debris to be processed.'",
                 "stats": {"health": 8, "damage": 3, "speed": "slow"},
                 "behavior": "Methodical. Approaches, scans, processes. No negotiation."},
            ],
            "tone_templates": [
                "Scrappy, desperate, real. Nobody has enough ammo for a proper firefight. Make every shot count.",
                "Survival combat. Running is a valid tactic. Winning means walking away.",
            ],
        },
        {
            "type": "discovery",
            "weight": 3,
            "location_tags": ["mystery", "underground"],
            "tone_templates": [
                "A piece of the old world, preserved. Technology, information, or a grave. Sometimes all three.",
                "The wasteland hides things. Some are worth finding. Some explain why the world ended.",
            ],
        },
        {
            "type": "dialogue",
            "weight": 2,
            "location_tags": ["social", "commerce"],
            "tone_templates": [
                "Trade, negotiation, alliance-building. Every conversation is a resource exchange.",
                "Trust is the rarest commodity. Proving yourself takes time the wasteland might not give you.",
            ],
        },
    ],

    "world_rules_template": {
        "setting": "Post-nuclear wasteland. The bombs fell generations ago. What's left is dust, radiation, and people who refuse to quit.",
        "tone": "Grim but not hopeless. Fallout's dark humor, Road's bleak beauty. Every small kindness matters more because everything else is hard.",
        "era": "Post-collapse. Technology is scavenged, repurposed, worshipped. Pre-war artifacts are treasure. Clean water is gold.",
        "magic_system": "None. Radiation does strange things to biology — mutations, adaptations, things that shouldn't be alive. It's not magic. It's worse — it's random.",
        "combat_rules": {
            "style": "Scrappy, resource-limited. Every bullet counts. Every wound matters.",
            "lethality": "very high — no hospitals, limited medicine, infections kill",
            "healing": "slow without medicine, dangerous with radiation exposure",
            "note": "Violence costs resources — ammo, health, reputation. Choose when to fight.",
        },
        "exploration_rules": {
            "style": "Scavenging and survival. Every ruin is a loot box and a death trap.",
            "discovery": "Pre-war technology, hidden bunkers, clean water, functioning machines.",
            "danger": "Radiation, raiders, mutant fauna, structural collapse, dehydration.",
        },
        "dialogue_rules": {
            "style": "Direct, practical, trust-based. People say what they mean because life's too short for subtext.",
            "trust": "Earned through reliability. Show up, deliver, don't steal. That's enough.",
            "information": "Worth trading for. News travels with caravans. Silence is suspicious.",
        },
    },

    "player_defaults": {
        "name": "the wanderer",
        "stats": {"health": 10, "radiation": 0, "survival": 6, "barter": 4},
        "starting_items": [
            {"id": "pipe_pistol", "name": "a pipe pistol",
             "description": "Plumbing pipe, spring, nail. Six shots if it doesn't jam."},
            {"id": "canteen", "name": "a dented canteen",
             "description": "Half full. The water's been purified. Probably."},
            {"id": "geiger", "name": "a pocket Geiger counter",
             "description": "Pre-war surplus. Battery at forty percent. The click is your best friend."},
            {"id": "caps", "name": "a pouch of bottle caps",
             "description": "Forty-three caps. The universal currency. Enough to not starve."},
        ],
    },
}
