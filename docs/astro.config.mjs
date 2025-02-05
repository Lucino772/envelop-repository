// @ts-check
import { defineConfig } from "astro/config";

import tailwind from "@astrojs/tailwind";
import icon from "astro-icon";
import sitemap from "@astrojs/sitemap";

// https://astro.build/config
export default defineConfig({
    site: "https://lucino772.github.io",
    base: "/envelop-repository",
    trailingSlash: "never",
    integrations: [
        tailwind({
            applyBaseStyles: false,
        }),
        icon(),
        sitemap(),
    ],
});
