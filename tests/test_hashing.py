from dynawatermark.hashing import canonical_json_sha256, file_sha256


def test_file_sha256(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("hello", encoding="utf-8")

    assert file_sha256(path) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_canonical_json_sha256_is_key_order_stable():
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}

    assert canonical_json_sha256(left) == canonical_json_sha256(right)
