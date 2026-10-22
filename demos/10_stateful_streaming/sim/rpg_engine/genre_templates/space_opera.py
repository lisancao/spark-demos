"""
Space Opera — Mass Effect style.

Military sci-fi, alien politics, space stations, and choices
that echo across star systems. The galaxy is bigger than you.
"""

TEMPLATE = {
    "genre": "space-opera",
    "display_name": "Space Opera",
    "description": "Military sci-fi. Space stations, alien diplomacy, and the weight of choices that shape the galaxy.",
    "register_preset": "space-opera",
    "default_name": "The Last Relay",
    "topology": "star_cluster",

    "location_count": {"min": 8, "max": 14},
    "location_types": [
        {
            "type": "space_station",
            "weight": 2,
            "tags": ["social", "commerce", "safe"],
            "is_start": True,
            "name_patterns": ["{name} Station", "The {adj} Hub", "Nexus {noun}"],
            "sensory": {
                "sight": [
                    "Curved corridors, viewport strips showing stars. Species you've never seen, moving with purpose.",
                    "Holographic signage in six languages. The atrium opens to all five levels. A ship docking through the viewport.",
                    "Clean lines, brushed metal, ambient lighting that shifts with the station's cycle. A galaxy in miniature.",
                ],
                "sound": [
                    "The hum of environmental systems. Announcements in Galactic Common. Footsteps on composite decking.",
                    "Distant engine tests. A cargo loader beeping. Conversations in languages that bypass your translator.",
                    "The station's heartbeat — HVAC, power conduits, the subtle vibration of a thing alive in vacuum.",
                ],
                "smell": [
                    "Recycled air with a metallic undertone. Coffee from the human district. Something floral from the asari wing.",
                    "Ozone near the power junctions. Cooking from the markets — familiar and alien, layered.",
                    "Clean. Almost too clean. The air scrubbers work hard. Underneath, the sweat of ten thousand beings.",
                ],
                "touch": [
                    "Smooth composite walls. The deck plates vibrate faintly — you feel the station breathing.",
                    "The railing is cool alloy. The gravity is point-nine standard — you feel lighter, slightly wrong.",
                    "Climate-controlled perfection. Twenty-one degrees, forty percent humidity, everywhere, always.",
                ],
            },
            "atmosphere": [
                "The crossroads of civilization. Every species, every agenda, one fragile peace.",
                "A city in space. All the complexity of ground-side life, compressed into a tin can.",
                "Neutral ground, in theory. In practice, a chessboard with a hundred players.",
            ],
        },
        {
            "type": "bridge",
            "weight": 1,
            "tags": ["authority", "safe"],
            "name_patterns": ["The {adj} Bridge", "{name} CIC", "Command Deck"],
            "sensory": {
                "sight": [
                    "Holographic displays, star charts, the blue glow of tactical readouts. The captain's chair, facing the viewport.",
                    "Crew at stations. Fingers on haptic interfaces. The galaxy map spinning slowly in the war room.",
                    "Screens showing hull integrity, engine status, comms traffic. Information, everywhere, demanding attention.",
                ],
                "sound": [
                    "Keyboard inputs. Status reports. The quiet confidence of a crew that knows their stations.",
                    "The FTL drive humming below decks. Comms chatter — filtered, prioritized, constant.",
                    "An alarm, quickly silenced. A course correction. The helm officer confirming, calm and precise.",
                ],
                "smell": [
                    "Electronics, coffee, the particular staleness of air that's been through the scrubbers too many times.",
                    "Metal, ozone from the displays, and whatever the XO had for lunch.",
                    "Nothing. Regulation clean. The bridge smells like discipline.",
                ],
                "touch": [
                    "The haptic interface responds before you finish the gesture. The chair fits you. The deck is steady.",
                    "Vibration through the deck — the engines, the mass effect core, the ship alive around you.",
                    "The armrest controls are worn smooth. Someone's been in this chair a long time.",
                ],
            },
            "atmosphere": [
                "The nerve center. Every decision made here ripples outward.",
                "Control. Or the illusion of it. The galaxy doesn't care about your chain of command.",
                "Where the weight lands. The captain's chair is the loneliest seat on the ship.",
            ],
        },
        {
            "type": "cargo_bay",
            "weight": 1,
            "tags": ["transitional", "commerce"],
            "name_patterns": ["Cargo Bay {noun}", "The {adj} Hold", "Loading Dock {noun}"],
            "sensory": {
                "sight": [
                    "Crates stamped with corporate logos. A forklift mech parked against the wall. The bay door to vacuum.",
                    "Cargo netting, mag-locked containers, a maintenance drone running diagnostics.",
                    "Sparse. Functional. The lighting is industrial — everything visible, nothing comfortable.",
                ],
                "sound": [
                    "The hiss of pressure seals. Mag-locks engaging. A crate settling with a metallic thunk.",
                    "The bay depressurizing for loading. Your suit comms crackling. The thrum of the ship.",
                    "Echoes. The bay is big enough to carry them. A wrench dropped sounds like a gunshot.",
                ],
                "smell": [
                    "Lubricant, packing material, the sharp clean of decontamination spray.",
                    "Metal and something organic — whatever's in the sealed containers.",
                    "Cold. Space is right outside that door, and you can almost smell it.",
                ],
                "touch": [
                    "The deck grating under your boots. Mag-locks on the soles. Everything vibrates.",
                    "Cold metal surfaces. The containers are sealed and humming with climate control.",
                    "The temperature drops near the bay door. Your breath almost fogs.",
                ],
            },
            "atmosphere": [
                "Where things arrive and disappear. Cargo, contraband, stowaways.",
                "The working guts of the ship. No glamour here. Just logistics.",
                "What's in the crates matters more than the crates. Always.",
            ],
        },
        {
            "type": "alien_district",
            "weight": 2,
            "tags": ["social", "commerce", "mystery"],
            "name_patterns": ["The {adj} Quarter", "{name} District", "The Alien Ward"],
            "sensory": {
                "sight": [
                    "Architecture that doesn't follow human logic. Curved walls, bioluminescent panels, gravity at odd angles.",
                    "Species you've seen in briefings but never in person. Markets selling things you can't identify.",
                    "Colors outside the human-comfortable spectrum. Your eyes adjust. Slowly.",
                ],
                "sound": [
                    "Languages your translator renders as music, static, or poetry. Footsteps on surfaces that aren't metal.",
                    "Clicking, humming, subsonic vibration. Communication on frequencies you can't hear fully.",
                    "Your translator working overtime. A delay before meaning arrives. Context lost in conversion.",
                ],
                "smell": [
                    "Unfamiliar atmospheres. Something like cinnamon, something like ozone, something with no human word.",
                    "The particular scent of a biosphere you weren't evolved for. Not unpleasant — just alien.",
                    "Spices from gardens on worlds you'll never visit. The air is richer here.",
                ],
                "touch": [
                    "The surfaces are warm and slightly textured. Organic architecture. The walls might be alive.",
                    "Different gravity in some sections. Your inner ear protests. You adapt, or you leave.",
                    "Humidity shifts between zones. Some species breathe wet. Your skin notices.",
                ],
            },
            "atmosphere": [
                "The reminder that the galaxy wasn't built for you. Humbling and thrilling.",
                "Diplomacy at street level. Every interaction is first contact in miniature.",
                "Beautiful, disorienting, and the best food on the station, if you can figure out what's food.",
            ],
        },
        {
            "type": "cantina",
            "weight": 2,
            "tags": ["social", "rest", "criminal"],
            "name_patterns": ["The {adj} Cantina", "{name}'s Bar", "Afterburner"],
            "sensory": {
                "sight": [
                    "Low light, multispecies clientele, a bartender with four arms mixing six drinks simultaneously.",
                    "Holographic entertainment in one corner. A card game in another. Species mingling in the universal language of alcohol.",
                    "Neon accents, scratched tables, a viewport showing the nebula. The drinks glow colors that aren't legal on some worlds.",
                ],
                "sound": [
                    "Music that blends three species' ideas of rhythm. Laughter across translator barriers.",
                    "Glass on metal. Arguments in shorthand. The clink of credits changing hands under the table.",
                    "The bass line vibrating through the floor. Someone telling a war story. The bartender, unimpressed.",
                ],
                "smell": [
                    "Dextro and levo alcohol, both. Something smoky. Something sweet. Something you shouldn't be inhaling.",
                    "Sweat, perfume, engine grease. Every species brings their own atmosphere. Literally.",
                    "The universal smell of a bar — old drinks, new lies, and the hope of a good night.",
                ],
                "touch": [
                    "The bar top is dented alloy. Your drink is cold, the glass unfamiliar in your hand.",
                    "The booth padding is worn but still comfortable. Someone's carved something in the table.",
                    "Warm. Too many bodies, not enough ventilation. The station's climate control gives up in bars.",
                ],
            },
            "atmosphere": [
                "Where information flows as freely as the drinks. The galaxy's neutral ground.",
                "Everyone here has a story. Half of them are true. All of them are interesting.",
                "The last stop before a bad decision. Or the first stop after one.",
            ],
        },
        {
            "type": "docking_bay",
            "weight": 1,
            "tags": ["transitional", "commerce", "dangerous"],
            "name_patterns": ["Docking Bay {noun}", "The {adj} Port", "{name} Hangar"],
            "sensory": {
                "sight": [
                    "Ships in various states of repair. A freighter venting coolant. Your ship, right where you left it.",
                    "Maintenance crews working under hull panels. Fuel lines snaking across the deck. Warning lights, amber.",
                    "The force field separating you from vacuum. Stars beyond it. A ship approaching on maneuvering thrusters.",
                ],
                "sound": [
                    "Engines cooling — the tick of metal contracting. Fuel pumps. A welding arc hissing.",
                    "Radio chatter from traffic control. The thrum of ships powering up. The whoosh of a shuttle launch.",
                    "Your boots on the deck. The echo of a space too big for its purpose. Announcements about departures.",
                ],
                "smell": [
                    "Drive plasma exhaust. Coolant. The sharp chemical of hull sealant curing.",
                    "Fuel — element zero processing has a smell like static electricity and burnt sugar.",
                    "Grease, metal filings, and the cold that seeps in from the void.",
                ],
                "touch": [
                    "The deck vibrates with launches and landings. Fuel puddles are slick underfoot.",
                    "Cold near the force field. Warm near the engines. The temperature map of a working port.",
                    "Your ship's hull, cool under your palm. Familiar. Reliable. Home, in a way.",
                ],
            },
            "atmosphere": [
                "Arrivals and departures. Every ship has a destination and a reason.",
                "The edge of the station. Beyond that force field is everything and nothing.",
                "Where journeys begin. And sometimes end, quietly, in bay seven.",
            ],
        },
        {
            "type": "medbay",
            "weight": 1,
            "tags": ["safe", "rest"],
            "name_patterns": ["The {adj} Medbay", "{name} Medical", "Clinic {noun}"],
            "sensory": {
                "sight": [
                    "White walls, blue holographic readouts, a medi-gel dispenser on every counter.",
                    "Beds with biometric overlays. A surgical drone in standby mode. The doctor, not looking up.",
                    "Clean. Aggressively clean. The kind of clean that makes you aware of your own dirt.",
                ],
                "sound": [
                    "Heart monitors. The hiss of a hypo. Someone breathing, measured and assisted.",
                    "The doctor's voice, calm and factual. The hum of diagnostic equipment.",
                    "Quiet. The medical bay enforces it. Even the machines whisper.",
                ],
                "smell": [
                    "Antiseptic, medi-gel, and the particular nothing-smell of filtered air.",
                    "Sterile. The absence of biology, enforced by chemistry.",
                    "Medi-gel has a smell — clean, chemical, vaguely minty. You learn to associate it with surviving.",
                ],
                "touch": [
                    "The bed is firm, climate-controlled. The sheets are regulation. Comfort is incidental.",
                    "The scanner passes over you — warm, tingling. The hypo is cold, then warm, then better.",
                    "Everything is smooth, rounded, designed to be cleaned. No edges. No hiding places for germs.",
                ],
            },
            "atmosphere": [
                "Where consequences get treated. The body count of your decisions, in beds.",
                "Healing. Or the closest thing to it that technology allows.",
                "The doc has seen worse. That's not comforting. That's informative.",
            ],
        },
        {
            "type": "colony_surface",
            "weight": 1,
            "tags": ["dangerous", "wilderness"],
            "name_patterns": ["{name} Colony", "The {adj} Settlement", "Outpost {noun}"],
            "sensory": {
                "sight": [
                    "Prefab structures against an alien skyline. Two suns. Vegetation that isn't green.",
                    "A colony half-built. Construction equipment idle. The perimeter fence sparking where something tested it.",
                    "Red dust. A settlement carved from rock and will. The horizon is wrong — too close, too curved.",
                ],
                "sound": [
                    "Wind carrying sounds you can't identify. The generator humming. Livestock — or the local equivalent.",
                    "The perimeter alarm, testing. Children playing in compounds. A radio, reaching for a signal.",
                    "Alien fauna in the distance. The settlers have stopped flinching. You haven't.",
                ],
                "smell": [
                    "Alien atmosphere, filtered through your suit. Dust with a chemical tang. Terraforming chemicals.",
                    "The particular smell of a world that isn't yours. Not hostile — just indifferent to your biology.",
                    "Cooking from the mess hall. Familiar food in an unfamiliar place. The comfort of it.",
                ],
                "touch": [
                    "Gravity is off — slightly more or less than standard. Your body adjusts, complaining.",
                    "Dust gets everywhere. In your suit, in your hair, in your food. Red, fine, persistent.",
                    "The sun is warmer than it should be, or colder. The star isn't Sol. Your skin knows.",
                ],
            },
            "atmosphere": [
                "The frontier. Where civilization thins and the galaxy shows its teeth.",
                "Hope and desperation in equal measure. People building something from nothing.",
                "Vulnerable. One bad season, one raider attack, one supply ship that doesn't come.",
            ],
        },
        {
            "type": "relay_hub",
            "weight": 1,
            "tags": ["transitional", "mystery", "dangerous"],
            "name_patterns": ["Relay {noun}", "The {adj} Relay", "Jump Point {name}"],
            "sensory": {
                "sight": [
                    "The relay itself — ancient, massive, glowing with energy that predates every species using it.",
                    "Ships queuing for transit. The relay arms spinning, building charge. Blue lightning between the pylons.",
                    "A structure no one built. Or no one alive built. The engineering is beyond anything current.",
                ],
                "sound": [
                    "The relay charging — a sound below hearing, felt in the bones. Your ship shuddering in response.",
                    "Comms traffic — ships calling out destinations, confirming vectors, counting down.",
                    "The transit itself is silent. That's the worst part. Something that powerful should make noise.",
                ],
                "smell": [
                    "Ozone. Your suit filters spike. Element zero processing on a scale that defies measurement.",
                    "Nothing in vacuum. But your suit recycles the air, and you taste electricity.",
                    "The recycled air in your helmet. Your own breathing. The particular smell of adrenaline.",
                ],
                "touch": [
                    "The vibration of the relay reaching through your ship's hull. Into your teeth.",
                    "Zero-G if you're outside. The magnetic field pulling at anything ferrous.",
                    "Transit: a moment of nothing, then everything. Your body arrives before your stomach.",
                ],
            },
            "atmosphere": [
                "The highways between stars. Built by gods, used by anyone. Nobody knows the toll.",
                "Ancient technology, still working, purpose still debated. Convenience or trap.",
                "The moment before transit. You're trusting your life to something nobody understands.",
            ],
        },
        {
            "type": "black_market",
            "weight": 1,
            "tags": ["criminal", "commerce", "dangerous"],
            "name_patterns": ["The {adj} Market", "{name}'s Bazaar", "The Underbelly"],
            "sensory": {
                "sight": [
                    "A converted maintenance level. Stalls between pipes. Goods you can't buy upstairs.",
                    "Low light, deliberate. Faces half-visible. A turian selling weapons next to a salarian selling data.",
                    "No signs. You find this place by reputation. If you're here, you know why.",
                ],
                "sound": [
                    "Whispered negotiations. The clink of credits — physical, untraceable. A scanner beeping over merchandise.",
                    "Ventilation systems. The market uses the station's blind spots. The machinery covers the sound.",
                    "Your translator struggling with slang from three species. Street dialect doesn't localize well.",
                ],
                "smell": [
                    "Machine oil, exotic spices, substances that don't have legal names.",
                    "The lower levels smell different. Less filtered. More honest.",
                    "Smoke from something you can't identify. Someone's cooking. Someone else is synthesizing.",
                ],
                "touch": [
                    "Cramped. Shoulders brush in the narrow corridors. The pipes are warm overhead.",
                    "The floor grating is rough. The air is warmer down here. Closer.",
                    "A hand on your arm. Someone getting your attention. Or your wallet.",
                ],
            },
            "atmosphere": [
                "The economy that keeps the station running. Officially, it doesn't exist.",
                "Everything has a price. Some prices are credits. Some are favors. Some are silence.",
                "Where the rules bend. Not lawless — just operating under different laws.",
            ],
        },
    ],

    "name_pools": {
        "adj": ["Crimson", "Stellar", "Dark", "Iron", "Nova", "Void",
                "Binary", "Phantom", "Azure", "Omega", "Shattered", "Silent",
                "Burning", "Drift", "Terminal", "Deep"],
        "noun": ["Seven", "Prime", "Zero", "Omega", "Sigma", "Delta",
                 "Core", "Nexus", "Veil", "Pulse", "Arc", "Vertex"],
        "noun2": ["Star", "Fleet", "Horizon", "Nebula", "Cipher", "Vector",
                  "Drift", "Echo", "Threshold", "Beacon"],
        "name": ["Arcturus", "Thessia", "Palaven", "Illium", "Noveria",
                 "Omega", "Citadel", "Horizon", "Virmire", "Feros",
                 "Pragia", "Tuchanka", "Rannoch", "Dekuuna", "Kahje",
                 "Irune", "Sur'Kesh", "Bekenstein"],
    },

    "npc_count": {"min": 5, "max": 10},
    "npc_archetypes": [
        {
            "role": "admiral",
            "voice": "commander",
            "weight": 1,
            "location_type": "bridge",
            "names": ["Admiral Vasquez", "Commander Rix", "Admiral Chen",
                      "Fleet-Captain Solus", "Admiral T'Kora", "Commander Hayes"],
            "personalities": [
                "Decisive, burdened, principled. Commands fleets but answers to politicians. The weight shows.",
                "Hard, fair, haunted by losses. Counts the living, mourns the dead, makes the call anyway.",
                "Political, strategic, human. Plays the long game because the short game gets people killed.",
            ],
            "knowledge_topics": ["fleet movements", "the threat", "military intelligence", "alliances"],
            "secret_types": ["a battle that went wrong", "orders they can't follow", "intelligence they're sitting on", "personal loss"],
            "default_disposition": "formal",
        },
        {
            "role": "pilot",
            "voice": "flyboy",
            "weight": 2,
            "location_type": "docking_bay",
            "names": ["Joker", "Vex", "Kai", "Tempest", "Drift",
                      "Nova", "Zip", "Ace", "Comet", "Rally"],
            "personalities": [
                "Cocky, skilled, deflects with humor. Best pilot in the fleet and won't let you forget it.",
                "Quiet, precise, all business in the chair. The ship is an extension of their body.",
                "Reckless, brilliant, lucky. Or skilled enough that luck is redundant. Hard to tell.",
            ],
            "knowledge_topics": ["ship systems", "trade routes", "smuggling lanes", "who flies what"],
            "secret_types": ["medical condition", "a ship they lost", "flying for the wrong people once", "in love with the ship"],
            "default_disposition": "casual",
        },
        {
            "role": "engineer",
            "voice": "tech",
            "weight": 1,
            "location_type": "cargo_bay",
            "names": ["Tali", "Wrench", "Sparks", "Doc Adams",
                      "Chief Kora", "Engineer Patel", "Bolts", "Rivet"],
            "personalities": [
                "Obsessive, brilliant, socially awkward. Talks to the ship like it listens. It might.",
                "Practical, unflappable, chronically underappreciated. Keeps everything running with spit and wire.",
                "Nervous, meticulous, indispensable. Panics about problems before they happen, which is why they don't.",
            ],
            "knowledge_topics": ["ship systems", "alien technology", "what's actually broken", "workarounds"],
            "secret_types": ["built something unauthorized", "knows the ship's real condition", "salvaged forbidden tech", "talking to an AI"],
            "default_disposition": "helpful",
        },
        {
            "role": "alien_diplomat",
            "voice": "diplomat",
            "weight": 1,
            "location_type": "alien_district",
            "names": ["Ambassador Tevos", "Envoy Rix", "Speaker Mordin",
                      "Delegate Shiala", "The Arbiter", "Voice-of-Many"],
            "personalities": [
                "Graceful, opaque, playing a game with rules you don't fully understand. Patient as geology.",
                "Blunt by alien standards, which still feels circuitous to humans. Genuinely wants peace. Defines it differently.",
                "Warm, curious, fascinated by humans. Uses charm like a scalpel — precise, purposeful.",
            ],
            "knowledge_topics": ["galactic politics", "species relations", "trade agreements", "ancient history"],
            "secret_types": ["species-first agenda", "personal disgrace", "forbidden knowledge", "empathy that looks like weakness"],
            "default_disposition": "diplomatic",
        },
        {
            "role": "smuggler",
            "voice": "rogue",
            "weight": 2,
            "location_type": "cantina",
            "names": ["Wrex", "Solo", "Kasha", "Flint", "Dodge",
                      "The Courier", "Patch", "Rogue", "Scar", "Haul"],
            "personalities": [
                "Charming, unreliable, surprisingly principled when it counts. Has a code — just not yours.",
                "Quiet, professional, expensive. Moves anything anywhere. Doesn't ask. Doesn't tell.",
                "Loud, brash, generous. Makes friends fast, enemies faster. The galaxy's worst best friend.",
            ],
            "knowledge_topics": ["black market", "smuggling routes", "who's buying", "station security gaps"],
            "secret_types": ["debt to the wrong people", "heart of gold", "witness protection", "running from something"],
            "default_disposition": "guarded",
        },
        {
            "role": "scientist",
            "voice": "academic",
            "weight": 1,
            "location_type": "medbay",
            "names": ["Dr. Solus", "Professor Vale", "Dr. T'Soni",
                      "Researcher Krios", "The Specialist", "Dr. Okuda"],
            "personalities": [
                "Brilliant, fast-talking, ethically flexible. Results matter. Methods are negotiable.",
                "Methodical, patient, haunted by what the data shows. The universe doesn't care about your feelings.",
                "Passionate, idealistic, naive about politics. Believes knowledge should be free. Keeps learning why it isn't.",
            ],
            "knowledge_topics": ["xenobiology", "ancient artifacts", "the anomaly", "classified research"],
            "secret_types": ["unethical experiment", "dangerous discovery", "working for two employers", "the cure they won't share"],
            "default_disposition": "curious",
        },
    ],

    "quest_patterns": [
        {
            "type": "mission",
            "name_templates": ["Operation {adj}", "The {name} Directive", "Priority {noun}"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Get briefed by {npc}.", "location_type": "bridge"},
                {"objective": "Gather intelligence at {location}.", "location_type": "cantina"},
                {"objective": "Infiltrate {destination}.", "location_type": "black_market"},
                {"objective": "Complete the objective and extract.", "location_type": "docking_bay"},
            ],
        },
        {
            "type": "diplomacy",
            "name_templates": ["The {adj} Summit", "First Contact: {name}", "The {noun} Accord"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Understand the situation from {npc}.", "location_type": "space_station"},
                {"objective": "Meet with the alien delegation at {location}.", "location_type": "alien_district"},
                {"objective": "Navigate the negotiation at {destination}.", "location_type": "space_station"},
                {"objective": "Secure the agreement or manage the fallout.", "location_type": "bridge"},
            ],
        },
        {
            "type": "investigation",
            "name_templates": ["The {adj} Signal", "Anomaly at {name}", "What {name} Found"],
            "stages": 3,
            "stage_templates": [
                {"objective": "Investigate the anomaly report from {npc}.", "location_type": "medbay"},
                {"objective": "Follow the trail to {location}.", "location_type": "relay_hub"},
                {"objective": "Discover the truth at {destination}.", "location_type": "colony_surface"},
            ],
        },
        {
            "type": "rescue",
            "name_templates": ["Extraction: {name}", "The {adj} Rescue", "No One Left Behind"],
            "stages": 3,
            "stage_templates": [
                {"objective": "Get the distress call details from {npc}.", "location_type": "bridge"},
                {"objective": "Navigate to {location}.", "location_type": "relay_hub"},
                {"objective": "Extract the survivors at {destination}.", "location_type": "colony_surface"},
            ],
        },
    ],

    "item_types": [
        {"category": "weapon", "tags": ["weapon"],
         "items": [
             {"name": "a standard-issue sidearm", "desc": "Carnifex hand cannon. Heavy, accurate, loud."},
             {"name": "a modded assault rifle", "desc": "Lancer variant. Extended mag, thermal scope. Someone's custom work."},
             {"name": "a biotic amp", "desc": "Surgically implanted. Amplifies mass effect fields. Headache included."},
             {"name": "an omni-blade", "desc": "Holographic edge, real damage. Deploys from the omni-tool in point-three seconds."},
         ]},
        {"category": "tool", "tags": ["tool"],
         "items": [
             {"name": "an omni-tool", "desc": "Standard issue. Hacks, scans, communicates, and makes a decent flashlight."},
             {"name": "a tech drone", "desc": "Reconnaissance model. Quiet, small, expendable. Has a camera."},
             {"name": "a false ID", "desc": "Biometric spoof. Good enough for station security. Not good enough for C-Sec."},
             {"name": "a signal scrambler", "desc": "Pocket-sized. Makes your comms invisible for about ten minutes."},
         ]},
        {"category": "consumable", "tags": ["consumable", "medical"],
         "items": [
             {"name": "a medi-gel pack", "desc": "Universal wound sealant. Apply, wait, fight. In that order."},
             {"name": "a ration pack", "desc": "Nutrient paste and caffeine tabs. Fuel, not food."},
             {"name": "a stim injection", "desc": "Twelve hours of sharp. Then the crash. Use sparingly."},
         ]},
        {"category": "clue", "tags": ["clue", "quest_item"],
         "items": [
             {"name": "a corrupted data pad", "desc": "Partial files. Coordinates, names, and a file marked URGENT."},
             {"name": "an alien artifact", "desc": "Smooth, warm, humming. Your omni-tool can't identify the material."},
             {"name": "a classified comm recording", "desc": "Encrypted. Two voices. One of them is someone you know."},
             {"name": "a navigation chart", "desc": "Hand-annotated. A route to somewhere that's not on any map."},
         ]},
    ],

    "faction_types": [
        {
            "type": "military",
            "name_templates": ["The {adj} Fleet", "{name} Command", "The Alliance"],
            "goals": ["Protect the colonies.", "Maintain readiness.", "Project strength."],
            "default_reputation": "friendly",
        },
        {
            "type": "alien_council",
            "name_templates": ["The {adj} Council", "The Conclave of {name}", "The Galactic Assembly"],
            "goals": ["Maintain peace.", "Balance power.", "Preserve the status quo."],
            "default_reputation": "neutral",
        },
        {
            "type": "criminal_syndicate",
            "name_templates": ["The {adj} Network", "{name} Syndicate", "The Shadow Brokers"],
            "goals": ["Profit.", "Information control.", "Power in the margins."],
            "default_reputation": "hostile",
        },
    ],

    "encounter_types": [
        {
            "type": "combat",
            "weight": 2,
            "location_tags": ["dangerous", "criminal"],
            "enemy_templates": [
                {"name": "mercenary squad", "desc": "Three, armored, organized. Professionals doing a job.",
                 "stats": {"health": 7, "damage": 4, "speed": "medium"},
                 "behavior": "Cover-based tactics. Suppressive fire. Flanking."},
                {"name": "a rogue mech", "desc": "Security model, hacked. Armor plating, mass accelerator arm.",
                 "stats": {"health": 12, "damage": 5, "speed": "slow"},
                 "behavior": "Advances. Shoots. Doesn't negotiate."},
                {"name": "hostile alien fauna", "desc": "Fast, armored, territorial. Not evil — just hungry and you're in its space.",
                 "stats": {"health": 8, "damage": 3, "speed": "fast"},
                 "behavior": "Charges. Uses terrain. Retreats if hurt badly enough."},
            ],
            "tone_templates": [
                "Cover, tactics, teamwork. Modern combat — fast, lethal, decided by positioning.",
                "Desperate survival. Outgunned, outmanned. Improvise or die.",
            ],
        },
        {
            "type": "discovery",
            "weight": 3,
            "location_tags": ["mystery", "transitional"],
            "tone_templates": [
                "The universe is bigger than you thought. Ancient technology, unexplained signals, questions without answers.",
                "A piece of the puzzle falls into place. The picture is worse than you expected.",
            ],
        },
        {
            "type": "dialogue",
            "weight": 3,
            "location_tags": ["social", "authority"],
            "tone_templates": [
                "Diplomacy as chess. Every word crosses a cultural divide. Meaning shifts with species.",
                "Command decisions. The right call for the many versus the right call for the few.",
            ],
        },
    ],

    "world_rules_template": {
        "setting": "Military sci-fi. A galaxy of diverse species, ancient technology, and conflicts that span star systems.",
        "tone": "Weighty, character-driven, morally complex. Mass Effect's blend of wonder and consequence. Every choice echoes.",
        "era": "Far future. FTL travel, artificial gravity, holographic interfaces. Technology enables but doesn't solve the fundamental problems of being alive.",
        "magic_system": "Biotics — mass effect field manipulation by organic beings. Rare, powerful, physically taxing. Technology fills the gaps. Ancient tech is indistinguishable from magic.",
        "combat_rules": {
            "style": "Modern military. Cover, shields, tech, biotics. Weapons are lethal. Armor buys seconds.",
            "lethality": "high — kinetic barriers help, but concentrated fire kills",
            "healing": "medi-gel for field treatment, proper medical facilities for real recovery",
            "note": "Combat has rules of engagement. Collateral damage matters. Witnesses exist.",
        },
        "exploration_rules": {
            "style": "Planet surveys, station investigation, archaeological discovery. The galaxy rewards curiosity.",
            "discovery": "Ancient technology, new species, classified data. Knowledge is power and danger.",
            "danger": "Vacuum is one hull breach away. Hostile worlds, hostile fauna, hostile people.",
        },
        "dialogue_rules": {
            "style": "Cross-species diplomacy. Cultural context matters. Your translator handles words, not meaning.",
            "trust": "Built through shared danger. Aliens judge you by different standards. Learn them.",
            "information": "Classified, compartmentalized, political. The truth is usually someone's liability.",
        },
    },

    "player_defaults": {
        "name": "the commander",
        "stats": {"health": 12, "shields": 8, "tech_skill": 5, "diplomacy": 5},
        "starting_items": [
            {"id": "sidearm", "name": "a standard sidearm",
             "description": "Carnifex hand cannon. Alliance issue. Five thermal clips."},
            {"id": "omni_tool", "name": "an omni-tool",
             "description": "Haptic interface, scanner suite, comms. Your right arm, digitally."},
            {"id": "dog_tags", "name": "dog tags",
             "description": "Name, rank, service number, blood type. Everything they need to identify you."},
            {"id": "medi_gel", "name": "two medi-gel packs",
             "description": "Standard field medical. Apply to wound. Hope for the best."},
        ],
    },
}
