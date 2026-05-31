from slugify import slugify


def make_slug(name: str) -> str:
    return slugify(name, separator="-", max_length=80)
