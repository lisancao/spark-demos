// Drive OpenScreen's editor over the Chrome DevTools protocol: open a .openscreen
// project, export it as MP4 at source quality, save it to the given path. Called by
// openscreen.sh, which owns the display and the app. Native file dialogs are GTK and
// get their paths from xdotool.
//   node export.mjs <port> <project.openscreen> <out.mp4>
import { execFileSync } from "node:child_process";
import { existsSync, statSync } from "node:fs";

const [port, project, out] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const xdo = (...a) => execFileSync("xdotool", a, { encoding: "utf8" }).trim();

async function page(kind) {
	for (let i = 0; i < 60; i++) {
		try {
			const pages = await (await fetch(`http://localhost:${port}/json`)).json();
			const p = pages.find((p) => p.type === "page" && p.url.includes(`windowType=${kind}`));
			if (p) return p.webSocketDebuggerUrl;
		} catch {}
		await sleep(500);
	}
	throw new Error(`no ${kind} window`);
}

async function evaluate(kind, expression, { wait = true } = {}) {
	const ws = new WebSocket(await page(kind));
	await new Promise((r) => ws.addEventListener("open", r));
	const done = new Promise((resolve) =>
		ws.addEventListener("message", (m) => {
			const d = JSON.parse(m.data);
			if (d.id === 1) resolve(d.result?.result?.value);
		}),
	);
	ws.send(JSON.stringify({ id: 1, method: "Runtime.evaluate",
		params: { expression, awaitPromise: true, returnByValue: true, userGesture: true } }));
	// A click that opens a native dialog doesn't return until the dialog closes.
	const value = wait ? await done : undefined;
	if (wait) ws.close();
	return value;
}

const click = (label, last = false) => `(() => {
	const all = [...document.querySelectorAll("button")].filter((b) =>
		(b.innerText.trim() || b.getAttribute("aria-label") || b.title || "").startsWith(${JSON.stringify(label)}));
	const b = ${last ? "all[all.length - 1]" : "all[0]"};
	if (!b) return false;
	b.click();
	return true;
})()`;

async function dialog(title, path) {
	for (let i = 0; i < 40; i++) {
		try {
			const id = xdo("search", "--onlyvisible", "--name", title).split("\n")[0];
			if (id) {
				xdo("windowactivate", "--sync", id);
				await sleep(400);
				xdo("key", "ctrl+l");
				await sleep(300);
				xdo("key", "ctrl+a");
				xdo("type", "--delay", "15", path);
				await sleep(300);
				xdo("key", "Return");
				return;
			}
		} catch {}
		await sleep(500);
	}
	throw new Error(`no "${title}" dialog`);
}

const webgl = await evaluate("hud-overlay", `(() => {
	const c = document.createElement("canvas").getContext("webgl2");
	const d = c && c.getExtension("WEBGL_debug_renderer_info");
	return d ? c.getParameter(d.UNMASKED_RENDERER_WEBGL) : "none";
})()`);
console.log(`renderer: ${webgl}`);
await evaluate("hud-overlay", "window.electronAPI.switchToEditor(), true");
await page("editor");
await sleep(3000);

evaluate("editor", click("Load Project…"), { wait: false });
await dialog("Open OpenScreen Project", project);
for (let i = 0; i < 60 && !(await evaluate("editor", `!!document.querySelector("video")?.duration`)); i++) await sleep(500);
const regions = await evaluate("editor", `[...document.querySelectorAll("*")].filter((e) =>
	e.children.length === 0 && /^\\d+(\\.\\d+)?×$/.test(e.textContent.trim())).length`);
console.log(`loaded ${project}: ${regions} zoom regions on the timeline`);

await evaluate("editor", click("Export Video"));
await sleep(1000);
await evaluate("editor", `${click("Source")}, ${click("MP4")}`);
evaluate("editor", click("Export Video", true), { wait: false });
await dialog("Save Exported Video", out);

const t0 = Date.now();
let last = "";
for (;;) {
	await sleep(5000);
	const progress = await evaluate("editor", `document.body.innerText.match(/(\\d+) \\/ (\\d+)/)?.[0] ?? ""`);
	if (progress && progress !== last) {
		console.log(`  ${progress} frames, ${Math.round((Date.now() - t0) / 1000)}s`);
		last = progress;
	}
	if (!progress && existsSync(out) && statSync(out).size > 0) {
		await sleep(3000);
		console.log(`${out}  ${(statSync(out).size / 1e6).toFixed(1)} MB in ${Math.round((Date.now() - t0) / 1000)}s`);
		break;
	}
}
// The dialog clicks above left sockets open; they would keep node running.
process.exit(0);
