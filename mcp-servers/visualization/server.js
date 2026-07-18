#!/usr/bin/env node
// Synthex — Visualization MCP server (Node, ESM).
// Implements DATA_CONTRACTS.md §3 "server `visualization`":
//   threejs_scaffold(name, kind="scene") -> { path }
//   react_component(name, spec)          -> { path }
//   preview_ui(path)                     -> { url }
// Sandbox resolved via SYNTHEX_ROOT (§1). Writes only under agent-output/artifacts/.

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { promises as fs } from "node:fs";
import path from "node:path";
import os from "node:os";
import { pathToFileURL } from "node:url";

// ---------------------------------------------------------------------------
// Sandbox path resolution (DATA_CONTRACTS.md §1)
// ---------------------------------------------------------------------------
function synthexRoot() {
  return process.env.CLAUDE_PROJECT_DIR || process.cwd();
}

function outputRoot(root = synthexRoot()) {
  return path.join(root, "agent-output");
}

function artifactsDir(root = synthexRoot()) {
  return path.join(outputRoot(root), "artifacts");
}

async function ensureArtifactsDir(root = synthexRoot()) {
  const dir = artifactsDir(root);
  await fs.mkdir(dir, { recursive: true }); // mkdir -p
  return dir;
}

// Reduce an arbitrary name to a safe single path segment (no traversal).
function safeName(name) {
  const base = path.basename(String(name ?? "").trim());
  const cleaned = base.replace(/[^A-Za-z0-9._-]/g, "_").replace(/^\.+/, "");
  return cleaned || "artifact";
}

// ---------------------------------------------------------------------------
// Templates
// ---------------------------------------------------------------------------
function renderThreeHtml(name, kind) {
  const k = String(kind || "scene").toLowerCase();
  let geometry;
  switch (k) {
    case "sphere":
      geometry = "new THREE.SphereGeometry(1, 32, 32)";
      break;
    case "torus":
      geometry = "new THREE.TorusGeometry(0.9, 0.35, 24, 80)";
      break;
    case "plane":
      geometry = "new THREE.PlaneGeometry(2, 2)";
      break;
    case "cube":
    case "box":
    case "scene":
    default:
      geometry = "new THREE.BoxGeometry(1, 1, 1)";
      break;
  }
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${name} — three.js (${k})</title>
<style>
  html, body { margin: 0; height: 100%; background: #0b0f14; overflow: hidden; }
  #info { position: fixed; top: 12px; left: 12px; color: #cfe3ff;
          font: 13px/1.4 system-ui, sans-serif; opacity: .8; }
</style>
</head>
<body>
<div id="info">${name} · kind: ${k}</div>
<script type="importmap">
{ "imports": { "three": "https://unpkg.com/three@0.160.0/build/three.module.js" } }
</script>
<script type="module">
import * as THREE from "three";

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0f14);

const camera = new THREE.PerspectiveCamera(
  60, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(2.5, 2, 3.5);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.5));
const key = new THREE.DirectionalLight(0xffffff, 1.0);
key.position.set(5, 8, 6);
scene.add(key);

const mesh = new THREE.Mesh(
  ${geometry},
  new THREE.MeshStandardMaterial({ color: 0x4f9dff, roughness: 0.4, metalness: 0.1 })
);
scene.add(mesh);

const grid = new THREE.GridHelper(10, 10, 0x224466, 0x112233);
grid.position.y = -1.2;
scene.add(grid);

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

function animate() {
  requestAnimationFrame(animate);
  mesh.rotation.x += 0.006;
  mesh.rotation.y += 0.01;
  renderer.render(scene, camera);
}
animate();
</script>
</body>
</html>
`;
}

function renderJsx(component, spec) {
  const specText = String(spec ?? "").trim() || "No spec provided.";
  const specComment = specText
    .split("\n")
    .map((line) => " * " + line)
    .join("\n");
  return `// ${component}.jsx — scaffolded by Synthex visualization MCP.
