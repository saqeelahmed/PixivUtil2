# PixivUtil2_Inputs.py
import PixivHelper


def ask(prompt: str, default: str = "") -> str:
    """General prompt with optional default."""
    resp = input(f"{prompt}{' [' + default + ']' if default else ''}: ").strip()
    return resp or default


def ask_int(prompt: str, default: int = 0) -> int:
    """Prompt for integer with default fallback."""
    resp = input(f"{prompt} (default={default}): ").strip()
    try:
        return int(resp or default)
    except ValueError:
        print(f"Invalid integer '{resp}', using {default}.")
        return default


def ask_flag(prompt: str, allowed=('y', 'n', 'o'), default='n') -> str:
    """Prompt for a single-char flag within allowed set."""
    while True:
        resp = input(f"{prompt} [{'|'.join(allowed)}, default={default}]: ").strip().lower() or default
        if resp in allowed:
            return resp
        print(f"Please enter one of {allowed}.")


def ask_ids(prompt: str, is_string=False):
    """Prompt for CSV of IDs, returning list of ints or strings."""
    raw = input(f"{prompt}: ").strip()
    return PixivHelper.get_ids_from_csv(raw, is_string=is_string)


def handle_keyboard_interrupt() -> bool:
    """Return True to continue after Ctrl-C, False to abort."""
    return ask_flag("Interrupted. Continue?", allowed=('y', 'n'), default='y') == 'y'
