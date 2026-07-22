import ast
from pathlib import Path

from project_manager import __version__
from project_manager.app import FormatProjectManagerTitle


def _GetAppModuleAst() -> ast.Module:
    _appPath = Path(__file__).resolve().parents[1] / "project_manager" / "app.py"
    _sourceText = _appPath.read_text(encoding="utf-8")
    return ast.parse(_sourceText)


def _GetClassNode(moduleAst: ast.Module, className: str) -> ast.ClassDef:
    for _node in moduleAst.body:
        if isinstance(_node, ast.ClassDef) and _node.name == className:
            return _node
    raise AssertionError(f"Class {className} not found in app.py")


def _GetClassMethodNames(classNode: ast.ClassDef) -> set[str]:
    return {
        _item.name
        for _item in classNode.body
        if isinstance(_item, ast.FunctionDef)
    }


def _GetRequiredLayoutActionMethods() -> set[str]:
    return {
        "_RenameProjectInline",
        "_CopyProject",
        "_DeleteProject",
        "_OnCloneWorkspace",
        "_CloneWorkspace",
        "_CreateEmptyProject",
        "_CreateEmptyGame",
        "_CopyGame",
        "_DeleteGame",
        "_RenameGameInline",
        "_AddScene",
        "_CopyScene",
        "_DeleteScene",
        "_RenameSceneInline",
        "_PlayScene",
    }


def test_layout_defines_all_action_handler_methods() -> None:
    _moduleAst = _GetAppModuleAst()
    _layoutNode = _GetClassNode(_moduleAst, "ProjectManagerLayout")
    _layoutMethods = _GetClassMethodNames(_layoutNode)
    _requiredMethods = _GetRequiredLayoutActionMethods()

    _missingMethods = sorted(_requiredMethods - _layoutMethods)
    assert not _missingMethods, f"Missing action methods on ProjectManagerLayout: {_missingMethods}"


def test_item_row_does_not_define_layout_action_handlers() -> None:
    _moduleAst = _GetAppModuleAst()
    _requiredMethods = _GetRequiredLayoutActionMethods()

    _itemRowNode = _GetClassNode(_moduleAst, "ItemRow")
    _itemRowMethods = _GetClassMethodNames(_itemRowNode)
    _wronglyPlacedMethods = sorted(_requiredMethods.intersection(_itemRowMethods))
    assert not _wronglyPlacedMethods, (
        f"ItemRow should not define layout action methods: {_wronglyPlacedMethods}"
    )


def test_clone_workspace_prompt_uses_folder_picker() -> None:
    _moduleAst = _GetAppModuleAst()
    _layoutNode = _GetClassNode(_moduleAst, "ProjectManagerLayout")
    _pickMethod = next(
        (_item for _item in _layoutNode.body if isinstance(_item, ast.FunctionDef) and _item.name == "_PickCloneDestinationFolder"),
        None,
    )

    assert _pickMethod is not None, "ProjectManagerLayout must define _PickCloneDestinationFolder."

    _callNames = {
        _node.func.attr
        for _node in ast.walk(_pickMethod)
        if isinstance(_node, ast.Call) and isinstance(_node.func, ast.Attribute)
    }
    assert "askdirectory" in _callNames, "Clone workspace folder picker must call askdirectory()."


def test_title_includes_version_and_workspace_root() -> None:
    _titleText = FormatProjectManagerTitle("clone-alpha", "corgogame", "helloworld")

    assert f"v{__version__}" in _titleText
    assert "clone-alpha" in _titleText
    assert "corgogame" in _titleText
    assert "helloworld" in _titleText
