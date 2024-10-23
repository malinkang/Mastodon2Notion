import argparse
import json
import os
import pendulum
from retrying import retry
import requests
from notion_helper import NotionHelper
import utils
from mastodon import Mastodon
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

from config import (
    TAG_ICON_URL,
)
from utils import get_icon


def get_timelines():
    results = []
    # 获取当前用户的 ID
    current_user = mastodon.account_verify_credentials()
    current_user_id = current_user["id"]
    # 初始化分页参数
    max_id = None
    while True:
        break_out = False
        # 获取当前用户的时间线（自己发布的内容），每次获取100条
        user_timeline = mastodon.account_statuses(
            current_user_id, max_id=max_id, limit=100
        )
        # 检查是否有更多数据
        if not user_timeline:
            break
        for timeline in user_timeline:
            created_at = int(
                    timeline.get("created_at")
                    .replace(second=0, microsecond=0)
                    .timestamp()
                )
            if created_at<= latest:
                break_out = True
                break
            results.append(timeline)
        if break_out:
            break
        # 处理和保存每条 toot
        results.extend(user_timeline)
        max_id = user_timeline[-1]["id"] - 1
    return results


def get_latest():
    sorts = [{"property": "日期", "direction": "descending"}]
    r = notion_helper.query(
        database_id=notion_helper.content_database_id, sorts=sorts, page_size=1
    )
    if len(r.get("results")):
        return utils.get_property_value(
            r.get("results")[0].get("properties").get("日期")
        )
    return 0


if __name__ == "__main__":
    notion_helper = NotionHelper()
    latest = get_latest()
    mastodon = Mastodon(
        api_base_url=os.getenv("MASTODON_API_BASE_URL"),
        access_token=os.getenv("MASTODON_ACCESS_TOKEN"),
    )
    timelines = get_timelines()
    d = notion_helper.get_property_type(notion_helper.content_database_id)
    for timeline in timelines:
        title = ""
        if timeline.get("content"):
            soup = BeautifulSoup(timeline.get("content"), "lxml")
            title = "".join(soup.p.find_all(text=True, recursive=False))
        status = {
            "标题": title,
            "id": str(timeline.get("id")),
            "链接": timeline.get("url"),
            "日期": int(timeline.get("created_at").timestamp()),
        }
        if timeline.get("tags"):
            status["标签"] = [
                notion_helper.get_relation_id(
                    x.get("name"),
                    notion_helper.tag_database_id,
                    icon=TAG_ICON_URL,
                )
                for x in timeline.get("tags")
            ]
        if timeline.get("media_attachments"):
            status["资源"] = [
                notion_helper.get_relation_id(
                    str(x.get("id")),
                    notion_helper.image_database_id,
                    icon=TAG_ICON_URL,
                    properties={
                        "链接": {
                            "files": [
                                {
                                    "type": "external",
                                    "name": "Cover",
                                    "external": {"url": x.get("url")},
                                }
                            ]
                        }
                    },
                )
                for x in timeline.get("media_attachments")
            ]
        properties = utils.get_properties(status, d)
        notion_helper.get_all_relation(properties)
        notion_helper.get_date_relation(
            properties,
            date=pendulum.from_timestamp(status.get("日期"), tz="Asia/Shanghai"),
        )
        parent = {
            "database_id": notion_helper.content_database_id,
            "type": "database_id",
        }
        icon = {"type": "emoji", "emoji": "📝"}
        notion_helper.create_page(parent=parent, properties=properties, icon=icon)
