# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import os
import pathlib

from ddqa.utils.fs import Path


class TestPath:
    def test_type(self):
        expected_type = type(pathlib.Path())

        assert isinstance(Path(), expected_type)
        assert issubclass(Path, expected_type)

    def test_resolve_relative_non_existent(self, tmp_path):
        origin = os.getcwd()
        os.chdir(tmp_path)
        try:
            expected_representation = os.path.join(tmp_path, 'foo')
            assert str(Path('foo').resolve()) == expected_representation
            assert str(Path('.', 'foo').resolve()) == expected_representation
        finally:
            os.chdir(origin)

    def test_ensure_dir_exists(self, tmp_path):
        path = Path(tmp_path, 'foo')
        path.ensure_dir_exists()

        assert path.is_dir()

    def test_as_cwd(self, tmp_path):
        origin = os.getcwd()

        with Path(tmp_path).as_cwd():
            assert os.getcwd() == str(tmp_path)

        assert os.getcwd() == origin

    def test_as_cwd_env_vars(self, tmp_path):
        env_var = str(self).encode().hex().upper()
        origin = os.getcwd()

        with Path(tmp_path).as_cwd(env_vars={env_var: 'foo'}):
            assert os.getcwd() == str(tmp_path)
            assert os.environ.get(env_var) == 'foo'

        assert os.getcwd() == origin
        assert env_var not in os.environ

    def test_remove_file(self, tmp_path):
        path = Path(tmp_path, 'foo')
        path.touch()

        assert path.is_file()
        path.remove()
        assert not path.exists()

    def test_remove_directory(self, tmp_path):
        path = Path(tmp_path, 'foo')
        path.mkdir()

        assert path.is_dir()
        path.remove()
        assert not path.exists()

    def test_remove_non_existent(self, tmp_path):
        path = Path(tmp_path, 'foo')

        assert not path.exists()
        path.remove()
        assert not path.exists()