/**
 * Spec:
${specComment}
 */
import React from "react";

export default function ${component}(props) {
  return (
    <section className="${component.toLowerCase()}" data-spec-driven="true">
      <h2>${component}</h2>
      {/* TODO: implement per spec above */}
      <pre>{${JSON.stringify(specText)}}</pre>
      {props.children}
    </section>
  );
}
`;
}

// ---------------------------------------------------------------------------
// Tool implementations (pure, transport-independent — reused by --selftest)
// ---------------------------------------------------------------------------
async function threejsScaffold({ name, kind = "scene" }, root = synthexRoot()) {
  const dir = await ensureArtifactsDir(root);
  const file = path.join(dir, `${safeName(name)}.html`);
  await fs.writeFile(file, renderThreeHtml(safeName(name), kind), "utf8");
  return { path: file };
}

async function reactComponent({ name, spec }, root = synthexRoot()) {
  const dir = await ensureArtifactsDir(root);
  const component = safeName(name);
  const file = path.join(dir, `${component}.jsx`);
  await fs.writeFile(file, renderJsx(component, spec), "utf8");
  return { path: file };
}

function previewUi({ path: target }, root = synthexRoot()) {
  const abs = path.isAbsolute(target)
    ? path.resolve(target)
    : path.resolve(root, target);
  // Validate the artifact lives under agent-output/ (the only writable zone).
  const base = path.resolve(outputRoot(root));
  const rel = path.relative(base, abs);
  if (rel === "" || rel.startsWith("..") || path.isAbsolute(rel)) {
    throw new Error(`preview_ui: path must be under agent-output/ (got: ${target})`);
  }
  return { url: pathToFileURL(abs).href };
}

// ---------------------------------------------------------------------------
// MCP server construction
// ---------------------------------------------------------------------------
function buildServer() {
  const server = new McpServer({
    name: "synthex-visualization",
    version: "0.1.0",
  });

  const ok = (result) => ({
    content: [{ type: "text", text: JSON.stringify(result) }],
  });

  server.registerTool(
    "threejs_scaffold",
    {
      title: "Three.js scaffold",
      description:
        "Write a self-contained three.js HTML scene to agent-output/artifacts/<name>.html and return its path.",
      inputSchema: {
        name: z.string().describe("Artifact base name (written as <name>.html)."),
        kind: z
          .string()
          .default("scene")
          .describe("Scene kind: scene|cube|sphere|torus|plane."),
      },
    },
    async ({ name, kind }) => ok(await threejsScaffold({ name, kind }))
  );

  server.registerTool(
    "react_component",
    {
      title: "React component scaffold",
      description:
        "Write a .jsx component scaffold reflecting `spec` to agent-output/artifacts/<name>.jsx and return its path.",
      inputSchema: {
        name: z.string().describe("Component name (written as <name>.jsx)."),
        spec: z.string().describe("Free-form spec describing the component."),
      },
    },
    async ({ name, spec }) => ok(await reactComponent({ name, spec }))
  );

  server.registerTool(
    "preview_ui",
    {
      title: "Preview UI artifact",
      description:
        "Return a file:// URL for an artifact under agent-output/ (validated).",
      inputSchema: {
        path: z.string().describe("Path to an artifact under agent-output/."),
      },
    },
    async ({ path: target }) => ok(previewUi({ path: target }))
  );

  return server;
}

// ---------------------------------------------------------------------------
// Startup: --selftest runs without the MCP transport; normal start connects.
// ---------------------------------------------------------------------------
async function main() {
  const argv = process.argv.slice(2);
  if (argv.includes("--selftest")) {
    const tmp = await fs.mkdtemp(path.join(os.tmpdir(), "synthex-viz-"));
    const { path: written } = await threejsScaffold(
      { name: "selftest", kind: "scene" },
      tmp
    );
    console.log(written);
    return;
  }

  const server = buildServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
