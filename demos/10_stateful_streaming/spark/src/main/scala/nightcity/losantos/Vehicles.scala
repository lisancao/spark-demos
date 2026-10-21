package nightcity.losantos

/**
 * The vehicle facts the processors need, from the same GTA V data dump the simulator uses
 * (sim/losantos/world_data.json, extracted from https://github.com/DurtyFree/gta-v-data-dumps):
 * which vehicles fly (planes, helicopters, and the two that hover) and which carry weapons.
 */
object Vehicles {
  val flying: Set[String] = Set("oppressor2", "deluxo", "seasparrow2", "lazer", "akula", "buzzard", "hydra", "raiju", "cuban800")
  val pvp: Set[String] = Set("oppressor2", "deluxo", "toreador", "seasparrow2", "lazer", "nightshark", "kuruma2", "scramjet",
    "vigilante", "akula", "buzzard", "hydra", "raiju")
}
