import json
from pathlib import Path

import pytest

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
    )
    assert all(catalog.contains(title) for title in expected)


def test_catalog_membership_is_case_and_whitespace_insensitive():
    catalog = PopularGameCatalog()
    assert catalog.contains('  counter-strike   2  ')
    assert catalog.contains('valorant')
    assert catalog.contains('elden ring')
    assert not catalog.contains('Definitely Not A Real Curated Game')


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
