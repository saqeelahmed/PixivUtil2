# platform_utils.py
import platform
import sys
import getpass


def setup_getpass():
    """Handle platform-specific password input masking."""
    if platform.system() == "Windows":
        # Windows-specific getpass with masking
        import msvcrt

        def win_getpass_with_mask(prompt='Password: ', stream=None):
            """Prompt for password with echo off, using Windows getch()."""
            if sys.stdin is not sys.__stdin__:
                return getpass.fallback_getpass(prompt, stream)
            for c in prompt:
                msvcrt.putch(c.encode())
            pw = ""
            while 1:
                c = msvcrt.getch().decode()
                if c == '\r' or c == '\n':
                    break
                if c == '\003':
                    raise KeyboardInterrupt
                if c == '\b':
                    pw = pw[:-1]
                    print("\b \b", end="")
                else:
                    pw += c
                    print("*", end="")
            msvcrt.putch('\r'.encode())
            msvcrt.putch('\n'.encode())
            return pw

        getpass.getpass = win_getpass_with_mask
        return 'utf-8-sig'
    else:
        return 'utf-8'


# Initialize platform encoding
platform_encoding = setup_getpass()
