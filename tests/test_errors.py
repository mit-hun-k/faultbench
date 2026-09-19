"""Friendly errors for bad world files (milestone 9 hardening)."""

import pytest

from worldbench.world import World, parse_world


def _write(tmp_path, text):
    p = tmp_path / "bad.yaml"
    p.write_text(text)
    return p


def test_missing_file():
    with pytest.raises(FileNotFoundError, match="world file not found"):
        World.load("/no/such/world.yaml")


def test_invalid_yaml(tmp_path):
    with pytest.raises(ValueError, match="invalid YAML"):
        World.load(_write(tmp_path, "name: x\n  bad: : :"))


def test_not_a_mapping(tmp_path):
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        World.load(_write(tmp_path, "- just\n- a\n- list"))


def test_missing_name():
    with pytest.raises(ValueError, match="needs a top-level 'name'"):
        parse_world({"services": {}})


def test_services_not_a_mapping():
    with pytest.raises(ValueError, match="'services' must be a mapping"):
        parse_world({"name": "x", "services": ["nope"]})


def test_record_not_a_mapping():
    with pytest.raises(ValueError, match="must be a mapping of field"):
        parse_world({"name": "x", "services": {"s": {"records": {"r": "oops"}}}})


def test_bad_field_type_names_the_record():
    with pytest.raises(ValueError, match="record 'r':.*unknown field type"):
        parse_world({"name": "x", "services": {"s": {"records": {"r": {"id": "blob"}}}}})
