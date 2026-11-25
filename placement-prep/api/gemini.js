const { generateGeminiContent } = require("../lib/gemini");
const { isRateLimited } = require("../lib/rate-limit");

const MAX_BODY_BYTES = 3_000_000;

function respond(res, statusCode, body) {
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("X-Content-Type-Options", "nosniff");
    return res.status(statusCode).json(body);
}

function getClientIdentifier(req) {
    const forwardedFor = req.headers["x-forwarded-for"];
    return String(
        req.headers["x-real-ip"] ||
        (typeof forwardedFor === "string" ? forwardedFor.split(",")[0] : "") ||
        req.socket?.remoteAddress ||
        "unknown",
    ).trim().slice(0, 128);
}

function readRequestBody(req) {
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

module.exports = async function geminiHandler(req, res) {
    res.setHeader("Cache-Control", "no-store");
    res.setHeader("X-Content-Type-Options", "nosniff");

    if (req.method !== "POST") {
        res.setHeader("Allow", "POST");
        return respond(res, 405, { error: "Use POST for Gemini requests." });
    }

    const origin = req.headers.origin;
    if (origin) {
        try {
            if (new URL(origin).host !== req.headers.host) {
                return respond(res, 403, { error: "Cross-origin requests are not allowed." });
            }
        } catch {
            return respond(res, 403, { error: "Invalid request origin." });
        }
    }

    if (isRateLimited(getClientIdentifier(req))) {
        return respond(res, 429, { error: "Too many requests. Please wait a minute and try again." });
    }

    try {
        let body = req.body;
        if (typeof body === "string") body = JSON.parse(body);
        if (!body || typeof body !== "object" || Array.isArray(body)) {
            body = await readRequestBody(req);
        }

        if (Buffer.byteLength(JSON.stringify(body), "utf8") > MAX_BODY_BYTES) {
            return respond(res, 413, { error: "Request body is too large." });
        }

        const result = await generateGeminiContent(body.parts ?? body.prompt, body.isJson === true);
        return respond(res, 200, result);
    } catch (error) {
        const statusCode = Number.isInteger(error.statusCode) ? error.statusCode : 500;
        if (statusCode >= 500) console.error("[gemini] Request failed:", error.message);
        return respond(res, statusCode, { error: error.message || "Gemini request failed." });
    }
};
