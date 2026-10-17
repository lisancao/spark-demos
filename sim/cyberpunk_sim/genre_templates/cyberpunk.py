"""
Cyberpunk 2077 — Night City.

Corporate dystopia, chrome and flesh, neon-lit misery.
A city that eats people and calls it progress.
"""

TEMPLATE = {
    "genre": "cyberpunk",
    "display_name": "Cyberpunk 2077",
    "description": "Night City. Corpo-controlled dystopia where chrome is cheaper than healthcare and everyone's got an angle. Neon, blood, and eddies.",
    "register_preset": "cyberpunk",
    "default_name": "Chrome and Neon",
    "topology": "urban_grid",

    "location_count": {"min": 40, "max": 55},
    "location_types": [
        {
            "type": "megabuilding",
            "weight": 3,
            "tags": ["residential", "social"],
            "is_start": True,
            "name_patterns": ["{name} Tower", "Megabuilding H{noun}", "The {adj} Stack"],
            "sensory": {
                "sight": [
                    "Corridor lights flicker between yellow and dead. Apartment doors every six feet, half of them dented. Vending machines casting blue glow on concrete walls.",
                    "Elevator out of order — handwritten sign, three weeks old. Stairwell graffiti in four languages. A kid's shoe on the landing, no kid in sight.",
                    "Forty stories of stacked humanity. Laundry lines between balconies. Neon advertisements bleeding through windows that don't open.",
                ],
                "sound": [
                    "Somebody's braindance session bleeding through the wall — moaning, gunshots, moaning again. The vending machine dispensing something. A door lock cycling.",
                    "HVAC rattling like a dying animal. Footsteps above, below, beside you. A baby crying in a language you don't speak.",
                    "Elevator cables groaning. A domestic argument in 14-C, same time every night. The hum of a hundred cheap holoprojectors.",
                ],
                "smell": [
                    "Synthetic ramen steam, piss in the stairwell, ozone from a busted power junction. Somebody's cooking real meat — you can tell because it smells wrong after years of synth.",
                    "Recycled air that's been through ten thousand lungs. Disinfectant that doesn't disinfect. The chemical sweetness of a vending machine meal.",
                    "Sweat, soy sauce, burnt wiring, and the flat plastic smell of everything being made of the same polymer.",
                ],
                "touch": [
                    "The hallway wall is damp. The elevator button sticks. Your shoes leave prints on whatever's coating the floor.",
                    "Handrail greasy under your palm. The apartment door is thin enough to punch through. You don't, because the lock is the only thing between you and everything.",
                    "Concrete vibrating from the building's guts — generators, water recyclers, things that keep forty floors alive. The air is body-temperature and tastes used.",
                ],
            },
            "atmosphere": [
                "Vertical slum with a corporate logo on the lobby. Two thousand people living in a building that hates them.",
                "Home. If you can call a six-by-eight box with a fold-down bed and a shared bathroom home. Most people can. Most people have to.",
                "The kind of place where nobody asks questions because they already know the answers and the answers are all bad.",
            ],
        },
        {
            "type": "ripperdoc_clinic",
            "weight": 2,
            "tags": ["commerce", "medical"],
            "name_patterns": ["{name}'s Clinic", "The {adj} Doc", "Chrome & Bone"],
            "sensory": {
                "sight": [
                    "Surgical chair under a ring light, leather cracked and stained dark. Chrome arms hanging from ceiling mounts. A display case of eyeballs — optical implants, sorted by price.",
                    "Antiseptic tiles, half of them chipped. A fridge humming in the corner — you don't want to know what's inside. Bioscanners blinking green on a tray.",
                    "Cyber limbs mounted on the wall like trophies. A patient in the chair, jaw slack, eyes rolled back — installation in progress. The doc's hands are chrome from the elbow down.",
                ],
                "sound": [
                    "The wet click of a neural port seating. A bone saw whining through something dense. Music playing — jazz, always jazz in these places — to cover the sounds.",
                    "Bioscanners pinging. The hiss of local anesthetic spraying. Someone in the recovery cot groaning as the new chrome handshakes with their nervous system.",
                    "Latex gloves snapping on. The click-whir of a cybernetic eye calibrating. A fridge compressor kicking in, loud in the silence between procedures.",
                ],
                "smell": [
                    "Antiseptic layered over old blood that no amount of cleaning gets out. Solder flux. The ozone tang of a freshly activated implant.",
                    "Rubbing alcohol, synthetic skin adhesive, and the copper-sweet smell of someone who's been opened up. Coffee, because the doc's been at it fourteen hours.",
                    "Burned bone from the bone-welder. Coolant fluid, sharp and chemical. The flat metallic taste that gets in your mouth and stays.",
                ],
                "touch": [
                    "The chair leather is cold, then warm, then you stop feeling things because the local kicks in. The restraints are padded. That's almost kind.",
                    "Chrome sample on the counter — pick it up and it's lighter than you expected. Warm from the display. Your reflection distorted in its surface.",
                    "The doc's chrome fingers on your jaw, precise and cold. The pinch of the neural jack going in. Then nothing, then everything, then you're someone with new parts.",
                ],
            },
            "atmosphere": [
                "Somewhere between a hospital and a chop shop. The doc's good — you're here because someone vouched. The ones without vouches go to the back-alley butchers.",
                "Chrome is freedom, chrome is prison. Depends on who's paying and what they're installing. The doc doesn't judge. The doc gets paid.",
                "You walk in meat. You walk out better. Or worse. Or you don't walk out. The waiver you signed covers all three.",
            ],
        },
        {
            "type": "nightclub",
            "weight": 2,
            "tags": ["social", "commerce", "criminal"],
            "name_patterns": ["Club {noun}", "The {adj} Lounge", "{name}'s"],
            "sensory": {
                "sight": [
                    "Neon tubes in the ceiling pulsing magenta-blue-magenta. Bodies on the dance floor, chrome catching light — arms, jaws, spinal columns lit up like circuitry. Braindance booths along the back wall, curtains half-drawn.",
                    "Bar top glowing from underneath, ice-blue. Bottles of synthetic liquor backlit like a shrine. A joytoy leaning on the railing of the second floor, watching the crowd with eyes that don't blink right.",
                    "Holographic dancers flickering between the real ones. A bouncer by the VIP rope — his arms are Gorilla Arms, you can tell by the seams at the shoulders. Someone's nose is bleeding at the bar. Nobody's helping.",
                ],
                "sound": [
                    "Bass that rewires your heartbeat. Synth-wave layered over something older, harder. The crowd noise is a wall — you shout to be heard at arm's length.",
                    "Glasses clinking, braindance booths humming their electromagnetic whine. A woman laughing too loud, too long. The DJ's mixing with a neural link — no turntables, just thought.",
                    "Muffled conversation from VIP — corpo accents, clipped and precise. Someone retching in the bathroom. The airlock-hiss of a booth curtain closing.",
                ],
                "smell": [
                    "Synth-alcohol sweat, ozone from the light rigs, perfume that costs more than a month's rent in Watson. Underneath it all, the meat smell of too many bodies.",
                    "Spilled drinks — sweet, chemical, blue. Smoke from something legal adjacent. The burnt-plastic scent of a braindance headset that's been running too hot.",
                    "Cologne, coolant — someone's leaking from a bad mod — and the sharp-clean smell of the disinfectant they spray in the booths between customers.",
                ],
                "touch": [
                    "Floor vibrating through your boots. Someone's shoulder — chrome, cold, hard — knocking yours as they push past. The bar rail is sticky with something neon-colored.",
                    "The braindance headset is warm from the last user. The booth cushion is synthetic leather, body-warm. Bass rattling your sternum.",
                    "Drink cold in your hand. Condensation dripping down the glass. The air is ten degrees too hot and humid with exhalation.",
                ],
            },
            "atmosphere": [
                "Lizzie's Bar with the serial numbers filed off. Braindance in the back, deals in the VIP, and enough noise to cover all of it.",
                "Everyone's here to forget something. The music helps. The drinks help more. The braindance booths help most of all — for a price.",
                "Neon and bass and the beautiful lie that tonight doesn't have consequences. It does. It always does.",
            ],
        },
        {
            "type": "corpo_tower",
            "weight": 2,
            "tags": ["authority", "commerce", "danger"],
            "name_patterns": ["{name} Corp Tower", "{name} Industries", "The {adj} Spire"],
            "sensory": {
                "sight": [
                    "Glass and steel rising sixty floors, cutting the skyline like a blade. Lobby floor polished to a mirror — your reflection walks toward you, smaller. Reception desk staffed by someone whose smile is contractually obligated.",
                    "Holographic company logo rotating above the lobby, twenty feet tall. Security checkpoints — scanners, armed guards, the subtle gleam of automated turrets tracking movement. Everything is white, chrome, and precisely lit.",
                    "Executive floor. Floor-to-ceiling windows showing Night City laid out below like a circuit board on fire. Furniture that costs more than most people's lives. A conference table long enough to land a helicopter on.",
                ],
                "sound": [
                    "The hush of money. Climate control so perfect you forget air exists. Heels on marble — sharp, deliberate, metronomic. An elevator chime, soft as a whisper.",
                    "Security comms crackling in earpieces. The whisper-click of mag-locked doors. Somewhere, a phone ringing once before being answered by someone paid to answer on the first ring.",
                    "Silence that costs. The kind you buy by putting enough steel, glass, and armed personnel between you and the city. A pen signing something that ruins lives, soft as a breath.",
                ],
                "smell": [
                    "Filtered air — no smell at all, which is its own kind of violence after the street. Then: leather, toner, the faint ozone of high-end electronics.",
                    "Coffee that costs forty eddies a cup. Fresh-cut flowers replaced daily — lilies, always lilies, because someone decided lilies say 'power.' Dry-cleaned fabric.",
                    "Nothing. That's the point. They've scrubbed the building of anything human. The absence of smell is a flex.",
                ],
                "touch": [
                    "Marble floor, cold through your shoes. The elevator rail is brushed steel, body-temperature from the climate control. Your visitor badge is thin plastic with a tracker in it.",
                    "The chair in the waiting area is ergonomic perfection — it's comfortable so you forget you're being watched. The glass desk is cold under your forearms.",
                    "Security scanner passing over your body. The micro-delay of the mag-lock releasing — they made you wait that extra half-second on purpose.",
                ],
            },
            "atmosphere": [
                "Arasaka, Militech, Kang Tao — the name changes, the tower doesn't. Glass and steel and the quiet violence of people who destroy lives with a memo.",
                "The higher the floor, the fewer the people. The fewer the people, the more the power. The top floor has one office and one person and they own everything you can see.",
                "You're not welcome here. You're tolerated. There's a difference, and the security team knows exactly what it is.",
            ],
        },
        {
            "type": "gang_hideout",
            "weight": 3,
            "tags": ["dangerous", "criminal"],
            "name_patterns": ["The {adj} Den", "{name}'s Turf", "The {noun} Pit"],
            "sensory": {
                "sight": [
                    "Graffiti on every surface — gang tags, kill counts, crude art that's actually good if you look past the subject matter. Weapons on a table: iron, tech, a mantis blade still sticky. Somebody's gaming on a rigged holoprojector.",
                    "Maelstrom chrome everywhere — faces more machine than flesh, red optic implants glowing in dim rooms. Cables running from a generator to a dozen devices. A workbench covered in cyberware parts, some of them still bloody.",
                    "Valentino gold and red on the walls, religious iconography mixed with gang signs. A shrine in the corner — candles, photos of the dead, a pistol laid across them like an offering. Music playing, corridos, somebody singing along.",
                ],
                "sound": [
                    "Chrome grinding on chrome — someone adjusting their implants with a wrench. Laughter, aggressive, the kind that dares you to not laugh along. A gun being field-stripped, click by click.",
                    "Tyger Claw tech-step rattling a speaker with a cracked cone. Japanese and English tangling together, fast and loud. The whine of a katana being sharpened on a diamond wheel.",
                    "Somebody sparring in the back — the meaty thud of augmented fists on a heavy bag. A dog barking. Radio chatter from a scanner, monitoring NCPD frequencies.",
                ],
                "smell": [
                    "Gun oil, cheap beer, sweat, and the burned-metal smell of recently fired weapons. Synthetic weed smoke hanging in layers. Underneath: blood. Old blood, in the concrete.",
                    "Soldering flux from cyberware repair. Takeout containers — real food and synth mixed together. The sharp chemical tang of combat stims, half-empty on the table.",
                    "Spray paint fumes, engine grease, ozone from overclocked implants. The copper smell of someone who got chromed up recently and is still healing.",
                ],
                "touch": [
                    "Concrete floor, cracked and uneven. The wall is tagged so thick the paint has texture. A shell casing rolls under your foot.",
                    "Folding chair that's seen better decades. The table is a cable spool, sticky with beer rings. Someone hands you a bottle — warm, already opened.",
                    "Air thick enough to taste. The bass from the speaker vibrating in your molars. Someone claps your shoulder and their hand is chrome — cold, hard, grip that could crush bone.",
                ],
            },
            "atmosphere": [
                "Family, if family means people who'd kill for you and maybe kill you. Depends on the day.",
                "Territory is everything. These walls, this block, this building — it's theirs and they'll bleed for it. They already have.",
                "The chrome is the uniform. The heavier the mod, the higher the rank. Or the more they've lost.",
            ],
        },
        {
            "type": "black_market",
            "weight": 2,
            "tags": ["commerce", "criminal"],
            "name_patterns": ["The {adj} Exchange", "{name}'s Stock", "The Back Shelf"],
            "sensory": {
                "sight": [
                    "Crates stacked to the ceiling, contents unmarked. A display case with cyberware that's definitely stolen — serial numbers acid-washed. A dealer in a mask, eyes only, gesturing at inventory.",
                    "Weapons laid out on black cloth like a surgeon's tools. Military-grade tech that has no business being here. A terminal showing encrypted transactions, numbers scrolling green.",
                    "Hidden behind a noodle shop, through a door that isn't there unless you know the knock. LED strips, red, casting everything in the color of the merchandise's provenance.",
                ],
                "sound": [
                    "Whispered negotiations. The click of a case opening — chrome inside, nestled in foam. A jammer buzzing, killing any signal in a twenty-foot radius.",
                    "Eddies transferring — the soft chime of a credchip reader. Somebody testing a weapon's action, slide racking in the quiet. Fabric rustling as contraband changes hands.",
                    "A scanner alarm outside — everyone freezes for three seconds, then the dealer waves it off. Background: the muffled noise of the legitimate business upstairs.",
                ],
                "smell": [
                    "Gun oil, packing foam, the chemical smell of factory-sealed cyberware. Underneath: fear-sweat from the buyer who knows what happens if NCPD finds this place.",
                    "Ozone from the jammer. New plastic — packaging, cases, the wrap on a fresh Sandevistan that fell off the Militech transport. Coffee from the shop above, incongruously normal.",
                    "Metal and money. The flat, dry smell of credchips handled by too many hands. Antiseptic from the cyberware — this stuff's clean. The street chrome isn't.",
                ],
                "touch": [
                    "The cyberware is cold and heavier than it looks. The dealer's handshake is dry, brief, all business. The credchip warm from your pocket.",
                    "Weapons have heft. The Lexington fits your grip like it was made for you. It wasn't — it was made for whoever they took it from.",
                    "The table is solid, bolted down. The stool doesn't swivel. Everything here is designed to not move quickly, including the customers.",
                ],
            },
            "atmosphere": [
                "Everything has a price and nothing has a receipt. Corpo surplus, stolen military tech, organs — if it exists, it's here.",
                "Trust is the product. The dealer trusts you were referred. You trust the chrome isn't booby-trapped. Both of you trust nobody followed the other one in.",
                "The economy that actually runs Night City. Eddies flow down here like water, invisible to the corpos who think they control the market.",
            ],
        },
        {
            "type": "combat_zone",
            "weight": 2,
            "tags": ["dangerous", "isolated"],
            "name_patterns": ["The {adj} Zone", "{name}'s Ruin", "Sector {noun}"],
            "sensory": {
                "sight": [
                    "Burned-out buildings, rebar jutting from concrete like broken bones. A Militech APC rusting on its side, tires gone, stripped to the frame. Somebody's living in it.",
                    "Pacifica skyline — half-built resort towers, construction cranes frozen mid-swing for a decade. Overgrown lots. A swimming pool filled with rainwater and garbage.",
                    "Bullet holes in everything. Scorch marks from incendiary grenades. A market set up in a parking garage — tarps, car batteries, people with guns visible.",
                ],
                "sound": [
                    "Gunfire — distant, sporadic, the background noise of a place with no law. A generator coughing somewhere. Dogs, feral, fighting over something you don't want to see.",
                    "Wind through broken windows, a sound like breathing. Rubble shifting — rats or people, same survival instinct. An explosion, far enough to not worry about. Yet.",
                    "Silence that's worse than the gunfire. The creak of a structure that's going to collapse eventually. Your own breathing, your own heartbeat, your own footsteps.",
                ],
                "smell": [
                    "Concrete dust, sewage, smoke. The sweet-rot smell of a building that's been wet inside for years. Gunpowder residue, faint but recent.",
                    "Burned plastic and the acrid tang of a chemical fire that went out days ago. Human waste. Cooking smoke from a camp you can't see.",
                    "Rust, mold, wet earth where the pavement's cracked open. The sharp clean smell of rain on rubble, which is the only clean thing here.",
                ],
                "touch": [
                    "Rubble underfoot — every step is a decision. Glass, gravel, rebar. The wall you lean against shifts and you stop leaning.",
                    "Air on your skin that's gritty, particulate, the kind that settles in your lungs. Everything you touch leaves residue on your fingers — dust, rust, ash.",
                    "The ground is uneven. Your ankle turns on broken concrete. The cover you're crouching behind is a car door and it won't stop anything bigger than a pistol round.",
                ],
            },
            "atmosphere": [
                "NCPD doesn't come here. Trauma Team charges triple. This is where Night City keeps the things it doesn't want to look at.",
                "Every building is a potential ambush. Every person is a potential threat. Paranoia isn't a disorder here — it's a survival skill.",
                "The city tried to build something here once. Now it's a monument to the gap between what Night City promises and what it delivers.",
            ],
        },
        {
            "type": "nomad_camp",
            "weight": 1,
            "tags": ["social", "safe", "isolated"],
            "name_patterns": ["{name} Camp", "The {adj} Convoy", "Mile {noun}"],
            "sensory": {
                "sight": [
                    "Vehicles circled like wagons — modified trucks, converted RVs, a tanker with solar panels bolted to the roof. Tents and tarps between them. Kids running.",
                    "Badlands stretching in every direction, brown and gold and endless. The camp is a cluster of color and movement in the nothing. Smoke from a cookfire.",
                    "Mechanic under a truck, legs sticking out. A rifle leaning on every third vehicle. A woman on watch, silhouetted against the sunset, scanning the horizon with enhanced optics.",
                ],
                "sound": [
                    "Engines being tuned — the cough and catch of an old V8 coming back to life. Someone playing guitar, real strings, around the fire. Laughter that echoes in the open air.",
                    "Wind — constant, dry, carrying sand that ticks against metal. Radio chatter between outriders. A dog barking at a dust devil.",
                    "The quiet of the desert at night, which isn't quiet at all — insects, the tick of cooling engines, coyotes in the distance. Someone telling a story by the fire, voice low.",
                ],
                "smell": [
                    "Campfire smoke, engine oil, the mineral smell of desert air. Somebody's grilling real meat — traded for, hunted for, earned.",
                    "Dust, gasoline, sunscreen that's been on too long. Coffee boiling in a tin pot. The clean, dry scent of nothing for fifty miles.",
                    "Leather, sweat, motor oil, and the open-air smell that city people forget exists. No synthetics. No recycled air. Just sky.",
                ],
                "touch": [
                    "Sand in everything — your boots, your hair, the creases of your hands. The fire's warmth on your face, the night cold on your back.",
                    "The truck hood is warm from the sun, even after dark. The camp chair canvas sags under you. Solid ground, real ground, not concrete.",
                    "Handshake that means something here. Callused palms, strong grip, eye contact that checks if you're real. The wind pulling at your jacket, steady and patient.",
                ],
            },
            "atmosphere": [
                "Family in the way that matters — chosen, tested, defended. The Badlands will kill you alone. Together is the only option.",
                "Freedom tastes like dust and diesel. No corpo leash, no city walls. The sky is the ceiling and it goes forever.",
                "The road is home. The camp is temporary. The people are permanent. That's the deal.",
            ],
        },
        {
            "type": "netrunner_den",
            "weight": 1,
            "tags": ["criminal", "isolated"],
            "name_patterns": ["The {adj} Node", "{name}'s Subnet", "ICE House"],
            "sensory": {
                "sight": [
                    "Server racks floor to ceiling, LEDs blinking like a cityscape laid sideways. Cables running everywhere — over the floor, up the walls, into the netrunner slumped in the chair with a cable in the base of their skull.",
                    "Screens — dozens — showing code, camera feeds, data streams, the Net rendered in blue-white geometry. A netrunner's body in a cooling chair, eyes moving behind closed lids, deep in a run.",
                    "Ice-blue light from the servers. No windows. Emergency shutdown switch — big, red, physical — by the door. A dead plant. A living netrunner, though you'd need a bioscan to confirm it.",
                ],
                "sound": [
                    "Server fans, a wall of white noise that becomes invisible after a minute. The click of fingers on a haptic keyboard. A flatline alarm, quickly silenced — false alarm. Probably.",
                    "Data transfer tones — musical, almost, if you've spent enough time here. The creak of the cooling chair adjusting. Someone's vitals beeping on a monitor, slow and steady.",
                    "The netrunner murmuring in their run — fragments of code spoken aloud, commands to daemons, the occasional gasp when ICE hits back. Cooling fans cycling higher. The building's power grid humming under the load.",
                ],
                "smell": [
                    "Ozone and hot plastic — servers cooking the air. Energy drinks, the citrus-chemical kind, empty cans everywhere. The stale smell of a room that hasn't been opened in weeks.",
                    "Coolant, the sharp kind used in server rigs. Solder from recent repairs. The sour smell of someone who forgot to eat, forgot to sleep, forgot they had a body.",
                    "Burnt insulation — something's running too hot. Synthetic food wrappers. The antiseptic tang of the neural cable sanitizer, because infections kill netrunners faster than ICE.",
                ],
                "touch": [
                    "The air is cold from the cooling system. The neural cable is smooth, warm from use, and plugging it in feels like falling. The keyboard is haptic — no keys, just pressure fields.",
                    "Server rack metal, vibrating faintly from the fans. The cooling chair's gel conforms to your body. The cable port at the back of your neck — cold metal ring, familiar as a scar.",
                    "Static on every surface. Touch a rack and your arm hair stands up. The floor is raised — hollow underneath, stuffed with cables. It flexes when you walk.",
                ],
            },
            "atmosphere": [
                "The meat world is a waiting room. The real work happens in the Net, in the data, in the spaces between systems that think they're secure.",
                "Voodoo Boys, independent runners, corporate defectors — different flags, same addiction. The Net is the only place that feels real to them.",
                "One wrong move in there and the body in the chair stops breathing. The equipment keeps humming either way.",
            ],
        },
        {
            "type": "chop_shop",
            "weight": 1,
            "tags": ["criminal", "commerce"],
            "name_patterns": ["{name}'s Garage", "The {adj} Shed", "Parts & Labor"],
            "sensory": {
                "sight": [
                    "A vehicle on the lift, half-disassembled — panels off, engine exposed like a patient on a table. Shelves of parts, tagged with numbers that aren't serial numbers. Sparks from a cutting torch.",
                    "Cyberware in jars on a shelf — arms, optic assemblies, a spinal column shining chrome under fluorescent light. A workbench covered in tools and blood. A drain in the floor.",
                    "Three cars in various stages of becoming other cars. A Quadra being turned into two Thortons and a pile of spare parts. VIN plates in a bucket by the door.",
                ],
                "sound": [
                    "Impact wrench screaming. The grind of a cutting wheel through chassis steel. Radio playing something old — rock, pre-war — to cover the noise of crimes in progress.",
                    "Hissing of a pneumatic lift. Metal on metal, the clang of a dropped wrench echoing. Someone arguing about a price — their voice bouncing off the concrete walls.",
                    "An engine revving — testing, not running. The pop-pop of spot welds. A compressor cycling on and off like a mechanical heartbeat.",
                ],
                "smell": [
                    "Grease, cutting fluid, hot metal, burned rubber. The tang of battery acid from a pile of used power cells. Underneath: the antiseptic smell of cyberware being prepped.",
                    "Motor oil so thick in the air it coats your tongue. Welding fumes — sharp, acrid, makes your eyes water. Old concrete soaked with decades of automotive fluids.",
                    "Hydraulic fluid, brake dust, and the iron-sweet smell of freshly cut steel. Coffee that's been reheating on the same hot plate since morning.",
                ],
                "touch": [
                    "Everything is gritty — your hands, the tools, the floor. The engine block is warm. Grease under your fingernails that won't come out for days.",
                    "The workbench vibrates when the impact wrench runs. Sparks from the grinder land on your arm — tiny, hot, brief. The chrome on the shelf is cold and greasy.",
                    "Concrete floor, cracked and oil-stained. The lift hydraulics shudder when they hold. Your feet stick to whatever's coating the ground near the drain.",
                ],
            },
            "atmosphere": [
                "Stolen cars in, clean parts out. Or stolen chrome in, sanitized implants out. Same business model, different inventory.",
                "The mechanic doesn't ask where it came from. You don't ask where it's going. Eddies change hands and everyone forgets everyone's face.",
                "Grease and crime, honest in their dishonesty. At least here, the transaction is straightforward.",
            ],
        },
        {
            "type": "braindance_parlor",
            "weight": 1,
            "tags": ["social", "commerce"],
            "name_patterns": ["BD {noun}", "The {adj} Experience", "{name}'s Dreams"],
            "sensory": {
                "sight": [
                    "Rows of reclining chairs, each in a curtained alcove. Headset visors hanging from adjustable arms. Wall display showing the menu — sensory experiences categorized, priced, rated.",
                    "Soft purple lighting, designed to relax. A customer in a chair, completely still, visor on, body twitching — they're someone else right now. A technician wiping down a headset with antiseptic.",
                    "The lobby is clean, corporate almost. The back rooms aren't on the menu — illegal BDs, snuff scrolls, XBDs that void your warranty and maybe your humanity.",
                ],
                "sound": [
                    "The electromagnetic whine of headsets at full immersion. Breathing — deep, slow, synchronized across a dozen customers. The soft chime of a session ending.",
                    "Near-silence, by design. Acoustic foam on every surface. The whisper of the technician checking vitals. A customer coming out of a deep scroll, gasping like they surfaced from water.",
                    "The hum of the recording equipment in the back. A customer laughing in their session — no, crying. Hard to tell. The body does strange things when the mind is elsewhere.",
                ],
                "smell": [
                    "Antiseptic on the headsets, that hospital-clean smell. The synthetic leather of the chairs. Air freshener — lavender, pumped through the vents to keep people calm.",
                    "Sweat from the customer who's been under for three hours. The chemical tang of the interface gel they smear on the contact points. Recycled air, over-filtered.",
                    "Clean. Almost too clean. The kind of clean that's hiding something. Underneath, if you breathe deep: the organic scent of people's bodies doing things their minds don't know about.",
                ],
                "touch": [
                    "The chair reclines smooth, supports your neck. The headset visor is warm from the last user, foam padding pressing your temples. The interface gel is cold, then numb, then gone.",
                    "You stop feeling the chair after thirty seconds. That's the point. The BD takes over — you feel what they recorded. Their hands, their skin, their pain, their pleasure.",
                    "Coming out is the worst part. The visor lifts and suddenly you have a body again — heavy, clumsy, yours. The chair is too firm. The air is too cold. Reality is a downgrade.",
                ],
            },
            "atmosphere": [
                "Legal escapism with an illegal back catalog. The front of house is therapy, entertainment, tourism. The back room is where the real eddies are.",
                "Everybody's running from something. BDs let you run into someone else's life instead. For an hour, you're not you. That's the product.",
                "Addiction dressed up as recreation. The regulars come every day. Their eyes get that flat look — the real world doesn't render at high enough resolution anymore.",
            ],
        },
        {
            "type": "food_stall",
            "weight": 2,
            "tags": ["social", "safe", "rest"],
            "name_patterns": ["{name}'s Noodles", "The {adj} Bowl", "Street {noun}"],
            "sensory": {
                "sight": [
                    "Steam rising from a vat of broth, lit neon-orange by the sign above. A counter with six stools, three occupied. The cook working fast — chopping, stirring, plating — chrome hands a blur.",
                    "Plastic tarps for walls, fairy lights strung between poles. Menu handwritten on a board, half in Japanese, half in English, prices in eddies. A cat sleeping on a crate of synth-noodles.",
                    "Night City street life flowing past — chrome, leather, neon reflections in puddles. The stall is an island of warm light and steam in the cold corridor of the street.",
                ],
                "sound": [
                    "Sizzling oil, the clatter of a wok, the cook shouting orders in a language that's three languages stitched together. Slurping — unapologetic, satisfied.",
                    "The hiss of steam. Chopsticks clicking on ceramic. A customer's holo ringing, ignored in favor of noodles. Street noise — traffic, voices, a siren wailing somewhere.",
                    "Bowls being set down — ceramic on metal, a solid sound. The cook humming. Rain on the plastic tarp roof, irregular and constant.",
                ],
                "smell": [
                    "Broth — real soy, real ginger, real garlic, or close enough that your tongue can't tell. Frying oil that's been used all day, dark and fragrant. Chili paste, eye-watering, on the counter.",
                    "Steam carrying pork fat and five-spice through the air. The clean, sharp smell of fresh scallions being cut. Underneath: the ever-present Night City ozone and exhaust.",
                    "Sesame oil, rice vinegar, the caramel-dark sweetness of the sauce. Your jacket will smell like this place for two days. You won't mind.",
                ],
                "touch": [
                    "The bowl is almost too hot to hold. Ceramic, heavy, full. The broth warms you from the inside out — first sip and your shoulders drop an inch.",
                    "Metal stool, cold under you. The counter is scarred and warm from the cooking surface below. Chopsticks — disposable, wooden, slightly splintery.",
                    "Steam on your face, opening your pores. Your hands wrapped around the bowl. For five minutes, Night City shrinks to the size of this counter and the food in front of you.",
                ],
            },
            "atmosphere": [
                "The last honest business in Night City. You pay, you eat, you feel human for twenty minutes. No angle, no agenda, just noodles.",
                "Neutral ground by unspoken law. Gangers eat next to corpos eat next to cops. The food doesn't care who you are. Neither does the cook.",
                "This is where the solos come after a job. Where the fixers close deals over dumplings. Where everybody is just a person with a bowl and a pair of chopsticks.",
            ],
        },
        {
            "type": "ncpd_precinct",
            "weight": 1,
            "tags": ["authority", "danger"],
            "name_patterns": ["Precinct {noun}", "NCPD {name} Division", "The {adj} Station"],
            "sensory": {
                "sight": [
                    "MaxTac gear on the rack — heavy armor, smart-link weapons, the matte-black helmets with the red visors. A holding cell with a plexiglass front, someone inside with too much chrome and dead eyes.",
                    "Desks drowning in case files and empty stim containers. A holographic crime map of the district, red dots clustered like disease. An officer with a bandaged arm typing one-handed.",
                    "Wanted holos cycling on the wall — faces, chrome descriptions, last known locations. A corpo liaison in a suit standing near the captain's office, not sitting, making a point.",
                ],
                "sound": [
                    "Dispatch comms — constant, overlapping, the voice of a city bleeding from a hundred wounds at once. Keyboards. A suspect in holding banging on the plexiglass, rhythmic, ignored.",
                    "The heavy footsteps of MaxTac boots. A phone ringing that nobody picks up. Someone reading rights to a perp — fast, monotone, like a prayer they've said too many times.",
                    "Coffee machine sputtering. The buzz of the mag-lock on the armory door. A detective arguing with a supervisor about overtime that won't get approved.",
                ],
                "smell": [
                    "Stale coffee, sweat, gunshot residue that's soaked into the furniture. The chemical tang of evidence bags. Cheap disinfectant fighting a losing war.",
                    "Toner, body armor polymer, the metallic aftertaste of too many stims. Takeout containers from three shifts ago. The ozone smell of the holding cell's suppression field.",
                    "Exhaustion has a smell — cortisol, old deodorant, the flat staleness of people who've been indoors too long. That's this place.",
                ],
                "touch": [
                    "Everything is hard surfaces — metal desks, plastic chairs, concrete under thin carpet. The chair doesn't adjust. The desk has a coffee ring older than your career.",
                    "The holding cell plexiglass is warm from the suppression field. The mag-lock keypad is worn smooth on 1, 4, 7, and 9 — someone should change the code.",
                    "Badge on your chest, heavy. Sidearm on your hip, heavier. The weight of a city that doesn't want to be policed pressing down on everything.",
                ],
            },
            "atmosphere": [
                "Underfunded, overwhelmed, and half-owned by the corpos they're supposed to regulate. Justice is a resource allocation problem nobody's solving.",
                "Good cops, bad cops, bought cops, burned-out cops. The uniform is the same. What's underneath varies. Sometimes fatally.",
                "The thin chrome line between order and the combat zone. Thinner every day.",
            ],
        },
        {
            "type": "fixer_office",
            "weight": 1,
            "tags": ["social", "commerce", "criminal"],
            "name_patterns": ["{name}'s Office", "The {adj} Connection", "Back Room {noun}"],
            "sensory": {
                "sight": [
                    "A back room behind a legitimate front — could be a bar, a laundromat, a ripperdoc's. Desk, terminal, two chairs. The screen is angled so only the fixer can see it.",
                    "Encrypted terminal with three screens — job listings, merc profiles, a live feed of NCPD dispatch. A wall of photos — contacts, assets, people who owe favors. Some photos have X marks.",
                    "Understated. A good chair, a clean desk, a bottle of something real on the shelf. No weapons visible, which means they're hidden well. The fixer doesn't need to flex.",
                ],
                "sound": [
                    "The soft click of encrypted comms connecting. The fixer's voice — calm, measured, every word chosen. A terminal notification chiming — new job, new opportunity, new body count.",
                    "Holo ringing. The fixer answering, three words, hanging up. Another call, same pattern. A city's worth of problems being routed through one desk.",
                    "Near-silence, enforced. White noise generator running. The room is clean — no bugs, scanned hourly. The only sound is negotiation.",
                ],
                "smell": [
                    "Good liquor, leather chair, the ozone of encrypted hardware. The absence of street smells — this room is sealed, filtered, private.",
                    "Coffee, real coffee — a flex in a city of synth-caf. The fixer's cologne or perfume, subtle, expensive. Paper — actual paper, because some records shouldn't be digital.",
                    "Money. Not a literal smell — the metaphorical weight of eddies flowing through this room, the invisible scent of transactions that shape the district.",
                ],
                "touch": [
                    "The chair is good — solid, leather, offered to you as a courtesy. The desk between you is a negotiating distance. The credchip the fixer slides across is warm from their hand.",
                    "Handshake — firm, brief, sealing. The drink poured for you is cold, smooth, a gesture that means you're worth the good stuff. Or that the job is bad enough to need it.",
                    "The shard the fixer hands you — job details, encrypted, self-deleting. Small, cold, sharp-edged. The weight of someone's life or death in a chip the size of your thumbnail.",
                ],
            },
            "atmosphere": [
                "The invisible infrastructure of Night City's real economy. Every job, every merc, every corpo hit and data steal runs through a room like this.",
                "The fixer remembers everything. Every favor, every debt, every betrayal. That's the job. That's the power.",
                "You're here because you need work or the fixer needs a problem solved. Either way, someone's getting paid and someone's getting hurt.",
            ],
        },
        {
            "type": "power_plant",
            "weight": 1,
            "tags": ["isolated", "danger"],
            "name_patterns": ["{name} Power Station", "Grid {noun}", "The {adj} Plant"],
            "sensory": {
                "sight": [
                    "Cooling towers bleeding steam into an orange sky. Turbine halls stretching long as city blocks, machinery the size of buildings. Warning signs in three languages, all saying the same thing: stay out.",
                    "Control room with a wall of monitors — power grid maps, reactor readings, security feeds showing empty corridors. Two techs, bored, watching numbers that could kill a district if they go wrong.",
                    "Pipe jungles — conduits running in every direction, color-coded, labeled, some leaking. Catwalks over the turbine floor, vibrating with the machinery below. Emergency lights casting everything in red-amber.",
                ],
                "sound": [
                    "The deep, bone-level hum of turbines at full output. A sound you feel more than hear — it lives in your chest, in your teeth. After ten minutes you stop noticing. After ten years it lives in your dreams.",
                    "Steam venting, a controlled scream. Cooling systems cycling — pumps, fans, the rush of water through pipes wide enough to crawl through. Alert chimes, routine, ignored.",
                    "Catwalks ringing under your boots. The clang of maintenance tools echoing in spaces built for machines, not people. Radio chatter from the control room, tinny and far away.",
                ],
                "smell": [
                    "Ozone, heavy and constant — the smell of electricity at industrial scale. Coolant, chemical and sharp. Machine oil, hot metal, and the faint burnt smell of insulation working overtime.",
                    "Steam that smells like minerals and heat. The rubber-and-plastic smell of high-voltage insulation. Somewhere, a coolant leak — sweet, toxic, giving someone a headache they'll blame on the shift.",
                    "The air tastes like metal. Your fillings ache near the transformers. Concrete dust and the dry, sterile smell of a building designed to contain something dangerous.",
                ],
                "touch": [
                    "Everything vibrates. The floor, the walls, the railing — the entire structure is a tuning fork for the turbines below. Your body adjusts. Your body shouldn't have to.",
                    "The catwalk grating under your feet, cold and sharp through thin soles. Static on your skin near the transformers. Your hair lifts in the electromagnetic field.",
                    "Warmth from the conduits — the pipes are hot to the touch, labeled DANGER, touched anyway because the catwalks are narrow. The control room door is vault-thick and whisper-quiet.",
                ],
            },
            "atmosphere": [
                "The beating heart of a district. If it stops, fifty thousand people go dark. That makes it valuable. That makes it a target.",
                "Santo Domingo industrial sprawl — power plants, factories, the infrastructure that Night City pretends doesn't exist while running on every watt it produces.",
                "The kind of place where an 'accident' can be worth millions. Or can kill thousands. Sometimes both, for the right client.",
            ],
        },
        {
            "type": "shanty_market",
            "weight": 2,
            "tags": ["commerce", "social"],
            "name_patterns": ["The {adj} Bazaar", "{name}'s Row", "Scrap {noun}"],
            "sensory": {
                "sight": [
                    "Improvised stalls made of shipping containers, car doors, and plastic sheeting. Goods hung from wires — clothes, tools, cyberware of questionable origin. Crowds pushing through aisles wide enough for one and a half people.",
                    "Dogtown sprawl — a market that grew like mold, organic and unstoppable. Hand-painted signs, holographic price tags powered by car batteries. A vendor demonstrating a used cyberdeck, sparks flying.",
                    "Color everywhere — painted metal, neon tape, fabric scraps used as awnings. A food vendor next to a weapons dealer next to a woman selling children's shoes. Night City's full spectrum in fifty meters.",
                ],
                "sound": [
                    "Haggling in six languages simultaneously. A vendor banging a pipe against a stall support to get attention. Music from three different stalls fighting for dominance — cumbia wins.",
                    "The crowd noise — dense, constant, a river of human sound. Credchip readers chiming. A child crying. Someone shouting a price, someone shouting a counter-offer.",
                    "A generator coughing to life. The sizzle of a food stall's grill. Fabric flapping in the wind tunnel between containers. A scuffle breaking out and resolving in thirty seconds flat.",
                ],
                "smell": [
                    "Fried food, machine oil, sweat, and the complex layered stink of a thousand things for sale in close quarters. Spices you can't name from cuisines that survived the corporate monoculture.",
                    "Burning plastic from a vendor melting down scrap. Incense from the stall selling religious items — Guadalupe candles next to Buddhist prayer flags next to Shinto charms. Diesel from the generators.",
                    "Humanity, concentrated. The smell of people living, buying, selling, eating, surviving in a space too small for the purpose. It's not pleasant. It's alive.",
                ],
                "touch": [
                    "Shoulder-to-shoulder in the main aisle. Someone's chrome arm brushing yours — cold, hard, apologetic nod. The goods on the table are mixed — some greasy, some clean, all secondhand.",
                    "Fabric of a jacket — real? synth? does it matter at this price? The vendor holds it up and the seams are solid. Your fingers find the hidden pocket. Sold.",
                    "Crowd pressure, the physics of too many bodies in too little space. Your hand on your credchip, protective. The stall counter is warm from the cooking surface next door.",
                ],
            },
            "atmosphere": [
                "Capitalism in its rawest form. No branding, no marketing, no corporate extraction. Just people selling things to people who need them.",
                "This is where the eddies go after the corpos take their cut — into the real economy, hand to hand, stall to stall.",
                "Dangerous, loud, alive. The corpos can't kill it. NCPD can't regulate it. It grows back every time they tear it down, like scar tissue.",
            ],
        },
    ],

    "name_pools": {
        "adj": ["Neon", "Chrome", "Burnt", "Red", "Black", "Bloody", "Wired",
                "Rusted", "Toxic", "Shattered", "Electric", "Dead", "Razor",
                "Cold", "Hot", "Digital"],
        "noun": ["Wire", "Edge", "Chrome", "Signal", "Grid", "Stack", "Void",
                 "Spike", "Byte", "Node", "Shard", "Ghost", "Pulse", "Drift"],
        "noun2": ["Steel", "Smoke", "Blood", "Acid", "Copper", "Iron", "Glass",
                  "Carbon", "Silicon", "Neon"],
        "name": ["Tanaka", "Vasquez", "Kowalski", "Okonkwo", "Patel", "Nguyen",
                 "Reyes", "Chen", "Volkov", "DuPont", "Mbeki", "Harada",
                 "Morrison", "Santos", "Kim", "Petrov", "Guerrero", "Nakamura",
                 "Blackwood", "Ortiz"],
    },

    "npc_count": {"min": 60, "max": 85},
    "npc_archetypes": [
        {
            "role": "corpo_exec",
            "voice": "corpo",
            "weight": 1,
            "location_type": "corpo_tower",
            "names": ["Director Tanaka", "VP Harlow", "Ms. Alvarez",
                      "Mr. Kessler", "Executive Park", "Director Osei",
                      "VP Nakamura", "The Board Rep", "Ms. Voss", "Director Lao"],
            "personalities": [
                "Cold, precise, smiling. Every word is a contract clause. Never raises their voice — doesn't need to. Has people for that.",
                "Polished, predatory, patient. Treats people like assets to be leveraged or liabilities to be written off. No middle ground.",
                "Charming in a way that makes your skin crawl. Offers you a drink while their security team runs your background. The drink is always excellent.",
            ],
            "knowledge_topics": ["corporate operations", "merger intel", "black projects", "political connections", "rival corp weaknesses"],
            "secret_types": ["embezzlement", "double-dealing with rivals", "illegal cyberware testing", "personal addiction", "kill order authorization"],
            "default_disposition": "calculating",
        },
        {
            "role": "gang_lieutenant",
            "voice": "gang_leader",
            "weight": 2,
            "location_type": "gang_hideout",
            "names": ["Razor", "La Catrina", "Iron Koji", "Brick",
                      "Valentina", "Chrome Fist", "Demon", "Santos",
                      "Viper", "Red"],
            "personalities": [
                "Loud, chrome-heavy, territorial. Earned the position by surviving when others didn't. Leads from the front with a mantis blade and a short fuse.",
                "Quiet, strategic, respected. The gang follows because the lieutenant's plans work. Violence is a tool, not a hobby — but they're fluent in it.",
                "Charismatic, volatile, loyal to the bone. Would die for the gang. Would kill for the gang. Hasn't decided which comes first.",
            ],
            "knowledge_topics": ["territory borders", "rival gang movements", "weapons caches", "protection rackets", "NCPD patrol schedules"],
            "secret_types": ["planning a coup", "informant for NCPD", "addicted to combat stims", "protecting a civilian family", "making deals with a rival"],
            "default_disposition": "hostile",
        },
        {
            "role": "street_soldier",
            "voice": "street",
            "weight": 3,
            "location_type": "combat_zone",
            "names": ["Twitch", "Nails", "Ghost", "Scrapper", "Nine",
                      "Blitz", "Kuro", "Reaper", "Zip", "Bones"],
            "personalities": [
                "Young, wired, running on stims and adrenaline. Eyes that dart too fast — the chrome makes them twitchy. Dangerous because they don't think past the next five minutes.",
                "Quiet, watchful, old for the life — meaning twenty-five. Moves like someone who's been shot before and knows what it costs. Doesn't waste words or ammo.",
                "Loud, reckless, burning bright. Covered in chrome, covered in scars, covered in ink. Talks too much before a fight and goes silent during one.",
            ],
            "knowledge_topics": ["street-level intel", "gang territory", "cheap chrome sources", "combat zone safe routes", "who's hiring"],
            "secret_types": ["wants out of the life", "cyberpsychosis symptoms starting", "protecting a younger sibling", "working for a fixer on the side"],
            "default_disposition": "wary",
        },
        {
            "role": "fixer",
            "voice": "fixer",
            "weight": 2,
            "location_type": "fixer_office",
            "names": ["Dex", "Wakako", "Padre", "Dakota",
                      "Mr. Hands", "Sebastian", "Rogue", "Muamar",
                      "The Broker", "Ash"],
            "personalities": [
                "Calm, connected, transactional. Every conversation is a negotiation. Remembers every favor owed and owed to, down to the eddie.",
                "Affable, dangerous, old-school. Built their network over decades. Knows where every body is buried because they arranged half the funerals.",
                "Professional, cold, efficient. Jobs in, eddies out, mercs matched to contracts by algorithm and instinct. Sentiment is overhead they can't afford.",
            ],
            "knowledge_topics": ["merc availability", "job listings", "corp movements", "gang politics", "who's reliable and who's flatlined"],
            "secret_types": ["playing multiple clients against each other", "building leverage for a power play", "has a personal code that contradicts the business", "knows who killed someone important"],
            "default_disposition": "professional",
        },
        {
            "role": "netrunner",
            "voice": "netrunner",
            "weight": 1,
            "location_type": "netrunner_den",
            "names": ["T-Bug", "Spider", "Null", "Daemon",
                      "Whisper", "Binary", "Root", "Glitch"],
            "personalities": [
                "Pale, wired, half-present. Conversations happen at Net-speed in their head and meat-speed out loud — the lag makes them seem distracted. They're not. They're running three processes.",
                "Paranoid, brilliant, erratic. Sees the Net in everything — patterns, connections, exploits. Talks in metaphors that only make sense if you've jacked in.",
                "Quiet, intense, precise. Every word is data-efficient. Doesn't waste bandwidth on pleasantries. Respects competence, ignores everything else.",
            ],
            "knowledge_topics": ["network architecture", "ICE patterns", "data vaults", "corporate security systems", "Net legends and urban myths"],
            "secret_types": ["found something in the Net they can't explain", "slowly losing themselves to cyberpsychosis", "maintaining a hidden AI contact", "blackmailing a corpo with stolen data"],
            "default_disposition": "distracted",
        },
        {
            "role": "ripperdoc",
            "voice": "medic",
            "weight": 1,
            "location_type": "ripperdoc_clinic",
            "names": ["Doc Vik", "Dr. Chrome", "Cassius", "Fingers",
                      "Doc Nkemelu", "The Surgeon", "Maria Salazar", "Dr. Park"],
            "personalities": [
                "Steady hands, steady voice, eyes that have seen everything open. Treats the body like a machine because it is one — some parts just happen to be organic.",
                "Compassionate under a gruff exterior. Charges fair, works clean, won't install kill-chrome on a kid. Has a line. Doesn't talk about where it is.",
                "Amoral, skilled, expensive. Installs whatever you're paying for — Sandevistan, mantis blades, the works. Doesn't ask why. The chrome doesn't judge and neither do they.",
            ],
            "knowledge_topics": ["cyberware compatibility", "chrome suppliers", "black-market implants", "cyberpsychosis symptoms", "who's been modified recently"],
            "secret_types": ["installing trackers for a corp", "running an unlicensed clinic on the side", "personal history as a corpo biotech researcher", "treating a cyberpsycho off the books"],
            "default_disposition": "clinical",
        },
        {
            "role": "ncpd_officer",
            "voice": "cop",
            "weight": 2,
            "location_type": "ncpd_precinct",
            "names": ["Detective Vasquez", "Officer Hendricks", "Sergeant Okafor",
                      "Lieutenant Stahl", "Detective Kim", "Officer Reeves",
                      "Sergeant Petrov", "Detective Cruz", "Captain Hayashi"],
            "personalities": [
                "Burned out, honest, barely holding on. Twenty years watching the city eat people. Still tries. Doesn't know why. The paperwork is the only thing that makes sense.",
                "Ambitious, political, careful. Knows the corpos pull the strings. Plays the game because the alternative is the combat zone. Keeps a clean desk and a dirty conscience.",
                "Corrupt and functioning. Takes the eddies, looks the other way, keeps the peace by keeping the powerful happy. Sleeps fine. That's the scary part.",
            ],
            "knowledge_topics": ["active investigations", "gang activity", "corporate crime they can't touch", "MaxTac deployment patterns", "who's cooperating"],
            "secret_types": ["on a corpo payroll", "building a case against their own precinct", "personal vendetta against a gang", "evidence they've buried"],
            "default_disposition": "suspicious",
        },
        {
            "role": "nomad",
            "voice": "nomad",
            "weight": 1,
            "location_type": "nomad_camp",
            "names": ["Panam", "Cassidy", "Mitch", "Saul",
                      "Dakota", "Scorpion", "River", "Carol"],
            "personalities": [
                "Direct, loyal, road-weathered. Judges people by what they do, not what they say. Handshake means more than a contract. Doesn't trust the city or anyone in it.",
                "Quiet, capable, watchful. Knows engines, knows the Badlands, knows when the weather's turning. Talks when there's something to say. Otherwise, listens.",
                "Fierce, protective, family-first. The clan is everything. Outsiders are tolerated, maybe. Trust is a long road with no shortcuts.",
            ],
            "knowledge_topics": ["Badlands routes", "smuggling corridors", "clan politics", "vehicle mechanics", "what the city doesn't want you to know"],
            "secret_types": ["considering leaving the clan", "running a side deal with a fixer", "knows a way past the city defenses", "lost someone and hasn't processed it"],
            "default_disposition": "guarded",
        },
        {
            "role": "civilian",
            "voice": "citizen",
            "weight": 3,
            "location_type": "megabuilding",
            "names": ["Kenji", "Mariana", "Oleg", "Priya",
                      "Tomás", "Aisha", "Jun", "Elena",
                      "Viktor", "Beatriz"],
            "personalities": [
                "Tired, ordinary, getting by. Works a job that a machine could do better but a machine costs more to maintain. Goes home to a megabuilding box and does it again tomorrow.",
                "Cheerful on the surface, angry underneath. Knows the system is rigged. Watches the corpo towers from the food stall and does the math on the distance. Keeps smiling because stopping is worse.",
                "Cautious, community-minded, invisible by design. Knows everybody in the building, knows what they need, trades favors instead of eddies. The glue holding the block together.",
            ],
            "knowledge_topics": ["neighborhood gossip", "megabuilding politics", "which vendors are honest", "where not to walk at night", "who disappeared recently"],
            "secret_types": ["witnessed something they shouldn't have", "hiding someone from a gang", "small-time side hustle", "used to be someone else before Night City"],
            "default_disposition": "nervous",
        },
        {
            "role": "solo_merc",
            "voice": "merc",
            "weight": 2,
            "location_type": "food_stall",
            "names": ["V", "Smasher", "Raven", "Kestrel",
                      "Blackhand", "Nomad", "Apex", "Frost",
                      "Trigger", "Widow"],
            "personalities": [
                "Professional, chrome-augmented, economy of movement. Sits with their back to the wall, exits mapped, weapon within reach. Eats fast because downtime is a luxury.",
                "Cocky, skilled, living on borrowed time and loving it. Sandevistan reflexes, mantis blade arms, the kind of chrome that says 'don't.' Talks like someone who's never lost. Will, eventually.",
                "Quiet, haunted, effective. Takes the jobs nobody else will. Comes back. Doesn't talk about it. The chrome keeps them alive. The noodles keep them human.",
            ],
            "knowledge_topics": ["combat tactics", "cyberware performance", "fixer networks", "who's hiring", "threat assessment"],
            "secret_types": ["cyberpsychosis creeping in", "one last job before retirement", "hunting someone specific", "protecting someone the job says they shouldn't"],
            "default_disposition": "alert",
        },
    ],

    "quest_patterns": [
        {
            "type": "data_heist",
            "name_templates": ["The {adj} Download", "The {noun} Breach", "{name}'s Data"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Get the job details from {npc}.", "location_type": "fixer_office"},
                {"objective": "Find a netrunner to crack the ICE at {location}.", "location_type": "netrunner_den"},
                {"objective": "Infiltrate {destination} and extract the data.", "location_type": "corpo_tower"},
                {"objective": "Deliver the shard to {npc} and collect payment.", "location_type": "food_stall"},
            ],
        },
        {
            "type": "gang_war",
            "name_templates": ["Blood on {name}", "The {adj} Turf", "Taking {noun}"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Meet with {npc} about the territory dispute.", "location_type": "gang_hideout"},
                {"objective": "Scout the contested zone at {location}.", "location_type": "combat_zone"},
                {"objective": "Eliminate the rival presence at {destination}.", "location_type": "shanty_market"},
                {"objective": "Report back to {npc} and claim the territory.", "location_type": "nightclub"},
            ],
        },
        {
            "type": "corpo_extraction",
            "name_templates": ["The {adj} Extraction", "Getting {name} Out", "Burning {noun}"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Get briefed by {npc} on the target.", "location_type": "fixer_office"},
                {"objective": "Surveil the target at {location}.", "location_type": "corpo_tower"},
                {"objective": "Extract the target from {destination}.", "location_type": "megabuilding"},
                {"objective": "Deliver the target to {npc} at the safe location.", "location_type": "nomad_camp"},
            ],
        },
        {
            "type": "cyberpsychosis_hunt",
            "name_templates": ["The {adj} Signal", "Flatline {name}", "Chrome Sickness"],
            "stages": 4,
            "stage_templates": [
                {"objective": "Get the contract from {npc} — a cyberpsycho is loose.", "location_type": "ncpd_precinct"},
                {"objective": "Track the cyberpsycho to {location}.", "location_type": "combat_zone"},
                {"objective": "Confront the cyberpsycho at {destination}.", "location_type": "power_plant"},
                {"objective": "Decide: neutralize or bring in. Report to {npc}.", "location_type": "ripperdoc_clinic"},
            ],
        },
    ],

    "item_types": [
        {"category": "weapon", "tags": ["weapon"],
         "items": [
             {"name": "a Lexington pistol", "desc": "Mass-produced, reliable, cheap. The gun Night City gives you when it's done being subtle."},
             {"name": "a thermal katana", "desc": "Heated blade, Tyger Claw style. Cuts through armor and bone. The edge glows orange when it's ready."},
             {"name": "Mantis Blades", "desc": "Forearm-mounted, retractable. The chrome splits at the wrist and two feet of serrated metal unfolds. You are the weapon."},
             {"name": "a tech shotgun", "desc": "Charges between shots. The delay is the trade-off for punching through walls and the person behind them."},
             {"name": "a Copperhead assault rifle", "desc": "Military surplus, full-auto capable. Kicks like a mule. Standard issue for people whose job title is 'problem.'"},
             {"name": "a monowire", "desc": "Spool in the wrist, filament thinner than hair. You flick it and things come apart. Quietly."},
         ]},
        {"category": "cyberware", "tags": ["cyberware", "chrome"],
         "items": [
             {"name": "a Sandevistan", "desc": "Spinal implant. Slows the world to molasses for twelve seconds. Your heart rate triples. Everything else stops."},
             {"name": "a Kerenzikov reflex booster", "desc": "Neural co-processor. Time dilates when you dodge — the bullet goes where you were. You're somewhere else."},
             {"name": "Kiroshi optic implants", "desc": "Eyes that aren't eyes. Zoom, scan, threat detection, low-light. The world annotated in real time, overlaid with data."},
             {"name": "a neural link", "desc": "Base-level interface port. Lets you jack into anything — vehicles, networks, people. The chrome that makes all other chrome work."},
             {"name": "a subdermal armor weave", "desc": "Polymer mesh under the skin. Stops small-caliber rounds. The bruise is spectacular but you're alive to see it."},
             {"name": "Gorilla Arms", "desc": "Hydraulic arm replacements. Crush strength at eight hundred PSI. Opening doors, opening skulls — same motion."},
         ]},
        {"category": "consumable", "tags": ["consumable", "medical"],
         "items": [
             {"name": "a MaxDoc inhaler", "desc": "Emergency medical. Inhale and the nanobots go to work — sealing wounds, killing pain, buying time. Not a cure. A pause button."},
             {"name": "a Bounce Back injector", "desc": "Field healing. Jab it in your thigh and the bio-compound floods your system. Hurts worse before it helps."},
             {"name": "a vial of synthblood", "desc": "Universal donor in a tube. Pour it where you're leaking. It bonds, clots, seals. Tastes like copper when it gets in your mouth."},
             {"name": "a combat stim", "desc": "Adrenaline, pain suppressors, reflex enhancers. Thirty seconds of being more than human. The crash afterward is the price."},
             {"name": "a can of NiCola", "desc": "Night City's soda. Caffeine, taurine, something blue that doesn't have a name. Tastes like battery acid and nostalgia."},
         ]},
        {"category": "data_shard", "tags": ["clue", "quest_item"],
         "items": [
             {"name": "an encrypted data shard", "desc": "Military-grade encryption. Whatever's on here, someone paid a lot to hide it. Someone else is paying you to find it."},
             {"name": "a corporate intel chip", "desc": "Board meeting minutes, project files, kill-order authorizations. The kind of data that starts wars between towers."},
             {"name": "a blackmail shard", "desc": "Photos, recordings, transaction logs. Somebody's leverage over somebody else. Now it's yours. Now you're a target too."},
             {"name": "a dead netrunner's memory core", "desc": "Neural recording from someone who didn't make it out of the Net. Their last run, their last thoughts, possibly their last breath. Might contain what they found."},
         ]},
    ],

    "faction_types": [
        {
            "type": "megacorp",
            "name_templates": ["{name} Corporation", "{name} Industries", "{name} Group"],
            "goals": ["Market dominance.", "Eliminate competition — through acquisition or elimination.", "Control the council. Control the city."],
            "default_reputation": "neutral",
        },
        {
            "type": "gang",
            "name_templates": ["The {name} Crew", "{adj} {noun}", "Los {name}"],
            "goals": ["Hold territory.", "Control the local economy — drugs, chrome, protection.", "Survive the other gangs and NCPD long enough to matter."],
            "default_reputation": "hostile",
        },
        {
            "type": "netrunner_collective",
            "name_templates": ["The {adj} Net", "{name} Protocol", "Subnet {noun}"],
            "goals": ["Control the data.", "Crack the Blackwall.", "Stay invisible to everyone who matters."],
            "default_reputation": "unknown",
        },
        {
            "type": "nomad_clan",
            "name_templates": ["The {name} Clan", "Clan {name}", "The {adj} Riders"],
            "goals": ["Protect the family.", "Keep the roads open.", "Stay free of corpo and city control."],
            "default_reputation": "neutral",
        },
        {
            "type": "law_enforcement",
            "name_templates": ["NCPD {name} Division", "MaxTac Unit {noun}", "The {adj} Squad"],
            "goals": ["Maintain order — or the illusion of it.", "Keep the corpos happy enough to keep funding the department.", "Survive the shift."],
            "default_reputation": "neutral",
        },
        {
            "type": "underground",
            "name_templates": ["The {adj} Network", "{name}'s Circle", "The {noun} Exchange"],
            "goals": ["Connect the dots.", "Profit from every transaction.", "Know more than anyone else in the room."],
            "default_reputation": "unknown",
        },
    ],

    "encounter_types": [
        {
            "type": "combat",
            "weight": 2,
            "location_tags": ["dangerous", "criminal"],
            "enemy_templates": [
                {"name": "a gang ganger", "desc": "Chrome jaw, cheap iron, eyes tweaking from stims. Young enough to be reckless, armed enough to be lethal.",
                 "stats": {"health": 6, "damage": 4, "speed": "fast"},
                 "behavior": "Aggressive, poorly coordinated. Rushes in, relies on chrome and aggression over tactics."},
                {"name": "a corpo security officer", "desc": "Armored, linked, professional. Smart-gun tracking your movement. They called for backup thirty seconds ago.",
                 "stats": {"health": 8, "damage": 5, "speed": "medium"},
                 "behavior": "Tactical. Uses cover, callouts, suppressive fire. Fights like someone with health insurance."},
                {"name": "a MaxTac officer", "desc": "Full tactical armor, Sandevistan blur, weapons that aren't on any civilian market. The thing Night City sends when the gangs aren't enough.",
                 "stats": {"health": 12, "damage": 8, "speed": "very fast"},
                 "behavior": "Lethal, efficient, zero hesitation. Breaches doors, clears rooms, neutralizes threats. You are the threat."},
                {"name": "a cyberpsycho", "desc": "Too much chrome, not enough mind left. Erratic, screaming, chrome grinding against chrome. They were a person once. Now they're a weapons platform with a broken pilot.",
                 "stats": {"health": 15, "damage": 10, "speed": "fast"},
                 "behavior": "Unpredictable. Charges, retreats, charges again. Immense strength, no self-preservation. Killing them is easy. Surviving until you do isn't."},
            ],
            "tone_templates": [
                "Chrome and lead. Everything moves too fast — Sandevistan fast, reflex-booster fast, dying fast. The first three seconds decide it.",
                "Gunfire in enclosed spaces. The muzzle flash strobes the room. Ricochet sparks off chrome. Your ears stop working and your body keeps moving.",
            ],
        },
        {
            "type": "netrun",
            "weight": 1,
            "location_tags": ["criminal", "isolated"],
            "tone_templates": [
                "The Net unfolds — blue geometry, data architecture, ICE crystallizing around you. Your body's in a chair. Your mind's in a fortress. The walls are code and the guards are daemons.",
                "Quiet and lethal. The hack is silent — fingers of code sliding through security layers, each one a trap waiting to spring. One wrong move and the ICE fries your neural link. With your brain attached.",
            ],
        },
        {
            "type": "negotiation",
            "weight": 3,
            "location_tags": ["social", "commerce"],
            "tone_templates": [
                "Words as weapons, silence as armor. Everyone at the table has a gun they're not showing and a number they're not saying. First one to flinch loses.",
                "The deal happens in the space between what's said and what's meant. Subtext, body language, the micro-expressions that chrome can't fake. Night City's real currency is leverage.",
            ],
        },
    ],

    "world_rules_template": {
        "setting": "Night City, Free State of Northern California. A corpo-controlled dystopia built on the bones of the American Dream. Chrome and flesh, neon and shadow, eddies and blood.",
        "tone": "Gritty, lived-in, darkly human. Not cool cyberpunk — desperate cyberpunk. The chrome is a coping mechanism. The neon is a distraction. Underneath it all: people trying to survive a city that was built to consume them.",
        "era": "2077. The Net is rebuilt after the DataKrash, corporations run the government, cyberware is ubiquitous, and the gap between the top of Corpo Plaza and the bottom of Pacifica is measured in human lives.",
        "magic_system": "None — but cyberware and quickhacks blur the line. A Sandevistan user moves faster than the eye can track. A netrunner can fry your brain from across the street. It's not magic. It's money.",
        "combat_rules": {
            "style": "Fast, brutal, chrome-dependent. Cyberware is the equalizer — or the advantage. Quickhacks can shut down a fight before a shot is fired. Mantis Blades don't jam. Sandevistans don't miss.",
            "lethality": "extreme — everyone is armed, everyone is augmented, everyone dies fast",
            "healing": "ripperdocs for the chrome, MaxDoc for the meat — both cost eddies you might not have",
            "note": "Violence is constant and consequence depends on who you killed. Ganger in the combat zone? Nobody blinks. Corpo in a tower? MaxTac in five minutes.",
        },
        "exploration_rules": {
            "style": "District-based danger levels. Watson is rough but survivable. Pacifica is a combat zone. City Center is safe if you belong — lethal if you don't.",
            "discovery": "Scan everything. Kiroshi optics reveal details. The Net reveals secrets. The streets reveal patterns if you watch long enough.",
            "danger": "Night City's danger is ambient. It's not if something happens — it's when. Walking at night, alone, in the wrong district, with visible chrome is an invitation.",
        },
        "dialogue_rules": {
            "style": "Everyone has an angle. The corpo wants leverage. The ganger wants respect. The fixer wants eddies. The civilian wants to survive the conversation. Nobody says what they mean on the first pass.",
            "trust": "Currency, not a feeling. Earned through jobs completed, promises kept, enemies shared. Lost through one betrayal, permanently.",
            "information": "Data is eddies. Nobody talks for free. A name costs. An address costs more. What someone's hiding costs everything.",
        },
    },

    "player_defaults": {
        "name": "the new merc",
        "stats": {"health": 10, "stamina": 8, "street_cred": 1, "cool": 5},
        "starting_items": [
            {"id": "credchip", "name": "a basic credchip",
             "description": "Fifty eddies loaded. Enough for a meal and a mag of ammo. Welcome to Night City."},
            {"id": "burner_holo", "name": "a burner holo",
             "description": "Disposable, prepaid, untraceable. One contact: a fixer who gave you a number and said 'call when you're ready.'"},
            {"id": "cheap_pistol", "name": "a cheap pistol",
             "description": "Unity model. Mass-produced, plastic-framed, thirteen rounds. The gun you carry until you can afford a gun worth carrying."},
            {"id": "worn_jacket", "name": "a worn jacket with ballistic weave",
             "description": "Synth-leather, fraying at the cuffs. The ballistic lining stops small-caliber rounds. Mostly. It's better than skin."},
        ],
    },
}
