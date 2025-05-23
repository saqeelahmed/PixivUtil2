# ui_helper.py
from colorama import Fore, Back, Style
from PixivConstant import PIXIVUTIL_VERSION, PIXIVUTIL_LINK, PIXIVUTIL_DONATE


def print_header():
    PADDING = 60
    print("┌" + "".ljust(PADDING - 2, "─") + "┐")
    print("│ " + Fore.YELLOW + Back.BLACK + Style.BRIGHT + f"PixivDownloader2 version {PIXIVUTIL_VERSION}".ljust(PADDING - 3, " ") + Style.RESET_ALL + "│")
    print("│ " + Fore.CYAN + Back.BLACK + Style.BRIGHT + PIXIVUTIL_LINK.ljust(PADDING - 3, " ") + Style.RESET_ALL + "│")
    print("│ " + Fore.YELLOW + Back.BLACK + Style.BRIGHT + f"Donate at {Fore.CYAN}{Style.BRIGHT}{PIXIVUTIL_DONATE}".ljust(PADDING + 6, " ") + Style.RESET_ALL + "│")
    print("└" + "".ljust(PADDING - 2, "─") + "┘")
