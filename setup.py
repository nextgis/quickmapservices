#!/usr/bin/env python3

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from configparser import ConfigParser
from pathlib import Path
from typing import Dict, List, Optional

try:
    import tomllib
except ImportError:
    import pip._vendor.tomli as tomllib


def with_name(
    path: Path, prefix: str = "", suffix: str = "", extension: str = ".py"
) -> Path:
    return path.with_name(f"{prefix}{path.stem}{suffix}{extension}")


class QgisPluginBuilder:
    def __init__(self):
        self.current_directory = Path(__file__).parent
        pyproject_file = self.current_directory / "pyproject.toml"

        self.settings = tomllib.loads(pyproject_file.read_text())
        self.project_settings = self.settings.get("project", {})
        self.qgspb_settings = self.settings.get("tool", {}).get("qgspb", {})
        self.data_settings = self.qgspb_settings.get("package-data", {})
        self.ui_settings = self.qgspb_settings.get("forms", {})
        self.qrc_settings = self.qgspb_settings.get("resources", {})
        self.ts_settings = self.qgspb_settings.get("translations", {})

    def bootstrap(
        self,
        *,
        compile_ui: Optional[bool] = None,
        compile_qrc: Optional[bool] = None,
        compile_ts: Optional[bool] = None,
        update_git_submodules: Optional[bool] = None,
    ) -> None:
        """
        Prepare the plugin environment and compile necessary components.

        :param compile_ui: Compile UI forms if True.
        :type compile_ui: Optional[bool]
        :param compile_qrc: Compile resource files if True.
        :type compile_qrc: Optional[bool]
        :param compile_ts: Compile translation files if True.
        :type compile_ts: Optional[bool]
        :param update_git_submodules: Update missing git submodules if True.
        :type update_git_submodules: Optional[bool]
        """

        # Enable full setup mode if no explicit flags are provided
        if all(
            setting is None
            for setting in (
                compile_ui,
                compile_qrc,
                compile_ts,
                update_git_submodules,
            )
        ):
            update_git_submodules = True
            compile_ui = True
            compile_qrc = True
            compile_ts = True

        if update_git_submodules:
            self.update_git_submodules()
        if compile_ui:
            self.compile_ui()
        if compile_qrc:
            self.compile_qrc()
        if compile_ts:
            self.compile_ts()

    def update_git_submodules(self) -> None:
        """
        Update missing git submodules by reading .gitmodules and
        initializing submodules that are not present.

        :raises RuntimeError: If git is not available or update fails.
        """
        # Construct path to .gitmodules file
        gitmodules_path = self.current_directory / ".gitmodules"
        if not gitmodules_path.exists():
            return

        # Parse .gitmodules to get all submodule paths
        submodule_paths = self._parse_gitmodules(gitmodules_path)
        # Identify missing submodules
        missing_submodules = [
            path
            for path in submodule_paths
            if not (self.current_directory / path / ".git").exists()
        ]
        if not missing_submodules:
            return

        for submodule in missing_submodules:
            print(f":: Initializing missing submodule: {submodule}")
            try:
                subprocess.check_call(
                    [
                        "git",
                        "submodule",
                        "update",
                        "--init",
                        "--",
                        str(submodule),
                    ],
                    cwd=str(self.current_directory),
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to update submodule {submodule}: {exc}"
                )

    def _parse_gitmodules(self, gitmodules_path: Path) -> List[str]:
        """
        Parse .gitmodules file and return a list of submodule paths.

        :param gitmodules_path: Path to .gitmodules file.
        :type gitmodules_path: Path
        :return: List of submodule paths.
        :rtype: List[str]
        """
        paths = []
        pattern = re.compile(r"^\s*path\s*=\s*(.+)$")

        # Extract 'path =' entries from .gitmodules
        for line in gitmodules_path.read_text(encoding="utf-8").splitlines():
            match = pattern.match(line)
            if match:
                paths.append(match.group(1).strip())
        return paths

    def compile_ui(self) -> None:
        if len(self.ui_settings) == 0 or not self.ui_settings.get(
            "compile", False
        ):
            return

        prefix = self.ui_settings.get("target-prefix", "")
        suffix = self.ui_settings.get("target-suffix", "")
        ui_patterns = self.ui_settings.get("ui-files", [])
        ui_paths = [
            ui_path
            for ui_pattern in ui_patterns
            for ui_path in Path(__file__).parent.rglob(ui_pattern)
        ]
        for ui_path in ui_paths:
            output_path = with_name(ui_path, prefix, suffix, ".py")
            subprocess.check_output(
                ["pyuic5", "-o", str(output_path), str(ui_path)]
            )
            self.__update_generated_file(output_path)

    def compile_qrc(self) -> None:
        if len(self.qrc_settings) == 0:
            return

        prefix = self.qrc_settings.get("target-prefix", "")
        suffix = self.qrc_settings.get("target-suffix", "")
        qrc_patterns = self.qrc_settings.get("qrc-files", [])
        qrc_paths = [
            qrc_path
            for qrc_pattern in qrc_patterns
            for qrc_path in Path(__file__).parent.rglob(qrc_pattern)
        ]
        for qrc_path in qrc_paths:
            output_path = with_name(qrc_path, prefix, suffix, ".py")
            subprocess.check_output(
                ["pyrcc5", "-o", str(output_path), str(qrc_path)]
            )
            self.__update_generated_file(output_path)

    def compile_ts(self):
        if len(self.ts_settings) == 0:
            return

        ts_patterns = self.ts_settings.get("ts-files", [])
        command_args = ["lrelease"]
        command_args.extend(
            str(ts_path)
            for ts_pattern in ts_patterns
            for ts_path in Path(__file__).parent.rglob(ts_pattern)
        )

        subprocess.check_output(command_args)

    def build(self) -> None:
        self.bootstrap()

        build_mapping = self.__create_build_mapping()

        project_name: str = self.project_settings["name"]
        project_version: str = self.project_settings["version"]

        zip_file_name = f"{project_name}-{project_version}.zip"

        build_directory = Path(__file__).parent / "build"
        build_directory.mkdir(exist_ok=True)

        created_directories = set()

        def create_directories(zip_file: zipfile.ZipFile, path: Path):
            directory = ""
            for part in path.parts[:-1]:
                directory += f"{part}/"
                if directory in created_directories:
                    continue
                zip_file.writestr(directory, "")
                created_directories.add(directory)

        zip_file_path = build_directory / zip_file_name
        with zipfile.ZipFile(
            zip_file_path, "w", zipfile.ZIP_DEFLATED
        ) as zip_file:
            for source_file, build_path in build_mapping.items():
                create_directories(zip_file, build_path)
                zip_file.write(source_file, "/".join(build_path.parts))

    def install(
        self,
        qgis: str,
        profile: Optional[str],
        editable: bool = False,
        force: bool = False,
    ) -> None:
        profile_path = self.__profile_path(qgis, profile)
        plugins_path = profile_path / "python" / "plugins"

        project_name: str = self.project_settings["name"]
        project_version: str = self.project_settings["version"]

        plugin_path = plugins_path / project_name

        installed_version = None

        print(f"Plugin {project_name} {project_version}\n")

        confirmation = (
            input(":: Proceed with installation? [Y/n] ").strip().lower()
        )

        if confirmation == "n":
            return

        print()

        if plugin_path.exists():
            metadata_path = plugin_path / "metadata.txt"
            if not metadata_path.exists():
                print(
                    f"Plugin {project_name} is already"
                    f' installed for "{profile_path.name}" profile'
                )
                if not force:
                    return

                print("\n:: Uninstalling broken plugin version...")
                self.__uninstall_plugin(plugin_path)

            else:
                metadata = ConfigParser()
                with open(metadata_path, encoding="utf-8") as f:
                    metadata.read_file(f)
                installed_version = metadata.get("general", "version")

                print(
                    f"Plugin {project_name} {installed_version} is already"
                    f' installed for "{profile_path.name}" profile'
                )

                if not force:
                    return

                print("\n:: Uninstalling previous plugin version...")

                self.__uninstall_plugin(plugin_path)

        self.bootstrap()

        print(":: Installing plugin...")

        build_mapping = self.__create_build_mapping()
        for source_file, build_path in build_mapping.items():
            (plugins_path / build_path).parent.mkdir(
                parents=True, exist_ok=True
            )
            print(f"- {build_path}")

            if editable:
                (plugins_path / build_path).symlink_to(source_file)
            else:
                shutil.copy(source_file, plugins_path / build_path)

        print(f"\n:: {project_name} {project_version} successfully installed")

    def uninstall(self, qgis: str, profile: Optional[str]) -> None:
        profile_path = self.__profile_path(qgis, profile)
        plugins_path = profile_path / "python" / "plugins"

        project_name: str = self.project_settings["name"]

        plugin_path = plugins_path / project_name

        if not plugin_path.exists():
            print(
                f"Plugin {project_name} is not installed for"
                f' "{profile_path.name}" profile'
            )
            return

        metadata_path = plugin_path / "metadata.txt"
        assert metadata_path.exists()

        metadata = ConfigParser()
        with open(metadata_path, encoding="utf-8") as f:
            metadata.read_file(f)
        installed_version = metadata.get("general", "version")

        print(f"Plugin {project_name} {installed_version}\n")

        confirmation = (
            input(":: Do you want to remove this plugin? [y/N] ")
            .strip()
            .lower()
        )

        if confirmation != "y":
            return

        self.__uninstall_plugin(plugin_path)

        print(
            f"\n:: {project_name} {installed_version} successfully uninstalled"
        )

    def clean(self) -> None:
        mappings = {
            **self.__create_resources_mapping(),
            **self.__create_translations_mapping(),
        }

        if self.ui_settings.get("compile", False):
            mappings.update(self.__create_forms_mapping())

        src_directory = Path(__file__).parent / "src"
        for path in mappings.values():
            (src_directory / path).unlink(missing_ok=True)

    def update_ts(self):
        if len(self.ts_settings) == 0:
            return

        command_args = ["pylupdate5"]
        if self.ts_settings.get("no-obsolete", False):
            command_args.append("-noobsolete")

        exclude_patterns = self.ts_settings.get("exclude-files", [])
        exclude_paths = set(
            exclude_path
            for exclude_pattern in exclude_patterns
            for exclude_path in Path(__file__).parent.rglob(exclude_pattern)
        )
        exclude_paths.update(
            path
            for path in self.__create_forms_mapping().keys()
            if path.suffix == ".py"
        )
        exclude_paths.update(self.__create_resources_mapping().keys())

        ui_patterns = self.ui_settings.get("ui-files", [])
        source_paths = list(self.__create_sources_mapping().keys())
        source_paths.extend(
            ui_path
            for ui_pattern in ui_patterns
            for ui_path in Path(__file__).parent.rglob(ui_pattern)
        )

        if len(source_paths) == 0:
            raise RuntimeError("Sources list is empty")

        ts_patterns = self.ts_settings.get("ts-files", [])
        if len(ts_patterns) == 0:
            raise RuntimeError("Empty translations list")

        command_args.extend(
            str(source_path)
            for source_path in source_paths
            if source_path not in exclude_paths
        )
        command_args.append("-ts")
        command_args.extend(
            str(ts_path)
            for ts_pattern in ts_patterns
            for ts_path in Path(__file__).parent.rglob(ts_pattern)
        )

        subprocess.check_output(command_args)

        # TODO (ivanbarsukov): check unfinished in ts files

    def __create_build_mapping(self) -> Dict[Path, Path]:
        result = self.__create_metadata_mapping()
        result.update(self.__create_readme_mapping())
        result.update(self.__create_license_mapping())
        result.update(self.__create_sources_mapping())
        result.update(self.__create_data_mapping())
        result.update(self.__create_forms_mapping())
        result.update(self.__create_resources_mapping())
        result.update(self.__create_translations_mapping())
        result = dict(sorted(result.items()))
        return result

    def __create_metadata_mapping(self) -> Dict[Path, Path]:
        project_version: str = self.project_settings["version"]

        src_directory = Path(__file__).parent / "src"
        project_name: str = self.project_settings["name"]

        metadata_path = src_directory / project_name / "metadata.txt"

        metadata = ConfigParser()
        with open(metadata_path, encoding="utf-8") as f:
            metadata.read_file(f)
        assert metadata.get("general", "version") == project_version

        build_path = Path(project_name) / metadata_path.name

        return {metadata_path: build_path}

    def __create_readme_mapping(self) -> Dict[Path, Path]:
        if "readme" not in self.project_settings:
            return {}

        readme_setting = self.project_settings["readme"]

        if isinstance(readme_setting, str):
            readme_path = Path(__file__).parent / readme_setting
        elif isinstance(readme_setting, dict):
            readme_path = Path(__file__).parent / readme_setting["file"]
        else:
            raise RuntimeError("Unknown readme setting")

        project_name: str = self.project_settings["name"]

        file_path = readme_path.absolute()
        build_path = Path(project_name) / file_path.name

        return {file_path: build_path}

    def __create_license_mapping(self) -> Dict[Path, Path]:
        if "license" not in self.project_settings:
            return {}

        license_setting = self.project_settings["license"]
        license_file = license_setting["file"]
        assert isinstance(license_file, str)

        project_name: str = self.project_settings["name"]

        file_path = (Path(__file__).parent / license_file).absolute()
        build_path = Path(project_name) / file_path.name

        return {file_path: build_path}

    def __create_sources_mapping(self) -> Dict[Path, Path]:
        project_name: str = self.project_settings["name"]
        src_directory = Path(__file__).parent / "src"

        exclude_patterns = self.qgspb_settings.get("exclude-files", [])
        exclude_paths = set(
            exclude_path.absolute()
            for exclude_pattern in exclude_patterns
            for exclude_path in Path(__file__).parent.rglob(exclude_pattern)
        )

        return {
            py_path.absolute(): py_path.relative_to(src_directory)
            for py_path in (src_directory / project_name).rglob("*.py")
            if py_path.absolute() not in exclude_paths
        }

    def __create_data_mapping(self) -> Dict[Path, Path]:
        if len(self.data_settings) == 0:
            return {}

        src_directory = Path(__file__).parent / "src"

        data_paths = []
        for package, resources in self.data_settings.items():
            package_path = src_directory / package.replace(".", "/")
            for data_template in resources:
                data_paths.extend(package_path.rglob(data_template))

        return {
            data_path.absolute(): data_path.relative_to(src_directory)
            for data_path in data_paths
        }

    def __create_forms_mapping(self) -> Dict[Path, Path]:
        if len(self.ui_settings) == 0:
            return {}

        ui_patterns = self.ui_settings.get("ui-files", [])
        ui_paths = [
            ui_path
            for ui_pattern in ui_patterns
            for ui_path in Path(__file__).parent.rglob(ui_pattern)
        ]

        src_directory = Path(__file__).parent / "src"

        if not self.ui_settings.get("compile", False):
            return {
                ui_file.absolute(): ui_file.relative_to(src_directory)
                for ui_file in ui_paths
            }

        prefix = self.ui_settings.get("target-prefix", "")
        suffix = self.ui_settings.get("target-suffix", "")

        result = {}
        for ui_path in ui_paths:
            py_path = with_name(ui_path, prefix, suffix, ".py")
            result[py_path.absolute()] = py_path.relative_to(src_directory)

        return result

    def __create_resources_mapping(self) -> Dict[Path, Path]:
        if len(self.qrc_settings) == 0:
            return {}

        prefix = self.qrc_settings.get("target-prefix", "")
        suffix = self.qrc_settings.get("target-suffix", "")
        qrc_patterns = self.qrc_settings.get("qrc-files", [])
        qrc_paths = [
            qrc_path
            for qrc_pattern in qrc_patterns
            for qrc_path in Path(__file__).parent.rglob(qrc_pattern)
        ]

        src_directory = Path(__file__).parent / "src"

        result = {}
        for qrc_path in qrc_paths:
            py_path = with_name(qrc_path, prefix, suffix, ".py")
            result[py_path.absolute()] = py_path.relative_to(src_directory)

        return result

    def __create_translations_mapping(self) -> Dict[Path, Path]:
        if len(self.ts_settings) == 0:
            return {}

        ts_patterns = self.ts_settings.get("ts-files", [])
        ts_paths = [
            ts_path
            for ts_pattern in ts_patterns
            for ts_path in Path(__file__).parent.rglob(ts_pattern)
        ]

        src_directory = Path(__file__).parent / "src"

        result = {}
        for ts_path in ts_paths:
            qm_file = ts_path.with_suffix(".qm")
            result[qm_file.absolute()] = qm_file.relative_to(src_directory)

        return result

    def __update_generated_file(self, file_path: Path) -> None:
        assert file_path.suffix == ".py"
        content = file_path.read_text(encoding="utf-8")
        file_path.write_text(content.replace("from PyQt5", "from qgis.PyQt"))

    def __profile_path(self, qgis: str, profile: Optional[str]) -> Path:
        system = platform.system()

        if qgis in ("Vanilla", "VanillaFlatpak"):
            qgis_profiles = Path("QGIS/QGIS3/profiles")
        elif qgis in ("NextGIS", "NextGISFlatpak"):
            qgis_profiles = Path("NextGIS/ngqgis/profiles")
        else:
            raise RuntimeError(f"Unknown QGIS: {qgis}")

        if system == "Linux":
            if qgis in ("Vanilla", "NextGIS"):
                profiles_path = (
                    Path("~/.local/share/").expanduser() / qgis_profiles
                )
            elif qgis == "VanillaFlatpak":
                profiles_path = (
                    Path("~/.var/app/org.qgis.qgis/data/").expanduser()
                    / qgis_profiles
                )
            elif qgis == "NextGISFlatpak":
                profiles_path = (
                    Path("~/.var/app/com.nextgis.ngqgis/data/").expanduser()
                    / qgis_profiles
                )

        elif system == "Windows":
            appdata = os.getenv("APPDATA")
            assert appdata is not None
            profiles_path = Path(appdata) / qgis_profiles

        elif system == "Darwin":  # macOS
            profiles_path = (
                Path("~/Library/Application Support/").expanduser()
                / qgis_profiles
            )

        else:
            raise OSError(f"Unsupported OS: {system}")

        if not profiles_path.exists():
            raise FileExistsError(
                f"Profiles path for {qgis} QGIS is not exists"
            )

        profiles: List[str] = []
        for path in profiles_path.glob("*"):
            if path.is_dir():
                profiles.append(path.name)

        if profile is not None and profile not in profiles:
            print(f'Warning: profile "{profile}"" is not found\n')
            profile = None

        if profile is None:
            profiles_ini_path = profiles_path / "profiles.ini"
            if not profiles_ini_path.exists():
                raise FileExistsError("profiles.ini is not exists")

            profiles_ini = ConfigParser()
            profiles_ini.read(profiles_ini_path)

            default_profile = profiles_ini.get(
                "core", "defaultProfile", fallback=None
            )

            if len(profiles) == 0:
                raise RuntimeError("There are no QGIS profiles")

            elif len(profiles) == 1:
                profile = profiles[0]

            else:
                print(f":: {len(profiles)} profiles found")
                for i, found_profile in enumerate(profiles, start=1):
                    print(f"{i:2} {found_profile}")
                print()

                default_profile_index = -1
                default_text = ""
                if default_profile in profiles:
                    default_profile_index = profiles.index(default_profile)
                    default_text = f" [default is {default_profile_index + 1}]"

                choosen_index = input(
                    f":: Choose QGIS profile{default_text}: "
                )
                print()
                if choosen_index.strip() == "":
                    choosen_index = default_profile_index + 1

                choosen_index = int(choosen_index)
                if choosen_index < 1 or choosen_index > len(profiles):
                    raise ValueError

                profile = profiles[choosen_index - 1]

        return profiles_path / profile

    def __uninstall_plugin(self, path: Path) -> None:
        if path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    def config(self, ide: str, qgis: str, profile: Optional[str]) -> None:
        if ide == "vscode":
            (self.current_directory / ".vscode").mkdir(exist_ok=True)
            self.__create_vscode_launch(qgis, profile)
            self.__create_vscode_tasks()
            self.__create_dotenv()
            return

        raise NotImplementedError

    def __create_vscode_launch(
        self, qgis: str, profile: Optional[str]
    ) -> None:
        profile_path = self.__profile_path(qgis, profile)
        plugins_path = profile_path / "python" / "plugins"
        project_name: str = self.project_settings["name"]
        plugin_path = plugins_path / project_name

        launch_file = self.current_directory / ".vscode" / "launch.json"

        launch_content = {}
        need_fill = True
        if launch_file.exists():
            try:
                launch_content = json.loads(self.__read_json(launch_file))
                need_fill = False
            except Exception:
                print(
                    f"An error occurred while reading {launch_file}. This file"
                    " will be overwrited"
                )
                pass

        if need_fill:
            launch_content["version"] = "0.2.0"
            launch_content["configurations"] = []

        new_configurations = [
            {
                "name": "Attach QGIS",
                "type": "debugpy",
                "request": "attach",
                "connect": {"host": "localhost", "port": 5678},
                "pathMappings": [
                    {
                        "localRoot": f"${{workspaceFolder}}/src/{project_name}",
                        "remoteRoot": str(plugin_path),
                    }
                ],
                "justMyCode": True,
            }
        ]

        for new_config in new_configurations:
            is_replaced = False
            for i, current_config in enumerate(
                launch_content["configurations"]
            ):
                if new_config["name"] == current_config["name"]:
                    launch_content["configurations"][i] = new_config
                    is_replaced = True
                    break

            if not is_replaced:
                launch_content["configurations"].append(new_config)

        launch_file.write_text(json.dumps(launch_content, indent=4))

    def __create_vscode_tasks(self) -> None:
        tasks_file = self.current_directory / ".vscode" / "tasks.json"

        tasks_conten = {}
        if tasks_file.exists():
            tasks_conten = json.loads(self.__read_json(tasks_file))
        else:
            tasks_conten["version"] = "2.0.0"
            tasks_conten["inputs"] = []
            tasks_conten["tasks"] = []

        new_inputs = [
            {
                "id": "qgis",
                "description": "QGIS build",
                "type": "pickString",
                "options": [
                    "Vanilla",
                    "NextGIS",
                    "VanillaFlatpak",
                    "NextGISFlatpak",
                ],
            }
        ]
        for new_input in new_inputs:
            is_replaced = False
            for i, current_input in enumerate(tasks_conten["inputs"]):
                if new_input["id"] == current_input["id"]:
                    tasks_conten["inputs"][i] = new_input
                    is_replaced = True
                    break

            if not is_replaced:
                tasks_conten["inputs"].append(new_input)

        new_tasks = [
            {
                "label": "Install plugin",
                "type": "shell",
                "group": "build",
                "command": "${command:python.interpreterPath} "
                "${workspaceFolder}/setup.py install --force --qgis "
                "${input:qgis}",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": True,
                    "panel": "shared",
                    "showReuseMessage": True,
                    "clear": False,
                },
            },
            {
                "label": "Install plugin [editable]",
                "type": "shell",
                "group": "build",
                "command": "${command:python.interpreterPath} "
                "${workspaceFolder}/setup.py install --editable --force "
                "--qgis ${input:qgis}",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": True,
                    "panel": "shared",
                    "showReuseMessage": True,
                    "clear": False,
                },
            },
            {
                "label": "Uninstall plugin",
                "type": "shell",
                "group": "build",
                "command": "${command:python.interpreterPath} "
                "${workspaceFolder}/setup.py uninstall",
                "presentation": {
                    "echo": True,
                    "reveal": "always",
                    "focus": True,
                    "panel": "shared",
                    "showReuseMessage": True,
                    "clear": False,
                },
            },
            {
                "label": "Build release zip",
                "type": "shell",
                "group": "build",
                "command": "${command:python.interpreterPath} "
                "${workspaceFolder}/setup.py build",
            },
            {
                "label": "Update translations",
                "type": "shell",
                "group": "build",
                "command": "${command:python.interpreterPath} "
                "${workspaceFolder}/setup.py update_ts",
            },
            {
                "label": "Generate resources",
                "type": "shell",
                "group": "build",
                "command": "${command:python.interpreterPath} "
                "${workspaceFolder}/setup.py bootstrap",
            },
            {
                "label": "Clean generated files",
                "type": "shell",
                "group": "build",
                "command": "${command:python.interpreterPath} "
                "${workspaceFolder}/setup.py clean",
            },
        ]

        for new_task in new_tasks:
            is_replaced = False
            for i, current_task in enumerate(tasks_conten["tasks"]):
                if new_task["label"] == current_task["label"]:
                    tasks_conten["tasks"][i] = new_task
                    is_replaced = True
                    break

            if not is_replaced:
                tasks_conten["tasks"].append(new_task)

        tasks_file.write_text(json.dumps(tasks_conten, indent=4))

    def __create_dotenv(self) -> None:
        if platform.system() == "Windows":
            self.__create_dotenv_for_windows()
        else:
            self.__create_dotenv_for_unix()

    def __read_json(self, json_path: Path) -> str:
        text = json_path.read_text()
        text = re.sub(r",(\s*)(\]|\})", r"\1\2", text, flags=re.MULTILINE)
        text = re.sub(r"^(\s*)\/\/.*\n", r"", text, flags=re.MULTILINE)
        return text

    def __create_dotenv_for_windows(self) -> None:
        # Capture updated state
        bat_file = self.__create_env_bat_file()
        if bat_file is None:
            self.__write_dotenv(self.__create_dotenv_dict({}, {}))
            return

        # Capture current state
        result = subprocess.run(
            ["cmd.exe", "/c", "set"],
            capture_output=True,
            text=True,
            shell=True,
            check=True,
        )
        current_env = self.__extract_env_vars_from_set_output(result.stdout)

        result = subprocess.run(
            f'cmd.exe /c "{bat_file} & set"',
            capture_output=True,
            text=True,
            shell=True,
            check=True,
        )
        updated_env = self.__extract_env_vars_from_set_output(result.stdout)

        bat_file.unlink()

        dotenv = self.__create_dotenv_dict(current_env, updated_env)
        self.__write_dotenv(dotenv)

    def __create_dotenv_for_unix(self) -> None:
        self.__write_dotenv(self.__create_dotenv_dict({}, {}))

    def __extract_env_vars_from_set_output(
        self, output: str
    ) -> Dict[str, str]:
        """Returns the current environment variables as a dictionary."""
        env_variables = {}
        for line in output.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            env_variables[key] = value

        return env_variables

    def __create_env_bat_file(self) -> Optional[Path]:
        bin_path = Path(sys.executable).parent
        osgeo_bat = bin_path / "python-qgis.bat"
        nextgis_bat = bin_path.parent / "run_ng_env.bat"

        source_bat_file = None
        for bat_path in (osgeo_bat, nextgis_bat):
            if not bat_path.exists():
                continue
            source_bat_file = bat_path
            break

        if source_bat_file is None:
            return None

        temp_bat_file = tempfile.mktemp(prefix="qgis_env", suffix=".bat")
        source_dir = str(source_bat_file.parent)
        source_bat = source_bat_file.read_text()

        with open(temp_bat_file, "w") as file:
            for line in source_bat.split("\n"):
                if line.lstrip().startswith(("start", "python", "@echo on")):
                    continue
                line = line.replace("%~dp0", source_dir)
                file.write(f"{line}\n")

        return Path(temp_bat_file)

    def __create_dotenv_dict(
        self, current_env: Dict[str, str], updated_env: Dict[str, str]
    ) -> Dict[str, str]:
        def is_permanent_key(key: str) -> bool:
            key = key.upper()
            return key.startswith(
                (
                    "O4W_",
                    "OSGEO4W_",
                    "QGIS_",
                    "QT_",
                    "GDAL_",
                    "VSI_",
                    "PDAL_",
                    "PROJ_",
                    "GS_",
                    "SSL_",
                    "OPENSSL_",
                    "PYTHON",
                )
            ) or key in ("PATH",)

        dotenv = {
            key: updated_env[key]
            for key in updated_env
            if is_permanent_key(key)
            or updated_env.get(key) != current_env.get(key)
        }

        pythonhome_key = "PYTHONPATH"
        for key in dotenv.keys():
            if key.upper() != pythonhome_key:
                continue
            pythonhome_key = key

        pythonhome_values = (
            dotenv[pythonhome_key].split(os.pathsep)
            if pythonhome_key in dotenv
            else []
        )

        if (self.current_directory / "src").exists():
            pythonhome_values.insert(0, str(self.current_directory / "src"))
        pythonhome_values.insert(0, str(self.current_directory))

        dotenv[pythonhome_key] = os.pathsep.join(pythonhome_values)

        return dotenv

    def __write_dotenv(self, env_variables: Dict[str, str]) -> None:
        dotenv_path = self.current_directory / ".env"
        with dotenv_path.open("w") as dotenv_file:
            for key, value in env_variables.items():
                dotenv_file.write(f"{key}={value}\n")


