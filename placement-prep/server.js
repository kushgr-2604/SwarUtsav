const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { generateGeminiContent } = require("./lib/gemini");
const { isRateLimited } = require("./lib/rate-limit");

const ROOT = __dirname;
const MAX_BODY_BYTES = 3_000_000;
const MIME_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".ico": "image/x-icon",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
};

function loadLocalEnvironment() {
    const envFiles = [".env.development.local", ".env.local", ".env"];
    for (const envFile of envFiles) {
        const envPath = path.join(ROOT, envFile);
        if (!fs.existsSync(envPath)) continue;

        for (const line of fs.readFileSync(envPath, "utf8").split(/\r?\n/)) {
            const match = line.match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
            if (!match || process.env[match[1]] !== undefined) continue;

            let value = match[2];
            if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
                value = value.slice(1, -1);
            }
            process.env[match[1]] = value;
        }
    }
}

function setSecurityHeaders(res) {
    res.setHeader("X-Content-Type-Options", "nosniff");
    res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
    res.setHeader("Permissions-Policy", "camera=(self), microphone=(self), geolocation=()");
    res.setHeader("Cache-Control", "no-store");
}

function getClientIdentifier(req) {
    const forwardedFor = req.headers["x-forwarded-for"];
    return String(
        req.headers["x-real-ip"] ||
        (typeof forwardedFor === "string" ? forwardedFor.split(",")[0] : "") ||
        req.socket.remoteAddress ||
        "unknown",
    ).trim().slice(0, 128);
}

function readJsonBody(req) {
    return new Promise((resolve, reject) => {
        const chunks = [];
        let size = 0;
        let settled = false;

        req.on("data", (chunk) => {
            if (settled) return;
            size += chunk.length;
            if (size > MAX_BODY_BYTES) {
                settled = true;
                const error = new Error("Request body is too large.");
                error.statusCode = 413;
                reject(error);
                req.resume();
                return;
            }
            chunks.push(chunk);
        });
        req.on("end", () => {
            if (settled) return;
            try {
                resolve(JSON.parse(Buffer.concat(chunks).toString("utf8")));
            } catch {
                const error = new Error("Request body must be valid JSON.");
                error.statusCode = 400;
                reject(error);
            }
        });
        req.on("error", reject);
    });
}

async function handleGemini(req, res) {
    if (req.method !== "POST") {
        res.setHeader("Allow", "POST");
        res.writeHead(405, { "Content-Type": "application/json; charset=utf-8" });
        res.end(JSON.stringify({ error: "Use POST for Gemini requests." }));
        return;
    }

    const origin = req.headers.origin;
    if (origin) {
        try {
            if (new URL(origin).host !== req.headers.host) {
                res.writeHead(403, { "Content-Type": "application/json; charset=utf-8" });
                res.end(JSON.stringify({ error: "Cross-origin requests are not allowed." }));
                return;
            }
        } catch {
            res.writeHead(403, { "Content-Type": "application/json; charset=utf-8" });
            res.end(JSON.stringify({ error: "Invalid request origin." }));
            return;
        }
    }

    if (isRateLimited(getClientIdentifier(req))) {
        res.writeHead(429, { "Content-Type": "application/json; charset=utf-8" });
        res.end(JSON.stringify({ error: "Too many requests. Please wait a minute and try again." }));
        return;
    }

    try {
        if (Number(req.headers["content-length"]) > MAX_BODY_BYTES) {
            const error = new Error("Request body is too large.");
            error.statusCode = 413;
            throw error;
        }

        const body = await readJsonBody(req);
        console.log(`[gemini] Processing request (isJson: ${body.isJson === true})...`);
        const startTime = Date.now();
        const result = await generateGeminiContent(body.parts ?? body.prompt, body.isJson === true);
        console.log(`[gemini] Completed successfully in ${((Date.now() - startTime) / 1000).toFixed(1)}s`);
        res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
        res.end(JSON.stringify(result));
    } catch (error) {
        const statusCode = Number.isInteger(error.statusCode) ? error.statusCode : 500;
        if (statusCode >= 500) console.error("[gemini] Request failed:", error.message);
        res.writeHead(statusCode, { "Content-Type": "application/json; charset=utf-8" });
        res.end(JSON.stringify({ error: error.message || "Gemini request failed." }));
    }
}

function serveStatic(req, res, url) {
    if (req.method !== "GET" && req.method !== "HEAD") {
        res.writeHead(405, { Allow: "GET, HEAD", "Content-Type": "text/plain; charset=utf-8" });
        res.end("Method not allowed");
        return;
    }

    let decodedPath;
    try {
        decodedPath = decodeURIComponent(url.pathname);
    } catch {
        res.writeHead(400, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Invalid path");
        return;
    }

    const requestPath = decodedPath === "/" ? "/index.html" : decodedPath;
    const filePath = path.resolve(ROOT, `.${requestPath}`);
    if (
        (filePath !== ROOT && !filePath.startsWith(`${ROOT}${path.sep}`)) ||
        path.basename(filePath).startsWith(".")
    ) {
        res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("Not found");
        return;
    }

    fs.readFile(filePath, (error, content) => {
        if (error) {
            res.writeHead(error.code === "ENOENT" ? 404 : 500, { "Content-Type": "text/plain; charset=utf-8" });
            res.end(error.code === "ENOENT" ? "Not found" : "Unable to read file");
            return;
        }

        res.writeHead(200, {
            "Content-Type": MIME_TYPES[path.extname(filePath)] || "application/octet-stream",
            "Content-Length": content.length,
        });
        res.end(req.method === "HEAD" ? undefined : content);
    });
}

loadLocalEnvironment();
const port = Number(process.env.PORT) || 3000;
const server = http.createServer((req, res) => {
    setSecurityHeaders(res);
    const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

    if (url.pathname === "/api/gemini") {
        void handleGemini(req, res);
        return;
    }

    serveStatic(req, res, url);
});

server.on("error", (err) => {
    if (err.code === "EADDRINUSE") {
        const nextPort = port + 1;
        console.warn(`Port ${port} is already in use. Switching automatically to port ${nextPort}...`);
        server.listen(nextPort, "0.0.0.0");
    } else {
        console.error("Server error:", err);
    }
});

server.listen(port, "0.0.0.0", () => {
    console.log(`GLA Prep Hub is listening on http://localhost:${server.address().port}`);
});
