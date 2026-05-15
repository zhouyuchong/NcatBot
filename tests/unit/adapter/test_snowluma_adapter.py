"""SnowLuma 适配器单元测试。

规范:
  SL-01: 内置适配器注册表包含 snowluma
  SL-02: SnowLumaConfig 规范化 URI 并拼接 access_token
  SL-03: cli_configure 自动安装分支跳过手动输入并返回默认值
  SL-04: cli_configure 手动分支采集地址、Token 与 skip_setup
"""

from __future__ import annotations

from unittest.mock import patch

from ncatbot.adapter import SnowLumaAdapter, adapter_registry
from ncatbot.adapter.snowluma.config import SnowLumaConfig


def test_snowluma_adapter_is_registered():
    """SL-01: 内置 adapter_registry 可发现 snowluma。"""
    discovered = adapter_registry.discover()

    assert discovered["snowluma"] is SnowLumaAdapter


def test_snowluma_config_normalizes_uris_and_token():
    """SL-02: 规范化 URI，并将 token 追加到 access_token 查询参数。"""
    cfg = SnowLumaConfig(
        ws_uri="127.0.0.1:3001",
        webui_uri="localhost:5099",
        ws_token="token with space",
    )

    assert cfg.ws_uri == "ws://127.0.0.1:3001"
    assert cfg.webui_uri == "http://localhost:5099"
    assert (
        cfg.get_uri_with_token()
        == "ws://127.0.0.1:3001?access_token=token%20with%20space"
    )


def test_cli_configure_auto_install_skips_manual_prompts():
    """SL-03: 自动安装分支应跳过手动输入并返回默认连接参数。"""
    with (
        patch("click.echo"),
        patch("click.confirm", return_value=True) as mock_confirm,
        patch("click.prompt") as mock_prompt,
        patch.object(SnowLumaAdapter, "_cli_install_snowluma") as mock_install,
    ):
        config = SnowLumaAdapter.cli_configure()

    mock_install.assert_called_once_with()
    mock_prompt.assert_not_called()
    assert mock_confirm.call_count == 1
    assert config == {
        "ws_uri": "ws://localhost:3001",
        "ws_token": "",
        "webui_uri": "http://localhost:5099",
        "skip_setup": False,
    }


def test_cli_configure_manual_flow_collects_fields():
    """SL-04: 手动分支应逐项采集 ws/webui 参数与 skip_setup。"""
    with (
        patch("click.echo"),
        patch("click.confirm", side_effect=[False, True]),
        patch(
            "click.prompt",
            side_effect=[
                "ws://127.0.0.1:3002",
                "secret-token",
                "http://127.0.0.1:5100",
            ],
        ),
        patch.object(SnowLumaAdapter, "_cli_install_snowluma") as mock_install,
    ):
        config = SnowLumaAdapter.cli_configure()

    mock_install.assert_not_called()
    assert config == {
        "ws_uri": "ws://127.0.0.1:3002",
        "ws_token": "secret-token",
        "webui_uri": "http://127.0.0.1:5100",
        "skip_setup": True,
    }