def create_parser():
    parser = argparse.ArgumentParser(description="QGIS plugins build tool")

    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    # bootstrap command
    parser_bootstrap = subparsers.add_parser(
        "bootstrap", help="Bootstrap the plugin"
    )
    parser_bootstrap.add_argument(
        "--ts",
        dest="compile_ts",
        default=None,
        action="store_true",
        help="Compile only translations",
    )
    parser_bootstrap.add_argument(
        "--ui",
        dest="compile_ui",
        default=None,
        action="store_true",
        help="Compile only forms",
    )
    parser_bootstrap.add_argument(
        "--qrc",
        dest="compile_qrc",
        default=None,
        action="store_true",
        help="Compile only resources",
    )
    parser_bootstrap.add_argument(
        "--git",
        dest="update_git_submodules",
        action="store_true",
        default=False,
        help="Update missing git submodules",
    )

    # build command
    subparsers.add_parser("build", help="Build the plugin")

    # install command
    parser_install = subparsers.add_parser(
        "install", help="Install the plugin"
    )
    parser_install.add_argument(
        "--qgis",
        default="Vanilla",
        choices=["Vanilla", "NextGIS", "VanillaFlatpak", "NextGISFlatpak"],
        help="QGIS build",
    )
    parser_install.add_argument(
        "--profile", default=None, help="QGIS profile name"
    )
    parser_install.add_argument(
        "--editable", action="store_true", help="Install in editable mode"
    )
    parser_install.add_argument(
        "--force", action="store_true", help="Reinstall if installed"
    )

    # uninstall command
    parser_uninstall = subparsers.add_parser(
        "uninstall", help="Uninstall the project"
    )
    parser_uninstall.add_argument(
        "--qgis",
        default="Vanilla",
        choices=["Vanilla", "NextGIS", "VanillaFlatpak", "NextGISFlatpak"],
        help="QGIS build",
    )
    parser_uninstall.add_argument(
        "--profile", default=None, help="QGIS profile name"
    )

    # clean command
    subparsers.add_parser("clean", help="Clean compiled files")

    # update_ts command
    subparsers.add_parser("update_ts", help="Update translations")

    # config
    parser_config = subparsers.add_parser(
        "config", help="Config repo for development"
    )
    parser_config.add_argument(
        "IDE",
        default="vscode",
        choices=["vscode"],
        help="IDE",
    )
    parser_config.add_argument(
        "--qgis",
        default="Vanilla",
        choices=["Vanilla", "NextGIS", "VanillaFlatpak", "NextGISFlatpak"],
        help="QGIS build",
    )
    parser_config.add_argument(
        "--profile", default=None, help="QGIS profile name"
    )

    return parser


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    builder = QgisPluginBuilder()

    try:
        if args.command == "bootstrap":
            builder.bootstrap(
                compile_ui=args.compile_ui,
                compile_qrc=args.compile_qrc,
                compile_ts=args.compile_ts,
                update_git_submodules=args.update_git_submodules,
            )
        elif args.command == "build":
            builder.build()
        elif args.command == "install":
            builder.install(args.qgis, args.profile, args.editable, args.force)
        elif args.command == "uninstall":
            builder.uninstall(args.qgis, args.profile)
        elif args.command == "clean":
            builder.clean()
        elif args.command == "update_ts":
            builder.update_ts()
        elif args.command == "config":
            builder.config(args.IDE, args.qgis, args.profile)

    except KeyboardInterrupt:
        print("\nInterrupt signal received")


if __name__ == "__main__":
    main()
