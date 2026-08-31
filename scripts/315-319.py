import json
from pathlib import Path


FILE = Path(
    "data/malanka_debug/responses/"
    "00031_200__central-system_api_v1_locations_map_info_"
    "1788188817991375200.json"
)

TARGETS = {
    700315,
    700316,
    700317,
    700318,
    700319,
}


def contains_target(value):
    text = json.dumps(
        value,
        ensure_ascii=False,
    )

    return any(
        str(target) in text
        for target in TARGETS
    )


def walk(value, path="root"):
    if isinstance(value, dict):

        if contains_target(value):

            print()
            print("=" * 120)
            print("PATH:", path)
            print("=" * 120)

            print(
                json.dumps(
                    value,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        for key, child in value.items():
            walk(
                child,
                f"{path}.{key}",
            )

    elif isinstance(value, list):

        for index, child in enumerate(value):
            walk(
                child,
                f"{path}[{index}]",
            )


def main():

    print("Reading:")
    print(FILE.resolve())

    with FILE.open(
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    walk(data)


if __name__ == "__main__":
    main()