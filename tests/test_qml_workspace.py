"""The QML workspace shell, and the two rules every later surface inherits.

A QML file that binds to a property which does not exist logs a warning,
renders nothing, and leaves a test suite green. That is the most likely silent
failure in this migration, so the first test here loads every component with
engine warnings treated as failures.

The second rule is single-source: the token values live in `qml/Theme.qml` and
nowhere else, and `Theme.qml` itself is checked against
`docs/design/visual-tokens.md` rather than trusted. The previous appearance
drifted because nothing held that line.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize, QUrl  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlApplicationEngine  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import icon_family  # noqa: E402
from app_runtime import (  # noqa: E402
    TIMECODE_FONT_FAMILY,
    UI_FONT_FAMILY,
    register_bundled_fonts,
)
from application_workflow import UNTITLED_ANALYSIS_TITLE  # noqa: E402
from main import build_workspace_context  # noqa: E402
from qml_icons import IconProvider  # noqa: E402
from qml_runtime import build_engine, quick_scene_path  # noqa: E402


PROJECT_ROOT = Path(__file__).parents[1]
QML_ROOT = PROJECT_ROOT / "qml"
THEME = QML_ROOT / "Theme.qml"
TOKEN_SPEC = PROJECT_ROOT / "docs" / "design" / "visual-tokens.md"


def qml_components() -> list[Path]:
    """Every QML file this application ships."""

    return sorted(QML_ROOT.glob("*.qml"))


@pytest.fixture(scope="session")
def application() -> QApplication:
    instance = QApplication.instance() or QApplication([])
    register_bundled_fonts()
    assert isinstance(instance, QApplication)
    return instance


@pytest.fixture()
def engine(application: QApplication) -> QQmlApplicationEngine:
    """An engine holding everything a component's bindings can name.

    The components bind to `workspace`, so a load test without it would report
    the missing view model rather than the mistake it exists to find.
    """

    return build_engine(QML_ROOT, context_objects=build_workspace_context())


# --- The load test ---------------------------------------------------------


def test_the_application_ships_the_components_the_shell_is_made_of() -> None:
    assert {path.name for path in qml_components()} == {
        "IconButton.qml",
        "Main.qml",
        "Toolbar.qml",
        "SeekButton.qml",
        "SegmentedControl.qml",
        "Sidebar.qml",
        "Stage.qml",
        "Theme.qml",
        "Tip.qml",
        "Transport.qml",
        "VolumeSlider.qml",
    }


@pytest.mark.parametrize(
    "component", qml_components(), ids=lambda path: str(path.name)
)
def test_every_component_loads_without_an_engine_warning(
    component: Path,
    application: QApplication,
    engine: QQmlApplicationEngine,
) -> None:
    """A warning is a failure, because the alternative is a blank panel.

    Nothing else in this suite can see a binding to a property that was
    renamed, misspelled or never existed: the engine reports it, draws nothing
    where the item should have been, and carries on.
    """

    warnings: list[str] = []
    engine.warnings.connect(
        lambda reported: warnings.extend(warning.toString() for warning in reported)
    )

    loaded = QQmlComponent(engine, QUrl.fromLocalFile(str(component)))
    assert loaded.status() == QQmlComponent.Status.Ready, [
        error.toString() for error in loaded.errors()
    ]

    if "pragma Singleton" not in component.read_text(encoding="utf-8"):
        # A singleton is not creatable by hand; every other component is, and
        # creating it is the only way its bindings are ever evaluated.
        created = loaded.create()
        assert created is not None, [error.toString() for error in loaded.errors()]
        application.processEvents()
        created.deleteLater()

    application.processEvents()
    assert warnings == [], f"{component.name} loaded with engine warnings"


def test_the_shipped_entry_point_is_the_shell_this_ticket_builds() -> None:
    assert quick_scene_path() == QML_ROOT / "Main.qml"
    assert "Toolbar" in quick_scene_path().read_text(encoding="utf-8")


# --- No Qt Quick Controls --------------------------------------------------


@pytest.mark.parametrize(
    "component", qml_components(), ids=lambda path: str(path.name)
)
def test_no_component_imports_qt_quick_controls(component: Path) -> None:
    """Controls are drawn from primitives, so no platform style argues back."""

    source = component.read_text(encoding="utf-8")
    assert "QtQuick.Controls" not in source
    assert "QtQuick.Templates" not in source


# --- One theme singleton, and nowhere else ---------------------------------

_COLOUR_LITERAL = re.compile(r"#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})\b")
_COMPUTED_COLOUR = re.compile(r"Qt\.(?:rgba|hsla|hsva|lighter|darker|tint)\s*\(")
_DECLARATION = re.compile(
    r"readonly property (?:color|int|real|string|var) (\w+):\s*([^\n]+)"
)


def _without_comments(source: str) -> str:
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", without_block)


@pytest.mark.parametrize(
    "component",
    [path for path in qml_components() if path != THEME],
    ids=lambda path: str(path.name),
)
def test_no_component_writes_a_colour_of_its_own(component: Path) -> None:
    source = _without_comments(component.read_text(encoding="utf-8"))
    assert _COLOUR_LITERAL.search(source) is None, (
        f"{component.name} writes a colour literal; the value belongs in Theme.qml"
    )
    assert _COMPUTED_COLOUR.search(source) is None, (
        f"{component.name} computes a colour; the value belongs in Theme.qml"
    )


def _theme_declarations() -> dict[str, str]:
    return {
        name: value.strip()
        for name, value in _DECLARATION.findall(
            _without_comments(THEME.read_text(encoding="utf-8"))
        )
    }


def _specified_colours() -> dict[str, str]:
    """Every colour the token spec freezes, by its row label."""

    rows = re.findall(
        r"^\|\s*`?([^|`]+?)`?\s*\|\s*`(#[0-9A-Fa-f]{6})`\s*\|",
        TOKEN_SPEC.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    return {label.strip(): value.upper() for label, value in rows}


def _specified_category_palette() -> list[str]:
    rows = re.findall(
        r"^\|\s*\d+\s*\|\s*\w+\s*\|\s*`(#[0-9A-Fa-f]{6})`\s*\|",
        TOKEN_SPEC.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    return [value.upper() for value in rows]


def test_the_spec_is_still_readable_by_this_test() -> None:
    """A guard on the guards: a reformatted table must not silently pass."""

    assert len(_specified_colours()) >= 15
    assert len(_specified_category_palette()) == 10


def test_every_colour_the_spec_freezes_is_declared_in_the_theme() -> None:
    declared = {
        value.strip('"').upper()
        for value in _theme_declarations().values()
        if value.startswith('"#')
    }
    palette = set(_specified_category_palette())
    missing = [
        f"{label} ({value})"
        for label, value in _specified_colours().items()
        if value not in declared and value not in palette
    ]
    assert missing == [], f"Theme.qml does not carry: {', '.join(missing)}"


def test_the_theme_invents_no_colour_the_spec_does_not_name() -> None:
    specified = set(_specified_colours().values()) | set(_specified_category_palette())
    written = {
        literal.upper()
        for literal in _COLOUR_LITERAL.findall(
            _without_comments(THEME.read_text(encoding="utf-8"))
        )
    }
    assert written <= specified, (
        f"Theme.qml writes colours the spec does not name: {sorted(written - specified)}"
    )


def test_the_category_palette_is_carried_in_the_spec_s_order() -> None:
    declaration = _theme_declarations()["categoryPalette"]
    block = THEME.read_text(encoding="utf-8").split("categoryPalette", 1)[1]
    assert declaration.startswith("[")
    assert [
        value.upper() for value in _COLOUR_LITERAL.findall(block.split("]", 1)[0])
    ] == _specified_category_palette()


#: The metrics table in the token spec, mapped onto the properties that carry
#: them. Spelled out rather than derived, so a renamed row fails here instead
#: of quietly dropping a metric from the comparison.
_METRIC_PROPERTIES = {
    "Toolbar height": "toolbarHeight",
    "Transport height": "transportHeight",
    "Clip row height": "clipRowHeight",
    "Clip editor width": "editorWidth",
    "Control height": "controlHeight",
    "Border width": "border",
}


def _specified_metrics() -> dict[str, str]:
    rows = re.findall(
        r"^\|\s*([A-Z][^|]*?)\s*\|\s*(\d+)\s*\|\s*$",
        TOKEN_SPEC.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    return {label.strip(): value for label, value in rows}


def test_every_metric_the_spec_freezes_is_declared_in_the_theme() -> None:
    specified = _specified_metrics()
    declared = _theme_declarations()

    for label, property_name in _METRIC_PROPERTIES.items():
        assert label in specified, f"the token spec no longer names {label!r}"
        assert declared.get(property_name) == specified[label], (
            f"Theme.{property_name} does not carry the spec's {label}"
        )


def test_the_theme_carries_the_metrics_the_spec_states_in_prose() -> None:
    declared = _theme_declarations()

    assert declared["unit"] == "4"
    assert declared["gutter"] == "16"
    assert declared["gap"] == "8"
    assert declared["radius"] == "3"
    assert declared["sidebarWidth"] == "300"
    assert declared["sidebarMinimum"] == "260"
    assert declared["sidebarMaximum"] == "420"
    assert declared["rulerHeight"] == "16"
    assert declared["trackHeight"] == "44"
    assert declared["timelineHeight"] == "rulerHeight + trackHeight"
    assert declared["minimumRangeWidth"] == "3"
    assert declared["categoryHeaderHeight"] == "30"
    assert declared["iconSize"] == "16"
    assert declared["transportIconSize"] == "20"
    assert declared["sizeTitle"] == "15"
    assert declared["sizeRow"] == "13"
    assert declared["sizeBody"] == "12"
    assert declared["sizeLabel"] == "11"
    assert declared["sizeTimecode"] == "12"
    assert declared["sizeRuler"] == "10"


# --- The vendored typography and icon family -------------------------------


def test_the_theme_names_the_vendored_families_python_registers() -> None:
    declared = _theme_declarations()
    assert declared["uiFamily"] == f'"{UI_FONT_FAMILY}"'
    assert declared["monoFamily"] == f'"{TIMECODE_FONT_FAMILY}"'


def test_the_families_the_theme_names_are_available_to_the_window(
    application: QApplication,
) -> None:
    families = set(QFontDatabase.families())
    assert UI_FONT_FAMILY in families
    assert TIMECODE_FONT_FAMILY in families


def _referenced_icons() -> set[str]:
    names: set[str] = set()
    for component in qml_components():
        source = _without_comments(component.read_text(encoding="utf-8"))
        names.update(re.findall(r'Theme\.icon\(\s*"([^"]+)"', source))
        names.update(re.findall(r'iconName:\s*"([^"]+)"', source))
    return names


def test_every_icon_the_shell_names_is_vendored() -> None:
    referenced = _referenced_icons()
    assert referenced, "the shell references no icons at all"
    assert referenced <= set(icon_family.available_icons()), (
        f"not vendored: {sorted(referenced - set(icon_family.available_icons()))}"
    )


def test_the_provider_serves_every_icon_the_shell_names(
    application: QApplication,
) -> None:
    provider = IconProvider()
    for name in sorted(_referenced_icons()):
        image = provider.requestImage(
            f"{name}?color=%23E8EAED", QSize(), QSize(32, 32)
        )
        assert not image.isNull(), f"the provider rendered nothing for {name}"
        assert image.width() == 32


def test_the_provider_reports_an_unvendored_icon_as_nothing(
    application: QApplication,
) -> None:
    provider = IconProvider()
    image = provider.requestImage("not-an-icon?color=%23E8EAED", QSize(), QSize(32, 32))
    assert image.isNull()


# --- The shell itself ------------------------------------------------------


def test_the_toolbar_placeholder_title_is_the_workflow_s_own() -> None:
    """The shell shows what a freshly started application shows.

    #47 replaces this with the workflow's live title. Pinning it meanwhile
    means the placeholder cannot drift into a second spelling of the same idea.
    """

    source = quick_scene_path().read_text(encoding="utf-8")
    assert f'property string analysisTitle: "{UNTITLED_ANALYSIS_TITLE}"' in source


# --- Starting into the workspace -------------------------------------------


def _options(*arguments: str) -> object:
    from main import build_argument_parser

    parsed, _ = build_argument_parser().parse_known_args(list(arguments))
    return parsed


def test_the_existing_interface_is_still_what_starting_the_application_gives() -> None:
    from main import WIDGETS_INTERFACE, selected_interface

    assert selected_interface(_options(), {}) == WIDGETS_INTERFACE


def test_the_qml_workspace_can_be_asked_for_on_the_command_line() -> None:
    from main import QML_INTERFACE, selected_interface

    assert selected_interface(_options("--qml"), {}) == QML_INTERFACE


def test_the_qml_workspace_can_be_asked_for_without_a_command_line() -> None:
    """A packaged application is double-clicked; there is nowhere to type."""

    from main import QML_INTERFACE, QML_WORKSPACE_VARIABLE, selected_interface

    assert selected_interface(_options(), {QML_WORKSPACE_VARIABLE: "1"}) == QML_INTERFACE
    assert selected_interface(_options(), {QML_WORKSPACE_VARIABLE: ""}) == "widgets"


def _smoke_report(
    tmp_path: Path, *arguments: str, **overrides: str
) -> dict[str, object]:
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["VIDEO_ANALYSE_LOG_DIR"] = str(tmp_path / "logs")
    environment.pop("VIDEO_ANALYSE_QML_WORKSPACE", None)
    environment.update(overrides)

    result = subprocess.run(
        [sys.executable, "main.py", "--smoke-test", *arguments],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_a_started_application_reports_which_interface_it_would_show(
    tmp_path: Path,
) -> None:
    assert _smoke_report(tmp_path)["interface"] == "widgets"
    assert _smoke_report(tmp_path, "--qml")["interface"] == "qml"
    assert _smoke_report(tmp_path, VIDEO_ANALYSE_QML_WORKSPACE="1")["interface"] == "qml"


def test_the_workspace_shell_renders_a_frame_with_no_warning(tmp_path: Path) -> None:
    """The whole path: the engine, the components, the icons, the backend."""

    report = _smoke_report(tmp_path, "--qml")

    assert report["sceneRendered"] is True
    assert report["qmlWarnings"] == []
    assert Path(str(report["qml"])) == QML_ROOT / "Main.qml"
    # The typography is registered before the window is built, so the families
    # `Theme.qml` names are the ones the window actually draws with.
    assert report["fonts"] == [UI_FONT_FAMILY, TIMECODE_FONT_FAMILY]
