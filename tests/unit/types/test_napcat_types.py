"""
NapCat 响应类型模型规范测试

规范:
  N-01: NapCatModel 自动将 int 类型 *_id 字段转为 str
  N-03: NapCatModel 允许额外字段 (extra="allow")
  N-04: SendMessageResult 将 int message_id 转为 str
  N-06: 群文件列表兼容 int uploader / creator
"""

from ncatbot.types.napcat import (
    GroupFileList,
    NapCatModel,
    SendMessageResult,
)


# ---- N-01: ID 强转 ----


class _IdModel(NapCatModel):
    user_id: str = ""
    group_id: str = ""


def test_napcat_model_coerces_int_id_to_str():
    """N-01: NapCatModel 将 int 类型 *_id 字段自动转为 str"""
    m = _IdModel.model_validate({"user_id": 12345, "group_id": 67890})
    assert m.user_id == "12345"
    assert m.group_id == "67890"


# ---- N-03: 额外字段 ----


def test_napcat_model_extra_fields():
    """N-03: NapCatModel 允许额外字段"""
    m = SendMessageResult.model_validate({"message_id": "1", "extra_field": "value"})
    assert m.message_id == "1"
    assert m.extra_field == "value"


# ---- N-04: SendMessageResult ----


def test_send_message_result_int_coerce():
    """N-04: SendMessageResult 将 int message_id 转为 str"""
    r = SendMessageResult.model_validate({"message_id": 123})
    assert r.message_id == "123"


# ---- N-06: GroupFileList ----


def test_group_file_list_coerces_int_uploader_and_creator():
    """N-06: NapCat 群文件列表中的 uploader / creator 可为 int"""
    result = GroupFileList.model_validate(
        {
            "files": [
                {
                    "group_id": 10001,
                    "file_id": "file-1",
                    "file_name": "1429682.pdf",
                    "uploader": 1620404337,
                }
            ],
            "folders": [
                {
                    "group_id": 10001,
                    "folder_id": "folder-1",
                    "folder_name": "本子",
                    "creator": 464692632,
                }
            ],
        }
    )

    assert result.files[0].group_id == "10001"
    assert result.files[0].uploader == "1620404337"
    assert result.folders[0].group_id == "10001"
    assert result.folders[0].creator == "464692632"
