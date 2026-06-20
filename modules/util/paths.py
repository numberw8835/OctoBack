import os

def get_vault_target_path(src_path: str, vault_path: str) -> str:
    abs_src = os.path.abspath(src_path)
    home = os.path.expanduser("~")
    
    if abs_src == home:
        return os.path.join(vault_path, "home")
    elif abs_src.startswith(home + os.sep):
        rel_to_home = abs_src[len(home):].lstrip(os.sep)
        return os.path.join(vault_path, "home", rel_to_home)
    else:
        rel_to_root = abs_src.lstrip(os.sep)
        return os.path.join(vault_path, "root", rel_to_root)


def get_source_path_from_vault(vault_target: str, vault_path: str) -> str:
    rel_path = os.path.relpath(vault_target, vault_path)
    parts = rel_path.split(os.sep)
    if parts[0] == "home":
        return os.path.join(os.path.expanduser("~"), *parts[1:])
    elif parts[0] == "root":
        return os.path.abspath(os.sep + os.path.join(*parts[1:]))
    else:
        return os.path.abspath(os.sep + os.path.join(*parts))
