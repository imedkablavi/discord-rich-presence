import json
from pathlib import Path

import pytest

from detectors.gaming import GamingDetector
from popular_games import PopularGameCatalog, load_popular_catalog, normalize_title


def test_bundled_catalog_has_at_least_300_unique_titles():
    catalog = PopularGameCatalog()
    assert len(catalog.games) >= 300
    normalized = [normalize_title(title) for title in catalog.games]
    assert len(normalized) == len(set(normalized))


def test_bundled_catalog_covers_major_launcher_ecosystems():
    catalog = PopularGameCatalog()
    expected = (
        'Counter-Strike 2',
        'Grand Theft Auto V',
        'ELDEN RING',
        'Fortnite',
        'VALORANT',
        'League of Legends',
        'Minecraft',
        'World of Warcraft',
        'Diablo IV',
        'Rocket League',
        'Genshin Impact',
        'Roblox',
        'PEAK',
        'Deadlock',
        'EA SPORTS FC 26',
        'Grand Theft Auto V Enhanced',
        'FiveM',
        'Hearts of Iron IV',
    )
    assert all(catalog.contains(title) for title in expected)


def test_catalog_membership_is_case_and_whitespace_insensitive():
    catalog = PopularGameCatalog()
    assert catalog.contains('  counter-strike   2  ')
    assert catalog.contains('valorant')
    assert catalog.contains('elden ring')
    assert not catalog.contains('Definitely Not A Real Curated Game')


def test_catalog_resolve_returns_canonical_title():
    catalog = PopularGameCatalog()
    assert catalog.resolve('  valorant ') == 'VALORANT'
    assert catalog.resolve('world OF warcraft') == 'World of Warcraft'
    assert catalog.resolve('ea sports fc 26') == 'EA SPORTS FC 26'
    assert catalog.resolve('not in catalog') is None


def test_launcher_title_fallback_only_accepts_curated_or_known_aliases():
    assert GamingDetector._extract_game_from_title('Fortnite - Epic Games') == 'Fortnite'
    assert GamingDetector._extract_game_from_title('world of warcraft - Battle.net') == 'World of Warcraft'
    assert GamingDetector._extract_game_from_title('VALORANT - Riot Client') == 'VALORANT'
    assert GamingDetector._extract_game_from_title('counter strike 2 - Steam') == 'Counter-Strike 2'
    assert GamingDetector._extract_game_from_title('Deadlock - Steam') == 'Deadlock'

    assert GamingDetector._extract_game_from_title('Store - Battle.net') is None
    assert GamingDetector._extract_game_from_title('News - Epic Games') is None
    assert GamingDetector._extract_game_from_title('Random Advertisement - Riot Client') is None


def test_loader_rejects_duplicate_titles(tmp_path: Path):
    path = tmp_path / 'catalog.json'
    path.write_text(
        json.dumps({'schema': 1, 'games': ['Example Game', ' example   game ']}),
        encoding='utf-8',
    )
    with pytest.raises(ValueError, match='duplicate'):
        load_popular_catalog(path)


def test_loader_rejects_non_string_titles(tmp_path: Path):
    path = tmp_path / 'catalog.json'
    path.write_text(json.dumps({'schema': 1, 'games': ['Game', 123]}), encoding='utf-8')
    with pytest.raises(ValueError, match='strings'):
        load_popular_catalog(path)


def test_loader_rejects_unsupported_schema(tmp_path: Path):
    path = tmp_path / 'catalog.json'
    path.write_text(json.dumps({'schema': 2, 'games': ['Game']}), encoding='utf-8')
    with pytest.raises(ValueError, match='schema'):
        load_popular_catalog(path)
