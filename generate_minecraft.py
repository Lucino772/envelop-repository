# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx==0.28.1",
#   "ruamel-yaml==0.18.10"
# ]
# ///

from __future__ import annotations

import asyncio
from pathlib import Path
from ruamel.yaml import YAML
import httpx

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


async def main():
    root = Path.cwd()
    yaml = YamlParser()
    output_dir = root / "apps" / "minecraft" / "vanilla"

    async with httpx.AsyncClient() as client:
        response = await client.get(MANIFEST_URL)
        versions = response.json()["versions"]
        tasks = []
        for version in versions:
            if version["type"] == "release":
                tasks.append(
                    asyncio.create_task(
                        download_version(client, yaml, version, output_dir)
                    )
                )
        await asyncio.wait(tasks)


async def download_version(
    client: httpx.AsyncClient, yaml: YamlParser, version: dict, output_dir: Path
):
    response = await client.get(version["url"])
    data = response.json()

    version_id = version["id"]
    jars = []
    depots = []

    downloads = data.get("downloads", {})
    if "windows_server" in downloads:
        jars.append(
            {
                "name": f"minecraft/vanilla/{version_id}-windows",
                "version": f"{version_id}",
                "os": ["windows"],
                "url": downloads["windows_server"]["url"],
                "sha1": downloads["windows_server"]["sha1"],
            }
        )
        jars.append(
            {
                "name": f"minecraft/vanilla/{version_id}-linux",
                "version": f"{version_id}",
                "os": ["linux"],
                "url": downloads["server"]["url"],
                "sha1": downloads["server"]["sha1"],
            }
        )
    elif "server" in downloads:
        jars.append(
            {
                "name": f"minecraft/vanilla/{version_id}",
                "version": f"{version_id}",
                "os": ["*"],
                "url": downloads["server"]["url"],
                "sha1": downloads["server"]["sha1"],
            }
        )

    for jar in jars:
        depots.append(
            {
                "name": jar["name"],
                "config": {"os": jar["os"], "arch": ["*"], "tags": []},
                "exports": {
                    "jar": "{{{{.Path }}}}/server-{}.jar".format(jar["version"])
                },
                "manifest": {
                    "type": "files",
                    "files": [
                        {
                            "filename": "server-{}.jar".format(jar["version"]),
                            "source": {
                                "type": "http",
                                "url": jar["url"],
                                "hash": "sha1:{}".format(jar["sha1"]),
                            },
                        }
                    ],
                },
            }
        )

    if len(depots) > 0:
        with open(output_dir / f"{version_id}.yaml", "wb") as fp:
            yaml.indent(mapping=2, sequence=4, offset=2)
            yaml.dump(
                {
                    "name": f"minecraft/vanilla/{version_id}",
                    "config": Tag("!content", "apps/minecraft/envelop.yaml"),
                    "depots": [Tag("!include", "apps/minecraft/eula.yaml"), *depots],
                },
                stream=fp,
            )


class Tag:
    def __init__(self, tag: str, value: str):
        self.tag = tag
        self.value = value


class YamlParser(YAML):
    def __init__(self) -> None:
        super().__init__(typ="rt", pure=False, output=None, plug_ins=None)
        self.representer.add_representer(Tag, self._represent_tag)

    def _represent_tag(self, dumper, data):
        return dumper.represent_scalar(data.tag, data.value)


if __name__ == "__main__":
    asyncio.run(main())
