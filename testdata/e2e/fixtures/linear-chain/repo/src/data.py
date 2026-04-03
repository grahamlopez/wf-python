"""Data processing pipeline - needs refactoring into stages."""


def process(raw_input):
    """Run the full pipeline: parse, transform, format."""
    parsed = parse(raw_input)
    transformed = transform(parsed)
    return format_output(transformed)


def parse(raw):
    return raw.strip().split("\n")


def transform(lines):
    return [line.upper() for line in lines]


def format_output(lines):
    return "\n".join(lines)
