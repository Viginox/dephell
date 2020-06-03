# built-in
from pathlib import Path
from zipfile import ZipFile

# external
import pytest
from dephell_discover import Root as RootPackage

# project
from dephell.controllers import Graph
from dephell.converters.wheel import WheelConverter
from dephell.models import Requirement, RootDependency


def test_load_deps(requirements_path: Path):
    loader = WheelConverter()
    path = requirements_path / 'wheel.whl'
    root = loader.load(path)
    deps = {dep.name: dep for dep in root.dependencies}
    assert set(deps) == {'attrs', 'cached-property', 'packaging', 'requests'}


def test_load_metadata(requirements_path: Path):
    loader = WheelConverter()
    path = requirements_path / 'wheel.whl'
    root = loader.load(path)

    assert root.name == 'dephell'
    assert root.version == '0.2.0'
    assert root.authors[0].name == 'orsinium'
    assert not root.license


def _write_pyproject_toml(filename, use_src: bool):
    if use_src:
        packages = '{ include = \"wheel_gen\", from = \"src\" }'
    else:
        packages = ''
    with open(filename, 'w') as pyproject_file:
        pyproject_file.write(
            """
[tool.poetry]
name = "dephell_wheel_test"
version = "0.1.0"
description = ""
authors = ["Viginox"]
packages = [
    {packages}
]

[tool.dephell.main]
from = {{format = "poetry", path = "pyproject.toml"}}
to = {{format = "setuppy", path = "setup.py"}}
            """.format(packages=packages)
        )


@pytest.mark.parametrize('files, use_src, expected', [
    [('wheel_gen/__init__.py', 'wheel_gen/test.py'), False,
     ('wheel_gen/__init__.py', 'wheel_gen/test.py')],  # package_dir = {'', '.'}
    [('src/__init__.py', 'src/test.py'), True,
     ('wheel_gen/__init__.py', 'wheel_gen/test.py')],  # pacakge_dir = {'wheel_gen': 'src'}
    [('__init__.py', 'test.py'), False,
     ('wheel_gen/__init__.py', 'wheel_gen/test.py')],  # package_dir = {'wheel_gen': ''}
    [('src/wheel_gen/__init__.py', 'src/wheel_gen/test.py'), True,
     ('wheel_gen/__init__.py', 'wheel_gen/test.py')],  # package_dir = {'': 'src'}
])
def test_dump(files, use_src, expected, tmp_path, requirements_path: Path):
    project_name = "wheel_gen"
    project_path = tmp_path / project_name
    project_path.mkdir()
    # generate project structure in temporary directory
    for file_path in files:
        path = project_path.joinpath(file_path)
        if '/' in file_path:
            path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    _write_pyproject_toml(tmp_path / "pyproject.toml", use_src)

    dist_path = Path('dist')

    to_path = dist_path / 'wheel.whl'

    # Run the wheel generation
    root = RootDependency(
        package=RootPackage(project_path)
    )
    # get the requirements from the project path
    reqs = Requirement.from_graph(Graph(root), lock=False)
    dumper = WheelConverter()
    dumper = dumper.copy(project_path=project_path)
    # dump the wheel file
    dumper.dump(
        path=project_path.joinpath(to_path),
        reqs=reqs,
        project=root,
    )

    with ZipFile(project_path.joinpath(to_path), 'r') as wheel_file:
        print(wheel_file.namelist())

        # assert that all required files are in the correct place
        for expected_file in expected:
            assert expected_file in wheel_file.namelist()
