"""SnowLuma CLI 单元测试。

规范:
  CX-16: snowluma 一级命令 --help 可正常退出
  CX-17: snowluma diagnose 子组 --help 可正常退出
  CX-18: snowluma diagnose ws 将 --uri/--token 传入 _check_ws
  CX-19: snowluma stop 在 Linux 下调用平台 stop 逻辑
  CX-20: snowluma install --yes 绑定到 skip_confirm 路径
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner

from ncatbot.cli.main import cli


def test_snowluma_help():
    """CX-16: snowluma --help 可正常退出。"""
    runner = CliRunner()

    result = runner.invoke(cli, ["snowluma", "--help"], catch_exceptions=False)

    assert result.exit_code == 0


def test_snowluma_diagnose_help():
    """CX-17: snowluma diagnose --help 可正常退出。"""
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["snowluma", "diagnose", "--help"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0


def test_snowluma_diagnose_ws_binds_uri_token():
    """CX-18: snowluma diagnose ws 将参数绑定到 WS 探针。"""
    runner = CliRunner()
    mock_check = AsyncMock(return_value=None)

    with patch("ncatbot.cli.commands.snowluma._check_ws", mock_check):
        result = runner.invoke(
            cli,
            [
                "snowluma",
                "diagnose",
                "ws",
                "--uri",
                "ws://127.0.0.1:3001",
                "--token",
                "tok",
            ],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    mock_check.assert_awaited_once_with("ws://127.0.0.1:3001", "tok")


def test_snowluma_stop_calls_platform_ops_on_linux():
    """CX-19: snowluma stop 在 Linux 下调用 stop_snowluma。"""
    runner = CliRunner()
    mock_ops = MagicMock()

    with (
        patch("platform.system", return_value="Linux"),
        patch(
            "ncatbot.adapter.snowluma.setup.platform.PlatformOps.create",
            return_value=mock_ops,
        ),
    ):
        result = runner.invoke(
            cli,
            ["snowluma", "stop"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    mock_ops.stop_snowluma.assert_called_once_with()
    assert "停止指令已发送" in result.output


def test_snowluma_install_yes_binds_skip_confirm():
    """CX-20: snowluma install --yes 应绑定 skip_confirm=True。"""
    runner = CliRunner()
    mock_ops = MagicMock()
    mock_ops.is_snowluma_installed.return_value = False

    with (
        patch(
            "ncatbot.adapter.snowluma.setup.platform.PlatformOps.create",
            return_value=mock_ops,
        ),
        patch(
            "ncatbot.adapter.snowluma.setup.installer.SnowLumaInstaller"
        ) as mock_installer_cls,
    ):
        mock_installer_cls.return_value.install.return_value = True
        result = runner.invoke(
            cli,
            ["snowluma", "install", "--yes"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    mock_installer_cls.return_value.install.assert_called_once_with(skip_confirm=True)
