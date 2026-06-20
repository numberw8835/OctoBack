import hashlib

def calculate_sha1(filepath):
    sha1 = hashlib.sha1()
    try:
        with open(filepath, "rb") as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()
    except Exception:
        return None
