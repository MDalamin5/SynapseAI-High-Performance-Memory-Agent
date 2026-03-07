import { createServer } from "node:http";
import { stat } from "node:fs/promises";
import { createReadStream } from "node:fs";
import { extname, join, normalize } from "node:path";
import { URL } from "node:url";

const FRONTEND_PORT = process.env.FRONTEND_PORT || 5173;
const BACKEND_ORIGIN = process.env.BACKEND_ORIGIN || "http://127.0.0.1:8000";
const ROOT = process.cwd();

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

function getSafeFilePath(pathname) {
  const safePath = normalize(pathname).replace(/^\.\.(\/|\\|$)+/, "");
  return join(ROOT, safePath === "/" ? "/index.html" : safePath);
}

function writeCorsHeaders(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
}

async function proxyApi(req, res) {
  const upstream = `${BACKEND_ORIGIN}${req.url}`;
  try {
    const headers = {};
    if (req.headers["content-type"]) {
      headers["content-type"] = req.headers["content-type"];
    }

    const method = req.method || "GET";

    const body = await new Promise((resolve, reject) => {
      if (["GET", "HEAD"].includes(method)) return resolve(undefined);
      const chunks = [];
      req.on("data", (chunk) => chunks.push(chunk));
      req.on("end", () => resolve(Buffer.concat(chunks)));
      req.on("error", reject);
    });

    const response = await fetch(upstream, {
      method,
      headers,
      body,
    });

    res.statusCode = response.status;
    writeCorsHeaders(res);

    response.headers.forEach((value, key) => {
      if (key.toLowerCase() === "content-encoding") return;
      res.setHeader(key, value);
    });

    if (!response.body) {
      res.end();
      return;
    }

    for await (const chunk of response.body) {
      res.write(chunk);
    }
    res.end();
  } catch (error) {
    res.statusCode = 502;
    writeCorsHeaders(res);
    res.setHeader("content-type", "application/json; charset=utf-8");
    res.end(JSON.stringify({ error: `Proxy failed: ${error.message}` }));
  }
}

async function serveStatic(req, res) {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);
    let pathname = url.pathname;
    if (pathname === "/") pathname = "/index.html";

    const filePath = getSafeFilePath(pathname);
    const fileStat = await stat(filePath);

    if (fileStat.isDirectory()) {
      res.statusCode = 403;
      res.end("Forbidden");
      return;
    }

    const ext = extname(filePath).toLowerCase();
    res.statusCode = 200;
    res.setHeader("content-type", mimeTypes[ext] || "application/octet-stream");
    createReadStream(filePath).pipe(res);
  } catch {
    res.statusCode = 404;
    res.setHeader("content-type", "text/plain; charset=utf-8");
    res.end("Not Found");
  }
}

const server = createServer(async (req, res) => {
  if (req.method === "OPTIONS") {
    writeCorsHeaders(res);
    res.statusCode = 204;
    res.end();
    return;
  }

  if (req.url.startsWith("/api/")) {
    await proxyApi(req, res);
    return;
  }

  await serveStatic(req, res);
});

server.listen(FRONTEND_PORT, () => {
  console.log(`Frontend running at http://127.0.0.1:${FRONTEND_PORT}`);
  console.log(`Proxying /api/* -> ${BACKEND_ORIGIN}`);
});
