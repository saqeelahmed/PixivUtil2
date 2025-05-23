# PixivUtil2_Menu.py
from colorama import Fore, Back, Style
from PixivUtil2_Header import print_header


def get_menu(read_lists_func, set_console_title_func):
    def menu():
        set_console_title_func()
        PADDING = 60
        print_header()  # Replace inline header code with this line
        print(Style.BRIGHT + '── Pixiv '.ljust(PADDING, "─") + Style.RESET_ALL)
        print(' 1.  Download by member_id')
        print(' 2.  Download by image_id')
        print(' 3.  Download by tags')
        print(' 4.  Download from list')
        print(' 5.  Download from followed artists (/bookmark.php?type=user)')
        print(' 6.  Download from bookmarked images (/bookmark.php)')
        print(' 7.  Download from tags list')
        print(' 8.  Download new illust from bookmarked members (/bookmark_new_illust.php)')
        print(' 9.  Download by Title/Caption')
        print(' 10. Download by Tag and Member Id')
        print(' 11. Download Member Bookmark (/bookmark.php?id=)')
        print(' 12. Download by Group Id')
        print(' 13. Download by Manga Series Id')
        print(' 14. Download by Novel Id')
        print(' 15. Download by Novel Series Id')
        print(' 16. Download by Rank')
        print(' 17. Download by Rank R-18')
        print(' 18. Download by New Illusts')
        print(' 19. Download by Unlisted image_id')
        print(Style.BRIGHT + '── FANBOX '.ljust(PADDING, "─") + Style.RESET_ALL)
        print(' f1. Download from supporting list (FANBOX)')
        print(' f2. Download by artist/creator id (FANBOX)')
        print(' f3. Download by post id (FANBOX)')
        print(' f4. Download from following list (FANBOX)')
        print(' f5. Download from custom list (FANBOX)')
        print(' f6. Download Pixiv by FANBOX Artist ID')
        print(Style.BRIGHT + '── Sketch '.ljust(PADDING, "─") + Style.RESET_ALL)
        print(' s1. Download by creator id (Sketch)')
        print(' s2. Download by post id (Sketch)')
        print(Style.BRIGHT + '── Batch Download '.ljust(PADDING, "─") + Style.RESET_ALL)
        print(' b. Batch Download from batch_job.json (experimental)')
        print(Style.BRIGHT + '── Others '.ljust(PADDING, "─") + Style.RESET_ALL)
        print(' d. Manage database')
        print(' l. Export local database.')
        print(' e. Export online followed artist.')
        print(' m. Export online other\'s followed artist.')
        print(' p. Export online image bookmarks.')
        print(' i. Import list file')
        print(' u. Ugoira re-encode')
        print(' r. Reload config.ini')
        print(' c. Print config.ini')
        print(' x. Exit')

        read_lists_func()

        sel = input('Input: ').rstrip("\r")
        return sel
    return menu
