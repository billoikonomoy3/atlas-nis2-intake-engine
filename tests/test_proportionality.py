"""Proportionality (heuristic) — every expected value hand-recomputed from the weights.

Weights (ruleset heuristic_weights): size{large25,medium14,below_medium6},
class{essential25,important12}, annex{I15,II8,none0}, xborder{systemic15,
sole_national15,cross_border9,none0}, supply{high5,moderate3,low0}, special_entity5,
footprint(g,e)=max(G,E) with G:>=7->10,>=4->7,>=2->4 and E:>=11->10,>=5->7,>=2->4.
Floors: essential & <60 -> 60; systemic/sole_national & <80 -> 80.
"""

from __future__ import annotations

from atlas.engine.proportionality import proportionality, tier_for


def test_national_tso_scores_critical_unfloored():
    p = proportionality(size_band="large", entity_class="essential", sector_annex="I",
                        cross_border_systemic="systemic", n_geographies=8, n_entities=12,
                        special_entity=False, supply_chain="high")
    # 25+25+15+15+10+0+5 = 95
    assert p.points == {"size_band": 25, "entity_class": 25, "sector_annex": 15,
                        "cross_border_systemic": 15, "footprint": 10, "special_entity": 0,
                        "supply_chain": 5}
    assert p.raw_score == 95 and p.score == 95
    assert p.tier == "Critical"
    assert p.floors_applied == []


def test_essential_floor_raises_to_enhanced():
    p = proportionality(size_band="below_medium", entity_class="essential", sector_annex="I")
    # 6+25+15 = 46 -> essential floor -> 60
    assert p.raw_score == 46
    assert p.score == 60
    assert p.tier == "Enhanced"
    assert any("essential" in f for f in p.floors_applied)


def test_systemic_floor_raises_to_critical():
    p = proportionality(size_band="medium", entity_class="important", sector_annex="II",
                        cross_border_systemic="sole_national")
    # 14+12+8+15 = 49 -> systemic/sole_national floor -> 80
    assert p.raw_score == 49
    assert p.score == 80
    assert p.tier == "Critical"
    assert any("systemic" in f or "sole-national" in f for f in p.floors_applied)


def test_important_medium_is_standard_no_floor():
    p = proportionality(size_band="medium", entity_class="important", sector_annex="I")
    # 14+12+15 = 41
    assert p.score == 41
    assert p.tier == "Standard"
    assert p.floors_applied == []


def test_footprint_takes_max_of_geographies_and_entities():
    p = proportionality(size_band="below_medium", entity_class="important", sector_annex="I",
                        n_geographies=4, n_entities=1, supply_chain="moderate")
    # footprint = max(G(4)=7, E(1)=0) = 7 ; 6+12+15+0+7+0+3 = 43
    assert p.points["footprint"] == 7
    assert p.score == 43 and p.tier == "Standard"


def test_tier_boundaries():
    assert tier_for(39)[0] == "Foundational"
    assert tier_for(40)[0] == "Standard"
    assert tier_for(59)[0] == "Standard"
    assert tier_for(60)[0] == "Enhanced"
    assert tier_for(79)[0] == "Enhanced"
    assert tier_for(80)[0] == "Critical"
    assert tier_for(100)[0] == "Critical"
