"""Reviewed scenarios; expected outcomes are not generated from production rules."""

from tests.pricing.knowledge.assessment.item_bank.cases.abyss_affixed_candidates import (
    CASES as ABYSS_AFFIXED_CANDIDATES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_amulets import CASES as ABYSS_AMULETS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_andariel import CASES as ABYSS_ANDARIEL
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_boots import CASES as ABYSS_BOOTS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_caster_unique_alternatives import (
    CASES as ABYSS_CASTER_UNIQUE_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_caster_weapons import CASES as ABYSS_CASTER_WEAPONS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_caster_word_alternatives import (
    CASES as ABYSS_CASTER_WORD_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_charged_dagger import CASES as ABYSS_CHARGED_DAGGER
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_diadem_payloads import CASES as ABYSS_DIADEM_PAYLOADS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_early_named import CASES as ABYSS_EARLY_NAMED
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_embedded_armors import CASES as ABYSS_EMBEDDED_ARMORS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_embedded_gloves_belts import (
    CASES as ABYSS_EMBEDDED_GLOVES_BELTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_embedded_helmets import CASES as ABYSS_EMBEDDED_HELMETS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_existing_armors import CASES as ABYSS_EXISTING_ARMORS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_existing_gloves_belts import (
    CASES as ABYSS_EXISTING_GLOVES_BELTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_grimoires import CASES as ABYSS_GRIMOIRES
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_guardian_components import (
    CASES as ABYSS_GUARDIAN_COMPONENTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_helmets import CASES as ABYSS_HELMETS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_insight import CASES as ABYSS_INSIGHT
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_inventory_charms import CASES as ABYSS_INVENTORY_CHARMS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_loot_shield_alternatives import (
    CASES as ABYSS_LOOT_SHIELD_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_magic_charms import CASES as ABYSS_MAGIC_CHARMS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_named import CASES as ABYSS_MERC_NAMED
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_progression_words import (
    CASES as ABYSS_MERC_PROGRESSION_WORDS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_remaining import CASES as ABYSS_MERC_REMAINING
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_um import CASES as ABYSS_MERC_UM
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_merc_words import CASES as ABYSS_MERC_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_mf_fortitude import CASES as ABYSS_MF_FORTITUDE
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_mf_shako import CASES as ABYSS_MF_SHAKO
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_named_glove_belt import CASES as ABYSS_NAMED_GLOVE_BELT
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_named_swaps import CASES as ABYSS_NAMED_SWAPS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_planner_daggers import CASES as ABYSS_PLANNER_DAGGERS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_player_insight import CASES as ABYSS_PLAYER_INSIGHT
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_player_words import CASES as ABYSS_PLAYER_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_progression_words import CASES as ABYSS_PROGRESSION_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_quality_boundaries import (
    CASES as ABYSS_QUALITY_BOUNDARIES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_rare_kris import CASES as ABYSS_RARE_KRIS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_remaining_armors import CASES as ABYSS_REMAINING_ARMORS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_renewed_sunder import CASES as ABYSS_RENEWED_SUNDER
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_rings import CASES as ABYSS_RINGS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_staff_alternatives import (
    CASES as ABYSS_STAFF_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_starter_tail import CASES as ABYSS_STARTER_TAIL
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_table_daggers import CASES as ABYSS_TABLE_DAGGERS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_teleport_alternatives import (
    CASES as ABYSS_TELEPORT_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_unique_charms import CASES as ABYSS_UNIQUE_CHARMS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_utility_swaps import CASES as ABYSS_UTILITY_SWAPS
from tests.pricing.knowledge.assessment.item_bank.cases.abyss_void import CASES as ABYSS_VOID
from tests.pricing.knowledge.assessment.item_bank.cases.aldur_boot_alternatives import CASES as ALDUR_BOOT_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.ali_baba_loot import CASES as ALI_BABA_LOOT
from tests.pricing.knowledge.assessment.item_bank.cases.andariel_damage_variants import (
    CASES as ANDARIEL_DAMAGE_VARIANTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.andariel_fire_variants import CASES as ANDARIEL_FIRE_VARIANTS
from tests.pricing.knowledge.assessment.item_bank.cases.andariel_native_variants import (
    CASES as ANDARIEL_NATIVE_VARIANTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.angelic import CASES as ANGELIC
from tests.pricing.knowledge.assessment.item_bank.cases.annihilus_tables import CASES as ANNIHILUS_TABLES
from tests.pricing.knowledge.assessment.item_bank.cases.annihilus_variants import CASES as ANNIHILUS_VARIANTS
from tests.pricing.knowledge.assessment.item_bank.cases.arachnid_caster_alternatives import (
    CASES as ARACHNID_CASTER_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.arctic_leveling import CASES as ARCTIC_LEVELING
from tests.pricing.knowledge.assessment.item_bank.cases.arm_king_leoric import CASES as ARM_KING_LEORIC
from tests.pricing.knowledge.assessment.item_bank.cases.armor_progression_baselines import (
    CASES as ARMOR_PROGRESSION_BASELINES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.atma_attack_amulet import CASES as ATMA_ATTACK_AMULET
from tests.pricing.knowledge.assessment.item_bank.cases.attack_survival_baselines import (
    CASES as ATTACK_SURVIVAL_BASELINES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.attack_unique_baselines import CASES as ATTACK_UNIQUE_BASELINES
from tests.pricing.knowledge.assessment.item_bank.cases.beast_summoner import CASES as BEAST_SUMMONER
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_boots import CASES as BERSERK_BOOTS
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_botd_merc import CASES as BERSERK_BOTD_MERC
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_circlet_tail import CASES as BERSERK_CIRCLET_TAIL
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_cure import CASES as BERSERK_CURE
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_defensive_accessories import (
    CASES as BERSERK_DEFENSIVE_ACCESSORIES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_farming_accessories import (
    CASES as BERSERK_FARMING_ACCESSORIES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_grief_oath import CASES as BERSERK_GRIEF_OATH
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_guardian_components import (
    CASES as BERSERK_GUARDIAN_COMPONENTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_helm_alternatives import (
    CASES as BERSERK_HELM_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_inventory_charms import (
    CASES as BERSERK_INVENTORY_CHARMS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_legacy_teleport import CASES as BERSERK_LEGACY_TELEPORT
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_merc_progression_words import (
    CASES as BERSERK_MERC_PROGRESSION_WORDS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_merc_weapon_tail import (
    CASES as BERSERK_MERC_WEAPON_TAIL,
)
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_mf_armor import CASES as BERSERK_MF_ARMOR
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_mf_equipment import CASES as BERSERK_MF_EQUIPMENT
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_native_merc_words import (
    CASES as BERSERK_NATIVE_MERC_WORDS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_renewed_sunder import CASES as BERSERK_RENEWED_SUNDER
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_smoke import CASES as BERSERK_SMOKE
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_standalone_sets import CASES as BERSERK_STANDALONE_SETS
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_starter_sigons import CASES as BERSERK_STARTER_SIGONS
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_starter_topaz import CASES as BERSERK_STARTER_TOPAZ
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_teleport_alternatives import (
    CASES as BERSERK_TELEPORT_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_unbending import CASES as BERSERK_UNBENDING
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_unique_amulets import CASES as BERSERK_UNIQUE_AMULETS
from tests.pricing.knowledge.assessment.item_bank.cases.berserk_utility_words import CASES as BERSERK_UTILITY_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.bk_utility_alternatives import CASES as BK_UTILITY_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.black_attack_modes import CASES as BLACK_ATTACK_MODES
from tests.pricing.knowledge.assessment.item_bank.cases.blizzard_accessories import CASES as BLIZZARD_ACCESSORIES
from tests.pricing.knowledge.assessment.item_bank.cases.blizzard_boots import CASES as BLIZZARD_BOOTS
from tests.pricing.knowledge.assessment.item_bank.cases.blizzard_fortitude import CASES as BLIZZARD_FORTITUDE
from tests.pricing.knowledge.assessment.item_bank.cases.blizzard_inventory_charms import (
    CASES as BLIZZARD_INVENTORY_CHARMS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.blizzard_magic_charms import CASES as BLIZZARD_MAGIC_CHARMS
from tests.pricing.knowledge.assessment.item_bank.cases.blizzard_mf_boots import CASES as BLIZZARD_MF_BOOTS
from tests.pricing.knowledge.assessment.item_bank.cases.blizzard_rare_rings import CASES as BLIZZARD_RARE_RINGS
from tests.pricing.knowledge.assessment.item_bank.cases.blizzard_skullder import CASES as BLIZZARD_SKULLDER
from tests.pricing.knowledge.assessment.item_bank.cases.blizzard_starter_accessories import (
    CASES as BLIZZARD_STARTER_ACCESSORIES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.blizzard_vipermagi import CASES as BLIZZARD_VIPERMAGI
from tests.pricing.knowledge.assessment.item_bank.cases.bloodpact_shard import CASES as BLOODPACT_SHARD
from tests.pricing.knowledge.assessment.item_bank.cases.botd_mercenaries import CASES as BOTD_MERCENARIES
from tests.pricing.knowledge.assessment.item_bank.cases.caster_crown_ages import CASES as CASTER_CROWN_AGES
from tests.pricing.knowledge.assessment.item_bank.cases.caster_enigma_gear import CASES as CASTER_ENIGMA_GEAR
from tests.pricing.knowledge.assessment.item_bank.cases.caster_frostburn import CASES as CASTER_FROSTBURN
from tests.pricing.knowledge.assessment.item_bank.cases.caster_magic_find_accessories import (
    CASES as CASTER_MAGIC_FIND_ACCESSORIES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.caster_ring_alternatives import (
    CASES as CASTER_RING_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.caster_socketed_named import CASES as CASTER_SOCKETED_NAMED
from tests.pricing.knowledge.assessment.item_bank.cases.caster_stormshield import CASES as CASTER_STORMSHIELD
from tests.pricing.knowledge.assessment.item_bank.cases.caster_support_uniques import CASES as CASTER_SUPPORT_UNIQUES
from tests.pricing.knowledge.assessment.item_bank.cases.caster_unique_baselines import CASES as CASTER_UNIQUE_BASELINES
from tests.pricing.knowledge.assessment.item_bank.cases.caster_utility_uniques import CASES as CASTER_UTILITY_UNIQUES
from tests.pricing.knowledge.assessment.item_bank.cases.cats_eye_alternatives import CASES as CATS_EYE_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.chance_guards_alternatives import (
    CASES as CHANCE_GUARDS_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.chaos_enigma import CASES as CHAOS_ENIGMA
from tests.pricing.knowledge.assessment.item_bank.cases.chaos_gloves import CASES as CHAOS_GLOVES
from tests.pricing.knowledge.assessment.item_bank.cases.charged_weapon_alternatives import (
    CASES as CHARGED_WEAPON_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.charm_trade import CASES as CHARM_TRADE
from tests.pricing.knowledge.assessment.item_bank.cases.circlet_candidates import CASES as CIRCLET_CANDIDATES
from tests.pricing.knowledge.assessment.item_bank.cases.civerb_cleglaw_leveling import CASES as CIVERB_CLEGLAW_LEVELING
from tests.pricing.knowledge.assessment.item_bank.cases.class_unique_progression import (
    CASES as CLASS_UNIQUE_PROGRESSION,
)
from tests.pricing.knowledge.assessment.item_bank.cases.class_weapon_baselines import CASES as CLASS_WEAPON_BASELINES
from tests.pricing.knowledge.assessment.item_bank.cases.coh_caster_roles import CASES as COH_CASTER_ROLES
from tests.pricing.knowledge.assessment.item_bank.cases.coh_variant_roles import CASES as COH_VARIANT_ROLES
from tests.pricing.knowledge.assessment.item_bank.cases.combat_boot_belt_alternatives import (
    CASES as COMBAT_BOOT_BELT_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.consumables import CASES as CONSUMABLES
from tests.pricing.knowledge.assessment.item_bank.cases.crafted_glove_candidates import (
    CASES as CRAFTED_GLOVE_CANDIDATES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.cta_caster_swaps import CASES as CTA_CASTER_SWAPS
from tests.pricing.knowledge.assessment.item_bank.cases.cta_prebuff_variants import CASES as CTA_PREBUFF_VARIANTS
from tests.pricing.knowledge.assessment.item_bank.cases.cure_gear_alternatives import CASES as CURE_GEAR_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.defensive_caster_belts import CASES as DEFENSIVE_CASTER_BELTS
from tests.pricing.knowledge.assessment.item_bank.cases.defensive_unique_baselines import (
    CASES as DEFENSIVE_UNIQUE_BASELINES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.double_throw_filled_diadems import (
    CASES as DOUBLE_THROW_FILLED_DIADEMS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.dracul_alternatives import CASES as DRACUL_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.dragon_talon_budget import CASES as DRAGON_TALON_BUDGET
from tests.pricing.knowledge.assessment.item_bank.cases.dragon_talon_cbf import CASES as DRAGON_TALON_CBF
from tests.pricing.knowledge.assessment.item_bank.cases.dragon_talon_guillaume import CASES as DRAGON_TALON_GUILLAUME
from tests.pricing.knowledge.assessment.item_bank.cases.dream_fire_words import CASES as DREAM_FIRE_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.dream_pair import CASES as DREAM_PAIR
from tests.pricing.knowledge.assessment.item_bank.cases.duress_endgame_merc import CASES as DURESS_ENDGAME_MERC
from tests.pricing.knowledge.assessment.item_bank.cases.duress_gear_alternatives import (
    CASES as DURESS_GEAR_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.dwarf_star_alternatives import CASES as DWARF_STAR_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.early_survival_uniques import CASES as EARLY_SURVIVAL_UNIQUES
from tests.pricing.knowledge.assessment.item_bank.cases.early_unique_baselines import CASES as EARLY_UNIQUE_BASELINES
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_cure import CASES as ECHOING_CURE
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_cure_progression import (
    CASES as ECHOING_CURE_PROGRESSION,
)
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_enigma import CASES as ECHOING_ENIGMA
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_fade import CASES as ECHOING_FADE
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_hellwarden import CASES as ECHOING_HELLWARDEN
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_insight import CASES as ECHOING_INSIGHT
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_insight_overview import (
    CASES as ECHOING_INSIGHT_OVERVIEW,
)
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_malice import CASES as ECHOING_MALICE
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_merc_enchant import CASES as ECHOING_MERC_ENCHANT
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_sazabi import CASES as ECHOING_SAZABI
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_sling import CASES as ECHOING_SLING
from tests.pricing.knowledge.assessment.item_bank.cases.echoing_starter_armor import CASES as ECHOING_STARTER_ARMOR
from tests.pricing.knowledge.assessment.item_bank.cases.elemental_colossal_recipients import (
    CASES as ELEMENTAL_COLOSSAL_RECIPIENTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.elemental_named_alternatives import (
    CASES as ELEMENTAL_NAMED_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.enchant_demon_machine import CASES as ENCHANT_DEMON_MACHINE
from tests.pricing.knowledge.assessment.item_bank.cases.enchant_raven_claw import CASES as ENCHANT_RAVEN_CLAW
from tests.pricing.knowledge.assessment.item_bank.cases.enchant_socketed_shako import CASES as ENCHANT_SOCKETED_SHAKO
from tests.pricing.knowledge.assessment.item_bank.cases.enchant_widowmaker import CASES as ENCHANT_WIDOWMAKER
from tests.pricing.knowledge.assessment.item_bank.cases.endgame_charges import CASES as ENDGAME_CHARGES
from tests.pricing.knowledge.assessment.item_bank.cases.endgame_gloves import CASES as ENDGAME_GLOVES
from tests.pricing.knowledge.assessment.item_bank.cases.enigma_quality import CASES as ENIGMA_QUALITY
from tests.pricing.knowledge.assessment.item_bank.cases.entropy_locket import CASES as ENTROPY_LOCKET
from tests.pricing.knowledge.assessment.item_bank.cases.eschuta_alternatives import CASES as ESCHUTA_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.ethereal_leveling_requirements import (
    CASES as ETHEREAL_LEVELING_REQUIREMENTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.ethereal_throwing import CASES as ETHEREAL_THROWING
from tests.pricing.knowledge.assessment.item_bank.cases.face_horror_mercenaries import CASES as FACE_HORROR_MERCENARIES
from tests.pricing.knowledge.assessment.item_bank.cases.facet_recipients import CASES as FACET_RECIPIENTS
from tests.pricing.knowledge.assessment.item_bank.cases.facet_shields import CASES as FACET_SHIELDS
from tests.pricing.knowledge.assessment.item_bank.cases.faith_rogues import CASES as FAITH_ROGUES
from tests.pricing.knowledge.assessment.item_bank.cases.farming_accessories import CASES as FARMING_ACCESSORIES
from tests.pricing.knowledge.assessment.item_bank.cases.farming_nagelring import CASES as FARMING_NAGELRING
from tests.pricing.knowledge.assessment.item_bank.cases.fathom_alternatives import CASES as FATHOM_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.fire_ars_diabolos import CASES as FIRE_ARS_DIABOLOS
from tests.pricing.knowledge.assessment.item_bank.cases.fire_blast_companions import CASES as FIRE_BLAST_COMPANIONS
from tests.pricing.knowledge.assessment.item_bank.cases.fire_warlock_books import CASES as FIRE_WARLOCK_BOOKS
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_andariel import CASES as FISSURE_ANDARIEL
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_armor_tail import CASES as FISSURE_ARMOR_TAIL
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_coh import CASES as FISSURE_COH
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_crescent_merc import CASES as FISSURE_CRESCENT_MERC
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_enigma import CASES as FISSURE_ENIGMA
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_ist_monarch import CASES as FISSURE_IST_MONARCH
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_merc_words import CASES as FISSURE_MERC_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_pelts import CASES as FISSURE_PELTS
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_player_words import CASES as FISSURE_PLAYER_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_rockstopper import CASES as FISSURE_ROCKSTOPPER
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_starter_leech import CASES as FISSURE_STARTER_LEECH
from tests.pricing.knowledge.assessment.item_bank.cases.fissure_table_words import CASES as FISSURE_TABLE_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.flayed_mercenaries import CASES as FLAYED_MERCENARIES
from tests.pricing.knowledge.assessment.item_bank.cases.flickering_casters import CASES as FLICKERING_CASTERS
from tests.pricing.knowledge.assessment.item_bank.cases.foh_heavens_light import CASES as FOH_HEAVENS_LIGHT
from tests.pricing.knowledge.assessment.item_bank.cases.foh_lawbringer import CASES as FOH_LAWBRINGER
from tests.pricing.knowledge.assessment.item_bank.cases.foh_topaz import CASES as FOH_TOPAZ
from tests.pricing.knowledge.assessment.item_bank.cases.fortitude_native_ranges import CASES as FORTITUDE_NATIVE_RANGES
from tests.pricing.knowledge.assessment.item_bank.cases.fortitude_variant_roles import CASES as FORTITUDE_VARIANT_ROLES
from tests.pricing.knowledge.assessment.item_bank.cases.gheeds_inventory_variants import (
    CASES as GHEEDS_INVENTORY_VARIANTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.gheeds_table_roles import CASES as GHEEDS_TABLE_ROLES
from tests.pricing.knowledge.assessment.item_bank.cases.giant_skull import CASES as GIANT_SKULL
from tests.pricing.knowledge.assessment.item_bank.cases.gladiator_mercenaries import CASES as GLADIATOR_MERCENARIES
from tests.pricing.knowledge.assessment.item_bank.cases.glove_boot_progression import CASES as GLOVE_BOOT_PROGRESSION
from tests.pricing.knowledge.assessment.item_bank.cases.gold_find_boot_candidates import (
    CASES as GOLD_FIND_BOOT_CANDIDATES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.gold_find_lem_sword import CASES as GOLD_FIND_LEM_SWORD
from tests.pricing.knowledge.assessment.item_bank.cases.gold_find_unbending import CASES as GOLD_FIND_UNBENDING
from tests.pricing.knowledge.assessment.item_bank.cases.goldskin import CASES as GOLDSKIN
from tests.pricing.knowledge.assessment.item_bank.cases.goldwrap_slot_roles import CASES as GOLDWRAP_SLOT_ROLES
from tests.pricing.knowledge.assessment.item_bank.cases.griffon_facets import CASES as GRIFFON_FACETS
from tests.pricing.knowledge.assessment.item_bank.cases.griffon_thunder import CASES as GRIFFON_THUNDER
from tests.pricing.knowledge.assessment.item_bank.cases.guardian_angel_mercenaries import (
    CASES as GUARDIAN_ANGEL_MERCENARIES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.guardian_angel_players import CASES as GUARDIAN_ANGEL_PLAYERS
from tests.pricing.knowledge.assessment.item_bank.cases.guardian_light_helms import CASES as GUARDIAN_LIGHT_HELMS
from tests.pricing.knowledge.assessment.item_bank.cases.guardian_light_recipients import (
    CASES as GUARDIAN_LIGHT_RECIPIENTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.guardian_thunder_recipients import (
    CASES as GUARDIAN_THUNDER_RECIPIENTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.gull_swaps import CASES as GULL_SWAPS
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_astreon import CASES as HAMMER_ASTREON
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_bk_ring import CASES as HAMMER_BK_RING
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_boots import CASES as HAMMER_BOOTS
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_caster_weapons import CASES as HAMMER_CASTER_WEAPONS
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_coh import CASES as HAMMER_COH
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_cure import CASES as HAMMER_CURE
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_defensive_accessories import (
    CASES as HAMMER_DEFENSIVE_ACCESSORIES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_defensive_shield_belt import (
    CASES as HAMMER_DEFENSIVE_SHIELD_BELT,
)
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_farming_accessories import (
    CASES as HAMMER_FARMING_ACCESSORIES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_fortitude import CASES as HAMMER_FORTITUDE
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_gloves_belts import CASES as HAMMER_GLOVES_BELTS
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_guardian_components import (
    CASES as HAMMER_GUARDIAN_COMPONENTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_inventory_charms import CASES as HAMMER_INVENTORY_CHARMS
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_lightning_jewel import CASES as HAMMER_LIGHTNING_JEWEL
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_loot_swaps import CASES as HAMMER_LOOT_SWAPS
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_merc_helms import CASES as HAMMER_MERC_HELMS
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_merc_progression_words import (
    CASES as HAMMER_MERC_PROGRESSION_WORDS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_mf_armor import CASES as HAMMER_MF_ARMOR
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_named_jewelry import CASES as HAMMER_NAMED_JEWELRY
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_principle import CASES as HAMMER_PRINCIPLE
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_progression_words import (
    CASES as HAMMER_PROGRESSION_WORDS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_renewed_sunder import CASES as HAMMER_RENEWED_SUNDER
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_rotw_accessories import CASES as HAMMER_ROTW_ACCESSORIES
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_smoke import CASES as HAMMER_SMOKE
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_starter_amulet import CASES as HAMMER_STARTER_AMULET
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_teleport import CASES as HAMMER_TELEPORT
from tests.pricing.knowledge.assessment.item_bank.cases.hammer_void import CASES as HAMMER_VOID
from tests.pricing.knowledge.assessment.item_bank.cases.hand_blessed_light import CASES as HAND_BLESSED_LIGHT
from tests.pricing.knowledge.assessment.item_bank.cases.harlequin_roles import CASES as HARLEQUIN_ROLES
from tests.pricing.knowledge.assessment.item_bank.cases.herald_alternatives import CASES as HERALD_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.highlord_alternatives import CASES as HIGHLORD_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.holy_bolt_fortitude import CASES as HOLY_BOLT_FORTITUDE
from tests.pricing.knowledge.assessment.item_bank.cases.holy_bolt_hand import CASES as HOLY_BOLT_HAND
from tests.pricing.knowledge.assessment.item_bank.cases.holy_bolt_helm_shield import CASES as HOLY_BOLT_HELM_SHIELD
from tests.pricing.knowledge.assessment.item_bank.cases.holy_bolt_vipermagi import CASES as HOLY_BOLT_VIPERMAGI
from tests.pricing.knowledge.assessment.item_bank.cases.hoto_caster_roles import CASES as HOTO_CASTER
from tests.pricing.knowledge.assessment.item_bank.cases.hoto_variants import CASES as HOTO_VARIANTS
from tests.pricing.knowledge.assessment.item_bank.cases.indestructible_word_alternatives import (
    CASES as INDESTRUCTIBLE_WORD_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.infinity_class import CASES as INFINITY_CLASS
from tests.pricing.knowledge.assessment.item_bank.cases.insight_merc import CASES as INSIGHT_MERC
from tests.pricing.knowledge.assessment.item_bank.cases.javelin_glove_candidates import (
    CASES as JAVELIN_GLOVE_CANDIDATES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.jmod_bases import CASES as JMOD_BASES
from tests.pricing.knowledge.assessment.item_bank.cases.lancers_javelins import CASES as LANCERS_JAVELINS
from tests.pricing.knowledge.assessment.item_bank.cases.late_named_sets import CASES as LATE_NAMED_SETS
from tests.pricing.knowledge.assessment.item_bank.cases.late_unique_weapons import CASES as LATE_UNIQUE_WEAPONS
from tests.pricing.knowledge.assessment.item_bank.cases.leveling_sets import CASES as LEVELING_SETS
from tests.pricing.knowledge.assessment.item_bank.cases.leveling_uniques import CASES as LEVELING_UNIQUES
from tests.pricing.knowledge.assessment.item_bank.cases.lidless_alternatives import CASES as LIDLESS_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.lidless_caster_tables import CASES as LIDLESS_CASTER_TABLES
from tests.pricing.knowledge.assessment.item_bank.cases.lightning_strike_filled_crowns import CASES as LS_FILLED_CROWNS
from tests.pricing.knowledge.assessment.item_bank.cases.lightning_tal_set import CASES as LIGHTNING_TAL_SET
from tests.pricing.knowledge.assessment.item_bank.cases.loose_facets import CASES as LOOSE_FACETS
from tests.pricing.knowledge.assessment.item_bank.cases.lore_fissure import CASES as LORE_FISSURE
from tests.pricing.knowledge.assessment.item_bank.cases.magefist_build_variants import CASES as MAGEFIST_BUILD_VARIANTS
from tests.pricing.knowledge.assessment.item_bank.cases.magefist_caster_tables import CASES as MAGEFIST_CASTER_TABLES
from tests.pricing.knowledge.assessment.item_bank.cases.magefist_remaining import CASES as MAGEFIST_REMAINING
from tests.pricing.knowledge.assessment.item_bank.cases.magic_find_uniques import CASES as MAGIC_FIND_UNIQUES
from tests.pricing.knowledge.assessment.item_bank.cases.mang_song import CASES as MANG_SONG
from tests.pricing.knowledge.assessment.item_bank.cases.maras import CASES as MARAS
from tests.pricing.knowledge.assessment.item_bank.cases.measured_wrath import CASES as MEASURED_WRATH
from tests.pricing.knowledge.assessment.item_bank.cases.melee_utility_baselines import CASES as MELEE_UTILITY_BASELINES
from tests.pricing.knowledge.assessment.item_bank.cases.memory_caster_swaps import CASES as MEMORY_CASTER_SWAPS
from tests.pricing.knowledge.assessment.item_bank.cases.mephisto_vampire_gaze import CASES as MEPHISTO_GAZE
from tests.pricing.knowledge.assessment.item_bank.cases.merc_resistance_armor import CASES as MERC_RESISTANCE_ARMOR
from tests.pricing.knowledge.assessment.item_bank.cases.merc_word_quality import CASES as MERC_WORD_QUALITY
from tests.pricing.knowledge.assessment.item_bank.cases.mercenary_farming_helmets import (
    CASES as MERCENARY_FARMING_HELMETS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.mercenary_ias_fire_jewels import (
    CASES as MERCENARY_IAS_FIRE_JEWELS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.mercenary_named_tiers import CASES as MERCENARY_NAMED_TIERS
from tests.pricing.knowledge.assessment.item_bank.cases.mercenary_progression_weapons import (
    CASES as MERCENARY_PROGRESSION_WEAPONS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.mercenary_resistance_jewels import (
    CASES as MERC_RESISTANCE_JEWELS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.mercenary_unique_tail import CASES as MERCENARY_UNIQUE_TAIL
from tests.pricing.knowledge.assessment.item_bank.cases.metalgrid_alternatives import CASES as METALGRID_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.meteor_crown import CASES as METEOR_CROWN
from tests.pricing.knowledge.assessment.item_bank.cases.mirrored_experimental_words import (
    CASES as MIRRORED_EXPERIMENTAL_WORDS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.mist_strafe import CASES as MIST_STRAFE
from tests.pricing.knowledge.assessment.item_bank.cases.mosers_alternatives import CASES as MOSERS_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.naj_puzzler_swaps import CASES as NAJ_PUZZLER_SWAPS
from tests.pricing.knowledge.assessment.item_bank.cases.named import CASES as NAMED
from tests.pricing.knowledge.assessment.item_bank.cases.named_caster_premiums import CASES as NAMED_CASTER_PREMIUMS
from tests.pricing.knowledge.assessment.item_bank.cases.named_glove_variants import CASES as NAMED_GLOVE_VARIANTS
from tests.pricing.knowledge.assessment.item_bank.cases.named_original_sunders import CASES as NAMED_ORIGINAL_SUNDERS
from tests.pricing.knowledge.assessment.item_bank.cases.named_premium_rolls import CASES as NAMED_PREMIUM_ROLLS
from tests.pricing.knowledge.assessment.item_bank.cases.named_rotw_sunders import CASES as NAMED_ROTW_SUNDERS
from tests.pricing.knowledge.assessment.item_bank.cases.named_socket_preparation import (
    CASES as NAMED_SOCKET_PREPARATION,
)
from tests.pricing.knowledge.assessment.item_bank.cases.native_skill_requirements import (
    CASES as NATIVE_SKILL_REQUIREMENTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.natures_peace_alternatives import (
    CASES as NATURES_PEACE_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.nightwing_alternatives import CASES as NIGHTWING_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.obsession_caster_uses import CASES as OBSESSION_CASTER_USES
from tests.pricing.knowledge.assessment.item_bank.cases.oculus_alternatives import CASES as OCULUS_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.ondal import CASES as ONDAL
from tests.pricing.knowledge.assessment.item_bank.cases.opalvein import CASES as OPALVEIN
from tests.pricing.knowledge.assessment.item_bank.cases.optional_leveling_sets import CASES as OPTIONAL_LEVELING_SETS
from tests.pricing.knowledge.assessment.item_bank.cases.original_sunder_remainder import (
    CASES as ORIGINAL_SUNDER_REMAINDER,
)
from tests.pricing.knowledge.assessment.item_bank.cases.original_sunder_tables import CASES as ORIGINAL_SUNDER_TABLES
from tests.pricing.knowledge.assessment.item_bank.cases.ormus_alternatives import CASES as ORMUS_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.phoenix_casters import CASES as PHOENIX_CASTERS
from tests.pricing.knowledge.assessment.item_bank.cases.plague_doom_casters import CASES as PLAGUE_DOOM_CASTERS
from tests.pricing.knowledge.assessment.item_bank.cases.player_topaz_armor import CASES as PLAYER_TOPAZ_ARMOR
from tests.pricing.knowledge.assessment.item_bank.cases.poison_andariel import CASES as POISON_ANDARIEL
from tests.pricing.knowledge.assessment.item_bank.cases.poison_andariel_socketed import (
    CASES as POISON_ANDARIEL_SOCKETED,
)
from tests.pricing.knowledge.assessment.item_bank.cases.poison_deaths_web import CASES as POISON_DEATHS_WEB
from tests.pricing.knowledge.assessment.item_bank.cases.poison_homunculus import CASES as POISON_HOMUNCULUS
from tests.pricing.knowledge.assessment.item_bank.cases.prebuff import CASES as PREBUFF
from tests.pricing.knowledge.assessment.item_bank.cases.premium_phase_blade_words import (
    CASES as PREMIUM_PHASE_BLADE_WORDS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.premium_unique_charms import CASES as PREMIUM_UNIQUE_CHARMS
from tests.pricing.knowledge.assessment.item_bank.cases.pride_mercenaries import CASES as PRIDE_MERCENARIES
from tests.pricing.knowledge.assessment.item_bank.cases.progression_leveling_sets import (
    CASES as PROGRESSION_LEVELING_SETS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.prose_named_alternatives import (
    CASES as PROSE_NAMED_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.protector_stone_recipients import (
    CASES as PROTECTOR_STONE_RECIPIENTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.qualified_tables import CASES as QUALIFIED_TABLES
from tests.pricing.knowledge.assessment.item_bank.cases.que_hegan_alternatives import CASES as QUE_HEGAN_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.ranged_unique_baselines import CASES as RANGED_UNIQUE_BASELINES
from tests.pricing.knowledge.assessment.item_bank.cases.raven import CASES as RAVEN
from tests.pricing.knowledge.assessment.item_bank.cases.ravenlore import CASES as RAVENLORE
from tests.pricing.knowledge.assessment.item_bank.cases.razortail_alternatives import CASES as RAZORTAIL_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.reaper_mercenary_alternatives import (
    CASES as REAPER_MERCENARY_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.remaining_named_sets import CASES as REMAINING_NAMED_SETS
from tests.pricing.knowledge.assessment.item_bank.cases.remaining_word_quality import CASES as REMAINING_WORD_QUALITY
from tests.pricing.knowledge.assessment.item_bank.cases.renewed_sunder_builds import CASES as RENEWED_SUNDER_BUILDS
from tests.pricing.knowledge.assessment.item_bank.cases.rhyme_class_shields import CASES as RHYME_CLASS_SHIELDS
from tests.pricing.knowledge.assessment.item_bank.cases.rockfleece_mercenaries import CASES as ROCKFLEECE_MERCENARIES
from tests.pricing.knowledge.assessment.item_bank.cases.rockstopper_mercenaries import CASES as ROCKSTOPPER_MERCENARIES
from tests.pricing.knowledge.assessment.item_bank.cases.rotw_named_baselines import CASES as ROTW_NAMED_BASELINES
from tests.pricing.knowledge.assessment.item_bank.cases.sandstorm_caster_alternatives import (
    CASES as SANDSTORM_CASTER_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.scalper import CASES as SCALPER
from tests.pricing.knowledge.assessment.item_bank.cases.seasonal_named_versions import CASES as SEASONAL_NAMED_VERSIONS
from tests.pricing.knowledge.assessment.item_bank.cases.shadow_dancer import CASES as SHADOW_DANCER
from tests.pricing.knowledge.assessment.item_bank.cases.shaftstop_mercenaries import CASES as SHAFTSTOP_MERCENARIES
from tests.pricing.knowledge.assessment.item_bank.cases.silkweave_alternatives import CASES as SILKWEAVE_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.skill_charge_combinations import (
    CASES as SKILL_CHARGE_COMBINATIONS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.skill_combination_candidates import (
    CASES as SKILL_COMBINATION_CANDIDATES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.skullder_alternatives import CASES as SKULLDER_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.smite_crown import CASES as SMITE_CROWN
from tests.pricing.knowledge.assessment.item_bank.cases.smite_shared_treachery import CASES as SMITE_SHARED_TREACHERY
from tests.pricing.knowledge.assessment.item_bank.cases.socket_materials import CASES as SOCKET_MATERIALS
from tests.pricing.knowledge.assessment.item_bank.cases.socketed_leveling_shields import (
    CASES as SOCKETED_LEVELING_SHIELDS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.sorceress_amulet_candidates import (
    CASES as SORCERESS_AMULET_CANDIDATES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.sorceress_cure_variants import CASES as SORCERESS_CURE_VARIANTS
from tests.pricing.knowledge.assessment.item_bank.cases.sorceress_endgame_rings import CASES as SORCERESS_ENDGAME_RINGS
from tests.pricing.knowledge.assessment.item_bank.cases.sorceress_mf_gloves import CASES as SORCERESS_MF_GLOVES
from tests.pricing.knowledge.assessment.item_bank.cases.specialist_skill_rolls import CASES as SPECIALIST_SKILL_ROLLS
from tests.pricing.knowledge.assessment.item_bank.cases.spirit_caster_roles import CASES as SPIRIT_CASTER
from tests.pricing.knowledge.assessment.item_bank.cases.spirit_endgame import CASES as SPIRIT_ENDGAME
from tests.pricing.knowledge.assessment.item_bank.cases.standalone_set_accessories import (
    CASES as STANDALONE_SET_ACCESSORIES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.stone_of_jordan_roles import CASES as STONE_OF_JORDAN_ROLES
from tests.pricing.knowledge.assessment.item_bank.cases.strafe_nagelring import CASES as STRAFE_NAGELRING
from tests.pricing.knowledge.assessment.item_bank.cases.string_ears_alternatives import (
    CASES as STRING_EARS_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.suicide_branch import CASES as SUICIDE_BRANCH
from tests.pricing.knowledge.assessment.item_bank.cases.summoner_andariel import CASES as SUMMONER_ANDARIEL
from tests.pricing.knowledge.assessment.item_bank.cases.supplies import CASES as SUPPLIES
from tests.pricing.knowledge.assessment.item_bank.cases.survival_leveling_sets import CASES as SURVIVAL_LEVELING_SETS
from tests.pricing.knowledge.assessment.item_bank.cases.tal_armor_amulet import CASES as TAL_ARMOR_AMULET
from tests.pricing.knowledge.assessment.item_bank.cases.tal_belt_orb import CASES as TAL_BELT_ORB
from tests.pricing.knowledge.assessment.item_bank.cases.tal_caster import CASES as TAL_CASTER
from tests.pricing.knowledge.assessment.item_bank.cases.tal_merc import CASES as TAL_MERC
from tests.pricing.knowledge.assessment.item_bank.cases.teleport_amulet_alternatives import (
    CASES as TELEPORT_AMULET_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.throw_arreat import CASES as THROW_ARREAT
from tests.pricing.knowledge.assessment.item_bank.cases.throwing_sustain import CASES as THROWING_SUSTAIN
from tests.pricing.knowledge.assessment.item_bank.cases.thundergod_alternatives import CASES as THUNDERGOD_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.tomb_reaver import CASES as TOMB_REAVER
from tests.pricing.knowledge.assessment.item_bank.cases.torch_caster_tables import CASES as TORCH_CASTER_TABLES
from tests.pricing.knowledge.assessment.item_bank.cases.torch_variants import CASES as TORCH_VARIANTS
from tests.pricing.knowledge.assessment.item_bank.cases.trang_caster_upgrades import CASES as TRANG_CASTER_UPGRADES
from tests.pricing.knowledge.assessment.item_bank.cases.treachery_endgame_mercs import CASES as TREACHERY_ENDGAME_MERCS
from tests.pricing.knowledge.assessment.item_bank.cases.treachery_shared_zeal import CASES as TREACHERY_SHARED_ZEAL
from tests.pricing.knowledge.assessment.item_bank.cases.trek_alternatives import CASES as TREK_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.tri_resist_boot_candidates import (
    CASES as TRI_RESIST_BOOT_CANDIDATES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.tribrid_raven import CASES as TRIBRID_RAVEN
from tests.pricing.knowledge.assessment.item_bank.cases.uber_charged_wands import CASES as UBER_CHARGED_WANDS
from tests.pricing.knowledge.assessment.item_bank.cases.unique_jewelry_progression import (
    CASES as UNIQUE_JEWELRY_PROGRESSION,
)
from tests.pricing.knowledge.assessment.item_bank.cases.valuable_named_alternatives import (
    CASES as VALUABLE_NAMED_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.valuable_skillers import CASES as VALUABLE_SKILLERS
from tests.pricing.knowledge.assessment.item_bank.cases.valuable_small_charms import CASES as VALUABLE_SMALL_CHARMS
from tests.pricing.knowledge.assessment.item_bank.cases.vampire_gaze_native import CASES as VAMPIRE_GAZE_NATIVE
from tests.pricing.knowledge.assessment.item_bank.cases.vampire_gaze_setups import CASES as VAMPIRE_GAZE_SETUPS
from tests.pricing.knowledge.assessment.item_bank.cases.venom_ward_mercenaries import CASES as VENOM_WARD_MERCENARIES
from tests.pricing.knowledge.assessment.item_bank.cases.verdungo_alternatives import CASES as VERDUNGO_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.vipermagi_caster_alternatives import (
    CASES as VIPERMAGI_CASTER_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.vipermagi_payloads import CASES as VIPERMAGI_PAYLOADS
from tests.pricing.knowledge.assessment.item_bank.cases.vipermagi_variant_components import (
    CASES as VIPERMAGI_VARIANT_COMPONENTS,
)
from tests.pricing.knowledge.assessment.item_bank.cases.war_traveler_casters import CASES as WAR_TRAVELER_CASTERS
from tests.pricing.knowledge.assessment.item_bank.cases.warlock_socketed_helms import CASES as WARLOCK_SOCKETED_HELMS
from tests.pricing.knowledge.assessment.item_bank.cases.warlord_leveling import CASES as WARLORD_LEVELING
from tests.pricing.knowledge.assessment.item_bank.cases.waterwalk_alternatives import CASES as WATERWALK_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.wisp_alternatives import CASES as WISP_ALTERNATIVES
from tests.pricing.knowledge.assessment.item_bank.cases.witchwild_strafe import CASES as WITCHWILD_STRAFE
from tests.pricing.knowledge.assessment.item_bank.cases.wizardspike_roles import CASES as WIZARDSPIKE_ROLES
from tests.pricing.knowledge.assessment.item_bank.cases.wraithstep import CASES as WRAITHSTEP
from tests.pricing.knowledge.assessment.item_bank.cases.zeal import CASES as ZEAL
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_affixed_accessories import (
    CASES as ZEAL_AFFIXED_ACCESSORIES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_affixed_helms import CASES as ZEAL_AFFIXED_HELMS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_armor_words import CASES as ZEAL_ARMOR_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_axes import CASES as ZEAL_AXES
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_blood_ring import CASES as ZEAL_BLOOD_RING
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_budget_words import CASES as ZEAL_BUDGET_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_caster_amulets import CASES as ZEAL_CASTER_AMULETS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_charms import CASES as ZEAL_CHARMS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_combat_words import CASES as ZEAL_COMBAT_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_death import CASES as ZEAL_DEATH
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_dual_lawbringer import CASES as ZEAL_DUAL_LAWBRINGER
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_early_merc import CASES as ZEAL_EARLY_MERC
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_existing_alternatives import (
    CASES as ZEAL_EXISTING_ALTERNATIVES,
)
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_gloves import CASES as ZEAL_GLOVES
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_helmets import CASES as ZEAL_HELMETS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_insight import CASES as ZEAL_INSIGHT
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_jewelry import CASES as ZEAL_JEWELRY
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_lawbringer import CASES as ZEAL_LAWBRINGER
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_maiming import CASES as ZEAL_MAIMING
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_melee import CASES as ZEAL_MELEE
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_merc_named import CASES as ZEAL_MERC_NAMED
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_merc_tail import CASES as ZEAL_MERC_TAIL
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_merc_um import CASES as ZEAL_MERC_UM
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_merc_words import CASES as ZEAL_MERC_WORDS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_named_gloves import CASES as ZEAL_NAMED_GLOVES
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_named_remainder import CASES as ZEAL_NAMED_REMAINDER
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_rare_weapon import CASES as ZEAL_RARE_WEAPON
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_reapers import CASES as ZEAL_REAPERS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_resistance_charms import CASES as ZEAL_RESISTANCE_CHARMS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_sets import CASES as ZEAL_SETS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_shields import CASES as ZEAL_SHIELDS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_socketed import CASES as ZEAL_SOCKETED
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_specialist_shields import CASES as ZEAL_SPECIALIST_SHIELDS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_starter_merc import CASES as ZEAL_STARTER_MERC
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_swaps import CASES as ZEAL_SWAPS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_tal_helm import CASES as ZEAL_TAL_HELM
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_unique_charms import CASES as ZEAL_UNIQUE_CHARMS
from tests.pricing.knowledge.assessment.item_bank.cases.zeal_utility_belts import CASES as ZEAL_UTILITY_BELTS


CASES = (
    *FISSURE_CRESCENT_MERC,
    *FOH_LAWBRINGER,
    *DURESS_ENDGAME_MERC,
    *DURESS_GEAR_ALTERNATIVES,
    *CURE_GEAR_ALTERNATIVES,
    *BLACK_ATTACK_MODES,
    *DRAGON_TALON_CBF,
    *DRAGON_TALON_GUILLAUME,
    *SHADOW_DANCER,
    *GIANT_SKULL,
    *ATMA_ATTACK_AMULET,
    *MIST_STRAFE,
    *PLAGUE_DOOM_CASTERS,
    *LANCERS_JAVELINS,
    *INDESTRUCTIBLE_WORD_ALTERNATIVES,
    *BOTD_MERCENARIES,
    *PRIDE_MERCENARIES,
    *DREAM_FIRE_WORDS,
    *HAMMER_LIGHTNING_JEWEL,
    *BEAST_SUMMONER,
    *PREMIUM_PHASE_BLADE_WORDS,
    *PHOENIX_CASTERS,
    *FAITH_ROGUES,
    *SKILL_CHARGE_COMBINATIONS,
    *CHARGED_WEAPON_ALTERNATIVES,
    *VALUABLE_NAMED_ALTERNATIVES,
    *SEASONAL_NAMED_VERSIONS,
    *POISON_DEATHS_WEB,
    *CASTER_CROWN_AGES,
    *CASTER_ENIGMA_GEAR,
    *RENEWED_SUNDER_BUILDS,
    *UBER_CHARGED_WANDS,
    *VALUABLE_SMALL_CHARMS,
    *VALUABLE_SKILLERS,
    *JMOD_BASES,
    *MERCENARY_IAS_FIRE_JEWELS,
    *BLIZZARD_RARE_RINGS,
    *SUICIDE_BRANCH,
    *FIRE_ARS_DIABOLOS,
    *DREAM_PAIR,
    *MOSERS_ALTERNATIVES,
    *NATURES_PEACE_ALTERNATIVES,
    *METALGRID_ALTERNATIVES,
    *CATS_EYE_ALTERNATIVES,
    *STRING_EARS_ALTERNATIVES,
    *THUNDERGOD_ALTERNATIVES,
    *LIDLESS_CASTER_TABLES,
    *LIDLESS_ALTERNATIVES,
    *MAGEFIST_BUILD_VARIANTS,
    *MAGEFIST_CASTER_TABLES,
    *MAGEFIST_REMAINING,
    *HIGHLORD_ALTERNATIVES,
    *WISP_ALTERNATIVES,
    *DWARF_STAR_ALTERNATIVES,
    *CHANCE_GUARDS_ALTERNATIVES,
    *VERDUNGO_ALTERNATIVES,
    *TREK_ALTERNATIVES,
    *BK_UTILITY_ALTERNATIVES,
    *LIGHTNING_TAL_SET,
    *TAL_BELT_ORB,
    *TAL_ARMOR_AMULET,
    *TORCH_VARIANTS,
    *TORCH_CASTER_TABLES,
    *ANNIHILUS_VARIANTS,
    *ANNIHILUS_TABLES,
    *ALI_BABA_LOOT,
    *GULL_SWAPS,
    *SKULLDER_ALTERNATIVES,
    *QUE_HEGAN_ALTERNATIVES,
    *ORMUS_ALTERNATIVES,
    *THROWING_SUSTAIN,
    *SCALPER,
    *ETHEREAL_THROWING,
    *HAMMER_PRINCIPLE,
    *HAMMER_VOID,
    *HAMMER_FORTITUDE,
    *HAMMER_COH,
    *BLIZZARD_FORTITUDE,
    *BLIZZARD_STARTER_ACCESSORIES,
    *BLIZZARD_VIPERMAGI,
    *BLIZZARD_SKULLDER,
    *BLIZZARD_MF_BOOTS,
    *BLIZZARD_BOOTS,
    *BLIZZARD_ACCESSORIES,
    *BLIZZARD_MAGIC_CHARMS,
    *BLIZZARD_INVENTORY_CHARMS,
    *HAMMER_PROGRESSION_WORDS,
    *HAMMER_STARTER_AMULET,
    *HAMMER_ASTREON,
    *HAMMER_BK_RING,
    *HAMMER_ROTW_ACCESSORIES,
    *HAMMER_DEFENSIVE_SHIELD_BELT,
    *HAMMER_LOOT_SWAPS,
    *HAMMER_NAMED_JEWELRY,
    *HAMMER_GLOVES_BELTS,
    *HAMMER_CASTER_WEAPONS,
    *HAMMER_MF_ARMOR,
    *HAMMER_TELEPORT,
    *HAMMER_BOOTS,
    *HAMMER_DEFENSIVE_ACCESSORIES,
    *HAMMER_FARMING_ACCESSORIES,
    *HAMMER_GUARDIAN_COMPONENTS,
    *HAMMER_RENEWED_SUNDER,
    *HAMMER_MERC_HELMS,
    *HAMMER_CURE,
    *HAMMER_SMOKE,
    *HAMMER_MERC_PROGRESSION_WORDS,
    *HAMMER_INVENTORY_CHARMS,
    *BERSERK_INVENTORY_CHARMS,
    *BERSERK_MF_EQUIPMENT,
    *BERSERK_LEGACY_TELEPORT,
    *BERSERK_GUARDIAN_COMPONENTS,
    *BERSERK_CIRCLET_TAIL,
    *BERSERK_STARTER_SIGONS,
    *BERSERK_MERC_WEAPON_TAIL,
    *BERSERK_UTILITY_WORDS,
    *BERSERK_SMOKE,
    *BERSERK_RENEWED_SUNDER,
    *BERSERK_MF_ARMOR,
    *BERSERK_DEFENSIVE_ACCESSORIES,
    *BERSERK_STANDALONE_SETS,
    *BERSERK_UNBENDING,
    *BERSERK_GRIEF_OATH,
    *BERSERK_UNIQUE_AMULETS,
    *BERSERK_BOOTS,
    *BERSERK_BOTD_MERC,
    *BERSERK_CURE,
    *BERSERK_MERC_PROGRESSION_WORDS,
    *BERSERK_TELEPORT_ALTERNATIVES,
    *BERSERK_FARMING_ACCESSORIES,
    *BERSERK_HELM_ALTERNATIVES,
    *BERSERK_NATIVE_MERC_WORDS,
    *ABYSS_STARTER_TAIL,
    *ABYSS_RENEWED_SUNDER,
    *ABYSS_CASTER_UNIQUE_ALTERNATIVES,
    *ABYSS_GUARDIAN_COMPONENTS,
    *ORIGINAL_SUNDER_REMAINDER,
    *ABYSS_MERC_PROGRESSION_WORDS,
    *ABYSS_CASTER_WORD_ALTERNATIVES,
    *ABYSS_STAFF_ALTERNATIVES,
    *ABYSS_LOOT_SHIELD_ALTERNATIVES,
    *ABYSS_TELEPORT_ALTERNATIVES,
    *ABYSS_PROGRESSION_WORDS,
    *ABYSS_MF_FORTITUDE,
    *ABYSS_MF_SHAKO,
    *ABYSS_INVENTORY_CHARMS,
    *ABYSS_AFFIXED_CANDIDATES,
    *CTA_PREBUFF_VARIANTS,
    *SMITE_CROWN,
    *METEOR_CROWN,
    *ANDARIEL_FIRE_VARIANTS,
    *ANDARIEL_DAMAGE_VARIANTS,
    *GUARDIAN_ANGEL_MERCENARIES,
    *MERCENARY_UNIQUE_TAIL,
    *REAPER_MERCENARY_ALTERNATIVES,
    *MERCENARY_FARMING_HELMETS,
    *VENOM_WARD_MERCENARIES,
    *GOLDSKIN,
    *GLADIATOR_MERCENARIES,
    *FACE_HORROR_MERCENARIES,
    *FLAYED_MERCENARIES,
    *FISSURE_ANDARIEL,
    *ANDARIEL_NATIVE_VARIANTS,
    *ROCKFLEECE_MERCENARIES,
    *ROCKSTOPPER_MERCENARIES,
    *VAMPIRE_GAZE_NATIVE,
    *SHAFTSTOP_MERCENARIES,
    *VAMPIRE_GAZE_SETUPS,
    *FIRE_BLAST_COMPANIONS,
    *FARMING_NAGELRING,
    *STRAFE_NAGELRING,
    *MEPHISTO_GAZE,
    *SUMMONER_ANDARIEL,
    *CASTER_SOCKETED_NAMED,
    *GRIFFON_THUNDER,
    *GRIFFON_FACETS,
    *FORTITUDE_VARIANT_ROLES,
    *FORTITUDE_NATIVE_RANGES,
    *COH_CASTER_ROLES,
    *COH_VARIANT_ROLES,
    *HERALD_ALTERNATIVES,
    *DRACUL_ALTERNATIVES,
    *POISON_ANDARIEL_SOCKETED,
    *POISON_ANDARIEL,
    *NAMED_CASTER_PREMIUMS,
    *NAMED_PREMIUM_ROLLS,
    *TRI_RESIST_BOOT_CANDIDATES,
    *GOLD_FIND_BOOT_CANDIDATES,
    *JAVELIN_GLOVE_CANDIDATES,
    *CRAFTED_GLOVE_CANDIDATES,
    *SORCERESS_AMULET_CANDIDATES,
    *FARMING_ACCESSORIES,
    *TELEPORT_AMULET_ALTERNATIVES,
    *RAZORTAIL_ALTERNATIVES,
    *COMBAT_BOOT_BELT_ALTERNATIVES,
    *STANDALONE_SET_ACCESSORIES,
    *ALDUR_BOOT_ALTERNATIVES,
    *WATERWALK_ALTERNATIVES,
    *SILKWEAVE_ALTERNATIVES,
    *SANDSTORM_CASTER_ALTERNATIVES,
    *CASTER_MAGIC_FIND_ACCESSORIES,
    *CASTER_RING_ALTERNATIVES,
    *DEFENSIVE_CASTER_BELTS,
    *ARACHNID_CASTER_ALTERNATIVES,
    *STONE_OF_JORDAN_ROLES,
    *HARLEQUIN_ROLES,
    *NIGHTWING_ALTERNATIVES,
    *FATHOM_ALTERNATIVES,
    *WIZARDSPIKE_ROLES,
    *OCULUS_ALTERNATIVES,
    *ESCHUTA_ALTERNATIVES,
    *WAR_TRAVELER_CASTERS,
    *GHEEDS_TABLE_ROLES,
    *GHEEDS_INVENTORY_VARIANTS,
    *GOLDWRAP_SLOT_ROLES,
    *CIRCLET_CANDIDATES,
    *SKILL_COMBINATION_CANDIDATES,
    *NAMED_ROTW_SUNDERS,
    *REMAINING_NAMED_SETS,
    *NAMED_ORIGINAL_SUNDERS,
    *PREMIUM_UNIQUE_CHARMS,
    *SPECIALIST_SKILL_ROLLS,
    *LOOSE_FACETS,
    *SUPPLIES,
    *SOCKET_MATERIALS,
    *SMITE_SHARED_TREACHERY,
    *ECHOING_FADE,
    *ECHOING_SAZABI,
    *ABYSS_GRIMOIRES,
    *ABYSS_MAGIC_CHARMS,
    *ABYSS_UNIQUE_CHARMS,
    *ABYSS_RINGS,
    *TRANG_CASTER_UPGRADES,
    *ENDGAME_GLOVES,
    *FOH_HEAVENS_LIGHT,
    *GOLD_FIND_UNBENDING,
    *MIRRORED_EXPERIMENTAL_WORDS,
    *ARM_KING_LEORIC,
    *POISON_HOMUNCULUS,
    *CASTER_STORMSHIELD,
    *CASTER_FROSTBURN,
    *THROW_ARREAT,
    *ENCHANT_DEMON_MACHINE,
    *ENCHANT_RAVEN_CLAW,
    *ENCHANT_WIDOWMAKER,
    *HAND_BLESSED_LIGHT,
    *BLOODPACT_SHARD,
    *ENTROPY_LOCKET,
    *MEASURED_WRATH,
    *OPALVEIN,
    *TOMB_REAVER,
    *MANG_SONG,
    *GUARDIAN_ANGEL_PLAYERS,
    *ONDAL,
    *FIRE_WARLOCK_BOOKS,
    *WRAITHSTEP,
    *GOLD_FIND_LEM_SWORD,
    *WITCHWILD_STRAFE,
    *FISSURE_PELTS,
    *ENDGAME_CHARGES,
    *SORCERESS_ENDGAME_RINGS,
    *ABYSS_AMULETS,
    *ABYSS_BOOTS,
    *ABYSS_EMBEDDED_GLOVES_BELTS,
    *ABYSS_NAMED_GLOVE_BELT,
    *ABYSS_EXISTING_GLOVES_BELTS,
    *ABYSS_REMAINING_ARMORS,
    *ABYSS_ANDARIEL,
    *ABYSS_MERC_UM,
    *ABYSS_EARLY_NAMED,
    *ABYSS_MERC_WORDS,
    *ABYSS_CASTER_WEAPONS,
    *ABYSS_PLAYER_WORDS,
    *ABYSS_NAMED_SWAPS,
    *ABYSS_UTILITY_SWAPS,
    *ABYSS_VOID,
    *ABYSS_PLANNER_DAGGERS,
    *ABYSS_HELMETS,
    *ABYSS_EMBEDDED_HELMETS,
    *ABYSS_EMBEDDED_ARMORS,
    *ABYSS_EXISTING_ARMORS,
    *ABYSS_DIADEM_PAYLOADS,
    *ABYSS_RARE_KRIS,
    *ABYSS_QUALITY_BOUNDARIES,
    *ABYSS_TABLE_DAGGERS,
    *ABYSS_CHARGED_DAGGER,
    *ABYSS_INSIGHT,
    *ABYSS_MERC_NAMED,
    *ABYSS_MERC_REMAINING,
    *ABYSS_PLAYER_INSIGHT,
    *CONSUMABLES,
    *ZEAL_MERC_TAIL,
    *ZEAL_MERC_UM,
    *ZEAL_MERC_NAMED,
    *ZEAL_MERC_WORDS,
    *ZEAL_EARLY_MERC,
    *ZEAL_REAPERS,
    *ZEAL_UNIQUE_CHARMS,
    *ANGELIC,
    *CHARM_TRADE,
    *TAL_CASTER,
    *TAL_MERC,
    *RAVEN,
    *MARAS,
    *ZEAL,
    *ZEAL_RARE_WEAPON,
    *ZEAL_BLOOD_RING,
    *ZEAL_CHARMS,
    *ZEAL_MAIMING,
    *ZEAL_RESISTANCE_CHARMS,
    *ZEAL_CASTER_AMULETS,
    *ZEAL_AFFIXED_ACCESSORIES,
    *ZEAL_NAMED_GLOVES,
    *ZEAL_SPECIALIST_SHIELDS,
    *ZEAL_SOCKETED,
    *ZEAL_AFFIXED_HELMS,
    *ZEAL_TAL_HELM,
    *ZEAL_HELMETS,
    *ZEAL_DEATH,
    *ZEAL_SETS,
    *PREBUFF,
    *ECHOING_SLING,
    *ECHOING_MALICE,
    *ELEMENTAL_NAMED_ALTERNATIVES,
    *ECHOING_INSIGHT,
    *ECHOING_CURE,
    *ECHOING_ENIGMA,
    *ENIGMA_QUALITY,
    *MERC_WORD_QUALITY,
    *REMAINING_WORD_QUALITY,
    *INFINITY_CLASS,
    *ORIGINAL_SUNDER_TABLES,
    *QUALIFIED_TABLES,
    *FISSURE_PLAYER_WORDS,
    *FISSURE_TABLE_WORDS,
    *FLICKERING_CASTERS,
    *FISSURE_MERC_WORDS,
    *FISSURE_COH,
    *FISSURE_ENIGMA,
    *PLAYER_TOPAZ_ARMOR,
    *FOH_TOPAZ,
    *FACET_SHIELDS,
    *FACET_RECIPIENTS,
    *PROTECTOR_STONE_RECIPIENTS,
    *GUARDIAN_THUNDER_RECIPIENTS,
    *GUARDIAN_LIGHT_RECIPIENTS,
    *ELEMENTAL_COLOSSAL_RECIPIENTS,
    *CTA_CASTER_SWAPS,
    *MEMORY_CASTER_SWAPS,
    *OBSESSION_CASTER_USES,
    *NAJ_PUZZLER_SWAPS,
    *TREACHERY_ENDGAME_MERCS,
    *TREACHERY_SHARED_ZEAL,
    *FISSURE_IST_MONARCH,
    *DOUBLE_THROW_FILLED_DIADEMS,
    *LS_FILLED_CROWNS,
    *BERSERK_STARTER_TOPAZ,
    *MERC_RESISTANCE_ARMOR,
    *FISSURE_ROCKSTOPPER,
    *FISSURE_STARTER_LEECH,
    *FISSURE_ARMOR_TAIL,
    *DRAGON_TALON_BUDGET,
    *ECHOING_CURE_PROGRESSION,
    *ECHOING_INSIGHT_OVERVIEW,
    *ECHOING_STARTER_ARMOR,
    *ECHOING_HELLWARDEN,
    *ENCHANT_SOCKETED_SHAKO,
    *ECHOING_MERC_ENCHANT,
    *NAMED,
    *OPTIONAL_LEVELING_SETS,
    *ARCTIC_LEVELING,
    *CASTER_UNIQUE_BASELINES,
    *CASTER_SUPPORT_UNIQUES,
    *UNIQUE_JEWELRY_PROGRESSION,
    *ATTACK_SURVIVAL_BASELINES,
    *ROTW_NAMED_BASELINES,
    *CASTER_UTILITY_UNIQUES,
    *LATE_UNIQUE_WEAPONS,
    *MELEE_UTILITY_BASELINES,
    *MAGIC_FIND_UNIQUES,
    *GLOVE_BOOT_PROGRESSION,
    *ARMOR_PROGRESSION_BASELINES,
    *MERCENARY_PROGRESSION_WEAPONS,
    *RANGED_UNIQUE_BASELINES,
    *CLASS_UNIQUE_PROGRESSION,
    *CLASS_WEAPON_BASELINES,
    *NATIVE_SKILL_REQUIREMENTS,
    *EARLY_SURVIVAL_UNIQUES,
    *DEFENSIVE_UNIQUE_BASELINES,
    *ETHEREAL_LEVELING_REQUIREMENTS,
    *SOCKETED_LEVELING_SHIELDS,
    *ATTACK_UNIQUE_BASELINES,
    *EARLY_UNIQUE_BASELINES,
    *WARLORD_LEVELING,
    *LATE_NAMED_SETS,
    *PROGRESSION_LEVELING_SETS,
    *SURVIVAL_LEVELING_SETS,
    *CIVERB_CLEGLAW_LEVELING,
    *NAMED_GLOVE_VARIANTS,
    *HOTO_VARIANTS,
    *SPIRIT_ENDGAME,
    *SPIRIT_CASTER,
    *HOTO_CASTER,
    *HOLY_BOLT_HAND,
    *HOLY_BOLT_FORTITUDE,
    *CHAOS_ENIGMA,
    *CHAOS_GLOVES,
    *GUARDIAN_LIGHT_HELMS,
    *WARLOCK_SOCKETED_HELMS,
    *TRIBRID_RAVEN,
    *PROSE_NAMED_ALTERNATIVES,
    *HOLY_BOLT_HELM_SHIELD,
    *HOLY_BOLT_VIPERMAGI,
    *VIPERMAGI_CASTER_ALTERNATIVES,
    *VIPERMAGI_PAYLOADS,
    *VIPERMAGI_VARIANT_COMPONENTS,
    *RAVENLORE,
    *LORE_FISSURE,
    *RHYME_CLASS_SHIELDS,
    *MERC_RESISTANCE_JEWELS,
    *MERCENARY_NAMED_TIERS,
    *SORCERESS_MF_GLOVES,
    *SORCERESS_CURE_VARIANTS,
    *LEVELING_SETS,
    *LEVELING_UNIQUES,
    *NAMED_SOCKET_PREPARATION,
    *ZEAL_MELEE,
    *ZEAL_JEWELRY,
    *ZEAL_GLOVES,
    *ZEAL_UTILITY_BELTS,
    *ZEAL_LAWBRINGER,
    *ZEAL_STARTER_MERC,
    *ZEAL_INSIGHT,
    *INSIGHT_MERC,
    *ZEAL_DUAL_LAWBRINGER,
    *ZEAL_COMBAT_WORDS,
    *ZEAL_AXES,
    *ZEAL_BUDGET_WORDS,
    *ZEAL_SHIELDS,
    *ZEAL_SWAPS,
    *ZEAL_ARMOR_WORDS,
    *ZEAL_NAMED_REMAINDER,
    *ZEAL_EXISTING_ALTERNATIVES,
)
