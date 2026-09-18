import re
from typing import List


def generate_users(usernames=None, quantity=50) -> List[dict]:
    # usernames => a list of unique usernames
    # username => a string in this format: firstname_lastname_number
    # examples of username => john_doe_1, jane_smith_2, etc.
    users = []
    base_number = 9800000000
    for i, username in enumerate(usernames or [f"user_{j + 1}" for j in range(quantity)]):
        email = f"{username}@gmail.com"
        phone_number = f"+977{base_number + i:010d}"
        full_name_parts = re.split(r'[_.]', username)  # Use r'[_.]' to avoid warning
        full_name = ' '.join(part.capitalize() for part in full_name_parts if not part.isdigit())
        is_phone_verified = True

        users.append({
            "username": username,
            "email": email,
            "phone_number": phone_number,
            "is_phone_verified": is_phone_verified,
            "full_name": full_name,
        })
    return users
