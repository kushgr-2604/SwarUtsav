const { generateGeminiContent } = require("../../lib/gemini");

exports.handler = async function (event) {
    if (event.httpMethod !== "POST") {
        return {
            statusCode: 405,
            headers: {
                "Content-Type": "application/json",
                "Allow": "POST"
            },
            body: JSON.stringify({ error: "Use POST for Gemini requests." })
        };
    }

    try {
        const body = JSON.parse(event.body || "{}");
        const result = await generateGeminiContent(body.parts ?? body.prompt, body.isJson === true);
        return {
            statusCode: 200,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(result)
        };
    } catch (error) {
        console.error("[netlify] Gemini function error:", error.message);
        return {
            statusCode: error.statusCode || 500,
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ error: error.message || "Gemini request failed." })
        };
    }
};
