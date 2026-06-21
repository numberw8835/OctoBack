import os

def get_vault_target_path(src_path: str, vault_path: str) -> str:
    """
    Computes the destination path within the backup vault for a given source path.
    Separates paths into 'home' and 'root' directories in the vault depending on 
    whether they reside inside the user's home directory.
    """
    abs_src = os.path.abspath(src_path)
    home = os.path.expanduser("~")
    
    # Check if the path is exactly the user's home directory
    if abs_src == home:
        return os.path.join(vault_path, "home")
    # Check if the path resides inside the home directory
    elif abs_src.startswith(home + os.sep):
        rel_to_home = abs_src[len(home):].lstrip(os.sep)
        return os.path.join(vault_path, "home", rel_to_home)
    # Otherwise, treat the path as a system-root relative path
    else:
        rel_to_root = abs_src.lstrip(os.sep)
        return os.path.join(vault_path, "root", rel_to_root)


def get_source_path_from_vault(vault_target: str, vault_path: str) -> str:
    """
    Reconstructs the original absolute file system path from a backup path inside the vault.
    Reverses the mapping performed by get_vault_target_path.
    """
    rel_path = os.path.relpath(vault_target, vault_path)
    parts = rel_path.split(os.sep)
    # If the backup resides in 'home', prefix it with the home directory path
    if parts[0] == "home":
        return os.path.join(os.path.expanduser("~"), *parts[1:])
    # If the backup resides in 'root', prefix it with the root directory path (/)
    elif parts[0] == "root":
        return os.path.abspath(os.sep + os.path.join(*parts[1:]))
    # Fallback default conversion
    else:
        return os.path.abspath(os.sep + os.path.join(*parts))
