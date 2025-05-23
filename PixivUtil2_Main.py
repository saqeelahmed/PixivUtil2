#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# flake8: noqa:E501,E128,E127

import codecs
import datetime
import gc
import getpass
import os
import platform
import re
import subprocess
import sys
import traceback
from optparse import OptionParser

import colorama
from colorama import Back, Fore, Style

import PixivArtistHandler
import PixivBatchHandler
import PixivBookmarkHandler
import PixivBrowserFactory
import PixivConfig
import PixivConstant
import PixivFanboxHandler
import PixivHelper
import PixivImageHandler
import PixivListHandler
import PixivModelFanbox
import PixivNovelHandler
import PixivRankingHandler
import PixivSketchHandler
import PixivTagsHandler
from PixivDBManager import PixivDBManager
from PixivException import PixivException
from PixivTags import PixivTags

colorama.init()
DEBUG_SKIP_PROCESS_IMAGE = False
DEBUG_SKIP_DOWNLOAD_IMAGE = False




# Module-level globals
script_path = PixivHelper.module_path()
op = ''
ERROR_CODE = 0
UTF8_FS = None

__config__ = PixivConfig.PixivConfig()
configfile = "config.ini"
__dbManager__ = None
__br__ = None
__blacklistTags = []
__suppressTags = []
__log__ = None
__errorList = []
__blacklistMembers = []
__blacklistTitles = []
__valid_options = ()
__seriesDownloaded = []

start_iv = False
dfilename = ""

# move to external file PixivUtil2_Platform.py
from PixivUtil2_Platform import platform_encoding

# move to external file PixivUtil2_Header
from PixivUtil2_Header import print_header

# move to external file PixivUtil2_Menu
from PixivUtil2_Menu import get_menu

# move to external file PixivUtil2_OptionParser.py
from PixivUtil2_OptionParser import setup_option_parser

# move to external file PixivUtil2_Inputs.py
from PixivUtil2_Inputs import ask, ask_int, ask_flag, ask_ids, handle_keyboard_interrupt

def get_validated_input(prompt, validation_func, error_msg="Invalid input"):
    while True:
        user_input = input(prompt).strip()
        if validation_func(user_input):
            return user_input
        print(error_msg)


def handle_pagination(options, default_pages=None):
    """Centralized pagination logic used by 10+ functions"""
    if options.start_page or options.end_page:
        return get_start_and_end_page_from_options(options)
    else:
        return PixivHelper.get_start_and_end_number(
            total_number_of_page=options.number_of_pages or default_pages
        )


def process_ids(handler):
    """Decorator for 7+ ID-based handlers"""
    def wrapper(op_is_valid, args, options):
        if op_is_valid and args:
            ids = [int(x) for x in args if x.isdigit()]
        else:
            ids = PixivHelper.get_ids_from_csv(input('IDs: '))
        for idx, item_id in enumerate(ids, 1):
            try:
                handler(item_id, idx, len(ids), options)
            except PixivException as ex:
                PixivHelper.print_and_log('error', f"ID Error: {ex}")
    return wrapper



def validate_selection(value, allowed):
    if value.lower() in allowed:
        return value.lower()
    raise ValueError(f"Invalid selection. Allowed: {', '.join(allowed)}")


