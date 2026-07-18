"""Compatibility checks for domain-focused built-in tool modules."""

from aero.toolbox import builtin_tools
from aero.toolbox.registry import get_registry

MIGRATED_TOOLS = (
    "launch_sub_agent",
    "query_sub_agents",
    "cancel_sub_agent",
    "search_datasets",
    "search_dataset_variables",
    "search_dataset_stations",
    "describe_dataset",
    "download_dataset",
    "parse_isd_csv",
    "inspect_csv_table",
    "scan_local_files",
    "record_instruction",
    "show_instructions",
    "clear_instructions",
    "record_memo",
    "show_memos",
    "update_memo",
    "delete_memo",
    "clear_memos",
    "initialize_paper_versioning",
    "paper_version_status",
    "save_paper_version",
    "list_paper_versions",
    "diff_paper_version",
    "restore_paper_version",
    "export_paper",
    "search_literature",
    "search_web",
    "save_literature",
    "download_literature_pdf",
    "list_literature",
    "write_plan_document",
    "propose_execution",
    "create_checkpoint",
    "list_checkpoints",
    "compare_checkpoint",
    "rename_checkpoint",
    "start_checkpoint_experiment",
    "configure_email_config",
    "check_email_config",
    "send_email",
    "inspect_nc",
    "subset_netcdf",
    "list_files",
    "list_figures",
    "delete_file",
    "read_file",
    "write_file",
    "edit_file",
    "read_pdf",
    "preview_image",
    "preview_pdf",
    "ensure_runtime_tools",
    "run_shell",
    "list_downloads",
    "query_download",
    "retry_download",
    "cleanup_downloads",
    "check_cds_config",
    "configure_cds_key",
    "list_llm_providers",
    "configure_llm_provider",
    "clear_llm_config",
    "clear_cds_config",
    "check_vision_model_config",
    "analyze_image",
    "configure_vision_model",
)


def test_migrated_tools_remain_available_from_compatibility_module():
    for name in MIGRATED_TOOLS:
        assert hasattr(builtin_tools, name)


def test_migrated_tools_are_registered():
    registry = get_registry()
    for name in MIGRATED_TOOLS:
        assert registry.get(name) is not None


def test_local_data_scan_only_requires_confirmation_when_registering():
    from aero.agent.loop import _tool_call_needs_confirmation
    from aero.toolbox.registry import get_registry

    spec = get_registry().get("scan_local_files")

    assert spec is not None
    assert spec.requires_confirmation is True
    assert _tool_call_needs_confirmation("scan_local_files", {"confirm": False}) is False
    assert _tool_call_needs_confirmation("scan_local_files", {"confirm": True}) is True


def test_preview_image_tool_description_requires_inline_image_too():
    tool = get_registry().get("preview_image")

    assert tool is not None
    assert "明确说打开图片" in tool.description
    assert "Markdown 图片语法" in tool.description
    assert "嵌入对话框" in tool.description
    assert "不能替代对话内预览" in tool.description


def test_preview_pdf_tool_description_distinguishes_opening_from_reading():
    tool = get_registry().get("preview_pdf")

    assert tool is not None
    assert "系统默认 PDF 查看器" in tool.description
    assert "不要让用户自己复制路径" in tool.description
