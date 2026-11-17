import pathspec

from teddy_executor.adapters.outbound import filesystem_helpers
from teddy_executor.adapters.outbound.local_file_system_adapter import (
    LocalFileSystemAdapter,
)
from teddy_executor.core.services.edit_simulator import EditSimulator


def build_adapter() -> LocalFileSystemAdapter:
    return LocalFileSystemAdapter(edit_simulator=EditSimulator(), root_dir="/app")


def test_list_directory_recursive_finds_nested_files(fs):
    fs.create_file("/app/src/main.py", contents="print('hello')")
    fs.create_file("/app/src/utils/helpers.py", contents="def help(): pass")
    fs.create_file("/app/docs/readme.md", contents="# Readme")

    files = build_adapter().list_directory_recursive("src")

    expected = ["src/main.py", "src/utils/helpers.py"]
    assert sorted(files) == sorted(expected)


def test_list_directory_recursive_respects_ignores(fs):
    fs.create_file("/app/.gitignore", contents="*.log\nnode_modules/")
    fs.create_file("/app/src/main.py", contents="print('hello')")
    fs.create_file("/app/src/app.log", contents="some log")
    fs.create_file("/app/node_modules/dep/index.js", contents="...")
    fs.create_file("/app/.teddyignore", contents="secret.txt")
    fs.create_file("/app/secret.txt", contents="shhh")

    files = build_adapter().list_directory_recursive(".")

    assert "src/app.log" not in files
    assert "node_modules/dep/index.js" not in files
    assert "secret.txt" not in files
    assert "src/main.py" in files


def test_list_directory_recursive_dot_resolves_correctly(fs):
    fs.create_file("/app/.gitignore", contents="*.log\nnode_modules/")
    fs.create_file("/app/src/main.py", contents="print('hello')")
    fs.create_file("/app/src/app.log", contents="some log")
    fs.create_file("/app/node_modules/dep/index.js", contents="...")
    fs.create_file("/app/.teddyignore", contents="secret.txt")
    fs.create_file("/app/secret.txt", contents="shhh")

    files = build_adapter().list_directory_recursive(".")

    assert "src/app.log" not in files
    assert "node_modules/dep/index.js" not in files
    assert "secret.txt" not in files
    assert "src/main.py" in files