def batch_error_handler(func):
    """Centralized error handling for 12+ functions"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PixivException as pe:
            PixivHelper.print_and_log('error', pe.message)
            global ERROR_CODE
            ERROR_CODE = pe.errorCode
        except KeyboardInterrupt:
            if not handle_keyboard_interrupt():
                sys.exit(1)
    return wrapper



def template_prompt(text, default, validation):
    prompt = f"{text} [default: {default}]: "
    while True:
        response = input(prompt).strip() or default
        if validation(response):
            return response


def process_list_file(options, default_file, config_dir):
    """Replaces 4 duplicate list-file handlers"""
    if options.list_file:
        full_path = os.path.join(config_dir, options.list_file)
        return full_path if os.path.exists(full_path) else default_file
    return default_file


def get_start_and_end_page_from_options(options):
    ''' Try to parse start and end page from options.'''
    page_num = 1
    if options.start_page is not None:
        try:
            page_num = int(options.start_page)
            print(f"Start Page = {page_num}")
        except BaseException:
            print(f"Invalid page number: {options.start_page}")
            raise

    end_page_num = 0
    if options.end_page is not None:
        try:
            end_page_num = int(options.end_page)
            print(f"End Page = {end_page_num}")
        except BaseException:
            print(f"Invalid end page number: {options.end_page}")
            raise
    elif options.number_of_pages is not None:
        end_page_num = options.number_of_pages
    else:
        end_page_num = __config__.numberOfPage

    if page_num > end_page_num and end_page_num != 0:
        print(f"Start Page ({page_num}) is bigger than End Page ({end_page_num}), assuming as page count ({page_num + end_page_num}).")
        end_page_num = page_num + end_page_num

    return page_num, end_page_num


def get_list_file_from_options(options, default_list_file):
    list_file_name = default_list_file
    if options.list_file is not None:
        if os.path.isabs(options.list_file):
            test_file_name = options.list_file
        else:
            test_file_name = __config__.downloadListDirectory + os.sep + options.list_file
        test_file_name = os.path.abspath(test_file_name)
        if os.path.exists(test_file_name):
            list_file_name = test_file_name
        else:
            PixivHelper.print_and_log("warn", f"The given list file [{test_file_name}] doesn't exists, using default list file [{list_file_name}].")
    return list_file_name


def set_console_title(title=''):
    set_title = f'PixivDownloader {PixivConstant.PIXIVUTIL_VERSION} {title}'
    PixivHelper.set_console_title(set_title)


def read_lists():
    # Implement #797
    if __config__.useBlacklistTags:
        global __blacklistTags
        __blacklistTags = PixivTags.parseTagsList("blacklist_tags.txt")
        PixivHelper.print_and_log('info', 'Using Blacklist Tags: ' + str(len(__blacklistTags)) + " items.")

    if __config__.useBlacklistMembers:
        global __blacklistMembers
        __blacklistMembers = PixivTags.parseTagsList("blacklist_members.txt")
        PixivHelper.print_and_log('info', 'Using Blacklist Members: ' + str(len(__blacklistMembers)) + " members.")

    if __config__.useBlacklistTitles:
        global __blacklistTitles
        __blacklistTitles = PixivTags.parseTagsList("blacklist_titles.txt")
        PixivHelper.print_and_log('info', 'Using Blacklist Titles: ' + str(len(__blacklistTitles)) + " items.")

    if __config__.useSuppressTags:
        global __suppressTags
        __suppressTags = PixivTags.parseTagsList("suppress_tags.txt")
        PixivHelper.print_and_log('info', 'Using Suppress Tags: ' + str(len(__suppressTags)) + " items.")


# move to external file PixivUtil2_Menu
menu = get_menu(read_lists, set_console_title)

# … next, all menu_* functions rewritten to use ask(), ask_int(), ask_flag(), ask_ids() …


def menu_download_by_member_id(opisvalid, args, options):
    __log__.info('Member id mode (1).')
    current_member = 1
    include_sketch = False

    if opisvalid and args:
        include_sketch = options.include_sketch
        if include_sketch:
            print("Including Pixiv Sketch.")
        page, end_page = get_start_and_end_page_from_options(options)
        member_ids = [int(x) for x in args if x.isdigit()]
    else:
        member_ids = ask_ids('Member ids')
        page, end_page = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
        default = __config__.defaultSketchOption.lower()
        if default in ('y', 'n'):
            include_sketch = (default == 'y')
            print("Including Pixiv Sketch." if include_sketch else "Excluding Pixiv Sketch.")
        else:
            include_sketch = (ask_flag('Include Pixiv Sketch', ('y', 'n'), 'n') == 'y')
        PixivHelper.print_and_log('info', f"Member IDs: {member_ids}")

    for member_id in member_ids:
        try:
            prefix = f"[{current_member} of {len(member_ids)}] "
            PixivArtistHandler.process_member(
                sys.modules[__name__], __config__, member_id,
                page=page, end_page=end_page, title_prefix=prefix
            )
            if include_sketch:
                artist_model, _ = __br__.getMemberPage(member_id)
                prefix = f"[{current_member} ({artist_model.artistToken}) of {len(member_ids)}] "
                PixivSketchHandler.process_sketch_artists(
                    sys.modules[__name__], __config__,
                    artist_model.artistToken, page, end_page, title_prefix=prefix
                )
            current_member += 1
        except PixivException:
            PixivHelper.print_and_log('error', f"Member ID: {member_id} is not valid")
            global ERROR_CODE
            ERROR_CODE = -1


def menu_download_by_member_bookmark(opisvalid, args, options):
    __log__.info('Member Bookmark mode (11).')
    page, end_page = 1, 0
    current_member = 1

    if opisvalid and args:
        valid_ids = []
        for m in args:
            try:
                valid_ids.append(int(m))
            except:
                PixivHelper.print_and_log('error', f"Member ID: {m} is not valid")
                ERROR_CODE = -1
        if __br__._myId in valid_ids:
            PixivHelper.print_and_log('error', f"Member ID: {__br__._myId} is your own id, use option 6 instead.")
        for mid in valid_ids:
            prefix = f"[{current_member} of {len(valid_ids)}] "
            PixivArtistHandler.process_member(
                sys.modules[__name__], __config__, mid,
                page=page, end_page=end_page, bookmark=True, tags=None, title_prefix=prefix
            )
            current_member += 1
    else:
        member_id = ask('Member id')
        tags = ask('Filter Tags')
        page, end_page = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
        if __br__._myId == int(member_id):
            PixivHelper.print_and_log('error', f"Member ID: {member_id} is your own id, use option 6 instead.")
        else:
            PixivArtistHandler.process_member(
                sys.modules[__name__], __config__, member_id,
                page=page, end_page=end_page, bookmark=True, tags=tags
            )


def menu_download_by_image_id(opisvalid, args, options):
    __log__.info('Image id mode (2).')
    if opisvalid and args:
        for image_id in args:
            try:
                PixivImageHandler.process_image(
                    sys.modules[__name__], __config__,
                    artist=None, image_id=int(image_id), useblacklist=False
                )
            except:
                PixivHelper.print_and_log('error', f"Image ID: {image_id} is not valid")
                ERROR_CODE = -1
    else:
        image_ids = ask_ids('Image ids')
        for iid in image_ids:
            PixivImageHandler.process_image(
                sys.modules[__name__], __config__,
                artist=None, image_id=iid, useblacklist=False
            )


def menu_download_by_tags(opisvalid, args, options):
    __log__.info('Tags mode (3).')
    if opisvalid and args:
        wildcard = options.use_wildcard_tag
        sort_order = options.tag_sort_order
        start_date = options.start_date
        end_date = options.end_date
        bookmark_count = options.bookmark_count_limit
        page, end_page = get_start_and_end_page_from_options(options)
        tags = " ".join(args)
    else:
        tags = ask('Tags')
        bookmark_count = ask('Bookmark Count') or None
        wildcard = (ask_flag('Use Partial Match (s_tag)', ('y', 'n'), 'n') == 'y')
        if __br__._isPremium:
            sort_order = ask('Sorting Order [date_d|date|popular_d|popular_male_d|popular_female_d]', default='date_d')
        else:
            sort_order = 'date'
        page, end_page = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
        start_date, end_date = PixivHelper.get_start_and_end_date()
        while True:
            type_mode = ask('Search type [a-all|i-Illustration and Ugoira|m-manga]', default='a')
            if type_mode in ('a', 'i', 'm'):
                break
            print("Valid values are 'a', 'i', or 'm'.")
    if bookmark_count not in (None, -1) and bookmark_count != '':
        bookmark_count = int(bookmark_count)
    PixivTagsHandler.process_tags(
        sys.modules[__name__], __config__, tags.strip(),
        page=page, end_page=end_page, wild_card=wildcard,
        start_date=start_date, end_date=end_date,
        use_tags_as_dir=__config__.useTagsAsDir,
        bookmark_count=bookmark_count,
        sort_order=sort_order,
        type_mode=type_mode
    )


def menu_download_by_title_caption(opisvalid, args, options):
    __log__.info('Title/Caption mode (9).')
    if opisvalid and args:
        start_date = options.start_date
        end_date = options.end_date
        page, end_page = get_start_and_end_page_from_options(options)
        tags = " ".join(args)
    else:
        tags = ask('Title/Caption')
        page, end_page = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
        start_date, end_date = PixivHelper.get_start_and_end_date()
    PixivTagsHandler.process_tags(
        sys.modules[__name__], __config__, tags.strip(),
        page=page, end_page=end_page, wild_card=False,
        title_caption=True,
        start_date=start_date, end_date=end_date,
        use_tags_as_dir=__config__.useTagsAsDir
    )


def menu_download_by_tag_and_member_id(opisvalid, args, options):
    __log__.info('Tag and MemberId mode (10).')
    if opisvalid and len(args) >= 2:
        page, end_page = get_start_and_end_page_from_options(options)
        member_id = int(args[0]) if args[0].isdigit() else 0
        if member_id == 0:
            PixivHelper.print_and_log('error', f"Member ID: {args[0]} is not valid")
            ERROR_CODE = -1
            return
        tags = " ".join(args[1:])
        PixivHelper.safePrint(f"Looking tags: {tags} from memberId: {member_id}")
    else:
        member_id = int(ask('Member Id'))
        tags = ask('Tag')
        page, end_page = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
    PixivTagsHandler.process_tags(
        sys.modules[__name__], __config__, tags.strip(),
        page=page, end_page=end_page,
        use_tags_as_dir=__config__.useTagsAsDir,
        member_id=member_id
    )


def menu_download_from_list(opisvalid, args, options):
    __log__.info('Batch mode from list (4).')
    include_sketch = False
    default_list = __config__.downloadListDirectory + os.sep + 'list.txt'
    tags = None

    if opisvalid and args:
        include_sketch = options.include_sketch
        list_file = get_list_file_from_options(options, default_list)
        if args:
            tags = args[0]
    else:
        tags = ask('Tag') or None
        include_sketch = (ask_flag('Include Pixiv Sketch', ('y', 'n'), 'n') == 'y')
        list_file = default_list

    PixivListHandler.process_list(
        sys.modules[__name__], __config__,
        list_file_name=list_file,
        tags=tags,
        include_sketch=include_sketch
    )


def menu_download_from_online_user_bookmark(opisvalid, args, options):
    __log__.info('User Bookmarked Artist mode (5).')
    hide = ask_flag('Include Private bookmarks', ('y', 'n', 'o'), 'n')
    page = ask_int('Start Page', 1)
    end_page = ask_int('End Page', 0)
    bookmark_count = ask('Bookmark Count') or None

    PixivBookmarkHandler.process_bookmark(
        sys.modules[__name__], __config__,
        hide, page, end_page,
        bookmark_count=int(bookmark_count) if bookmark_count not in ('', None) else None
    )


def menu_download_from_online_image_bookmark(opisvalid, args, options):
    __log__.info("User's Image Bookmark mode (6).")
    hide = ask_flag('Include Private bookmarks', ('y', 'n', 'o'), 'n')
    tag = ask('Tag (press enter for all images)') or ''
    use_image_tag = False
    if tag:
        use_image_tag = (ask_flag('Use Image Tags as filter', ('y', 'n'), 'n') == 'y')
    page = ask_int('Start Page', 1)
    end_page = ask_int('End Page', 0)

    PixivBookmarkHandler.process_image_bookmark(
        sys.modules[__name__], __config__,
        hide=hide,
        start_page=page,
        end_page=end_page,
        tag=tag,
        use_image_tag=use_image_tag
    )


def menu_download_from_tags_list(opisvalid, args, options):
    __log__.info('Taglist mode (7).')
    if opisvalid and args:
        filename = get_list_file_from_options(options, './tags.txt')
        sort_order = options.tag_sort_order
        wildcard = options.use_wildcard_tag
        start_date = options.start_date
        end_date = options.end_date
        page, end_page = get_start_and_end_page_from_options(options)
        bookmark_count = options.bookmark_count_limit
    else:
        filename = ask('Tags list filename', './tags.txt')
        wildcard = (ask_flag('Use Wildcard', ('y', 'n'), 'n') == 'y')
        if __br__._isPremium:
            sort_order = ask('Sorting Order [date_d|date|popular_d|popular_male_d|popular_female_d]', 'date_d')
        else:
            sort_order = 'date'
        bookmark_count = ask('Bookmark Count') or None
        page, end_page = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
        start_date, end_date = PixivHelper.get_start_and_end_date()

    PixivListHandler.process_tags_list(
        sys.modules[__name__], __config__,
        filename, page, end_page,
        wild_card=wildcard,
        sort_order=sort_order,
        bookmark_count=int(bookmark_count) if bookmark_count not in ('', None) else None,
        start_date=start_date,
        end_date=end_date
    )


def menu_download_new_illust_from_bookmark(opisvalid, args, options):
    __log__.info('New Illust from Bookmark mode (8).')
    if opisvalid and options.bookmark_count_limit is not None:
        page_num, end_page_num = get_start_and_end_page_from_options(options)
        bookmark_count = options.bookmark_count_limit
    else:
        page_num, end_page_num = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
        bookmark_count = ask('Bookmark Count') or None

    PixivBookmarkHandler.process_new_illust_from_bookmark(
        sys.modules[__name__], __config__,
        page_num=page_num,
        end_page_num=end_page_num,
        bookmark_count=int(bookmark_count) if bookmark_count not in ('', None) else None
    )


def menu_download_by_manga_series_id(opisvalid, args, options):
    __log__.info('Manga Series mode (13).')
    if opisvalid and args:
        start_page, end_page = get_start_and_end_page_from_options(options)
        manga_series_ids = [int(x) for x in args if x.isdigit()]
    else:
        manga_series_ids = ask_ids('Manga Series IDs')
        start_page, end_page = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)

    for mid in manga_series_ids:
        PixivImageHandler.process_manga_series(
            sys.modules[__name__], __config__,
            manga_series_id=mid,
            start_page=start_page,
            end_page=end_page
        )


def menu_download_by_novel_id(opisvalid, args, options):
    __log__.info('Novel mode (14).')
    novel_ids = ask_ids('Novel IDs')
    for nid in novel_ids:
        PixivNovelHandler.process_novel(sys.modules[__name__], __config__, nid)


def menu_download_by_novel_series_id(opisvalid, args, options):
    __log__.info('Novel Series mode (15).')
    novel_series_ids = ask_ids('Novel Series IDs')
    start_page, end_page = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
    for nsid in novel_series_ids:
        PixivNovelHandler.process_novel_series(
            sys.modules[__name__], __config__, nsid,
            start_page=start_page,
            end_page=end_page
        )


def menu_download_by_group_id(opisvalid, args, options):
    __log__.info('Group mode (12).')
    if opisvalid and len(args) >= 3:
        group_id = args[0]
        limit = int(args[1])
        process_external = (args[2].lower() == 'y')
    else:
        group_id = ask('Group Id')
        limit = ask_int('Limit')
        process_external = (ask_flag('Process External Image', ('y', 'n'), 'n') == 'y')

    PixivBookmarkHandler.process_from_group(
        sys.modules[__name__], __config__,
        group_id,
        limit=limit,
        process_external=process_external
    )


def menu_download_by_unlisted_image_id(opisvalid, args, options):
    __log__.info('Unlisted ID mode (19).')
    if opisvalid and args:
        image_ids = args
    else:
        image_ids = ask_ids('Image ids', is_string=True)

    for iid in image_ids:
        PixivImageHandler.process_image(
            sys.modules[__name__], __config__,
            artist=None, image_id=iid,
            useblacklist=False, is_unlisted=True
        )


def menu_ugoira_reencode(opisvalid, args, options):
    __log__.info('Re-encode Ugoira (u)')
    print(Fore.YELLOW + Style.NORMAL + 'WARNING: THIS ACTION CANNOT BE UNDONE!' + Style.RESET_ALL)
    sure = ask_flag('Do you really want to proceed?', ('y', 'n'), 'n')
    if sure != 'y':
        return
    if __config__.overwrite:
        sure2 = ask_flag(
            'Overwrite is set: re-download from Pixiv instead of local re-encode?', 'y', 'n'
        )
        if sure2 != 'y':
            return
    PixivImageHandler.process_ugoira_local(sys.modules[__name__], __config__)


def menu_export_database_images(opisvalid, args, options):
    __log__.info('Export local database (l)')
    filename = ask('Filename', 'export-database.txt')
    use_pixiv = ask_flag('Include Pixiv database', ('y', 'n', 'o'), 'n')
    use_fanbox = ask_flag('Include Fanbox database', ('y', 'n', 'o'), 'n')
    use_sketch = ask_flag('Include Sketch database', ('y', 'n', 'o'), 'n')
    PixivBookmarkHandler.export_image_table(
        sys.modules[__name__], filename,
        use_pixiv, use_fanbox, use_sketch
    )


def menu_export_online_bookmark(opisvalid, args, options):
    __log__.info('Export Followed Artists mode (e).')
    filename = ask('Filename', 'export.txt')
    hide = ask_flag('Include Private bookmarks', ('y', 'n', 'o'), 'y')
    PixivBookmarkHandler.export_bookmark(
        sys.modules[__name__], __config__, filename, hide
    )


def menu_export_online_user_bookmark(opisvalid, args, options):
    __log__.info("Export Other's Followed Artist mode (m).")
    filename = ask('Filename', 'export-user.txt')
    member_id = ask('Member Id')
    if not member_id.isdigit():
        print("Invalid member id")
        return
    PixivBookmarkHandler.export_bookmark(
        sys.modules[__name__], __config__, filename, 'n', 1, 0, member_id
    )


def menu_export_from_online_image_bookmark(opisvalid, args, options):
    __log__.info("Export User's Image Bookmark mode (p).")
    filename = ask('Filename', 'Exported_images.txt')
    hide = ask_flag('Include Private bookmarks', ('y', 'n', 'o'), 'n')
    tag = ask('Tag', '')
    use_image_tag = False
    if tag:
        use_image_tag = (ask_flag('Use Image Tags as filter', ('y', 'n'), 'n') == 'y')
    page = ask_int('Start Page', 1)
    end_page = ask_int('End Page', 0)
    PixivBookmarkHandler.export_image_bookmark(
        sys.modules[__name__], __config__,
        hide=hide, start_page=page,
        end_page=end_page, tag=tag,
        use_image_tag=use_image_tag, filename=filename
    )


def menu_fanbox_download_from_list(op_is_valid, via, args, options):
    via_type = {PixivModelFanbox.FanboxArtist.SUPPORTING: "supporting",
                PixivModelFanbox.FanboxArtist.FOLLOWING: "following",
                PixivModelFanbox.FanboxArtist.CUSTOM: "custom"}[via]
    __log__.info(f'Download FANBOX {via_type.capitalize()} list mode.')
    if op_is_valid:
        start_page, end_page = get_start_and_end_page_from_options(options)
    else:
        end_page = ask_int('End Page', 0)
    if via in (PixivModelFanbox.FanboxArtist.SUPPORTING,
               PixivModelFanbox.FanboxArtist.FOLLOWING):
        ids = __br__.fanboxGetArtistList(via)
    else:
        list_file = get_list_file_from_options(options, __config__.listPathFanbox)
        ids = [
            line.strip() for line in open(list_file)
            if line.strip() and not line.startswith('#')
        ]
    if not ids:
        PixivHelper.print_and_log("info", f"No artist in {via_type} list!")
        return
    for idx, aid in enumerate(ids, 1):
        try:
            PixivFanboxHandler.process_fanbox_artist_by_id(
                sys.modules[__name__], __config__, aid, end_page,
                title_prefix=f"{idx} of {len(ids)}"
            )
        except Exception as ex:
            PixivHelper.print_and_log('error', str(ex))


def menu_fanbox_download_by_post_id(op_is_valid, args, options):
    __log__.info('Download FANBOX by post id mode.')
    post_ids = args if (op_is_valid and args) else ask_ids('Post ids')
    for pid in post_ids:
        try:
            post = __br__.fanboxGetPostById(pid)
            PixivFanboxHandler.process_fanbox_post(
                sys.modules[__name__], __config__, post, post.parent
            )
            del post
        except Exception as ex:
            PixivHelper.print_and_log('error', str(ex))


def menu_fanbox_download_by_id(op_is_valid, args, options):
    __log__.info('Download FANBOX by Artist or Creator ID mode.')
    if op_is_valid and args:
        start_page, end_page = get_start_and_end_page_from_options(options)
        member_ids = args
    else:
        member_ids = ask_ids('Artist/Creator IDs', is_string=True)
        end_page = ask_int('End page', 0)
    for idx, aid in enumerate(member_ids, 1):
        try:
            PixivFanboxHandler.process_fanbox_artist_by_id(
                sys.modules[__name__], __config__, aid, end_page,
                title_prefix=f"{idx} of {len(member_ids)}"
            )
        except Exception as ex:
            PixivHelper.print_and_log('error', str(ex))


def menu_fanbox_download_pixiv_by_fanbox_id(op_is_valid, args, options):
    __log__.info('Download FANBOX by Artist or Creator ID mode (f6).')
    if op_is_valid and args:
        start_page, end_page = get_start_and_end_page_from_options(options)
        member_ids = args
    else:
        member_ids = ask_ids('Artist/Creator IDs', is_string=True)
        start_page = ask_int('Start page', 0)
        end_page = ask_int('End page', 0)
    for idx, aid in enumerate(member_ids, 1):
        try:
            PixivFanboxHandler.process_pixiv_by_fanbox_id(
                sys.modules[__name__], __config__, aid,
                start_page=start_page, end_page=end_page,
                title_prefix=f"{idx} of {len(member_ids)}"
            )
        except Exception as ex:
            PixivHelper.print_and_log('error', str(ex))


def menu_sketch_download_by_artist_id(op_is_valid, args, options):
    __log__.info('Download Sketch by Artist ID mode.')
    page, end_page = ask_int('Start Page', 1), ask_int('End Page', 0)
    member_ids = args if (op_is_valid and args) else ask_ids('Artist ids', is_string=True)
    for idx, mid in enumerate(member_ids, 1):
        try:
            PixivSketchHandler.process_sketch_artists(
                sys.modules[__name__], __config__, mid, page, end_page,
                title_prefix=f"{idx} of {len(member_ids)}"
            )
        except Exception as ex:
            PixivHelper.print_and_log('error', str(ex))


def menu_sketch_download_by_post_id(op_is_valid, args, options):
    __log__.info('Download Sketch by Post ID mode.')
    post_ids = args if (op_is_valid and args) else ask_ids('Post ids')
    for pid in post_ids:
        try:
            PixivSketchHandler.process_sketch_post(
                sys.modules[__name__], __config__, int(pid)
            )
        except Exception as ex:
            PixivHelper.print_and_log('error', str(ex))


def menu_download_by_rank(op_is_valid, args, options, valid_modes=None):
    if valid_modes is None:
        valid_modes = ["daily", "weekly", "monthly", "rookie", "original", "male", "female"]
    __log__.info('Download Ranking mode.')
    if op_is_valid and args:
        start_page, end_page = get_start_and_end_page_from_options(options)
        mode = options.rank_mode
        content = options.rank_content
        date = options.rank_date
    else:
        mode = ask('Mode')
        content = ask('Type')
        date = ask('Date (YYYYMMDD)', default=datetime.date.today().strftime('%Y%m%d'))
        start_page, end_page = PixivHelper.get_start_and_end_number()
    PixivRankingHandler.process_ranking(
        sys.modules[__name__], __config__, mode, content, start_page, end_page, date=date, filter=None
    )


def menu_download_by_rank_r18(op_is_valid, args, options):
    __log__.info('Download R-18 Ranking mode.')
    menu_download_by_rank(op_is_valid, args, options, valid_modes=[
        "daily_r18", "weekly_r18", "male_r18", "female_r18"
    ])


def menu_download_new_illusts(op_is_valid, args, options):
    __log__.info('Download New Illust mode.')
    if op_is_valid and args:
        mode = options.rank_mode
        max_page = options.end_page
    else:
        mode = ask('Mode')
        max_page = ask_int('Max Page', 0)
    PixivRankingHandler.process_new_illusts(
        sys.modules[__name__], __config__, mode, max_page
    )


def menu_reload_config():
    __log__.info('Manual Reload Config (r).')
    __config__.loadConfig(path=configfile)


def menu_print_config():
    __log__.info('Print Current Config (p).')
    __config__.printConfig()


def menu_import_list():
    __log__.info('Import List mode (i).')
    list_name = input("List filename = ").rstrip("\r")
    if len(list_name) == 0:
        list_name = "list.txt"
    PixivListHandler.import_list(sys.modules[__name__], __config__, list_name)


# =============================================================================
# MENU HANDLERS REGISTRY (must be defined *before* main_loop)
# =============================================================================
MENU_HANDLERS = {
    '1': menu_download_by_member_id,
    '2': menu_download_by_image_id,
    '3': menu_download_by_tags,
    '4': menu_download_from_list,
    '5': menu_download_from_online_user_bookmark,
    '6': menu_download_from_online_image_bookmark,
    '7': menu_download_from_tags_list,
    '8': menu_download_new_illust_from_bookmark,
    '9': menu_download_by_title_caption,
    '10': menu_download_by_tag_and_member_id,
    '11': menu_download_by_member_bookmark,
    '12': menu_download_by_group_id,
    '13': menu_download_by_manga_series_id,
    '14': menu_download_by_novel_id,
    '15': menu_download_by_novel_series_id,
    '16': menu_download_by_rank,
    '17': menu_download_by_rank_r18,
    '18': menu_download_new_illusts,
    '19': menu_download_by_unlisted_image_id,
    'l': menu_export_database_images,
    'b': PixivBatchHandler.process_batch_job,
    'e': menu_export_online_bookmark,
    'm': menu_export_online_user_bookmark,
    'p': menu_export_from_online_image_bookmark,
    'u': menu_ugoira_reencode,
    'd': lambda op, args, opts: __dbManager__.main(),
    'r': menu_reload_config,
    'c': menu_print_config,
    'i': menu_import_list,
    'f1': lambda op, args, opts: menu_fanbox_download_from_list(op, PixivModelFanbox.FanboxArtist.SUPPORTING, args, opts),
    'f2': menu_fanbox_download_by_id,
    'f3': menu_fanbox_download_by_post_id,
    'f4': lambda op, args, opts: menu_fanbox_download_from_list(op, PixivModelFanbox.FanboxArtist.FOLLOWING, args, opts),
    'f5': lambda op, args, opts: menu_fanbox_download_from_list(op, PixivModelFanbox.FanboxArtist.CUSTOM, args, opts),
    'f6': menu_fanbox_download_pixiv_by_fanbox_id,
    's1': menu_sketch_download_by_artist_id,
    's2': menu_sketch_download_by_post_id,
}

def dispatch(selection, *args):
    """Look up the handler in MENU_HANDLERS and call it."""
    handler = MENU_HANDLERS.get(selection)
    if handler:
        handler(*args)
    else:
        print(f"Unknown selection: {selection}")

# Main loop


def main_loop(ewd, op_is_valid, selection, np_is_valid_local, args, options):
    while True:
        try:
            if __errorList:
                for err in __errorList:
                    PixivHelper.print_and_log('error', f"{err['type']}: {err['id']} ==> {err['message']}")
                __errorList.clear()
                global ERROR_CODE
                ERROR_CODE = 1

            sel = selection if op_is_valid else menu()

            if sel == 'x':
                break
            elif sel == '-all':
                np_is_valid_local = not np_is_valid_local
                options.number_of_pages = 0 if np_is_valid_local else __config__.numberOfPage
                print(f"{'All' if np_is_valid_local else 'Paged'} mode activated")
            else:
                dispatch(sel, op_is_valid, args, options)

            if ewd:
                break
            op_is_valid = False

        except KeyboardInterrupt:
            PixivHelper.print_and_log("info", f"Keyboard Interrupt, selection: {sel}")
            continue
        except EOFError:
            break
        except PixivException as ex:
            if ex.htmlPage:
                fname = f"Dump_{PixivHelper.sanitize_filename(ex.value)}.html"
                PixivHelper.dump_html(fname, ex.htmlPage)
            raise

    return np_is_valid_local, False, sel


def doLogin(password, username):
    global __br__
    if username:
        __br__._username = username
    if password:
        __br__._password = password
    try:
        if __config__.cookie:
            return __br__.loginUsingCookie()
    except Exception:
        raise PixivException("Cannot Login!", PixivException.CANNOT_LOGIN)
    return False


def main():
    global __log__, __br__, __dbManager__, dfilename, ERROR_CODE

    # 1. Console and header
    set_console_title()
    print_header()

    # 2. Parse command‐line options
    parser, __valid_options = setup_option_parser()
    options, args = parser.parse_args()

    op = options.start_action
    op_is_valid = op in __valid_options
    ewd = options.exit_when_done

    # 3. Number‐of‐pages parsing
    try:
        options.number_of_pages = int(options.number_of_pages) if options.number_of_pages else None
        np_valid = bool(options.number_of_pages)
    except Exception:
        np_valid = False

    # 4. Load config and logger (into module globals)
    try:
        __config__.loadConfig(path=options.configlocation)
        PixivHelper.set_config(__config__)
        __log__ = PixivHelper.get_logger(reload=True)
    except Exception:
        PixivHelper.print_and_log("error", f"Failed to read configuration from {configfile}")

    # 5. Instantiate browser (into module global)
    __br__ = PixivBrowserFactory.getBrowser(config=__config__)
    if __config__.checkNewVersion:
        PixivHelper.check_version(__br__, config=__config__)

    # 6. Prepare download list filename
    today = datetime.date.today()
    dfilename = os.path.join(
        __config__.downloadListDirectory,
        f"Downloaded_on_{today.strftime('%Y-%m-%d')}.txt"
    )
    os.makedirs(os.path.dirname(dfilename), exist_ok=True)

    # 7. Warn about post‐processing if enabled
    if __config__.enablePostProcessing and __config__.postProcessingCmd:
        PixivHelper.print_and_log(
            "warn",
            f"Post Processing after download is enabled: {__config__.postProcessingCmd}"
        )

    # 8. Check FFmpeg if any ugoira/video formats are enabled
    if __config__.createGif or __config__.createApng or __config__.createWebm or __config__.createWebp:
        cmd = f"{__config__.ffmpeg} -encoders"
        try:
            proc = subprocess.run(
                cmd.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            if __config__.ffmpegCodec not in proc.stdout:
                __config__.createWebm = False
                PixivHelper.print_and_log(
                    'error',
                    f"Missing FFmpeg codec {__config__.ffmpegCodec}; createWebm disabled."
                )
        except Exception:
            PixivHelper.print_and_log('error', 'Failed to load ffmpeg.')

    # 9. Initialize database manager (into module global)
    __dbManager__ = PixivDBManager(
        root_directory=__config__.rootDirectory,
        target=__config__.dbPath
    )
    __dbManager__.createDatabase()

    # 10. Optionally import initial list
    if __config__.useList:
        PixivListHandler.import_list(sys.modules[__name__], __config__, 'list.txt')

    # 11. Read blacklist/suppress lists
    read_lists()

    # 12. Login
    print(
        Fore.RED + Style.BRIGHT
        + "Username login is broken, use Cookies to log in."
        + Style.RESET_ALL
    )
    username = __config__.username
    password = __config__.password
    result = doLogin(password, username)

    # 13. Main loop or exit
    if result:
        np_valid, op_is_valid, sel = main_loop(ewd, op_is_valid, op, np_valid, args, options)

        # After loop: optionally launch IrfanView
        if start_iv:
            PixivHelper.start_irfanview(
                dfilename,
                __config__.IrfanViewPath,
                __config__.startIrfanSlide,
                __config__.startIrfanView
            )
    else:
        # login failed
        ERROR_CODE = PixivException.NOT_LOGGED_IN

    # 14. Cleanup and exit
    __dbManager__.close()
    sys.exit(ERROR_CODE)


if __name__ == '__main__':
    if not sys.version_info >= (3, 7):
        print("Require Python 3.7++")
        sys.exit(1)
    gc.enable()
    main()
    gc.collect()
    gc.collect()
