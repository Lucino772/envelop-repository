import { defineCollection, z } from "astro:content";
import { glob, file } from "astro/loaders";

const manifests = defineCollection({
    loader: glob({
        pattern: "**/*.yaml",
        base: "../generated/",
        generateId: (opts) => {
            return opts.data.name as string;
        },
    }),
    schema: z.object({
        name: z.string(),
        config: z.string(),
        depots: z.array(
            z.object({
                name: z.string(),
                config: z.object({
                    os: z.array(z.string()),
                    arch: z.array(z.string()),
                    tags: z.array(z.string()),
                }),
                exports: z.record(z.string(), z.any()).optional(),
                manifest: z.discriminatedUnion("type", [
                    z.object({
                        type: z.literal("files"),
                        files: z.array(
                            z.object({
                                filename: z.string(),
                            }),
                        ),
                    }),
                    z.object({
                        type: z.literal("steam"),
                        appid: z.number(),
                    }),
                ]),
            }),
        ),
    }),
});

const apps = defineCollection({
    loader: file("../generated/root.json", {
        parser: (text) => JSON.parse(text),
    }),
    schema: z.object({
        url: z.string().url(),
        hash: z.string(),
    }),
});

export const collections = { manifests, apps };
