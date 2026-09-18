import re


def slugify(value, max_length=None):
    """Return a lowercase slug, or an empty string when no alphanumerics remain."""
    slug = re.sub(r"[\W_]+", "-", value.lower()).strip("-")
    if max_length is not None:
        slug = slug[:max_length].rstrip("-")
    return slug
