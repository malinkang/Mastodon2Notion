import json
import os
import pendulum
import requests

from notion_helper import NotionHelper
import mistletoe
from mistletoe import HtmlRenderer
from notion_helper import NotionHelper
from notion_renderer import NotionPyRenderer
import utils

base_url = os.getenv("MEMOS_URL")
def authenticate_user():
    url = f"{base_url}api/v1/auth/signin"
    data = {
        "email": os.getenv("MEMOS_USERNAME"),
        "username": os.getenv("MEMOS_USERNAME"),
        "password": os.getenv("MEMOS_PASSWORD"),
        "remember": True
    }

    response = requests.post(url, json=data)
    print(response.text)
    if response.status_code == 200:
        return response.cookies
    else:
        return None

def get_memos(cookies,ids):
    url = f"{base_url}api/v1/memo"
    params = {
        "rowStatus": "NORMAL"
    }
    response = requests.get(url, params=params, cookies=cookies)
    timelines = response.json()
    for timeline in timelines:
        print(timeline)
        id = str(timeline.get("id"))
        if id in ids:
            print(f"{id} 已经存在")
            continue
        title = timeline.get("content")
        children = []
        status = {
            "标题": title,
            "id": id,
            "日期": int(timeline.get("createdTs")),
            "平台":"memos",
            "链接":f"{base_url}m/{timeline.get('name')}"
        }
        l = mistletoe.markdown(title, NotionPyRenderer)
        children.extend(l)
        if timeline.get("resourceList"):
            status["资源"] = [
                notion_helper.get_relation_id(
                    str(x.get("id")),
                    notion_helper.image_database_id,
                    x.get("externalLink"),
                    properties={
                        "链接": {
                            "files": [
                                {
                                    "type": "external",
                                    "name": "Cover",
                                    "external": {"url": x.get("externalLink")},
                                }
                            ]
                        }
                    },
                )
                for x in timeline.get("resourceList")
            ]
            children.extend([utils.get_image(x.get("externalLink")) for x in timeline.get("resourceList")])
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
        page_id = notion_helper.create_page(parent=parent, properties=properties, icon=icon).get("id")
        notion_helper.append_blocks(page_id,children)




if __name__ == "__main__":
    notion_helper = NotionHelper()
    cookies = authenticate_user()
    d = notion_helper.get_property_type(notion_helper.content_database_id)
    filter = {
        "property": "平台",
        "select": {
            "equals": "memos"
        }
    }
    notion_data = notion_helper.query_all_by_filter(notion_helper.content_database_id,filter)
    ids = [ utils.get_property_value(result.get("properties").get("id")) for result in notion_data]
    if cookies:
        get_memos(cookies,ids)
    else:
        print("Authentication failed.")
