'''
Author: zhouyuchong
Date: 2025-08-04 10:48:42
Description: parse group message
LastEditors: zhouyuchong
LastEditTime: 2025-08-13 16:13:27
'''
import re
import time
import asyncio 

from .jmcomic_crawler import jmcomic_crawler, jm_search
from .setu import setu_get_url, download_image
from .daily import daily_function
from .constants import *

async def message_parser(msg, last_time, logger):
    return_msg = dict()
    return_msg['upload_file'] = False
    return_msg['direct_upload'] = False

    jm_msg_match = re.search(JM_MATCH, msg)
    if jm_msg_match:
        if last_time and time.time() - last_time < DOWNLOAD_TIME_INTERVAL:
            return_msg['text'] = f"太频繁啦, 请在{DOWNLOAD_TIME_INTERVAL-int(time.time()-last_time)}秒后再试"
            return_msg['updated_time'] = last_time
            return return_msg

        after_jm = jm_msg_match.group(1).strip() 
        if re.fullmatch(r'\d+', after_jm):
            # jm_result = re.match(JMCOMIC_PATTERN, jm_result)
            jm_number = int(after_jm)
            file_name, file_path = jmcomic_crawler(jm_number, logger)
            return_msg['file_name'] = file_name
            return_msg['file_path'] = file_path
            return_msg['upload_file'] = True
            return_msg['upload_folder_name'] = '本子'
            return_msg['text'] = f"文件已上传"
            return_msg['updated_time'] = time.time()
            return return_msg
        else:
            jm_tags = after_jm.split()
            text = jm_search(jm_tags, logger)
            return_msg['text'] = text
            return_msg['updated_time'] = last_time
            return return_msg

    setu_match = re.search(SETU_PATTERN, msg)
    if setu_match:
        tags = setu_match.group(1)
        tags = [[tag] for tag in tags.strip().split()] if tags else []
        logger.debug(f"setu tags: {tags}")
        if len(tags) > 3:
            return_msg['text'] = f"最多支持3个标签"
            return_msg['updated_time'] = last_time
            return return_msg
        retry = 0
        url_request_retry = 1
        while True:
            if retry > 3:
                return_msg['text'] = f"尝试了{retry}次, 都失败了喵"
                return_msg['updated_time'] = last_time
                return return_msg
            try: 
                if url_request_retry:
                    ret, url = await setu_get_url(tags, logger)
                    url_request_retry = 0
                if not ret:
                    return_msg['text'] = url
                    return_msg['updated_time'] = last_time
                    return return_msg

                logger.debug(f"setu url: {url}")
                if url:
                    file_name = os.path.basename(url)
                    file_name = file_name.replace('.jpg', '.png')
                    file_path = os.path.join(IMAGE_DIR, file_name)
                    download_ret = await download_image(url, file_path, logger)
                    if not download_ret:
                        url_request_retry = 1
                        retry += 1
                        continue
                return_msg['file_name'] = file_name
                return_msg['file_path'] = file_path
                return_msg['upload_file'] = True
                return_msg['upload_folder_name'] = '涩图'
                return_msg['text'] = f"请查收"
                return_msg['updated_time'] = last_time
                # return_msg['direct_upload'] = True
                return return_msg
            except Exception as e:
                logger.error(f"setu error: {e}")
                retry += 1

    if "每日新闻" in msg:
        file_path = await daily_function()
        return_msg['file_name'] = ""
        return_msg['file_path'] = file_path
        return_msg['upload_file'] = True
        return_msg['direct_upload'] = True
        return_msg['text'] = f"请查收"
        return_msg['updated_time'] = last_time
        return return_msg

    return_msg['text'] = f"无法理解喵"
    return_msg['updated_time'] = last_time
    return return_msg
    