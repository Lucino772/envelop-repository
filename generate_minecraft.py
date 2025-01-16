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
import datetime as dt

VANILLA_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
PAPER_MANIFEST_URL = "https://api.papermc.io/v2/projects/paper"


async def main():
    await asyncio.gather(
        download_vanilla(),
        download_paper(),
    )


async def download_vanilla():
    root = Path.cwd()
    yaml = YamlParser()
    output_dir = root / "apps" / "minecraft" / "vanilla"

    async with httpx.AsyncClient() as client:
        response = await client.get(VANILLA_MANIFEST_URL)
        versions = response.json()["versions"]
        tasks = []
        for version in versions:
            if version["type"] == "release":
                tasks.append(
                    asyncio.create_task(
                        download_vanilla_version(client, yaml, version, output_dir)
                    )
                )
        await asyncio.wait(tasks)


async def download_vanilla_version(
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


async def download_paper():
    root = Path.cwd()
    yaml = YamlParser()
    output_dir = root / "apps" / "minecraft" / "paper"

    async with httpx.AsyncClient() as client:
        response = await client.get(PAPER_MANIFEST_URL)
        versions = response.json()["versions"]

        tasks = []
        for version in versions:
            if version != "1.13-pre7":
                tasks.append(
                    asyncio.create_task(
                        download_paper_version(client, yaml, version, output_dir)
                    )
                )
        await asyncio.wait(tasks)


async def download_paper_version(
    client: httpx.AsyncClient, yaml: YamlParser, version: str, output_dir: Path
):
    response = await client.get(
        f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds"
    )
    data = response.json()
    latest_build = next(
        iter(
            sorted(
                data["builds"],
                key=lambda val: dt.datetime.fromisoformat(val["time"]),
                reverse=True,
            )
        ),
        None,
    )

    depots = []
    if latest_build is not None:
        download = latest_build["downloads"]["application"]
        download_url = "https://api.papermc.io/v2/projects/paper/versions/{}/builds/{}/downloads/{}".format(
            version,
            latest_build["build"],
            download["name"],
        )
        depots.append(
            {
                "name": f"minecraft/paper/{version}",
                "config": {"os": ["*"], "arch": ["*"], "tags": []},
                "exports": {"jar": "{{{{.Path }}}}/paper-{}.jar".format(version)},
                "manifest": {
                    "type": "files",
                    "files": [
                        {
                            "filename": "paper-{}.jar".format(version),
                            "source": {
                                "type": "http",
                                "url": download_url,
                                "hash": "sha256:{}".format(download["sha256"]),
                            },
                        }
                    ],
                },
            }
        )

    if len(depots) > 0:
        with open(output_dir / f"{version}.yaml", "wb") as fp:
            yaml.indent(mapping=2, sequence=4, offset=2)
            yaml.dump(
                {
                    "name": f"minecraft/paper/{version}",
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
