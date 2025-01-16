# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "jsonschema==4.23.0",
#   "ruamel-yaml==0.18.10"
# ]
# ///

import json
from pathlib import Path
from urllib.parse import urljoin
from ruamel.yaml import YAML
import jsonschema
import hashlib

INCLUDES = [
    "apps/minecraft/vanilla/*.yaml",
    "apps/minecraft/paper/*.yaml",
    "apps/valheim/valheim.yaml",
]
ROOT_URL = (
    "https://raw.githubusercontent.com/Lucino772/envelop-repository/refs/heads/main/"
)


def main():
    root = Path.cwd()
    yaml = YamlParser(root)
    yaml.indent(mapping=2, sequence=4, offset=2)
    output_dir = root / "generated"

    schema_path = root / "manifest-spec.json"
    with schema_path.open("rb") as fp:
        schema = json.load(fp)

    manifests = {}
    for file in _iter_files(root, INCLUDES):
        data = yaml.load(file)
        jsonschema.validate(data, schema=schema)
        out_filename = output_dir / "{}.yaml".format(data["name"])
        out_filename.parent.mkdir(parents=True, exist_ok=True)
        with out_filename.open("wb") as fp:
            yaml.dump(data, stream=fp)
        manifests[data["name"]] = {
            "url": urljoin(ROOT_URL, str(out_filename.relative_to(root))),
            "hash": "sha1:{}".format(
                hashlib.sha1(out_filename.read_bytes()).hexdigest()
            ),
        }

    with (output_dir / "root.json").open("w") as fp:
        json.dump(manifests, fp, indent=4)


def _iter_files(root: Path, patterns: list[str]):
    for pattern in patterns:
        yield from root.glob(pattern)


class YamlParser(YAML):
    class Content(str): ...

    def __init__(self, root: Path) -> None:
        super().__init__(typ="rt", pure=False, output=None, plug_ins=None)
        self._root = root
        self.constructor.add_constructor("!include", self._include_constructor)
        self.constructor.add_constructor("!content", self._include_content)
        self.representer.add_representer(self.Content, self._represent_content)

    def _include_constructor(self, loader, node):
        filename = loader.construct_scalar(node)
        with self._root.joinpath(filename).open("rb") as fp:
            return YamlParser(self._root).load(fp)

    def _include_content(self, loader, node):
        filename = loader.construct_scalar(node)
        return self.Content(self._root.joinpath(filename).read_text())

    def _represent_content(self, dumper, data):
        return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style="|")


if __name__ == "__main__":
    main()
