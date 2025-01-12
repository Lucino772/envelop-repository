# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "jsonschema==4.23.0",
#   "ruamel-yaml==0.18.10"
# ]
# ///

import functools
import json
from pathlib import Path
from ruamel.yaml import YAML
import jsonschema

INCLUDES = ["apps/minecraft/vanilla/*.yaml", "apps/valheim/valheim.yaml"]


def main():
    root = Path.cwd()

    with root.joinpath("manifest-spec.json").open("rb") as fp:
        schema = json.load(fp)

    yaml = YamlParser(root)
    files = functools.reduce(
        lambda prev, pattern: prev + list(root.glob(pattern)),
        INCLUDES,
        [],
    )

    manifest = {}
    for file in files:
        data = yaml.load(file)
        jsonschema.validate(data, schema=schema)
        output = root.joinpath("generated", data["name"] + ".yaml")
        output.parent.mkdir(parents=True, exist_ok=True)
        with root.joinpath("generated", data["name"] + ".yaml").open("wb") as fp:
            yaml.dump(data, stream=fp)
        manifest[data["name"]] = str(output.relative_to(root))

    with open(root.joinpath("generated", "root.json"), "w") as fp:
        json.dump(manifest, fp, indent=4)


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
