"""
Modern Crime — GTA V style.

Urban crime, gangs, corrupt cops, drug trade. Neon-lit streets,
back-alley deals, and loyalty that lasts until the money runs out.
"""

TEMPLATE = {
    "genre": "modern-crime",
    "display_name": "Modern Crime",
    "description": "Urban crime drama. Gangs, corrupt cops, drug money, and the kind of loyalty that gets people killed.",
    "register_preset": "modern-crime",
    "default_name": "Concrete and Blood",
    "topology": "urban_grid",

    "location_count": {"min": 8, "max": 14},
    "location_types": [
        {
            "type": "nightclub",
            "weight": 2,
            "tags": ["social", "commerce", "criminal"],
            "is_start": True,
            "name_patterns": ["{name}", "Club {noun}", "The {adj} Lounge"],
            "sensory": {
                "sight": [
                    "Strobes cutting through smoke. Bodies moving on the floor. VIP rope glowing purple.",
                    "LED strips along the bar, shifting blue to pink. Bottles backlit like a skyline.",
                    "Dark booths in the back. Somebody's bodyguard standing by the bathroom door.",
                ],
                "sound": [
                    "Bass so deep you feel it in your teeth. Laughter breaking through the beat.",
                    "Ice in glasses. A woman shouting an order. The DJ transitioning, badly.",
                    "Muffled conversation from the VIP section. Someone's phone buzzing on the bar.",
                ],
                "smell": [
                    "Cologne, sweat, spilled vodka, and the chemical sweetness of fog machine fluid.",
                    "Perfume layered over cigarette smoke that shouldn't be here. Lime wedges.",
                    "Hair product, tequila, and the sharp undercut of bleach from the bathrooms.",
                ],
                "touch": [
                    "Sticky floor. The bass vibrating through the soles of your shoes.",
                    "Cold glass in your hand. Someone bumps your shoulder, doesn't apologize.",
                    "The leather booth sticks to your arms. The air is body-warm.",
                ],
            },
            "atmosphere": [
                "Money moving in the dark. Half the people here are working. The other half don't know it.",
                "Loud enough that nobody can hear you. That's the point.",
                "Glamour over grime. The lights hide the stains.",
            ],
        },
        {
            "type": "warehouse",
            "weight": 2,
            "tags": ["dangerous", "criminal", "isolated"],
            "name_patterns": ["{name} Storage", "Unit {noun}", "The {adj} Warehouse"],
            "sensory": {
                "sight": [
                    "Concrete floor, steel shelving, a single work light casting hard shadows.",
                    "Plastic-wrapped pallets. A folding table with a scale on it. Two chairs.",
                    "Loading dock half-open. Puddle of rainwater reflecting a security light.",
                ],
                "sound": [
                    "Pigeons in the rafters. A drip from a pipe. Distant highway traffic.",
                    "Footsteps echoing on concrete. A phone vibrating on metal.",
                    "The loading door rattling in the wind. A car idling outside.",
                ],
                "smell": [
                    "Diesel, damp concrete, cardboard. Something chemical underneath.",
                    "Motor oil and dust. Cold air through the gap in the loading door.",
                    "Rust, stale water, and the faint sweetness of whatever's in those crates.",
                ],
                "touch": [
                    "Cold concrete through your shoes. The air is ten degrees colder in here.",
                    "Grit on every surface. The folding chair wobbles when you sit.",
                    "Metal shelving, ice-cold to the touch. Dust on your fingertips.",
                ],
            },
            "atmosphere": [
                "The kind of place things happen that don't get reported.",
                "Functional. Ugly. Nobody comes here for the ambiance.",
                "Every sound carries. Every entrance is also an exit. You count them.",
            ],
        },
        {
            "type": "apartment_block",
            "weight": 2,
            "tags": ["social", "residential"],
            "name_patterns": ["{name} Towers", "The {adj} Arms", "{noun} Heights"],
            "sensory": {
                "sight": [
                    "Flickering hallway lights. Peeling paint. Apartment numbers in mismatched fonts.",
                    "Stairwell graffiti. A bicycle chained to the railing. Somebody's mail piling up.",
                    "Balconies cluttered with laundry and dead plants. Satellite dishes like barnacles.",
                ],
                "sound": [
                    "TV through thin walls. A baby crying two floors up. The elevator grinding.",
                    "Somebody's music. Footsteps above. A dog barking, then stopping abruptly.",
                    "The hum of fluorescent lights. A door slamming. Muffled argument.",
                ],
                "smell": [
                    "Cooking — cumin, garlic, frying oil — from three different apartments.",
                    "Bleach in the stairwell, weed in the hallway, mothballs near 4C.",
                    "Damp carpet, Febreze, and something burnt from the microwave.",
                ],
                "touch": [
                    "The handrail is sticky. The elevator button doesn't light up.",
                    "Thin walls. You can feel the bass from next door in the drywall.",
                    "Carpet worn to thread. The door lock needs three tries.",
                ],
            },
            "atmosphere": [
                "People living on top of each other, pretending the walls are thicker than they are.",
                "Everybody knows everybody's business. Nobody says anything about it.",
                "Home, if you squint. Better than the street.",
            ],
        },
        {
            "type": "docks",
            "weight": 1,
            "tags": ["dangerous", "commerce", "isolated"],
            "name_patterns": ["Pier {noun}", "{name} Docks", "The {adj} Wharf"],
            "sensory": {
                "sight": [
                    "Container stacks like metal canyons. Cranes silhouetted against orange sky.",
                    "Oily water between the pilings. A cargo ship rusting at berth.",
                    "Floodlights on the loading zone. Shadows everywhere else.",
                ],
                "sound": [
                    "Water slapping against hulls. The groan of mooring lines. Distant foghorn.",
                    "Forklifts beeping. Metal on metal. Gulls screaming at nothing.",
                    "Chains rattling. The low rumble of an idling truck. Radio chatter.",
                ],
                "smell": [
                    "Salt, diesel, fish guts, and the metallic tang of shipping containers.",
                    "Creosote pilings, brackish water, exhaust fumes.",
                    "Tar, brine, and motor oil. The ocean, industrialized.",
                ],
                "touch": [
                    "Salt spray on your face. The dock planks flex under your weight.",
                    "Wind off the water, cutting through your jacket. Everything is damp.",
                    "Rope rough against your palms. The railing is crusted with salt.",
                ],
            },
            "atmosphere": [
                "Things arrive here and disappear. Cargo, people, evidence.",
                "After hours, this place belongs to whoever's brave or stupid enough to use it.",
                "The water doesn't judge. It just takes what falls in.",
            ],
        },
        {
            "type": "strip_mall",
            "weight": 2,
            "tags": ["social", "commerce"],
            "name_patterns": ["{name} Plaza", "The {adj} Strip", "{noun} Square"],
            "sensory": {
                "sight": [
                    "A nail salon, a check-cashing place, a laundromat with one working dryer.",
                    "Parking lot cracked and weedy. A liquor store sign buzzing half-lit.",
                    "Faded awnings. A barber pole turning. Someone asleep in a parked car.",
                ],
                "sound": [
                    "Traffic. A bell over a door. Spanish radio from the taco shop.",
                    "Shopping carts rattling. Kids on bikes. Somebody honking.",
                    "The hum of neon. A lottery scratcher being scratched at the counter.",
                ],
                "smell": [
                    "Grease from the taco stand. Nail salon acetone. Exhaust.",
                    "Fresh laundry and stale cigarettes. Hot asphalt.",
                    "Coffee, fried chicken, and car exhaust. America in three scents.",
                ],
                "touch": [
                    "Sun-hot pavement. The door handle is warm metal.",
                    "Plastic chairs outside the laundromat, warped by the sun.",
                    "Cracked concrete underfoot. The AC hits you like a wall when you step inside.",
                ],
            },
            "atmosphere": [
                "Everyday life. The kind of place crime moves through without stopping.",
                "Nobody looks twice. That's what makes it useful.",
                "Ordinary people doing ordinary things. The perfect cover.",
            ],
        },
        {
            "type": "police_station",
            "weight": 1,
            "tags": ["social", "authority", "danger"],
            "name_patterns": ["{name} Precinct", "The {adj} Station", "Precinct {noun}"],
            "sensory": {
                "sight": [
                    "Fluorescent hell. Desks piled with paperwork. A coffee ring on every surface.",
                    "Mugshot wall. A whiteboard with case notes in three colors of marker.",
                    "Holding cells in the back. Badge photos on the wall, some with black bands.",
                ],
                "sound": [
                    "Phones ringing. Keyboard clatter. Someone in the holding cell kicking the bench.",
                    "A detective swearing at a printer. Radio dispatch, tinny and constant.",
                    "The buzz of the door lock. Footsteps on linoleum. Coffee maker gurgling.",
                ],
                "smell": [
                    "Bad coffee, old carpet, body odor, and the chemical tang of hand sanitizer.",
                    "Burnt coffee, toner, and the ghost of a thousand microwaved lunches.",
                    "Leather holsters, floor wax, anxiety sweat.",
                ],
                "touch": [
                    "Plastic chairs designed to be uncomfortable. The counter is chest-height.",
                    "Metal detector wand. Cold cuffs if you're unlucky.",
                    "The bench is bolted down. Everything here is bolted down.",
                ],
            },
            "atmosphere": [
                "The thin blue line between order and chaos, staffed by people barely holding it together.",
                "Half the cops here are honest. Good luck figuring out which half.",
                "Justice, allegedly. The fluorescent lights make everyone look guilty.",
            ],
        },
        {
            "type": "back_alley",
            "weight": 2,
            "tags": ["dangerous", "criminal", "transitional"],
            "name_patterns": ["The {adj} Alley", "Behind {name}", "{name} Cut"],
            "sensory": {
                "sight": [
                    "Dumpsters, fire escapes, a single light above a service door.",
                    "Graffiti layered on graffiti. A cat watching from a window ledge.",
                    "Chain-link fence at the far end. Broken glass glittering on asphalt.",
                ],
                "sound": [
                    "Dripping from an AC unit. Rats in the dumpster. Your own footsteps.",
                    "Muffled bass from a club wall. A bottle rolling in the wind.",
                    "Distant sirens. A door opening somewhere above. Silence.",
                ],
                "smell": [
                    "Garbage, urine, wet concrete, and the ghost of last night's rain.",
                    "Dumpster juice and cigarette butts. Something sweet and rotting.",
                    "Grease trap exhaust from the restaurant. Wet cardboard.",
                ],
                "touch": [
                    "Puddles you can't see the bottom of. The wall is damp brick.",
                    "Cold air funneling between buildings. Grit underfoot.",
                    "The fire escape ladder is rusted but holds. Barely.",
                ],
            },
            "atmosphere": [
                "Deals, drops, and the occasional body. The city's backstage.",
                "The cameras don't reach here. That's why you're here.",
                "Nobody walks through an alley. You go in for a reason.",
            ],
        },
        {
            "type": "safehouse",
            "weight": 1,
            "tags": ["safe", "rest", "criminal"],
            "name_patterns": ["The {adj} Spot", "{name}'s Place", "The Hideout"],
            "sensory": {
                "sight": [
                    "Blinds drawn. A mattress on the floor. Burner phones on the counter.",
                    "Sparse. Clean. A duffel bag by the door that's always packed.",
                    "Takeout containers on the table. A police scanner humming. No personal items.",
                ],
                "sound": [
                    "The scanner crackling. Traffic outside. The fridge humming.",
                    "Quiet. The kind of quiet you maintain deliberately.",
                    "Your breathing. The scanner. A car alarm three blocks away.",
                ],
                "smell": [
                    "Stale air, cold Chinese food, gun oil.",
                    "Bleach. Somebody cleaned recently and thoroughly.",
                    "Cigarettes, energy drinks, and the flat smell of a place with no plants.",
                ],
                "touch": [
                    "The deadbolt has three turns. The window has a bar across it.",
                    "Cheap sheets. The couch has a spring that catches your back.",
                    "Cold tile in the kitchen. The gun under the sink is right where it should be.",
                ],
            },
            "atmosphere": [
                "Not home. A place to breathe between moves.",
                "Safe is relative. Safe enough. For now.",
                "Everything here can be abandoned in under two minutes. That's the design.",
            ],
        },
        {
            "type": "penthouse",
            "weight": 1,
            "tags": ["social", "luxury", "criminal"],
            "name_patterns": ["The {adj} Suite", "{name}'s Penthouse", "The Top Floor"],
            "sensory": {
                "sight": [
                    "Floor-to-ceiling windows. The city laid out below like a circuit board.",
                    "White furniture, abstract art, a bar with bottles that cost more than your car.",
                    "Clean lines. Nothing out of place. The kind of order that requires staff.",
                ],
                "sound": [
                    "The hush of money. HVAC so quiet you forget it's there. Ice in a glass.",
                    "Heels on marble. A phone buzzing, silenced immediately.",
                    "Ambient music — something curated, inoffensive, expensive.",
                ],
                "smell": [
                    "Leather, cedar, single malt, and the total absence of cooking.",
                    "Fresh flowers, expensive cologne, and the neutrality of filtered air.",
                    "Sandalwood candle. The kind that costs sixty dollars and burns for forty hours.",
                ],
                "touch": [
                    "Italian leather. The glass is Waterford. The carpet swallows your steps.",
                    "Marble countertops, cold and perfect. The railing is brushed steel.",
                    "The couch is the kind of soft that costs five figures. You sink.",
                ],
            },
            "atmosphere": [
                "The top of the food chain. Everything below is territory.",
                "Clean money, dirty hands. The view is the reward.",
                "Power that doesn't need to announce itself. But does anyway.",
            ],
        },
        {
            "type": "diner",
            "weight": 1,
            "tags": ["safe", "social", "rest"],
            "name_patterns": ["{name}'s", "The {adj} Diner", "{noun} Grill"],
            "sensory": {
                "sight": [
                    "Red vinyl booths, a Formica counter, coffee brewing since 5 AM.",
                    "Neon in the window. A pie case turning slowly. Menus with pictures.",
                    "A waitress with a coffee pot making rounds. Regulars at the counter.",
                ],
                "sound": [
                    "Plates clattering. The bell when the cook puts up an order. Oldies on the radio.",
                    "Coffee pouring. Forks on ceramic. Someone reading the paper out loud.",
                    "The grill sizzling. A spoon stirring sugar into coffee. The door chime.",
                ],
                "smell": [
                    "Bacon grease, burnt coffee, maple syrup, and the clean hit of bleach.",
                    "Hash browns and onions. Coffee that's been on the burner too long.",
                    "Pie crust, dish soap, and the warm fog of a working kitchen.",
                ],
                "touch": [
                    "The booth seat crackles when you slide in. The coffee mug is thick ceramic, too hot.",
                    "Sticky laminated menu. The counter is worn smooth.",
                    "The Formica tabletop is warm from the sun through the window.",
                ],
            },
            "atmosphere": [
                "Neutral ground. Even rivals sit here and eat without incident.",
                "Open 24 hours. The kind of place you end up at 3 AM with decisions to make.",
                "The food is honest. Nothing else in this city is.",
            ],
        },
    ],

    "name_pools": {
        "adj": ["Neon", "Broken", "South", "Dead", "Last", "Dirty",
                "Cold", "Red", "Black", "Crooked", "Downtown", "Midnight",
                "Rusted", "Low", "Burnt", "East"],
        "noun": ["Crown", "Line", "Corner", "Vice", "King", "Jack",
                 "Dollar", "Wire", "Edge", "Block", "Iron", "Gutter"],
        "noun2": ["Gold", "Blood", "Smoke", "Blade", "Dice", "Chrome",
                  "Glass", "Brick", "Bullet", "Cash"],
        "name": ["Kowalski", "Delgado", "Santos", "Morrison", "Tran",
                 "Vasquez", "Chen", "Abramov", "DuPont", "Reyes",
                 "Marchetti", "O'Brien", "Kim", "Jackson", "Petrov",
                 "Guerrero", "Foster", "Nakamura"],
    },

    "npc_count": {"min": 5, "max": 10},
    "npc_archetypes": [
        {
            "role": "crime_boss",
            "voice": "boss",
            "weight": 1,
            "location_type": "penthouse",
            "names": ["Victor", "Elena", "Marcus", "Rosa", "The Old Man",
                      "Mr. K", "Big Sal", "Diamond", "Anton", "Mama Reyes"],
            "personalities": [
                "Quiet, controlled, terrifying. Speaks softly because nobody dares make him repeat himself.",
                "Charismatic, generous, ruthless. Treats loyalty like a religion and betrayal like a death sentence.",
                "Cold, analytical, patient. Treats the operation like a business because it is one.",
            ],
            "knowledge_topics": ["territory", "rival operations", "police movements", "money flow"],
            "secret_types": ["paranoia", "hidden weakness", "past they buried", "federal investigation"],
            "default_disposition": "guarded",
        },
        {
            "role": "detective",
            "voice": "cop",
            "weight": 2,
            "location_type": "police_station",
            "names": ["Detective Ruiz", "Sergeant Holt", "Detective Park",
                      "Officer Chen", "Lieutenant Gray", "Detective Morrow",
                      "Sergeant Kowalski", "Detective Okafor"],
            "personalities": [
                "Burned out, sharp, bitter. Twenty years on the job. Knows the game, tired of playing.",
                "Ambitious, clean — mostly. Willing to bend rules, not break them. Hasn't decided yet.",
                "Corrupt and comfortable with it. Friendly, helpful, completely transactional.",
            ],
            "knowledge_topics": ["active cases", "gang activity", "evidence", "who's cooperating"],
            "secret_types": ["on the take", "personal vendetta", "buried evidence", "drinking problem"],
            "default_disposition": "suspicious",
        },
        {
            "role": "street_dealer",
            "voice": "street",
            "weight": 2,
            "location_type": "back_alley",
            "names": ["Slim", "DeeDee", "Ghost", "Rico", "Tweety",
                      "Skids", "Mango", "Razor", "Bliss", "Nines"],
            "personalities": [
                "Fast-talking, paranoid, surprisingly funny. Knows every shortcut in a ten-block radius.",
                "Quiet, watchful, young. Old eyes in a young face. Doesn't trust easy.",
                "Charismatic, reckless, living like there's no tomorrow because there might not be.",
            ],
            "knowledge_topics": ["supply chains", "territory lines", "who's buying", "police patterns"],
            "secret_types": ["wants out", "informant", "skimming", "protecting someone"],
            "default_disposition": "wary",
        },
        {
            "role": "bartender",
            "voice": "bartender",
            "weight": 1,
            "location_type": "nightclub",
            "names": ["Jackie", "Dex", "Marlene", "Tommy", "Yuki",
                      "Benny", "Cass", "Nico"],
            "personalities": [
                "Heard everything, says nothing. Mixes drinks and keeps secrets with equal precision.",
                "Friendly, observant, neutral. Everybody talks to the bartender. The bartender talks to nobody.",
                "Sharp-tongued, protective of their regulars, knows when to pour and when to cut off.",
            ],
            "knowledge_topics": ["who drinks here", "overheard conversations", "VIP guests", "who owes tabs"],
            "secret_types": ["witness to something", "former something-else", "running from their past"],
            "default_disposition": "neutral",
        },
        {
            "role": "fixer",
            "voice": "fixer",
            "weight": 1,
            "location_type": "diner",
            "names": ["Silk", "The Accountant", "Vera", "Mr. Glass",
                      "Bones", "The Broker", "Paloma", "Ash"],
            "personalities": [
                "Calm, precise, expensive. Solves problems for people who can pay. No moral compass, just a price list.",
                "Affable, connected, dangerous. Knows everyone. Everyone owes him something.",
                "Professional, discreet, ice-cold. Emotion is a liability. So is talking too much.",
            ],
            "knowledge_topics": ["connections", "logistics", "who needs what", "how to disappear"],
            "secret_types": ["double agent", "terminal illness", "building an exit", "playing both sides"],
            "default_disposition": "professional",
        },
        {
            "role": "informant",
            "voice": "snitch",
            "weight": 1,
            "location_type": "strip_mall",
            "names": ["Whisper", "Donnie", "Lil Tee", "Patches",
                      "Maria", "Squeak", "No-Name", "Curly"],
            "personalities": [
                "Nervous, chatty, desperate. Sells information because it's all they have.",
                "Shrewd, careful, playing every side. Survives by being useful to everyone.",
                "Twitchy, observant, scared. Knows too much and it shows in their eyes.",
            ],
            "knowledge_topics": ["who's moving what", "police raids", "gang politics", "safe routes"],
            "secret_types": ["wearing a wire", "in witness protection", "addicted", "owes money to the wrong people"],
            "default_disposition": "nervous",
        },
    ],

    "quest_patterns": [
        {
            "type": "heist",
            "name_templates": ["The {adj} Job", "The {noun} Score", "{name}'s Play"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Get the job details from {npc}.", "location_type": "diner"},
                {"objective": "Scout {location} and plan the approach.", "location_type": "warehouse"},
                {"objective": "Execute the job at {destination}.", "location_type": "docks"},
                {"objective": "Deliver the take to {npc}.", "location_type": "safehouse"},
            ],
        },
        {
            "type": "turf_war",
            "name_templates": ["The {adj} Line", "Blood on {name}", "Taking {noun}"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Learn about the territory dispute from {npc}.", "location_type": "nightclub"},
                {"objective": "Confront the rival crew at {location}.", "location_type": "back_alley"},
                {"objective": "Secure the contested {destination}.", "location_type": "strip_mall"},
                {"objective": "Report back to {npc}.", "location_type": "penthouse"},
            ],
        },
        {
            "type": "investigation",
            "name_templates": ["The {adj} Trail", "Finding {name}", "Who Killed {name}"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Talk to {npc} about what happened.", "location_type": "police_station"},
                {"objective": "Follow the lead to {location}.", "location_type": "apartment_block"},
                {"objective": "Find evidence at {destination}.", "location_type": "warehouse"},
                {"objective": "Confront {npc} with the truth.", "location_type": "diner"},
            ],
        },
        {
            "type": "betrayal",
            "name_templates": ["The {adj} Setup", "{name}'s Double", "Crossed"],
            "stages": 3,
            "stage_templates": [
                {"objective": "Something doesn't add up. Talk to {npc}.", "location_type": "safehouse"},
                {"objective": "Follow {npc} to {location}.", "location_type": "docks"},
                {"objective": "Decide what to do with what you know.", "location_type": "any"},
            ],
        },
    ],

    "item_types": [
        {"category": "weapon", "tags": ["weapon"],
         "items": [
             {"name": "a snub-nosed .38", "desc": "Cold steel, six rounds. Filed serial number."},
             {"name": "a switchblade", "desc": "Spring-loaded. Clicks open with a sound that ends conversations."},
             {"name": "a baseball bat", "desc": "Aluminum. Dented. Not from baseball."},
             {"name": "a Glock 19", "desc": "Reliable, common, untraceable. The Honda Civic of handguns."},
         ]},
        {"category": "tool", "tags": ["tool"],
         "items": [
             {"name": "a burner phone", "desc": "Prepaid. Three calls left. Then it goes in the river."},
             {"name": "a lockpick set", "desc": "Professional grade. Leather case, tension wrenches, rakes."},
             {"name": "a police scanner", "desc": "Handheld. Frequencies already programmed."},
             {"name": "a crowbar", "desc": "Two feet of hardened steel. Opens anything."},
         ]},
        {"category": "consumable", "tags": ["consumable", "medical"],
         "items": [
             {"name": "a first-aid kit", "desc": "Gauze, tape, antiseptic, painkillers. Enough for a bad night."},
             {"name": "a bottle of whiskey", "desc": "Cheap. Burns going down. That's the point."},
             {"name": "a bag of takeout", "desc": "Lukewarm lo mein. Fortune cookie you won't read."},
         ]},
        {"category": "clue", "tags": ["clue", "quest_item"],
         "items": [
             {"name": "a burner phone with one text", "desc": "Address. Time. No name. Sent three hours ago."},
             {"name": "a stained ledger page", "desc": "Numbers that don't add up. Initials instead of names."},
             {"name": "a security camera photo", "desc": "Grainy. Timestamp 2:47 AM. A face you recognize."},
             {"name": "a business card", "desc": "Plain white. A phone number. Nothing else."},
         ]},
    ],

    "faction_types": [
        {
            "type": "gang",
            "name_templates": ["The {name} Crew", "The {adj} Boys", "{name} Cartel"],
            "goals": ["Control the territory.", "Move the product.", "Eliminate competition."],
            "default_reputation": "hostile",
        },
        {
            "type": "police",
            "name_templates": ["{name} Precinct", "The Task Force", "Internal Affairs"],
            "goals": ["Build cases.", "Maintain order. Or the appearance of it.", "Protect their own."],
            "default_reputation": "neutral",
        },
        {
            "type": "syndicate",
            "name_templates": ["The {name} Family", "The {adj} Organization", "The Network"],
            "goals": ["Long-term profit.", "Political influence.", "Legitimate fronts for illegitimate money."],
            "default_reputation": "unknown",
        },
    ],

    "encounter_types": [
        {
            "type": "combat",
            "weight": 2,
            "location_tags": ["dangerous", "criminal"],
            "enemy_templates": [
                {"name": "a rival crew member", "desc": "Hoodie up, piece in hand. Young and scared and dangerous.",
                 "stats": {"health": 6, "damage": 4, "speed": "fast"},
                 "behavior": "Aggressive. Shoots first, panics second."},
                {"name": "a corrupt cop", "desc": "Badge on the belt, gun drawn. No bodycam running.",
                 "stats": {"health": 7, "damage": 3, "speed": "medium"},
                 "behavior": "Controlled. Issues commands. Escalates methodically."},
                {"name": "a hired enforcer", "desc": "Big, quiet, professional. This is just Tuesday for him.",
                 "stats": {"health": 9, "damage": 5, "speed": "slow"},
                 "behavior": "Patient. Closes distance. Doesn't stop until the job's done."},
            ],
            "tone_templates": [
                "Fast, messy, real. Guns are loud. People miss. Adrenaline makes everything stupid.",
                "Tense standoff that breaks sudden. The first move decides everything.",
            ],
        },
        {
            "type": "discovery",
            "weight": 2,
            "location_tags": ["criminal", "isolated"],
            "tone_templates": [
                "The quiet moment you find something you weren't supposed to. Now you know. Now what.",
                "Pieces clicking together. The picture gets worse as it gets clearer.",
            ],
        },
        {
            "type": "dialogue",
            "weight": 3,
            "location_tags": ["social"],
            "tone_templates": [
                "Negotiation as combat. Every word is a move. Silence is a weapon.",
                "Casual on the surface. Lethal underneath. Reading the room is survival.",
            ],
        },
    ],

    "world_rules_template": {
        "setting": "Modern-day urban sprawl. A city with money at the top, desperation at the bottom, and crime filling the gap between.",
        "tone": "Gritty, tense, darkly funny. The Wire meets GTA. No heroes — just people with different angles on the same hustle.",
        "era": "Present day. Smartphones, surveillance cameras, social media. Technology is a tool and a liability.",
        "magic_system": "None. The only power is money, guns, and information. Occasionally charisma.",
        "combat_rules": {
            "style": "Fast and consequential. Gunfights are over in seconds. Knife fights are personal.",
            "lethality": "very high — bullets don't care about your backstory",
            "healing": "hospitals ask questions, street docs don't — but they cost",
            "note": "Violence has consequences. Cops, witnesses, cameras. Clean getaways are rare.",
        },
        "exploration_rules": {
            "style": "Urban navigation. Knowing the streets is knowing the game.",
            "discovery": "Information is power. People, places, patterns.",
            "danger": "Wrong neighborhood, wrong time. Being noticed is sometimes the threat.",
        },
        "dialogue_rules": {
            "style": "Everyone is performing. The real conversation is under the words.",
            "trust": "Earned slowly, lost instantly. Loyalty is the scarcest resource.",
            "information": "Nobody talks for free. Everything costs — money, favors, leverage.",
        },
    },

    "player_defaults": {
        "name": "the new player",
        "stats": {"health": 10, "stamina": 8, "street_cred": 3, "nerve": 6},
        "starting_items": [
            {"id": "burner", "name": "a prepaid burner phone",
             "description": "Cracked screen. Three contacts. No name on the account."},
            {"id": "cash_roll", "name": "a roll of twenties",
             "description": "Eight hundred dollars. Rubber-banded. Enough to start something."},
            {"id": "pocket_knife", "name": "a folding knife",
             "description": "Three inches. Not a weapon — a tool. That's what you'd tell a cop."},
            {"id": "car_keys", "name": "keys to a beater",
             "description": "2004 Civic. Runs. Doesn't stand out. That's the point."},
        ],
    },
}
