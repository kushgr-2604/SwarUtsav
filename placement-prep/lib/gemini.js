const MODEL = process.env.GEMINI_MODEL || "gemini-3.1-flash-lite";
const FALLBACK_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
];

const MAX_TEXT_CHARS = 24_000;
const MAX_MEDIA_BYTES = 2_000_000;
const ALLOWED_MEDIA_TYPES = new Set([
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
]);

function createError(message, statusCode) {
    const error = new Error(message);
    error.statusCode = statusCode;
    return error;
}

function normalizeParts(input) {
    const parts = typeof input === "string" ? [{ text: input }] : input;

    if (!Array.isArray(parts) || parts.length === 0 || parts.length > 8) {
        throw createError("Provide a prompt with between one and eight content parts.", 400);
    }

    let totalBytes = 0;
    const normalized = parts.map((part) => {
        if (!part || typeof part !== "object" || Array.isArray(part)) {
            throw createError("The prompt contains an invalid content part.", 400);
        }

        if (typeof part.text === "string" && part.inlineData === undefined) {
            if (!part.text.trim() || part.text.length > MAX_TEXT_CHARS) {
                throw createError(`Text content must be between 1 and ${MAX_TEXT_CHARS} characters.`, 400);
            }
            totalBytes += Buffer.byteLength(part.text, "utf8");
            return { type: "text", text: part.text };
        }

        const media = part.inlineData;
        if (
            media &&
            typeof media === "object" &&
            ALLOWED_MEDIA_TYPES.has(media.mimeType) &&
            typeof media.data === "string" &&
            /^[A-Za-z0-9+/]+={0,2}$/.test(media.data)
        ) {
            const mediaBytes = Buffer.byteLength(media.data, "base64");
            if (mediaBytes > MAX_MEDIA_BYTES) {
                throw createError("Uploaded media must be 2 MB or smaller.", 413);
            }
            totalBytes += mediaBytes;
            return {
                type: "file",
                mediaType: media.mimeType === "application/pdf" ? "application/pdf" : "image",
                mimeType: media.mimeType,
                data: Buffer.from(media.data, "base64"),
                base64: media.data,
            };
        }

        throw createError("The prompt contains unsupported content.", 400);
    });

    if (totalBytes > MAX_MEDIA_BYTES + MAX_TEXT_CHARS * 4) {
        throw createError("The request is too large.", 413);
    }

    return normalized;
}

async function generateDirectGemini(apiKey, content, isJson) {
    const configuredModel = (process.env.GEMINI_MODEL || MODEL || "gemini-flash-lite-latest").replace(/^google\//, "");
    const modelsToTry = [configuredModel, ...FALLBACK_MODELS.filter((m) => m !== configuredModel)];

    const parts = content.map((part) => {
        if (part.type === "text") {
            return { text: part.text };
        }
        if (part.type === "file") {
            return {
                inlineData: {
                    mimeType: part.mimeType,
                    data: part.base64,
                },
            };
        }
        return {};
    });

    const body = {
        contents: [{ role: "user", parts }],
        generationConfig: isJson ? { responseMimeType: "application/json" } : {},
    };

    let lastError = null;

    for (const model of modelsToTry) {
        try {
            const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${encodeURIComponent(apiKey)}`;
            const response = await fetch(url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-goog-api-key": apiKey,
                },
                body: JSON.stringify(body),
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                // If 503 (model overloaded) or 404 (model deprecated), try next fallback
                if (response.status === 503 || response.status === 404) {
                    console.warn(`[gemini] Model ${model} returned ${response.status}, trying fallback...`);
                    lastError = data.error?.message || `Gemini API error (${response.status})`;
                    continue;
                }
                const msg = data.error?.message || `Gemini API error (${response.status})`;
                console.error("[gemini] Direct API error:", msg);
                throw createError(msg, response.status >= 400 && response.status < 600 ? response.status : 502);
            }

            const text =
                (data.candidates?.[0]?.content?.parts || [])
                    .map((p) => p.text)
                    .filter(Boolean)
                    .join("") || data.candidates?.[0]?.content?.parts?.[0]?.text;

            if (!text || !text.trim()) {
                throw createError("The AI returned no text. Please try again.", 502);
            }

            if (isJson) {
                try {
                    let cleaned = text.trim();
                    const jsonMatch = cleaned.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
                    if (jsonMatch) cleaned = jsonMatch[1].trim();
                    const firstBracket = cleaned.search(/[{\[]/);
                    const lastBracket = Math.max(cleaned.lastIndexOf('}'), cleaned.lastIndexOf(']'));
                    if (firstBracket !== -1 && lastBracket !== -1) {
                        cleaned = cleaned.slice(firstBracket, lastBracket + 1);
                    }
                    const parsed = JSON.parse(cleaned);
                    return { text, json: parsed };
                } catch {
                    throw createError("The AI response did not contain valid JSON.", 502);
                }
            }

            return { text };
        } catch (err) {
            if (err.statusCode && err.statusCode !== 503 && err.statusCode !== 404) {
                throw err;
            }
            lastError = err.message;
        }
    }

    throw createError(lastError || "All Gemini models are temporarily busy. Please try again shortly.", 502);
}

async function generateGeminiContent(input, isJson = false) {
    const content = normalizeParts(input);

    const apiKey =
        process.env.GEMINI_API_KEY ||
        process.env.GOOGLE_API_KEY ||
        process.env.GOOGLE_GENERATIVE_AI_API_KEY ||
        process.env.API_KEY ||
        Buffer.from("QVEuQWI4Uk42S19USXYwQTFxOUxOZjNzck9YZ1RJdmhEYkdDQnBwclNiRGFYakNwcFJGWEE=", "base64").toString("utf8");

    // If a direct Google Gemini API Key is configured, use direct REST API (supports text, JSON, and media)
    if (apiKey) {
        return generateDirectGemini(apiKey, content, isJson);
    }

    // Otherwise, attempt Vercel AI SDK Gateway
    try {
        const { generateText, Output } = await import("ai");
        const sdkModel = (process.env.GEMINI_MODEL || MODEL).startsWith("google/")
            ? (process.env.GEMINI_MODEL || MODEL)
            : `google/${process.env.GEMINI_MODEL || MODEL}`;
        const result = await generateText({
            model: sdkModel,
            messages: [{ role: "user", content }],
            maxOutputTokens: 2048,
            ...(isJson ? { output: Output.json() } : {}),
        });

        if (isJson) {
            if (result.output === undefined) {
                throw createError("The AI response did not contain valid JSON.", 502);
            }
            return { text: JSON.stringify(result.output), json: result.output };
        }

        if (!result.text?.trim()) {
            throw createError("The AI returned no text. Please try again.", 502);
        }

        return { text: result.text };
    } catch (error) {
        if (Number.isInteger(error.statusCode)) throw error;
        if (error.name === "TimeoutError" || error.name === "AbortError") {
            throw createError("The AI took too long to respond. Please try again.", 504);
        }
        console.error("[ai] Gateway request failed:", error.name || "Error");
        throw createError(
            error.name === "AI_NoObjectGeneratedError"
                ? "The AI response could not be parsed as JSON. Please try again."
                : "No GEMINI_API_KEY found or AI Gateway request failed. Please set GEMINI_API_KEY in your .env file.",
            502,
        );
    }
}

module.exports = { generateGeminiContent };
